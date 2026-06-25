"""
NextAI — provider-agnostic LLM assistant over the LIVE candidate ranking.

The recruiter asks natural-language questions about the current rank list
(e.g. "who are the top 3 for backend?", "which strong candidates can join in
30 days?", "summarise the risks in the top 10"). We build a compact JSON
context from the in-memory ranking and send it to a chat LLM.

Configuration (in the project ``.env`` — the key can be added later):

    NEXTAI_PROVIDER = openai | gemini | anthropic   (default: openai)
    NEXTAI_API_KEY  = <your key>                    (or use a provider env var)
    NEXTAI_MODEL    = <model id>                     (sensible default per provider)
    NEXTAI_BASE_URL = <override>  (OpenAI-compatible only: Groq/OpenRouter/local)

Fallback key env vars also recognised:
    OPENAI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY,
    GEMINI_API_KEY / GOOGLE_API_KEY, ANTHROPIC_API_KEY

Zero extra dependencies — all HTTP via stdlib ``urllib``.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from api import supabase_store as _cfg

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-1.5-flash",
    "anthropic": "claude-3-5-sonnet-20241022",
}

SYSTEM_PROMPT = (
    "You are NextAI, a precise recruiting-analytics assistant embedded in the "
    "Redrob Ranker dashboard. You answer the recruiter's questions about the "
    "CURRENT live candidate ranking, using ONLY the JSON context provided. "
    "Cite candidates by their rank and candidate_id. Be concise and factual; "
    "use short markdown (bullets, bold) when helpful. If the answer is not in "
    "the provided data (e.g. a candidate outside the loaded top set), say so "
    "plainly rather than inventing details. Never fabricate scores or skills."
)


def _provider() -> str:
    return (_cfg.env("NEXTAI_PROVIDER") or "openai").strip().lower()


def _api_key(provider: str) -> str:
    key = _cfg.env("NEXTAI_API_KEY")
    if key:
        return key
    if provider == "openai":
        return (_cfg.env("OPENAI_API_KEY") or _cfg.env("GROQ_API_KEY")
                or _cfg.env("OPENROUTER_API_KEY") or "")
    if provider == "gemini":
        return _cfg.env("GEMINI_API_KEY") or _cfg.env("GOOGLE_API_KEY") or ""
    if provider == "anthropic":
        return _cfg.env("ANTHROPIC_API_KEY") or ""
    return ""


def _model(provider: str) -> str:
    return _cfg.env("NEXTAI_MODEL") or _DEFAULT_MODELS.get(provider, "gpt-4o-mini")


def configured() -> dict:
    provider = _provider()
    return {
        "configured": bool(_api_key(provider)),
        "provider": provider,
        "model": _model(provider),
    }


def status() -> dict:
    return configured()


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
def _post(url: str, payload: dict, headers: dict, timeout: float = 60.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"LLM API error {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"LLM network error: {e.reason}") from e


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
def _build_user_content(question: str, context: dict) -> str:
    ctx = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    return (f"RANKING CONTEXT (JSON):\n{ctx}\n\n"
            f"RECRUITER QUESTION:\n{question}")


def _chat_openai(question, history, context, key, model):
    base = (_cfg.env("NEXTAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-8:]:
        role = "assistant" if h.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": str(h.get("content", ""))})
    messages.append({"role": "user", "content": _build_user_content(question, context)})
    out = _post(f"{base}/chat/completions",
                {"model": model, "messages": messages, "temperature": 0.2},
                {"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    return out["choices"][0]["message"]["content"]


def _chat_gemini(question, history, context, key, model):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={key}")
    contents = []
    for h in history[-8:]:
        role = "model" if h.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": str(h.get("content", ""))}]})
    contents.append({"role": "user",
                     "parts": [{"text": _build_user_content(question, context)}]})
    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {"temperature": 0.2},
    }
    out = _post(url, payload, {"Content-Type": "application/json"})
    return out["candidates"][0]["content"]["parts"][0]["text"]


def _chat_anthropic(question, history, context, key, model):
    messages = []
    for h in history[-8:]:
        role = "assistant" if h.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": str(h.get("content", ""))})
    messages.append({"role": "user", "content": _build_user_content(question, context)})
    payload = {"model": model, "system": SYSTEM_PROMPT, "messages": messages,
               "max_tokens": 1024, "temperature": 0.2}
    out = _post("https://api.anthropic.com/v1/messages", payload,
                {"Content-Type": "application/json", "x-api-key": key,
                 "anthropic-version": "2023-06-01"})
    return out["content"][0]["text"]


_DISPATCH = {"openai": _chat_openai, "gemini": _chat_gemini, "anthropic": _chat_anthropic}


def chat(question: str, history: list, context: dict) -> dict:
    """Answer a question about the live ranking. Returns {answer, provider, model}."""
    provider = _provider()
    key = _api_key(provider)
    model = _model(provider)

    if not context or not context.get("ready"):
        return {"answer": "No ranking is loaded yet. Run a ranking on the "
                          "**Candidates** tab first, then ask me about the results.",
                "provider": provider, "model": model, "configured": bool(key)}

    if not key:
        return {
            "answer": (
                "**NextAI is not configured yet.** Add your LLM API key to the "
                "project `.env` to enable live answers:\n\n"
                "```\nNEXTAI_PROVIDER=openai   # or gemini / anthropic\n"
                "NEXTAI_API_KEY=sk-...\nNEXTAI_MODEL=gpt-4o-mini\n```\n\n"
                "Until then, here is a quick data snapshot I can read locally: "
                f"**{context['stats']['ranked']:,} candidates** ranked for "
                f"**{context.get('role_title') or context.get('role')}**, "
                f"avg score **{context['stats']['avg_score']}**, "
                f"**{context['stats']['strong_matches']}** strong matches, "
                f"**{context['stats']['honeypots']}** honeypots excluded. "
                f"Top pick: rank 1 · {context['leaderboard'][0]['title']} "
                f"({context['leaderboard'][0]['candidate_id']})."
                if context.get("leaderboard") else ""
            ),
            "provider": provider, "model": model, "configured": False,
        }

    fn = _DISPATCH.get(provider, _chat_openai)
    try:
        answer = fn(question, history or [], context, key, model)
        return {"answer": answer, "provider": provider, "model": model,
                "configured": True}
    except Exception as e:
        return {"answer": f"NextAI request failed: {e}", "provider": provider,
                "model": model, "configured": True, "error": str(e)}
