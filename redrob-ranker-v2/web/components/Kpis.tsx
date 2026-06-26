"use client";
import { IconUsers, IconSpark, IconAlert, IconClock, IconBolt } from "./icons";
import type { Summary } from "@/lib/types";

function Kpi({ icon, label, value, sub, tone = "ink" }: {
  icon: React.ReactNode; label: string; value: string; sub: string; tone?: string;
}) {
  const toneCls: Record<string, string> = {
    ink: "text-ink", green: "text-positive", amber: "text-warn", brand: "text-brand",
  };
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-ink-muted text-[13px] font-medium">
        <span className="text-ink-faint">{icon}</span>{label}
      </div>
      <div className={`mt-2 text-[28px] font-extrabold tracking-tight ${toneCls[tone]}`}>{value}</div>
      <div className="text-xs text-ink-faint mt-0.5">{sub}</div>
    </div>
  );
}

export default function Kpis({ s }: { s: Summary }) {
  const i = (C: any) => <C className="h-4 w-4" />;
  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] gap-3.5">
      <Kpi icon={i(IconUsers)} label="Candidates ranked" value={s.ranked.toLocaleString()}
        sub={`of ${s.ingested.toLocaleString()} ingested`} />
      <Kpi icon={i(IconSpark)} label="Strong matches" value={s.strong_matches.toLocaleString()}
        sub="score ≥ 85 · tier 1" tone="green" />
      <Kpi icon={i(IconAlert)} label="Honeypots flagged" value={String(s.honeypots)}
        sub="excluded from ranking" tone="amber" />
      <Kpi icon={i(IconClock)} label={`Notice ≤ 30 days`} value={`${s.notice_pct}%`}
        sub="of top 100" />
      <Kpi icon={i(IconBolt)} label="Runtime" value={`${s.runtime}s`}
        sub="CPU · offline" tone="brand" />
    </div>
  );
}
