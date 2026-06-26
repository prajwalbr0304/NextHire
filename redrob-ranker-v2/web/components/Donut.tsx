"use client";
import type { WeightPct } from "@/lib/types";

const COLORS: Record<string, string> = {
  semantic_seer: "#10A37F", name_rectifier: "#f59e0b", evidence_scout: "#10b981",
  mask_piercer: "#ec4899", path_reader: "#06b6d4", terrain_master: "#3b82f6",
};

export default function Donut({ weights }: { weights: WeightPct[] }) {
  const total = weights.reduce((a, w) => a + w.pct, 0) || 100;
  const R = 52, C = 2 * Math.PI * R;
  let offset = 0;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="font-semibold">Scoring weights</div>
        <div className="text-xs text-ink-faint">Σ 100%</div>
      </div>
      <div className="flex items-center gap-5">
        <div className="relative h-[136px] w-[136px] shrink-0">
          <svg viewBox="0 0 140 140" className="-rotate-90">
            <circle cx="70" cy="70" r={R} fill="none" stroke="#eef1f5" strokeWidth="16" />
            {weights.map((w) => {
              const frac = w.pct / total;
              const len = frac * C;
              const seg = (
                <circle key={w.key} cx="70" cy="70" r={R} fill="none"
                  stroke={COLORS[w.key] ?? "#999"} strokeWidth="16"
                  strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-offset}
                  strokeLinecap="butt" />
              );
              offset += len;
              return seg;
            })}
          </svg>
          <div className="absolute inset-0 grid place-items-center">
            <div className="text-center">
              <div className="text-2xl font-extrabold leading-none">100</div>
              <div className="text-[11px] text-ink-faint">%</div>
            </div>
          </div>
        </div>
        <div className="flex-1 space-y-2">
          {weights.map((w) => (
            <div key={w.key} className="flex items-center gap-2 text-sm">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: COLORS[w.key] ?? "#999" }} />
              <span className="text-ink-soft flex-1">{w.label}</span>
              <span className="font-semibold tabular-nums">{w.pct}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
