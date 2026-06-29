"""
Stage [0a] — Data loading.

Streams the 100K-candidate JSONL pool with the fastest available JSON parser
(orjson if present, else stdlib json). Returns plain Python dicts so every
downstream module stays dependency-light and CPU-only.
"""
from __future__ import annotations

import gzip
import io
import os
from typing import Iterator, List

try:
    import orjson as _json

    def _loads(b):
        return _json.loads(b)
except Exception:  # pragma: no cover - fallback
    import json as _json

    def _loads(b):
        return _json.loads(b)


def _open_any(path: str):
    """Open a plain or gzipped JSONL file transparently."""
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def iter_candidates(path: str) -> Iterator[dict]:
    """Yield candidate dicts one at a time (memory-friendly)."""
    with _open_any(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield _loads(line)
                continue
            except Exception:
                pass
            # Recover a line with stray text wrapped around the JSON object rather
            # than silently dropping a real candidate. (An earlier revision of the
            # pool shipped one record prefixed with junk before the '{', which a
            # strict json.loads rejects.) Re-parse the substring spanning the first
            # '{' to the last '}'; if that still fails the line is skipped below.
            a, b = line.find("{"), line.rfind("}")
            if a != -1 and b > a:
                try:
                    yield _loads(line[a:b + 1])
                    continue
                except Exception:
                    pass
            # genuinely unparseable -> skip rather than crash a long run
            continue


def _looks_like_json_array(path: str) -> bool:
    """Peek the first non-whitespace byte to detect a pretty-printed JSON array."""
    try:
        with _open_any(path) as f:
            while True:
                ch = f.read(1)
                if ch == "":
                    return False
                if not ch.isspace():
                    return ch == "["
    except Exception:
        return False


def load_candidates(path: str, limit: int | None = None) -> List[dict]:
    """Load candidates from JSONL (one object per line) OR a JSON array file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Candidate file not found: {path}")

    # JSON array (e.g. sample_candidates.json) — parse the whole document.
    if _looks_like_json_array(path):
        with _open_any(path) as f:
            data = _json.loads(f.read())
        if isinstance(data, list):
            return data[:limit] if limit is not None else data
        return []

    # JSONL — stream line by line.
    out: List[dict] = []
    for c in iter_candidates(path):
        out.append(c)
        if limit is not None and len(out) >= limit:
            break
    return out
