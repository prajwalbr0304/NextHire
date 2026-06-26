"use client";
import type { Compliance, FairnessAttr } from "@/lib/types";
import { ChartCard, StatTile } from "./charts";
import { Empty } from "./Views";

const ATTR_LABEL: Record<string, string> = {
  region: "Region", institution_tier: "Institution tier",
};

function StatusBanner({ c }: { c: Compliance }) {
  const ok = c.overall.passes;
  return (
    <div className={`card p-5 border-l-4 ${ok ? "border-l-positive" : "border-l-warn"}`}>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className={`h-10 w-10 rounded-xl grid place-items-center ${ok ? "bg-positive/10 text-positive" : "bg-amber-50 text-warn"}`}>
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              {ok ? <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
                : <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />}
            </svg>
          </div>
          <div>
            <div className="font-semibold text-ink">{ok ? "No statistical bias detected" : `${c.overall.n_flags} bias signal(s) flagged`}</div>
            <div className="text-sm text-ink-muted">{c.overall.summary}</div>
          </div>
        </div>
        <span className="pill bg-brand-wash text-brand-dark">EU AI Act · Annex III high-risk</span>
      </div>
    </div>
  );
}

function BiasDetection({ c }: { c: Compliance }) {
  if (!c.bias_flags.length) {
    return (
      <ChartCard title="Bias detection" subtitle="Automated scan against audited protected/proxy attributes.">
        <div className="mt-4 rounded-lg border border-positive/20 bg-positive/5 px-4 py-3 text-sm text-ink-soft">
          All audited attributes pass the 4/5ths rule and show no material score gaps. No action required.
        </div>
      </ChartCard>
    );
  }
  return (
    <ChartCard title="Bias detection" subtitle="Potential disparities surfaced for mandatory human review (Article 14).">
      <div className="mt-4 space-y-2.5">
        {c.bias_flags.map((f, i) => {
          const tone = f.severity === "high" ? "danger" : "warn";
          return (
            <div key={i} className={`rounded-lg border px-4 py-3 ${tone === "danger" ? "border-danger/20 bg-danger/5" : "border-warn/20 bg-amber-50/60"}`}>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`pill ${tone === "danger" ? "bg-danger/15 text-danger" : "bg-amber-100 text-warn"}`}>{f.severity} severity</span>
                <span className="font-semibold text-sm">{f.metric}</span>
                <span className="text-xs text-ink-faint">{f.attribute} · value {f.value}</span>
              </div>
              <div className="text-sm text-ink-soft mt-1.5">{f.message}</div>
            </div>
          );
        })}
      </div>
    </ChartCard>
  );
}

function MetricsTable({ attr, m }: { attr: string; m: FairnessAttr }) {
  const groups = Object.entries(m.groups)
    .sort((a, b) => (b[1].n_pool ?? 0) - (a[1].n_pool ?? 0)).slice(0, 8);
  const maxRate = Math.max(0.0001, ...groups.map(([, v]) => v.selection_rate));
  return (
    <ChartCard title={ATTR_LABEL[attr] ?? attr} subtitle={`Disparate impact, selection rates and mean scores by ${ATTR_LABEL[attr]?.toLowerCase() ?? attr}.`}
      right={<span className={`pill ${m.passes_four_fifths ? "bg-positive/10 text-positive" : "bg-amber-50 text-warn"}`}>DI {m.disparate_impact_ratio} · {m.passes_four_fifths ? "pass" : "review"}</span>}>
      <div className="grid grid-cols-3 gap-2 mt-4 mb-3">
        <div className="rounded-lg bg-gray-50 border border-line px-3 py-2">
          <div className="text-[11px] text-ink-faint">Disparate impact</div>
          <div className={`text-lg font-bold tabular-nums ${m.passes_four_fifths ? "text-positive" : "text-warn"}`}>{m.disparate_impact_ratio}</div>
        </div>
        <div className="rounded-lg bg-gray-50 border border-line px-3 py-2">
          <div className="text-[11px] text-ink-faint">Parity diff</div>
          <div className="text-lg font-bold tabular-nums text-ink">{((m.statistical_parity_diff ?? 0) * 100).toFixed(1)}%</div>
        </div>
        <div className="rounded-lg bg-gray-50 border border-line px-3 py-2">
          <div className="text-[11px] text-ink-faint">Score gap</div>
          <div className="text-lg font-bold tabular-nums text-ink">{m.score_gap ?? 0} pt</div>
        </div>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-ink-faint text-[11px] uppercase tracking-wide border-b border-line">
            <th className="text-left font-semibold py-1.5">Group</th>
            <th className="text-right font-semibold py-1.5">Pool</th>
            <th className="text-left font-semibold py-1.5 pl-3 w-1/3">Selection rate</th>
            <th className="text-right font-semibold py-1.5">Avg score</th>
          </tr>
        </thead>
        <tbody>
          {groups.map(([g, v]) => (
            <tr key={g} className="border-b border-line/60">
              <td className="py-1.5 truncate max-w-[120px]" title={g}>{g || "—"}</td>
              <td className="text-right tabular-nums text-ink-muted">{(v.pool_share * 100).toFixed(1)}%</td>
              <td className="py-1.5 pl-3">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                    <div className="h-full rounded-full bg-brand" style={{ width: `${(v.selection_rate / maxRate) * 100}%` }} />
                  </div>
                  <span className="tabular-nums text-xs w-10 text-right">{(v.selection_rate * 100).toFixed(0)}%</span>
                </div>
              </td>
              <td className="text-right tabular-nums font-medium">{v.avg_score ?? 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </ChartCard>
  );
}

function ScoringExplainer({ c }: { c: Compliance }) {
  const s = c.scoring;
  const maxAvg = Math.max(0.0001, ...s.council.map((x) => x.avg));
  return (
    <ChartCard title="Explainable scoring" subtitle="Exactly how each composite score is produced — fully inspectable per EU AI Act Art. 13.">
      <div className="mt-3 rounded-lg bg-ink text-white/90 px-4 py-3 font-mono text-xs overflow-x-auto">{s.formula}</div>
      <p className="text-sm text-ink-soft mt-3">{s.explanation}</p>

      <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mt-5 mb-2">Additive Council scorers (weighted)</div>
      <div className="space-y-2.5">
        {s.council.map((sc) => (
          <div key={sc.key} className="rounded-lg border border-line p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-sm">{sc.label}</span>
              <span className="pill bg-brand-wash text-brand-dark">weight {sc.weight}%</span>
            </div>
            <div className="text-xs text-ink-muted mt-1">{sc.description}</div>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-[11px] text-ink-faint w-16">avg {Math.round(sc.avg * 100)}%</span>
              <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                <div className="h-full rounded-full bg-brand" style={{ width: `${(sc.avg / maxAvg) * 100}%` }} />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mt-5 mb-2">Multiplicative gates</div>
      <div className="grid sm:grid-cols-3 gap-2.5">
        {s.gates.map((g) => (
          <div key={g.name} className="rounded-lg border border-line p-3">
            <div className="font-semibold text-sm">{g.name}</div>
            <div className="text-[11px] text-brand font-mono mt-0.5">{g.type}</div>
            <div className="text-xs text-ink-muted mt-1.5">{g.detail}</div>
          </div>
        ))}
      </div>
    </ChartCard>
  );
}

export default function GovernanceView({ c }: { c: Compliance | null }) {
  if (!c || !c.scoring) return <Empty />;
  const attrs = Object.entries(c.metrics);
  return (
    <div className="space-y-4">
      <StatusBanner c={c} />

      {/* Fairness metric KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        {attrs.map(([attr, m]) => (
          <StatTile key={attr} label={`${ATTR_LABEL[attr] ?? attr} · DI`} value={String(m.disparate_impact_ratio)}
            sub={m.passes_four_fifths ? "passes 4/5ths rule" : "below 0.80 threshold"}
            accent={m.passes_four_fifths ? "#0e9f6e" : "#d97706"} />
        ))}
        <StatTile label="Bias flags" value={String(c.overall.n_flags)} sub="for human review" accent={c.overall.n_flags ? "#e25950" : "#0e9f6e"} />
        <StatTile label="Honeypots excluded" value={String((c.audit as any).honeypots_detected ?? 0)} sub="integrity warden" accent="#3b82f6" />
      </div>

      <BiasDetection c={c} />

      {/* Fairness metrics */}
      <div className="grid lg:grid-cols-2 gap-4">
        {attrs.map(([attr, m]) => <MetricsTable key={attr} attr={attr} m={m} />)}
      </div>

      <ScoringExplainer c={c} />

      {/* Compliance audit log */}
      <ChartCard title="Immutable run log" subtitle="Logging & traceability record (EU AI Act Art. 12).">
        <pre className="text-xs bg-gray-50 border border-line rounded-lg p-4 overflow-auto font-mono text-ink-soft mt-3">
{JSON.stringify(c.audit, null, 2)}
        </pre>
      </ChartCard>
    </div>
  );
}
