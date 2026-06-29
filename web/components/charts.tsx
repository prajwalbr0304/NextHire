"use client";
import { useState } from "react";

// Shared categorical palette (matches the Council/brand colours).
export const PALETTE = [
  "#10A37F", "#06b6d4", "#10b981", "#f59e0b",
  "#ec4899", "#3b82f6", "#0e9f6e", "#e25950",
];

export const COUNCIL_COLORS: Record<string, string> = {
  semantic_seer: "#10A37F", name_rectifier: "#f59e0b", evidence_scout: "#10b981",
  mask_piercer: "#ec4899", path_reader: "#06b6d4", terrain_master: "#3b82f6",
};

// ---------------------------------------------------------------------------
// Card wrapper
// ---------------------------------------------------------------------------
export function ChartCard({
  title, subtitle, right, children, className = "",
}: {
  title: string; subtitle?: string; right?: React.ReactNode;
  children: React.ReactNode; className?: string;
}) {
  return (
    <div className={`card p-4 sm:p-5 ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold text-ink">{title}</div>
          {subtitle && <div className="text-xs text-ink-faint mt-0.5">{subtitle}</div>}
        </div>
        {right}
      </div>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Vertical bar chart (with hover value)
// ---------------------------------------------------------------------------
export function BarsV({
  data, color = "#10A37F", height = 170, unit = "",
}: { data: { label: string; count: number }[]; color?: string; height?: number; unit?: string }) {
  const max = Math.max(1, ...data.map((d) => d.count));
  const [hover, setHover] = useState<number | null>(null);
  return (
    <div className="mt-4">
      <div className="flex items-end gap-1.5" style={{ height }}>
        {data.map((d, i) => {
          const h = Math.max((d.count / max) * 100, 1.5);
          const active = hover === i;
          return (
            <div key={i} className="flex-1 h-full flex flex-col justify-end items-center group relative"
              onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
              <div className={`text-[10px] font-bold tabular-nums mb-1 transition-opacity ${active ? "opacity-100" : "opacity-0"}`}
                style={{ color }}>{d.count.toLocaleString()}{unit}</div>
              <div className="w-full rounded-t-md transition-all duration-150"
                style={{ height: `${h}%`, background: color, opacity: active ? 1 : 0.82 }} />
            </div>
          );
        })}
      </div>
      <div className="flex gap-1.5 mt-2">
        {data.map((d, i) => (
          <div key={i} className="flex-1 text-[10px] text-ink-faint text-center leading-tight truncate" title={d.label}>
            {d.label}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Smooth area + line chart (good for distributions)
// ---------------------------------------------------------------------------
export function AreaChart({
  data, color = "#10A37F", height = 190,
}: { data: { label: string; count: number }[]; color?: string; height?: number }) {
  const W = 560, H = height, pad = 8;
  const max = Math.max(1, ...data.map((d) => d.count));
  const n = data.length;
  const x = (i: number) => pad + (i * (W - pad * 2)) / Math.max(1, n - 1);
  const y = (v: number) => H - 22 - (v / max) * (H - 40);
  const pts = data.map((d, i) => [x(i), y(d.count)] as const);
  // smooth path via Catmull-Rom-ish midpoints
  const line = pts.map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` :
    `L${p[0]},${p[1]}`)).join(" ");
  const area = `${line} L${x(n - 1)},${H - 22} L${x(0)},${H - 22} Z`;
  const id = `g-${color.replace("#", "")}`;
  return (
    <div className="mt-4">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height }} preserveAspectRatio="none">
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.32" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75, 1].map((g) => (
          <line key={g} x1={pad} x2={W - pad} y1={y(max * g)} y2={y(max * g)}
            stroke="#eef1f5" strokeWidth="1" />
        ))}
        <path d={area} fill={`url(#${id})`} />
        <path d={line} fill="none" stroke={color} strokeWidth="2.5"
          strokeLinejoin="round" strokeLinecap="round" />
        {pts.map((p, i) => (
          <g key={i}>
            <circle cx={p[0]} cy={p[1]} r="3.5" fill="white" stroke={color} strokeWidth="2" />
            <title>{`${data[i].label}: ${data[i].count.toLocaleString()}`}</title>
          </g>
        ))}
      </svg>
      <div className="flex justify-between px-1 mt-1">
        {data.map((d, i) => (
          <div key={i} className="text-[10px] text-ink-faint text-center flex-1 truncate" title={d.label}>{d.label}</div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Horizontal bars (with optional "verified" overlay)
// ---------------------------------------------------------------------------
export function HBars({
  data, color = "#10A37F", showOverlay = false,
}: {
  data: { label: string; count: number; overlay?: number }[];
  color?: string; showOverlay?: boolean;
}) {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div className="mt-4 space-y-2.5">
      {data.map((d, i) => (
        <div key={i} className="flex items-center gap-2 sm:gap-3">
          <div className="w-20 sm:w-28 shrink-0 text-xs text-ink-soft truncate text-right" title={d.label}>{d.label}</div>
          <div className="flex-1 h-5 rounded-md bg-gray-100 overflow-hidden relative">
            <div className="h-full rounded-md absolute inset-y-0 left-0" style={{ width: `${(d.count / max) * 100}%`, background: color, opacity: 0.25 }} />
            {showOverlay && d.overlay != null && (
              <div className="h-full rounded-md absolute inset-y-0 left-0" style={{ width: `${(d.overlay / max) * 100}%`, background: color }} />
            )}
            {!showOverlay && (
              <div className="h-full rounded-md absolute inset-y-0 left-0" style={{ width: `${(d.count / max) * 100}%`, background: color }} />
            )}
          </div>
          <div className="w-14 sm:w-16 shrink-0 text-xs font-semibold tabular-nums text-right">
            {d.count.toLocaleString()}
            {showOverlay && d.overlay != null && <span className="text-ink-faint font-normal"> ·{d.overlay}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Donut chart with legend
// ---------------------------------------------------------------------------
export function DonutChart({
  data, centerLabel,
}: { data: { label: string; count: number }[]; centerLabel?: string }) {
  const total = data.reduce((a, d) => a + d.count, 0) || 1;
  const R = 52, C = 2 * Math.PI * R;
  let offset = 0;
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-5 mt-4">
      <div className="relative h-[136px] w-[136px] shrink-0">
        <svg viewBox="0 0 140 140" className="-rotate-90">
          <circle cx="70" cy="70" r={R} fill="none" stroke="#eef1f5" strokeWidth="16" />
          {data.map((d, i) => {
            const len = (d.count / total) * C;
            const seg = (
              <circle key={i} cx="70" cy="70" r={R} fill="none"
                stroke={PALETTE[i % PALETTE.length]} strokeWidth="16"
                strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-offset} strokeLinecap="butt">
                <title>{`${d.label}: ${d.count.toLocaleString()} (${((d.count / total) * 100).toFixed(1)}%)`}</title>
              </circle>
            );
            offset += len;
            return seg;
          })}
        </svg>
        <div className="absolute inset-0 grid place-items-center">
          <div className="text-center">
            <div className="text-xl font-extrabold leading-none">{total.toLocaleString()}</div>
            <div className="text-[10px] text-ink-faint mt-0.5">{centerLabel || "total"}</div>
          </div>
        </div>
      </div>
      <div className="flex-1 space-y-1.5 min-w-0">
        {data.map((d, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: PALETTE[i % PALETTE.length] }} />
            <span className="text-ink-soft flex-1 truncate" title={d.label}>{d.label}</span>
            <span className="font-semibold tabular-nums">{((d.count / total) * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Radar / spider chart (great for the 6 Council scorers)
// ---------------------------------------------------------------------------
export function Radar({
  axes, color = "#10A37F", size = 260,
}: { axes: { label: string; value: number }[]; color?: string; size?: number }) {
  const cx = size / 2, cy = size / 2, R = size / 2 - 46;
  const n = axes.length;
  const ang = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / n;
  const pt = (i: number, r: number) => [cx + r * Math.cos(ang(i)), cy + r * Math.sin(ang(i))] as const;
  const poly = axes.map((a, i) => pt(i, R * Math.max(0, Math.min(1, a.value))).join(",")).join(" ");
  return (
    <div className="mt-3 flex justify-center">
      <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[300px] h-auto" style={{ aspectRatio: "1 / 1" }}>
        {[0.25, 0.5, 0.75, 1].map((g) => (
          <polygon key={g} points={axes.map((_, i) => pt(i, R * g).join(",")).join(" ")}
            fill="none" stroke="#e3e8ee" strokeWidth="1" />
        ))}
        {axes.map((_, i) => {
          const [ex, ey] = pt(i, R);
          return <line key={i} x1={cx} y1={cy} x2={ex} y2={ey} stroke="#e3e8ee" strokeWidth="1" />;
        })}
        <polygon points={poly} fill={color} fillOpacity="0.18" stroke={color} strokeWidth="2.5" strokeLinejoin="round" />
        {axes.map((a, i) => {
          const [px, py] = pt(i, R * Math.max(0, Math.min(1, a.value)));
          return <circle key={i} cx={px} cy={py} r="3.5" fill="white" stroke={color} strokeWidth="2" />;
        })}
        {axes.map((a, i) => {
          const [lx, ly] = pt(i, R + 22);
          return (
            <text key={i} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle"
              className="fill-ink-muted" style={{ fontSize: 9, fontWeight: 600 }}>
              {a.label.length > 16 ? a.label.slice(0, 15) + "…" : a.label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Heatmap (skills × proficiency)
// ---------------------------------------------------------------------------
export function Heatmap({
  rows, cols, matrix, base = "16,163,127",
}: { rows: string[]; cols: string[]; matrix: number[][]; base?: string }) {
  const max = Math.max(1, ...matrix.flat());
  return (
    <div className="mt-4 overflow-x-auto">
      <div className="inline-grid gap-1 min-w-full"
        style={{ gridTemplateColumns: `140px repeat(${cols.length}, minmax(64px, 1fr))` }}>
        <div />
        {cols.map((c) => (
          <div key={c} className="text-[10px] font-semibold text-ink-muted text-center pb-1 uppercase tracking-wide">{c}</div>
        ))}
        {rows.map((r, ri) => (
          <FragmentRow key={r} label={r} values={matrix[ri]} max={max} base={base} />
        ))}
      </div>
    </div>
  );
}

function FragmentRow({ label, values, max, base }: { label: string; values: number[]; max: number; base: string }) {
  return (
    <>
      <div className="text-xs text-ink-soft truncate flex items-center pr-2" title={label}>{label}</div>
      {values.map((v, ci) => {
        const alpha = v === 0 ? 0.04 : 0.12 + (v / max) * 0.82;
        const light = alpha > 0.55;
        return (
          <div key={ci} className="h-9 rounded-md grid place-items-center text-[11px] font-semibold tabular-nums"
            style={{ background: `rgba(${base},${alpha})`, color: light ? "white" : "#3c4257" }}
            title={`${label} · ${v.toLocaleString()}`}>
            {v > 0 ? v.toLocaleString() : ""}
          </div>
        );
      })}
    </>
  );
}

// ---------------------------------------------------------------------------
// Funnel chart
// ---------------------------------------------------------------------------
export function Funnel({ data }: { data: { stage: string; count: number }[] }) {
  const top = Math.max(1, data[0]?.count ?? 1);
  return (
    <div className="mt-4 space-y-1.5">
      {data.map((d, i) => {
        const w = Math.max((d.count / top) * 100, 6);
        const pct = ((d.count / top) * 100).toFixed(1);
        return (
          <div key={i} className="flex items-center gap-2 sm:gap-3">
            <div className="w-20 sm:w-32 shrink-0 text-xs text-ink-soft text-right">{d.stage}</div>
            <div className="flex-1 flex justify-center">
              <div className="h-9 rounded-md grid place-items-center text-white text-xs font-bold transition-all"
                style={{ width: `${w}%`, background: PALETTE[i % PALETTE.length], minWidth: 60 }}>
                {d.count.toLocaleString()}
              </div>
            </div>
            <div className="w-10 sm:w-12 shrink-0 text-xs text-ink-faint tabular-nums">{pct}%</div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Horizontal stacked bar (e.g. company background)
// ---------------------------------------------------------------------------
export function StackedBar({ data }: { data: { label: string; count: number; color: string }[] }) {
  const total = data.reduce((a, d) => a + d.count, 0) || 1;
  return (
    <div className="mt-4">
      <div className="h-6 w-full rounded-lg overflow-hidden flex">
        {data.map((d, i) => (
          <div key={i} className="h-full first:rounded-l-lg last:rounded-r-lg"
            style={{ width: `${(d.count / total) * 100}%`, background: d.color }}
            title={`${d.label}: ${d.count.toLocaleString()}`} />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3">
        {data.map((d, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: d.color }} />
            <span className="text-ink-soft">{d.label}</span>
            <span className="font-semibold tabular-nums">{d.count.toLocaleString()}</span>
            <span className="text-ink-faint text-xs">({((d.count / total) * 100).toFixed(0)}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small KPI tile
// ---------------------------------------------------------------------------
export function StatTile({
  label, value, sub, accent = "#10A37F", icon,
}: { label: string; value: string; sub?: string; accent?: string; icon?: React.ReactNode }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-ink-muted text-[13px] font-medium">
        {icon && <span style={{ color: accent }}>{icon}</span>}{label}
      </div>
      <div className="mt-2 text-[26px] font-extrabold tracking-tight" style={{ color: accent }}>{value}</div>
      {sub && <div className="text-xs text-ink-faint mt-0.5">{sub}</div>}
    </div>
  );
}
