"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ChatMessage, NextAiStatus } from "@/lib/types";
import { IconSend, IconBolt, IconSpark } from "./icons";

const SUGGESTIONS = [
  "Who are the top 3 candidates and why?",
  "Which strong candidates can join within 30 days?",
  "Summarise the key risks in the top 10.",
  "Who has the strongest verified skills for this role?",
];

function escapeHtml(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function inlineFmt(s: string) {
  let h = escapeHtml(s);
  h = h.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  h = h.replace(/`([^`]+)`/g, '<code class="bg-black/10 px-1 py-0.5 rounded text-[12px] font-mono">$1</code>');
  return h;
}

function Markdown({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div className="space-y-1 text-sm leading-relaxed">
      {lines.map((line, i) => {
        const t = line.trimEnd();
        if (!t.trim()) return <div key={i} className="h-1.5" />;
        const bullet = /^\s*[-*]\s+/.test(t);
        const numbered = /^\s*\d+\.\s+/.test(t);
        const content = bullet ? t.replace(/^\s*[-*]\s+/, "") : numbered ? t.replace(/^\s*\d+\.\s+/, "") : t;
        if (bullet || numbered) {
          return (
            <div key={i} className="flex gap-2">
              <span className="text-brand mt-0.5 shrink-0">{numbered ? `${t.match(/^\s*(\d+)\./)?.[1]}.` : "•"}</span>
              <span dangerouslySetInnerHTML={{ __html: inlineFmt(content) }} />
            </div>
          );
        }
        return <p key={i} dangerouslySetInnerHTML={{ __html: inlineFmt(t) }} />;
      })}
    </div>
  );
}

export default function NextAiView({ ready }: { ready: boolean }) {
  const [status, setStatus] = useState<NextAiStatus | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { api.nextaiStatus().then(setStatus).catch(() => {}); }, []);
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [messages, sending]);

  const send = async (q: string) => {
    const question = q.trim();
    if (!question || sending) return;
    const history = messages.slice(-8);
    setMessages((m) => [...m, { role: "user", content: question }]);
    setInput("");
    setSending(true);
    try {
      const r = await api.nextaiChat(question, history);
      setMessages((m) => [...m, { role: "assistant", content: r.answer }]);
      if (status) setStatus({ ...status, configured: r.configured });
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: `Request failed: ${e.message || e}` }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="grid lg:grid-cols-[1fr_300px] gap-4">
      {/* Chat */}
      <div className="card flex flex-col h-[calc(100vh-220px)] min-h-[460px] overflow-hidden">
        <div className="px-5 py-3 border-b border-line flex items-center justify-between bg-gradient-to-r from-indigo-500/5 to-purple-500/5">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 grid place-items-center text-white shadow-sm">
              <IconBolt className="h-5 w-5" />
            </div>
            <div>
              <div className="font-semibold leading-tight">NextAI Assistant</div>
              <div className="text-xs text-ink-faint">
                {ready ? <span className="text-positive">● Connected to live ranking</span> : <span className="text-warn">● No ranking loaded</span>}
              </div>
            </div>
          </div>
          {status && (
            <span className={`pill ${status.configured ? "bg-positive/10 text-positive" : "bg-amber-50 text-warn"}`}>
              {status.configured ? `${status.provider} · ${status.model}` : "LLM key not set"}
            </span>
          )}
        </div>

        <div ref={scrollRef} className="flex-1 overflow-auto px-5 py-5 space-y-4">
          {messages.length === 0 && (
            <div className="h-full grid place-items-center text-center">
              <div className="max-w-sm">
                <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 grid place-items-center text-white mx-auto mb-3">
                  <IconSpark className="h-6 w-6" />
                </div>
                <div className="font-semibold text-ink">Ask anything about your rank list</div>
                <div className="text-sm text-ink-muted mt-1">
                  NextAI reads the live leaderboard from the Candidates tab and answers questions about candidates, scores, skills and fit.
                </div>
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[82%] rounded-2xl px-4 py-2.5 ${m.role === "user"
                ? "bg-brand text-white rounded-br-sm"
                : "bg-gray-50 border border-line text-ink-soft rounded-bl-sm"}`}>
                {m.role === "user" ? <span className="text-sm">{m.content}</span> : <Markdown text={m.content} />}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-gray-50 border border-line rounded-2xl rounded-bl-sm px-4 py-3 flex gap-1.5">
                {[0, 1, 2].map((d) => (
                  <span key={d} className="h-2 w-2 rounded-full bg-ink-faint animate-bounce" style={{ animationDelay: `${d * 0.15}s` }} />
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-line p-3">
          <div className="flex items-end gap-2">
            <textarea
              value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
              rows={1} placeholder={ready ? "Ask about the ranked candidates…" : "Run a ranking first, then ask away…"}
              className="flex-1 resize-none bg-white border border-line rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 max-h-32"
            />
            <button onClick={() => send(input)} disabled={sending || !input.trim()}
              className="btn-primary h-[42px] px-4 disabled:opacity-50 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700">
              <IconSend className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Side panel */}
      <div className="space-y-4">
        <div className="card p-4">
          <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mb-2.5">Suggested questions</div>
          <div className="space-y-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)} disabled={sending}
                className="w-full text-left text-sm px-3 py-2 rounded-lg border border-line hover:border-brand/40 hover:bg-brand-wash transition disabled:opacity-50">
                {s}
              </button>
            ))}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mb-2">How it works</div>
          <p className="text-xs text-ink-muted leading-relaxed">
            NextAI is grounded in your current ranking — the top candidates, their scores, verified skills and Council
            breakdown are sent as context with every question, so answers stay factual.
          </p>
          {status && !status.configured && (
            <div className="mt-3 rounded-lg bg-amber-50 border border-warn/20 px-3 py-2 text-xs text-ink-soft">
              Add <code className="font-mono">NEXTAI_API_KEY</code> to <code className="font-mono">.env</code> to enable live AI answers.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
