"use client";
import type { Detail } from "@/lib/types";
import { IconClose } from "./icons";

const CK = ["semantic_seer", "name_rectifier", "evidence_scout", "mask_piercer", "path_reader", "terrain_master"] as const;
const LABEL: Record<string, string> = {
  semantic_seer: "Semantic Seer", name_rectifier: "Name-Rectifier", evidence_scout: "Evidence Scout",
  mask_piercer: "Mask-Piercer", path_reader: "Path-Reader", terrain_master: "Terrain Master",
};

export default function CandidateDrawer({ d, loading, onClose }:
  { d: Detail | null; loading: boolean; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-ink/30 backdrop-blur-[1px]" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-full max-w-[560px] bg-white shadow-pop border-l border-line overflow-y-auto animate-[slidein_.2s_ease]">
        <style>{`@keyframes slidein{from{transform:translateX(20px);opacity:.4}to{transform:none;opacity:1}}`}</style>
        {loading || !d ? (
          <div className="p-8 text-ink-faint">Loading candidate…</div>
        ) : (
          <div>
            <div className="sticky top-0 bg-white border-b border-line px-6 py-4 flex items-start gap-3">
              <div className="h-11 w-11 rounded-xl bg-brand-wash text-brand-dark grid place-items-center font-extrabold">
                #{d.rank}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-bold text-lg leading-tight">{d.title}</div>
                <div className="text-sm text-ink-faint">{d.candidate_id} · {d.yoe ?? "—"} yrs · {d.location || "—"}</div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-extrabold text-brand">{d.score.toFixed(0)}</div>
                <div className="text-[10px] uppercase tracking-wide text-ink-faint">Relevance</div>
              </div>
              <button onClick={onClose} className="ml-1 text-ink-faint hover:text-ink p-1"><IconClose className="h-5 w-5" /></button>
            </div>

            <div className="p-6 space-y-6">
              <div className="rounded-lg bg-brand-wash/60 border border-brand/15 px-4 py-3 text-sm text-ink-soft">
                <span className="font-semibold text-brand-dark">Grounded reasoning. </span>{d.reasoning}
              </div>

              <div>
                <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mb-2">Council of Nine</div>
                <div className="space-y-2.5">
                  {CK.map((k) => (
                    <div key={k}>
                      <div className="flex justify-between text-sm">
                        <span className="text-ink-soft">{LABEL[k]}</span>
                        <span className="font-semibold tabular-nums">{((d.council[k] ?? 0) * 100).toFixed(0)}%</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden mt-1">
                        <div className="h-full rounded-full bg-brand" style={{ width: `${(d.council[k] ?? 0) * 100}%` }} />
                      </div>
                      {d.rationales[LABEL[k]] && (
                        <div className="text-xs text-ink-faint mt-1">{d.rationales[LABEL[k]]}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {d.summary && (
                <div>
                  <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mb-1.5">Summary</div>
                  <p className="text-sm text-ink-soft leading-relaxed">{d.summary}</p>
                </div>
              )}

              <div>
                <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mb-2">Verified relevant skills</div>
                <div className="flex flex-wrap gap-1.5">
                  {d.verified_skills.length ? d.verified_skills.map((s) => (
                    <span key={s} className="pill bg-positive/10 text-positive">{s}</span>
                  )) : <span className="text-sm text-ink-faint">None verified</span>}
                </div>
                <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mb-2 mt-3">All listed skills</div>
                <div className="flex flex-wrap gap-1.5">
                  {d.all_skills.map((s) => <span key={s} className="pill bg-gray-100 text-ink-muted">{s}</span>)}
                </div>
              </div>

              {d.education?.length > 0 && (
                <div>
                  <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mb-1.5">Education</div>
                  {d.education.map((e, i) => (
                    <div key={i} className="text-sm text-ink-soft">{e.degree} {e.field} — {e.institution} <span className="text-ink-faint">({e.tier})</span></div>
                  ))}
                </div>
              )}

              <div>
                <div className="text-xs font-bold uppercase tracking-wide text-ink-faint mb-2">Career timeline</div>
                <div className="space-y-3">
                  {d.career.map((r, i) => (
                    <div key={i} className="border-l-2 border-line pl-3">
                      <div className="text-sm font-semibold">{r.title} · <span className="font-normal text-ink-soft">{r.company}</span></div>
                      <div className="text-xs text-ink-faint">{r.start} → {r.end} · {r.months} mo</div>
                      <div className="text-xs text-ink-muted mt-1 leading-relaxed">{r.description}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
