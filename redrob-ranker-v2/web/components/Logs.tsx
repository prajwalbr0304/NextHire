"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Log } from "@/lib/types";

const LEVEL: Record<string, { dot: string; text: string; label: string }> = {
  info: { dot: "#60a5fa", text: "#cbd5e1", label: "INFO" },
  success: { dot: "#34d399", text: "#a7f3d0", label: " OK " },
  warn: { dot: "#fbbf24", text: "#fde68a", label: "WARN" },
  error: { dot: "#f87171", text: "#fecaca", label: "ERR " },
};

export default function Logs({ logs, running }: { logs: Log[]; running: boolean }) {
  const [filter, setFilter] = useState<"all" | "backend" | "frontend">("all");
  const bodyRef = useRef<HTMLDivElement>(null);
  const atBottom = useRef(true);

  const shown = useMemo(
    () => logs.filter((l) => filter === "all" || l.source === filter),
    [logs, filter]
  );

  useEffect(() => {
    const el = bodyRef.current;
    if (el && atBottom.current) el.scrollTop = el.scrollHeight;
  }, [shown.length]);

  const counts = useMemo(() => ({
    backend: logs.filter((l) => l.source === "backend").length,
    frontend: logs.filter((l) => l.source === "frontend").length,
  }), [logs]);

  return (
    <div className="rounded-xl overflow-hidden border border-[#1e293b] shadow-card"
      style={{ background: "#0b1220" }}>
      {/* title bar */}
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-[#1e293b]"
        style={{ background: "#0d1526" }}>
        <div className="flex gap-1.5">
          <span className="h-3 w-3 rounded-full bg-[#ff5f57]" />
          <span className="h-3 w-3 rounded-full bg-[#febc2e]" />
          <span className="h-3 w-3 rounded-full bg-[#28c840]" />
        </div>
        <span className="font-mono text-xs text-slate-400 ml-1">council@redrob: ~/system.log</span>
        <div className="ml-auto flex items-center gap-3">
          {running && (
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" /> LIVE
            </span>
          )}
          <div className="flex items-center rounded-md border border-[#1e293b] overflow-hidden text-[11px] font-medium">
            {(["all", "backend", "frontend"] as const).map((f) => (
              <button key={f} onClick={() => setFilter(f)}
                className={`px-2.5 py-1 capitalize transition ${
                  filter === f ? "bg-brand text-white" : "text-slate-400 hover:text-slate-200"}`}>
                {f}{f !== "all" ? ` ${f === "backend" ? counts.backend : counts.frontend}` : ` ${logs.length}`}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* log body */}
      <div ref={bodyRef}
        onScroll={(e) => {
          const el = e.currentTarget;
          atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
        }}
        className="font-mono text-[12.5px] leading-relaxed px-4 py-3 h-[560px] overflow-y-auto">
        {shown.length === 0 ? (
          <div className="text-slate-500 py-6 text-center">
            No activity yet. Drop a dataset and press <span className="text-slate-300">Rank candidates</span> to see the system work.
          </div>
        ) : shown.map((l, i) => {
          const lv = LEVEL[l.level] ?? LEVEL.info;
          const sep = l.msg.startsWith("─");
          if (sep) {
            return (
              <div key={i} className="flex items-center gap-2 my-2 text-slate-600">
                <span className="flex-1 border-t border-dashed border-[#1e293b]" />
                <span className="text-[10px] uppercase tracking-widest text-slate-500">{l.msg.replace(/─/g, "").trim()}</span>
                <span className="flex-1 border-t border-dashed border-[#1e293b]" />
              </div>
            );
          }
          return (
            <div key={i} className="flex items-start gap-2.5 py-[3px] hover:bg-white/[0.03] rounded px-1 -mx-1">
              <span className="text-slate-600 tabular-nums shrink-0">{l.ts}</span>
              <span className="shrink-0 text-[10px] font-bold px-1.5 rounded mt-[2px]"
                style={{
                  color: l.source === "backend" ? "#67e8f9" : "#6ee7b7",
                  background: l.source === "backend" ? "rgba(103,232,249,.1)" : "rgba(110,231,183,.1)",
                }}>
                {l.source === "backend" ? "BE" : "FE"}
              </span>
              <span className="shrink-0 font-bold tabular-nums" style={{ color: lv.dot }}>{lv.label}</span>
              <span className="min-w-0 break-words" style={{ color: lv.text }}>{l.msg}</span>
            </div>
          );
        })}
      </div>

      {/* footer */}
      <div className="px-4 py-2 border-t border-[#1e293b] flex items-center justify-between text-[11px] text-slate-500 font-mono"
        style={{ background: "#0d1526" }}>
        <span>{shown.length} events</span>
        <span>frontend ↔ /api proxy ↔ FastAPI ↔ Council of Nine (src/)</span>
      </div>
    </div>
  );
}
