"use client";
import type { Analytics, Compliance, Honeypots, JobIntent } from "@/lib/types";

function BarChart({ data, color = "#10A37F" }: { data: { bucket: string; count: number }[]; color?: string }) {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div className="mt-3">
      <div className="h-40 flex items-end gap-2">
        {data.map((d) => (
          <div key={d.bucket} className="flex-1 h-full flex items-end" title={`${d.count.toLocaleString()}`}>
            <div className="w-full rounded-t-md transition-all"
              style={{ height: `${Math.max((d.count / max) * 100, 1.5)}%`, background: color, opacity: 0.85 }} />
          </div>
        ))}
      </div>
      <div className="flex gap-2 mt-1.5">
        {data.map((d) => (
          <div key={d.bucket} className="flex-1 text-[10px] text-ink-faint text-center leading-tight">{d.bucket}</div>
        ))}
      </div>
    </div>
  );
}

export function AnalyticsView({ a }: { a: Analytics }) {
  if (!a?.score_hist) return <Empty />;
  const cmp = a.company;
  const cmpTotal = cmp.product + cmp.services + cmp.mixed || 1;
  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <div className="card p-5">
        <div className="font-semibold">Relevance score distribution</div>
        <div className="text-xs text-ink-faint">A healthy power-law: few elite, many marginal.</div>
        <BarChart data={a.score_hist} />
      </div>
      <div className="card p-5">
        <div className="font-semibold">Experience (years) distribution</div>
        <div className="text-xs text-ink-faint">Where the ranked pool sits on seniority.</div>
        <BarChart data={a.yoe_hist} color="#06b6d4" />
      </div>
      <div className="card p-5">
        <div className="font-semibold mb-3">Company background</div>
        {[["Product-company", cmp.product, "#10b981"], ["Services-only", cmp.services, "#f59e0b"], ["Mixed / other", cmp.mixed, "#94a3b8"]].map(
          ([label, val, c]) => (
            <div key={label as string} className="mb-2.5">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-ink-soft">{label as string}</span>
                <span className="font-semibold tabular-nums">{(val as number).toLocaleString()}</span>
              </div>
              <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${((val as number) / cmpTotal) * 100}%`, background: c as string }} />
              </div>
            </div>
          ))}
      </div>
      <div className="card p-5">
        <div className="font-semibold mb-3">Average Council scorer (all ranked)</div>
        {a.council_avg.map((s) => (
          <div key={s.key} className="mb-2.5">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-ink-soft">{s.label}</span>
              <span className="font-semibold tabular-nums">{(s.avg * 100).toFixed(0)}%</span>
            </div>
            <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
              <div className="h-full rounded-full bg-brand" style={{ width: `${s.avg * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ComplianceView({ c }: { c: Compliance }) {
  if (!c?.fairness) return <Empty />;
  return (
    <div className="grid lg:grid-cols-2 gap-4">
      {Object.entries(c.fairness).map(([attr, d]) => (
        <div key={attr} className="card p-5">
          <div className="flex items-center justify-between">
            <div className="font-semibold capitalize">{attr.replace("_", " ")}</div>
            <span className={`pill ${d.passes_four_fifths ? "bg-positive/10 text-positive" : "bg-amber-50 text-warn"}`}>
              DI {d.disparate_impact_ratio} · {d.passes_four_fifths ? "pass" : "review"}
            </span>
          </div>
          <table className="w-full mt-3 text-sm">
            <thead><tr className="text-ink-faint text-xs uppercase tracking-wide">
              <th className="text-left font-semibold py-1">Group</th>
              <th className="text-right font-semibold py-1">Pool</th>
              <th className="text-right font-semibold py-1">Selected</th>
              <th className="text-right font-semibold py-1">Sel. rate</th>
            </tr></thead>
            <tbody>
              {Object.entries(d.groups).slice(0, 8).map(([g, v]) => (
                <tr key={g} className="border-t border-line">
                  <td className="py-1.5">{g || "—"}</td>
                  <td className="text-right tabular-nums">{(v.pool_share * 100).toFixed(1)}%</td>
                  <td className="text-right tabular-nums">{(v.selected_share * 100).toFixed(1)}%</td>
                  <td className="text-right tabular-nums">{(v.selection_rate * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      <div className="card p-5 lg:col-span-2">
        <div className="font-semibold mb-2">Immutable run log · EU AI Act Art. 12</div>
        <pre className="text-xs bg-gray-50 border border-line rounded-lg p-4 overflow-auto font-mono text-ink-soft">
{JSON.stringify(c.audit, null, 2)}
        </pre>
      </div>
    </div>
  );
}

export function IntegrityView({ h }: { h: Honeypots }) {
  if (!h) return <Empty />;
  return (
    <div className="card p-5">
      <div className="font-semibold mb-1">Integrity Warden — exclusion log</div>
      <div className="text-sm text-ink-faint mb-4">
        {h.total} profiles flagged as logically impossible and excluded{h.items.length < h.total ? ` (showing first ${h.items.length})` : ""}.
      </div>
      <div className="space-y-2.5">
        {h.items.map((it) => (
          <div key={it.candidate_id} className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="pill bg-danger/15 text-danger">Blocked</span>
              <span className="font-semibold text-sm">{it.title}</span>
              <span className="text-xs text-ink-faint">{it.candidate_id}</span>
            </div>
            <div className="text-sm text-ink-soft mt-1.5">{it.reasons.join("; ")}</div>
          </div>
        ))}
        {h.items.length === 0 && <div className="text-ink-faint text-sm">No honeypots flagged.</div>}
      </div>
    </div>
  );
}

function Pills({ items, tone }: { items: string[]; tone: "pos" | "neg" | "neutral" }) {
  const cls = tone === "pos" ? "bg-positive/10 text-positive"
    : tone === "neg" ? "bg-danger/10 text-danger" : "bg-gray-100 text-ink-muted";
  return <div className="flex flex-wrap gap-1.5">{items.map((s) => <span key={s} className={`pill ${cls}`}>{s}</span>)}</div>;
}

export function JobIntentView({ j }: { j: JobIntent }) {
  if (!j) return <Empty />;
  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="font-semibold">{j.role_title}</div>
        <div className="text-xs text-ink-faint mt-0.5 mb-3">How the engine interpreted the role.</div>
        <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mb-2">Must-have capabilities</div>
        <Pills items={j.must_have} tone="pos" />
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mb-2">Positive title signals</div>
          <Pills items={j.positive_titles} tone="pos" />
        </div>
        <div className="card p-5">
          <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mb-2">Negative title signals · anti-stuffer</div>
          <Pills items={j.negative_titles} tone="neg" />
        </div>
      </div>
      <div className="card p-5">
        <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mb-2">Query passed to retrieval</div>
        <pre className="text-xs bg-gray-50 border border-line rounded-lg p-4 whitespace-pre-wrap font-mono text-ink-soft">{j.query_text}</pre>
      </div>
    </div>
  );
}

export function Empty() {
  return <div className="card p-10 text-center text-ink-faint">No data yet — run a ranking to populate this view.</div>;
}
