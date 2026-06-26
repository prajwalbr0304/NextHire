"use client";
import type { Detail } from "@/lib/types";
import {
  IconClose, IconSpark, IconCheck, IconAlert, IconShield, IconChart,
  IconBriefcase, IconTarget, IconClock, IconStar, IconBolt,
} from "./icons";

const CK = ["semantic_seer", "name_rectifier", "evidence_scout", "mask_piercer", "path_reader", "terrain_master"] as const;
const LABEL: Record<string, string> = {
  semantic_seer: "Role-Signal Alignment", name_rectifier: "Title Calibration Index", evidence_scout: "Delivery Velocity",
  mask_piercer: "Declared vs. Demonstrated Skill", path_reader: "Tenure & Progression Depth", terrain_master: "Domain Density",
};

// Stripe-style segment palette (matches the donut weights icon)
const PALETTE = ["#10A37F", "#f59e0b", "#10b981", "#ec4899", "#06b6d4", "#3b82f6"];

function tierOf(score: number) {
  if (score >= 85) return { label: "Tier 1 · Strong match", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" };
  if (score >= 70) return { label: "Tier 2 · Solid match", cls: "bg-blue-50 text-blue-700 border-blue-200" };
  if (score >= 55) return { label: "Tier 3 · Moderate match", cls: "bg-amber-50 text-amber-700 border-amber-200" };
  return { label: "Tier 4 · Marginal", cls: "bg-gray-100 text-gray-600 border-gray-200" };
}

// Circular score gauge
function ScoreRing({ value }: { value: number }) {
  const r = 34, c = 2 * Math.PI * r, pct = Math.max(0, Math.min(100, value));
  const color = value >= 85 ? "#10b981" : value >= 70 ? "#10A37F" : value >= 55 ? "#f59e0b" : "#94a3b8";
  return (
    <div className="relative h-[84px] w-[84px] shrink-0">
      <svg viewBox="0 0 84 84" className="h-full w-full -rotate-90">
        <circle cx="42" cy="42" r={r} fill="none" stroke="#eef0f4" strokeWidth="8" />
        <circle cx="42" cy="42" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (pct / 100) * c} style={{ transition: "stroke-dashoffset .6s ease" }} />
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center leading-none">
          <div className="text-[26px] font-extrabold tracking-tight text-ink tabular-nums">{value.toFixed(0)}</div>
          <div className="text-[9px] font-semibold uppercase tracking-wider text-ink-faint">Score</div>
        </div>
      </div>
    </div>
  );
}

function Section({ icon, title, right, children }: { icon: React.ReactNode; title: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-line bg-white shadow-[0_1px_2px_rgba(16,24,40,.04)]">
      <div className="flex items-center justify-between gap-3 px-5 pt-4 pb-3">
        <div className="flex items-center gap-2.5">
          <span className="h-7 w-7 rounded-lg bg-brand-wash text-brand grid place-items-center">{icon}</span>
          <h3 className="text-[13px] font-bold uppercase tracking-wide text-ink-soft">{title}</h3>
        </div>
        {right}
      </div>
      <div className="px-5 pb-5">{children}</div>
    </section>
  );
}

function StatChip({ label, value, tone = "default" }: { label: string; value: string; tone?: "default" | "good" | "warn" | "bad" }) {
  const tones: Record<string, string> = {
    default: "bg-gray-50 text-ink-soft border-line",
    good: "bg-emerald-50 text-emerald-700 border-emerald-200",
    warn: "bg-amber-50 text-amber-700 border-amber-200",
    bad: "bg-red-50 text-red-700 border-red-200",
  };
  return (
    <div className={`rounded-xl border px-3 py-2 ${tones[tone]}`}>
      <div className="text-[10px] font-semibold uppercase tracking-wide opacity-70">{label}</div>
      <div className="text-sm font-bold mt-0.5">{value}</div>
    </div>
  );
}

const SEV: Record<string, { dot: string; text: string }> = {
  high: { dot: "bg-red-500", text: "text-red-600" },
  medium: { dot: "bg-amber-500", text: "text-amber-600" },
  low: { dot: "bg-gray-400", text: "text-gray-500" },
};

export default function CandidateDrawer({ d, loading, onClose }:
  { d: Detail | null; loading: boolean; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-full max-w-[680px] bg-canvas shadow-pop border-l border-line overflow-y-auto animate-[slidein_.22s_ease]">
        <style>{`@keyframes slidein{from{transform:translateX(28px);opacity:.3}to{transform:none;opacity:1}}`}</style>
        {loading || !d ? (
          <div className="p-10 text-ink-faint text-lg">Loading candidate…</div>
        ) : (
          <CandidateBody d={d} onClose={onClose} />
        )}
      </div>
    </div>
  );
}

function CandidateBody({ d, onClose }: { d: Detail; onClose: () => void }) {
  const tier = tierOf(d.score);
  const breakdown = d.score_breakdown ?? [];
  const totalPoints = breakdown.reduce((s, b) => s + b.points, 0) || 1;
  const careerMax = Math.max(1, ...d.career.map((r) => r.months || 0));
  const risk = d.risk;
  const riskColor = risk?.level === "high" ? "#ef4444" : risk?.level === "medium" ? "#f59e0b" : "#10b981";
  const riskTone = risk?.level === "high" ? "text-red-600" : risk?.level === "medium" ? "text-amber-600" : "text-emerald-600";

  return (
    <div>
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white/90 backdrop-blur border-b border-line px-4 sm:px-7 py-5">
        <div className="flex items-start gap-4">
          <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-brand to-brand-light text-white grid place-items-center font-extrabold text-lg shadow-sm shrink-0">
            #{d.rank}
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="font-extrabold text-[22px] leading-tight tracking-tight truncate">{d.title}</h2>
            <div className="text-sm text-ink-muted mt-1 flex items-center gap-2 flex-wrap">
              <span className="font-mono text-ink-faint">{d.candidate_id}</span>
              <span className="text-ink-faint">·</span>
              <span>{d.yoe ?? "—"} yrs exp</span>
              <span className="text-ink-faint">·</span>
              <span>{d.location || d.country || "—"}</span>
            </div>
            <span className={`inline-flex items-center mt-2 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${tier.cls}`}>{tier.label}</span>
          </div>
          <ScoreRing value={d.score} />
          <button onClick={onClose} className="ml-1 text-ink-faint hover:text-ink p-1.5 rounded-lg hover:bg-gray-100 transition-colors shrink-0">
            <IconClose className="h-6 w-6" />
          </button>
        </div>

        {/* Quick stat chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4">
          <StatChip label="Notice" value={d.notice_days === 0 ? "Immediate" : `${d.notice_days}d`} tone={d.notice_days <= 30 ? "good" : d.notice_days <= 60 ? "warn" : "bad"} />
          <StatChip label="Activity" value={d.active ? "Active" : "Dormant"} tone={d.active ? "good" : "warn"} />
          <StatChip label="Company" value={d.product ? "Product" : "Services"} tone={d.product ? "good" : "default"} />
          <StatChip label="Location" value={d.location_match ? "Match" : "Other"} tone={d.location_match ? "good" : "default"} />
        </div>
      </div>

      <div className="p-4 sm:p-7 space-y-5">
        {/* AI reasoning */}
        <div className="rounded-2xl bg-gradient-to-br from-brand-wash to-brand-wash/40 border border-brand/15 px-5 py-4">
          <div className="flex items-center gap-2 mb-1.5">
            <IconSpark className="h-4 w-4 text-brand" />
            <span className="text-xs font-bold uppercase tracking-wide text-brand-dark">AI reasoning</span>
          </div>
          <p className="text-[15px] text-ink-soft leading-relaxed">{d.reasoning}</p>
        </div>

        {/* Summary */}
        {d.summary && (
          <Section icon={<IconBolt className="h-4 w-4" />} title="Summary">
            <p className="text-[15px] text-ink-soft leading-relaxed">{d.summary}</p>
          </Section>
        )}

        {/* Score breakdown */}
        {breakdown.length > 0 && (
          <Section
            icon={<IconChart className="h-4 w-4" />}
            title="Score breakdown"
            right={<span className="text-xs text-ink-faint">weighted contribution</span>}
          >
            {/* Stacked contribution bar */}
            <div className="flex h-3 w-full rounded-full overflow-hidden mb-5 bg-gray-100">
              {breakdown.map((b, i) => (
                <div key={b.key} title={`${b.label}: ${b.points} pts`}
                  style={{ width: `${(b.points / totalPoints) * 100}%`, background: PALETTE[i % PALETTE.length] }} />
              ))}
            </div>
            <div className="space-y-3.5">
              {breakdown.map((b, i) => (
                <div key={b.key}>
                  <div className="flex items-center justify-between text-sm mb-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="h-2.5 w-2.5 rounded-sm shrink-0" style={{ background: PALETTE[i % PALETTE.length] }} />
                      <span className="text-ink-soft truncate">{b.label}</span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 tabular-nums">
                      <span className="text-ink-faint text-xs">w {b.weight}%</span>
                      <span className="font-bold text-ink w-10 text-right">{b.score}</span>
                    </div>
                  </div>
                  <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${b.score}%`, background: PALETTE[i % PALETTE.length] }} />
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Strengths & Weaknesses */}
        {(d.strengths?.length || d.weaknesses?.length) && (
          <div className="grid md:grid-cols-2 gap-5">
            <Section icon={<IconCheck className="h-4 w-4" />} title="Strengths">
              <ul className="space-y-3">
                {(d.strengths ?? []).map((s, i) => (
                  <li key={i} className="flex gap-2.5">
                    <span className="mt-0.5 h-5 w-5 rounded-full bg-emerald-100 text-emerald-600 grid place-items-center shrink-0">
                      <IconCheck className="h-3 w-3" />
                    </span>
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-ink">{s.label}</div>
                      <div className="text-[13px] text-ink-muted leading-snug">{s.detail}</div>
                    </div>
                  </li>
                ))}
                {!d.strengths?.length && <li className="text-sm text-ink-faint">No standout strengths.</li>}
              </ul>
            </Section>
            <Section icon={<IconAlert className="h-4 w-4" />} title="Weaknesses">
              <ul className="space-y-3">
                {(d.weaknesses ?? []).map((w, i) => (
                  <li key={i} className="flex gap-2.5">
                    <span className="mt-0.5 h-5 w-5 rounded-full bg-amber-100 text-amber-600 grid place-items-center shrink-0">
                      <IconAlert className="h-3 w-3" />
                    </span>
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-ink">{w.label}</div>
                      <div className="text-[13px] text-ink-muted leading-snug">{w.detail}</div>
                    </div>
                  </li>
                ))}
                {!d.weaknesses?.length && <li className="text-sm text-ink-faint">No notable weaknesses.</li>}
              </ul>
            </Section>
          </div>
        )}

        {/* Risk factor */}
        {risk && (
          <Section
            icon={<IconShield className="h-4 w-4" />}
            title="Risk assessment"
            right={<span className={`text-xs font-bold uppercase tracking-wide ${riskTone}`}>{risk.level} risk</span>}
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="flex-1 h-2.5 rounded-full bg-gray-100 overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${risk.score}%`, background: riskColor, transition: "width .6s ease" }} />
              </div>
              <span className={`text-sm font-bold tabular-nums w-10 text-right ${riskTone}`}>{risk.score}</span>
            </div>
            <ul className="space-y-2">
              {risk.factors.map((f, i) => (
                <li key={i} className="flex items-center gap-2.5 text-sm">
                  <span className={`h-2 w-2 rounded-full shrink-0 ${SEV[f.severity]?.dot ?? "bg-gray-400"}`} />
                  <span className="text-ink-soft flex-1">{f.label}</span>
                  <span className={`text-[11px] font-semibold uppercase ${SEV[f.severity]?.text ?? "text-gray-500"}`}>{f.severity}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* Missing qualifications */}
        {(d.missing_qualifications?.length || d.must_have_coverage != null) && (
          <Section
            icon={<IconTarget className="h-4 w-4" />}
            title="Missing qualifications"
            right={d.must_have_coverage != null ? (
              <span className="text-xs text-ink-faint tabular-nums">{d.must_have_covered ?? 0}/{d.must_have_total ?? 0} must-haves</span>
            ) : undefined}
          >
            {d.must_have_coverage != null && (
              <div className="flex items-center gap-2 mb-4">
                <span className="text-xs text-ink-faint w-20">Coverage</span>
                <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
                  <div className="h-full rounded-full bg-brand" style={{ width: `${d.must_have_coverage}%` }} />
                </div>
                <span className="text-sm font-bold tabular-nums w-10 text-right text-ink">{d.must_have_coverage}%</span>
              </div>
            )}
            {d.missing_qualifications?.length ? (
              <div className="flex flex-wrap gap-2">
                {d.missing_qualifications.map((m, i) => (
                  <span key={i} className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[13px] font-medium border ${m.kind === "experience" ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-red-50 text-red-600 border-red-200"}`}>
                    <IconAlert className="h-3 w-3" />{m.label}
                  </span>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-sm text-emerald-600">
                <IconCheck className="h-4 w-4" /> Meets all must-have requirements.
              </div>
            )}
          </Section>
        )}

        {/* Skills */}
        <Section icon={<IconStar className="h-4 w-4" />} title="Skills">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-emerald-600 mb-2">Verified & relevant</div>
          <div className="flex flex-wrap gap-2 mb-4">
            {d.verified_skills.length ? d.verified_skills.map((s) => (
              <span key={s} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[13px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <IconCheck className="h-3 w-3" />{s}
              </span>
            )) : <span className="text-sm text-ink-faint">None verified</span>}
          </div>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-faint mb-2">All listed</div>
          <div className="flex flex-wrap gap-2">
            {d.all_skills.map((s) => <span key={s} className="px-2.5 py-1 rounded-lg text-[13px] bg-gray-50 text-ink-muted border border-line">{s}</span>)}
          </div>
        </Section>

        {/* Similar role match */}
        {d.similar_roles?.length ? (
          <Section icon={<IconTarget className="h-4 w-4" />} title="Similar role match">
            <div className="space-y-3">
              {d.similar_roles.map((r) => (
                <div key={r.role}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-ink-soft">{r.role}</span>
                    <span className="font-bold tabular-nums text-ink">{r.match}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                    <div className="h-full rounded-full bg-gradient-to-r from-brand to-brand-light" style={{ width: `${r.match}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </Section>
        ) : null}

        {/* Education */}
        {d.education?.length > 0 && (
          <Section icon={<IconStar className="h-4 w-4" />} title="Education">
            <div className="space-y-2.5">
              {d.education.map((e, i) => (
                <div key={i} className="flex items-start gap-3">
                  <span className="mt-1 h-2 w-2 rounded-full bg-brand shrink-0" />
                  <div>
                    <div className="text-sm font-semibold text-ink">{e.degree} {e.field && `· ${e.field}`}</div>
                    <div className="text-[13px] text-ink-muted">{e.institution} {e.tier && <span className="text-ink-faint">({e.tier})</span>}</div>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Career timeline — graphical */}
        <Section icon={<IconBriefcase className="h-4 w-4" />} title="Career timeline">
          <div className="relative pl-6">
            {/* vertical gradient spine */}
            <div className="absolute left-[7px] top-2 bottom-2 w-[2px] bg-gradient-to-b from-brand via-brand-light to-transparent rounded-full" />
            <div className="space-y-5">
              {d.career.map((r, i) => {
                const color = PALETTE[i % PALETTE.length];
                const yrs = r.months ? (r.months / 12).toFixed(1) : null;
                return (
                  <div key={i} className="relative">
                    {/* node */}
                    <span className="absolute -left-6 top-1 h-4 w-4 rounded-full border-[3px] border-white shadow-sm" style={{ background: color }} />
                    <div className="rounded-2xl border border-line bg-white p-4 shadow-[0_1px_2px_rgba(16,24,40,.04)]">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-[15px] font-bold text-ink leading-tight">{r.title}</div>
                          <div className="text-sm text-ink-muted">{r.company}</div>
                        </div>
                        {r.months ? (
                          <span className="shrink-0 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-brand-wash text-brand-dark">
                            {r.months} mo{yrs && Number(yrs) >= 1 ? ` · ${yrs}y` : ""}
                          </span>
                        ) : null}
                      </div>
                      <div className="flex items-center gap-1.5 text-[12px] text-ink-faint mt-1.5">
                        <IconClock className="h-3.5 w-3.5" />
                        <span>{r.start} → {r.end}</span>
                      </div>
                      {/* tenure bar */}
                      {r.months ? (
                        <div className="mt-2.5 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${Math.max(6, (r.months / careerMax) * 100)}%`, background: color }} />
                        </div>
                      ) : null}
                      {r.description && (
                        <p className="text-[13px] text-ink-muted leading-relaxed mt-2.5">{r.description}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </Section>
      </div>
    </div>
  );
}
