"use client";
import { useState } from "react";
import type { JobIntent } from "@/lib/types";
import {
  IconTarget, IconRefresh, IconSpark, IconCheck, IconAlert, IconClose,
  IconChevron, IconClock, IconDatabase, IconCopy, IconChart, IconShield,
} from "./icons";
import { Empty } from "./Views";

// ---- Confidence ring (semantic colours: success / warning / danger) ----------
function ConfidenceRing({ value }: { value: number }) {
  const r = 40, c = 2 * Math.PI * r, pct = Math.max(0, Math.min(100, value));
  const color = value >= 75 ? "#10A37F" : value >= 55 ? "#d97706" : "#e25950";
  return (
    <div className="relative h-[116px] w-[116px] shrink-0">
      <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
        <circle cx="50" cy="50" r={r} fill="none" stroke="#eef0f4" strokeWidth="9" />
        <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (pct / 100) * c} style={{ transition: "stroke-dashoffset .7s ease" }} />
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center leading-none">
          <div className="text-[30px] font-extrabold tabular-nums text-ink">{value}</div>
          <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-faint">Confidence</div>
        </div>
      </div>
    </div>
  );
}

function SubBar({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-ink-soft">{label}</span>
        <span className="font-bold tabular-nums text-ink">{value}%</span>
      </div>
      <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${value}%`, background: tone }} />
      </div>
    </div>
  );
}

function SectionCard({ label, title, right, children }: {
  label?: string; title?: string; right?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <div className="card p-5">
      {(label || title || right) && (
        <div className="flex items-start justify-between gap-3 mb-1">
          <div>
            {label && <div className="text-[11px] font-bold uppercase tracking-wider text-ink-faint">{label}</div>}
            {title && <div className="font-semibold text-ink mt-0.5">{title}</div>}
          </div>
          {right}
        </div>
      )}
      {children}
    </div>
  );
}

function Pill({ children, tone }: { children: React.ReactNode; tone: "high" | "moderate" | "neutral" | "pos" | "neg" }) {
  const cls = {
    high: "bg-brand-wash text-brand-dark border-brand/25",
    moderate: "bg-blue-50 text-blue-700 border-blue-200",
    neutral: "bg-gray-100 text-ink-muted border-gray-200",
    pos: "bg-brand-wash text-brand-dark border-brand/25",
    neg: "bg-red-50 text-red-700 border-red-200",
  }[tone];
  return <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[13px] font-medium border ${cls}`}>{children}</span>;
}

function fmtTime(iso?: string) {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); }
  catch { return iso; }
}

export default function RoleView({
  j, onRank, running, onReindex,
}: {
  j: JobIntent | null;
  onRank: () => void;
  running: boolean;
  onReindex?: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [dismissed, setDismissed] = useState<string[]>([]);

  if (!j) return <Empty />;

  const conf = j.confidence;
  const stats = j.stats;
  const ret = j.retrieval;
  const conflicts = (j.signal_conflicts ?? []).filter((c) => !dismissed.includes(c.signal));

  const copyQuery = async () => {
    try { await navigator.clipboard.writeText(j.query_text || ""); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* ignore */ }
  };

  const capTier = (cap: string): "high" | "moderate" => {
    const c = cap.toLowerCase();
    return (j.query_text || "").toLowerCase().includes(c) ? "high" : "moderate";
  };

  return (
    <div className="space-y-4">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-ink-faint">
        <span className="hover:text-ink-soft cursor-default">Roles</span>
        <IconChevron className="h-3 w-3" />
        <span className="text-ink-soft font-medium truncate">{j.role_title}</span>
      </div>

      {/* Header */}
      <div className="card p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-3 min-w-0">
            <div className="h-11 w-11 rounded-xl bg-brand-wash text-brand grid place-items-center shrink-0">
              <IconTarget className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-xl font-extrabold tracking-tight text-ink truncate">{j.role_title}</h2>
              <div className="flex items-center gap-2 text-xs text-ink-faint mt-1 flex-wrap">
                <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">{j.role_id ?? "—"}</span>
                <span className="text-ink-faint">·</span>
                <span className="flex items-center gap-1"><IconClock className="h-3 w-3" /> Last indexed {fmtTime(j.last_indexed)}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onReindex} disabled={running}
              className="btn bg-white border border-line text-ink-soft hover:bg-gray-50 disabled:opacity-50">
              <IconRefresh className="h-4 w-4" /> Re-index
            </button>
            <button onClick={onRank} disabled={running} className="btn-primary disabled:opacity-50">
              <IconSpark className="h-4 w-4" /> {running ? "Ranking…" : "Run ranking"}
            </button>
          </div>
        </div>
      </div>

      <>
          {/* Confidence banner */}
          {conf && (
            <div className="card p-5">
              <div className="flex items-center gap-6 flex-wrap">
                <ConfidenceRing value={conf.score} />
                <div className="flex-1 min-w-[260px]">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-lg font-bold text-ink">{conf.label}</span>
                    <span className={`pill ${conf.status_ok ? "bg-positive/10 text-positive" : "bg-amber-50 text-warn"}`}>
                      {conf.status_ok ? <IconCheck className="h-3 w-3" /> : <IconAlert className="h-3 w-3" />}{conf.status}
                    </span>
                    <span className="pill bg-gray-100 text-ink-muted">{conf.model_version}</span>
                  </div>
                  <div className="grid sm:grid-cols-3 gap-4 mt-4">
                    <SubBar label="Skill coverage" value={conf.skill_coverage} tone="#10A37F" />
                    <SubBar label="Title clarity" value={conf.title_clarity} tone="#34B794" />
                    <SubBar label="Noise rejection" value={conf.noise_rejection} tone="#5AC7A8" />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Alert strip — signal conflicts */}
          {conflicts.map((c) => (
            <div key={c.signal} className="rounded-xl border border-warn/30 bg-amber-50/70 px-4 py-3 flex items-start gap-3">
              <IconAlert className="h-4 w-4 text-warn mt-0.5 shrink-0" />
              <div className="flex-1 text-sm text-ink-soft">{c.message}</div>
              <button onClick={() => setDismissed((d) => [...d, c.signal])} className="text-ink-faint hover:text-ink shrink-0" title="Dismiss">
                <IconClose className="h-4 w-4" />
              </button>
            </div>
          ))}

          {/* Stats row */}
          {stats && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              <SectionCard>
                <div className="text-[11px] font-bold uppercase tracking-wider text-ink-faint">Candidates in pool</div>
                <div className="text-[26px] font-extrabold tracking-tight text-brand mt-1">{stats.candidates_in_pool.toLocaleString()}</div>
                <div className="text-xs text-ink-faint mt-0.5">ingested for this role</div>
              </SectionCard>
              <SectionCard>
                <div className="text-[11px] font-bold uppercase tracking-wider text-ink-faint">Must-have keywords</div>
                <div className="text-[26px] font-extrabold tracking-tight text-ink mt-1">{stats.must_have_count}</div>
                <div className="text-xs text-ink-faint mt-0.5">+ {stats.nice_to_have_count} nice-to-have signals</div>
              </SectionCard>
              <SectionCard>
                <div className="text-[11px] font-bold uppercase tracking-wider text-ink-faint">Blocked title patterns</div>
                <div className="text-[26px] font-extrabold tracking-tight text-danger mt-1">{stats.blocked_title_count}</div>
                <div className="text-xs text-ink-faint mt-0.5">anti-stuffer filters</div>
              </SectionCard>
            </div>
          )}

          {/* Two-column signals */}
          <div className="grid lg:grid-cols-2 gap-4">
            <SectionCard label="Must-have capabilities" title={undefined}>
              <div className="flex items-center gap-3 text-[11px] text-ink-faint mb-3">
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-brand" /> High confidence</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-blue-500" /> Moderate</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-gray-400" /> Inferred</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {j.must_have.map((m) => (
                  <Pill key={m} tone={capTier(m)}>
                    {capTier(m) === "high" ? <IconCheck className="h-3 w-3" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}{m}
                  </Pill>
                ))}
                {j.nice_to_have.map((m) => <Pill key={m} tone="neutral">{m}</Pill>)}
                {!j.must_have.length && <span className="text-sm text-ink-faint">No must-have capabilities parsed.</span>}
              </div>
            </SectionCard>

            <div className="space-y-4">
              <SectionCard label="Positive title signals">
                <div className="flex flex-wrap gap-2 mt-1">
                  {j.positive_titles.map((t) => <Pill key={t} tone="pos"><IconCheck className="h-3 w-3" />{t}</Pill>)}
                  {!j.positive_titles.length && <span className="text-sm text-ink-faint">None.</span>}
                </div>
              </SectionCard>
              <SectionCard label="Negative title signals · anti-stuffer">
                <div className="flex flex-wrap gap-2 mt-1">
                  {j.negative_titles.map((t) => <Pill key={t} tone="neg"><IconClose className="h-3 w-3" />{t}</Pill>)}
                  {!j.negative_titles.length && <span className="text-sm text-ink-faint">None.</span>}
                </div>
              </SectionCard>
            </div>
          </div>

          {/* Retrieval query block */}
          <SectionCard label="Retrieval query" title={undefined}
            right={
              <button onClick={copyQuery} className="btn bg-white border border-line text-ink-soft hover:bg-gray-50 !py-1.5">
                {copied ? <><IconCheck className="h-3.5 w-3.5 text-positive" /> Copied</> : <><IconCopy className="h-3.5 w-3.5" /> Copy</>}
              </button>
            }>
            <pre className="mt-2 text-xs bg-ink text-white/90 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">{j.query_text || "—"}</pre>
            {ret && (
              <div className="flex flex-wrap gap-x-6 gap-y-2 mt-3 text-xs">
                <Meta icon={<IconDatabase className="h-3.5 w-3.5" />} label="Embedding model" value={ret.embedding_model} />
                <Meta icon={<IconChart className="h-3.5 w-3.5" />} label="Vector store" value={ret.vector_store} />
                <Meta icon={<IconTarget className="h-3.5 w-3.5" />} label="Top-k" value={ret.top_k.toLocaleString()} />
                <Meta icon={<IconShield className="h-3.5 w-3.5" />} label="Re-rank size" value={ret.rerank_size.toLocaleString()} />
              </div>
            )}
          </SectionCard>

          {/* Bottom: weights + activity */}
          <div className="grid lg:grid-cols-2 gap-4">
            <SectionCard label="Ranking weight breakdown">
              <div className="space-y-3 mt-2">
                {(j.weights ?? []).map((w) => (
                  <div key={w.key}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-ink-soft">{w.label}</span>
                      <span className="font-bold tabular-nums text-ink">{w.pct}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                      <div className="h-full rounded-full bg-brand" style={{ width: `${w.pct}%` }} />
                    </div>
                  </div>
                ))}
                {!(j.weights ?? []).length && <span className="text-sm text-ink-faint">Run a ranking to populate weights.</span>}
              </div>
            </SectionCard>

            <SectionCard label="Recent activity">
              <div className="relative pl-5 mt-2">
                <div className="absolute left-[5px] top-1.5 bottom-1.5 w-px bg-line" />
                <div className="space-y-4">
                  {(j.activity_log ?? []).map((a, i) => (
                    <div key={i} className="relative">
                      <span className="absolute -left-5 top-1 h-2.5 w-2.5 rounded-full bg-brand border-2 border-white shadow-sm" />
                      <div className="text-sm text-ink-soft">{a.label}</div>
                      <div className="text-[11px] text-ink-faint mt-0.5">{fmtTime(a.ts)}</div>
                    </div>
                  ))}
                  {!(j.activity_log ?? []).length && <span className="text-sm text-ink-faint">No activity yet.</span>}
                </div>
              </div>
            </SectionCard>
          </div>
        </>
    </div>
  );
}

function Meta({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-ink-faint">{icon}</span>
      <span className="text-ink-faint">{label}:</span>
      <span className="font-medium text-ink-soft">{value}</span>
    </div>
  );
}
