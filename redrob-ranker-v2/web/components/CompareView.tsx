"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Detail, Row } from "@/lib/types";
import { Empty } from "./Views";
import { IconClose, IconSearch, IconPlus, IconCheck } from "./icons";

const COUNCIL: [string, string][] = [
  ["semantic_seer", "Role-Signal Alignment"],
  ["name_rectifier", "Title Calibration"],
  ["evidence_scout", "Delivery Velocity"],
  ["mask_piercer", "Skill Verification"],
  ["path_reader", "Tenure & Progression"],
  ["terrain_master", "Domain Density"],
];
const MAX = 4;

const COLORS = ["#10A37F", "#06b6d4", "#f59e0b", "#ec4899"];

function bestIndex(vals: (number | null)[]): number {
  let bi = -1, bv = -Infinity;
  vals.forEach((v, i) => { if (v != null && v > bv) { bv = v; bi = i; } });
  return bi;
}

function AddBar({ ids, onAdd, ready }: { ids: string[]; onAdd: (id: string) => void; ready: boolean }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Row[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ready || !q.trim()) { setResults([]); return; }
    const t = setTimeout(() => {
      api.leaderboard(1, 8, q).then((r) => { setResults(r.items); setOpen(true); }).catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [q, ready]);

  useEffect(() => {
    function onDoc(e: MouseEvent) { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const full = ids.length >= MAX;
  return (
    <div className="relative max-w-md" ref={ref}>
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint"><IconSearch className="h-4 w-4" /></span>
      <input
        value={q} onChange={(e) => setQ(e.target.value)} onFocus={() => results.length && setOpen(true)}
        disabled={!ready || full}
        placeholder={full ? `Maximum ${MAX} candidates selected` : "Search by name or ID to add a candidate…"}
        className="w-full bg-white border border-line rounded-lg pl-10 pr-4 py-2 text-sm placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand/30 disabled:opacity-60"
      />
      {open && results.length > 0 && !full && (
        <div className="absolute z-20 left-0 right-0 top-full mt-1 bg-white border border-line rounded-lg shadow-pop py-1 max-h-72 overflow-auto">
          {results.map((r) => {
            const sel = ids.includes(r.candidate_id);
            return (
              <button key={r.candidate_id} disabled={sel}
                onClick={() => { onAdd(r.candidate_id); setQ(""); setOpen(false); }}
                className="w-full text-left px-3 py-2 hover:bg-gray-50 flex items-center justify-between gap-2 disabled:opacity-50">
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">{r.title}</div>
                  <div className="text-xs text-ink-faint font-mono truncate">#{r.rank} · {r.candidate_id}</div>
                </div>
                {sel ? <IconCheck className="h-4 w-4 text-positive shrink-0" /> : <IconPlus className="h-4 w-4 text-brand shrink-0" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Cat({ title }: { title: string }) {
  return (
    <div className="px-4 py-2 bg-gray-50/80 border-y border-line text-[11px] font-bold uppercase tracking-wide text-ink-faint">
      {title}
    </div>
  );
}

export default function CompareView({
  ids, setIds, ready, cols,
}: { ids: string[]; setIds: (ids: string[]) => void; ready: boolean; cols: number }) {
  const [details, setDetails] = useState<Record<string, Detail | null>>({});

  useEffect(() => {
    ids.forEach((id) => {
      if (details[id] === undefined) {
        setDetails((d) => ({ ...d, [id]: null }));
        api.candidate(id).then((d) => setDetails((prev) => ({ ...prev, [id]: d }))).catch(() => {});
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids]);

  const add = (id: string) => { if (!ids.includes(id) && ids.length < MAX) setIds([...ids, id]); };
  const remove = (id: string) => setIds(ids.filter((x) => x !== id));

  const loaded = ids.map((id) => details[id]).filter(Boolean) as Detail[];
  const template = `200px repeat(${ids.length}, minmax(180px, 1fr))`;

  if (!ready) return <Empty />;

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <div className="font-semibold">Select candidates to compare</div>
            <div className="text-xs text-ink-faint mt-0.5">Add up to {MAX} candidates from the leaderboard, then compare side by side.</div>
          </div>
          <div className="flex items-center gap-3">
            <span className="pill bg-brand-wash text-brand-dark">{ids.length}/{MAX} selected</span>
            {ids.length > 0 && (
              <button onClick={() => setIds([])} className="btn bg-white border border-line text-ink-soft hover:bg-gray-50">Clear all</button>
            )}
          </div>
        </div>
        <div className="mt-4"><AddBar ids={ids} onAdd={add} ready={ready} /></div>
      </div>

      {ids.length === 0 ? (
        <div className="card p-10 text-center text-ink-faint">
          No candidates selected yet. Use the search above, or click <span className="font-semibold text-ink-soft">Compare</span> on any leaderboard row.
        </div>
      ) : (
        <div className="card overflow-x-auto">
          {/* Candidate column headers */}
          <div className="grid items-stretch" style={{ gridTemplateColumns: template, minWidth: 200 + ids.length * 180 }}>
            <div className="px-4 py-3 flex items-end text-[11px] font-bold uppercase tracking-wide text-ink-faint">Attribute</div>
            {ids.map((id, i) => {
              const d = details[id];
              return (
                <div key={id} className="px-4 py-3 border-l border-line relative" style={{ borderTop: `3px solid ${COLORS[i]}` }}>
                  <button onClick={() => remove(id)} className="absolute top-2 right-2 p-1 rounded hover:bg-gray-100 text-ink-faint">
                    <IconClose className="h-3.5 w-3.5" />
                  </button>
                  {d ? (
                    <>
                      <div className="text-xs font-mono text-ink-faint truncate">{d.candidate_id}</div>
                      <div className="font-semibold text-sm text-ink mt-0.5 truncate" title={d.title}>{d.title}</div>
                      <div className="text-xs text-ink-muted truncate">{d.company || "—"}</div>
                      <div className="mt-2 inline-flex items-center gap-1.5">
                        <span className="text-lg font-extrabold tabular-nums" style={{ color: COLORS[i] }}>{d.score.toFixed(0)}</span>
                        <span className="text-[11px] text-ink-faint">#{d.rank}</span>
                      </div>
                    </>
                  ) : (
                    <div className="text-sm text-ink-faint animate-pulse py-4">Loading…</div>
                  )}
                </div>
              );
            })}
          </div>

          {loaded.length === ids.length && <ComparisonRows ids={ids} details={details} template={template} />}
        </div>
      )}
    </div>
  );
}

function ComparisonRows({ ids, details, template }: { ids: string[]; details: Record<string, Detail | null>; template: string }) {
  const ds = ids.map((id) => details[id]!) as Detail[];
  const minWidth = 200 + ids.length * 180;

  const TextRow = ({ label, get }: { label: string; get: (d: Detail) => React.ReactNode }) => (
    <div className="grid border-t border-line/60" style={{ gridTemplateColumns: template, minWidth }}>
      <div className="px-4 py-2.5 text-sm text-ink-muted">{label}</div>
      {ds.map((d, i) => <div key={i} className="px-4 py-2.5 text-sm border-l border-line truncate">{get(d)}</div>)}
    </div>
  );

  const NumRow = ({ label, vals, fmt, pct }: { label: string; vals: (number | null)[]; fmt?: (v: number) => string; pct?: boolean }) => {
    const best = bestIndex(vals);
    return (
      <div className="grid border-t border-line/60" style={{ gridTemplateColumns: template, minWidth }}>
        <div className="px-4 py-2.5 text-sm text-ink-muted">{label}</div>
        {vals.map((v, i) => (
          <div key={i} className="px-4 py-2.5 text-sm border-l border-line">
            {v == null ? <span className="text-ink-faint">—</span> : (
              pct ? (
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${v * 100}%`, background: COLORS[i] }} />
                  </div>
                  <span className="tabular-nums text-xs w-9 text-right font-medium">{Math.round(v * 100)}</span>
                  {i === best && best >= 0 && <span className="pill bg-positive/10 text-positive !px-1.5 !py-0">top</span>}
                </div>
              ) : (
                <span className={`tabular-nums font-medium ${i === best && best >= 0 ? "text-positive" : ""}`}>
                  {fmt ? fmt(v) : v}{i === best && best >= 0 && <span className="ml-1.5 pill bg-positive/10 text-positive !px-1.5 !py-0">best</span>}
                </span>
              )
            )}
          </div>
        ))}
      </div>
    );
  };

  const BoolRow = ({ label, get }: { label: string; get: (d: Detail) => boolean }) => (
    <div className="grid border-t border-line/60" style={{ gridTemplateColumns: template, minWidth }}>
      <div className="px-4 py-2.5 text-sm text-ink-muted">{label}</div>
      {ds.map((d, i) => (
        <div key={i} className="px-4 py-2.5 text-sm border-l border-line">
          {get(d)
            ? <span className="pill bg-positive/10 text-positive">Yes</span>
            : <span className="pill bg-gray-100 text-ink-faint">No</span>}
        </div>
      ))}
    </div>
  );

  return (
    <div>
      <Cat title="Overview" />
      <NumRow label="Composite score" vals={ds.map((d) => d.score)} fmt={(v) => v.toFixed(1)} />
      <NumRow label="Rank" vals={ds.map((d) => d.rank ? -d.rank : null)} fmt={(v) => `#${-v}`} />
      <TextRow label="Location" get={(d) => d.location || d.country || "—"} />

      <Cat title="Experience & availability" />
      <NumRow label="Years of experience" vals={ds.map((d) => d.yoe)} fmt={(v) => `${v.toFixed(1)} yrs`} />
      <NumRow label="Notice period (days)" vals={ds.map((d) => d.notice_days != null ? -d.notice_days : null)} fmt={(v) => `${-v} days`} />
      <BoolRow label="Active (≤30d)" get={(d) => d.active} />

      <Cat title="Council scores" />
      {COUNCIL.map(([key, label]) => (
        <NumRow key={key} label={label} vals={ds.map((d) => (d.council as any)?.[key] ?? null)} pct />
      ))}

      <Cat title="Signals" />
      <BoolRow label="Verified title" get={(d) => d.verified_title} />
      <BoolRow label="Product-company background" get={(d) => d.product} />
      <BoolRow label="Location match" get={(d) => d.location_match} />

      <Cat title="Verified relevant skills" />
      <div className="grid border-t border-line/60" style={{ gridTemplateColumns: template, minWidth }}>
        <div className="px-4 py-2.5 text-sm text-ink-muted">Top skills</div>
        {ds.map((d, i) => (
          <div key={i} className="px-4 py-2.5 border-l border-line">
            <div className="flex flex-wrap gap-1">
              {(d.verified_skills || []).slice(0, 8).map((s) => <span key={s} className="pill bg-brand-wash text-brand-dark">{s}</span>)}
              {(!d.verified_skills || d.verified_skills.length === 0) && <span className="text-ink-faint text-sm">—</span>}
            </div>
          </div>
        ))}
      </div>

      <Cat title="Education" />
      <div className="grid border-t border-line/60" style={{ gridTemplateColumns: template, minWidth }}>
        <div className="px-4 py-2.5 text-sm text-ink-muted">Highest qualification</div>
        {ds.map((d, i) => {
          const e = d.education?.[0];
          return (
            <div key={i} className="px-4 py-2.5 text-sm border-l border-line">
              {e ? <>
                <div className="font-medium truncate">{e.degree || "—"}</div>
                <div className="text-xs text-ink-faint truncate">{e.field || ""}{e.tier ? ` · ${e.tier}` : ""}</div>
              </> : <span className="text-ink-faint">—</span>}
            </div>
          );
        })}
      </div>

      <Cat title="Why this rank" />
      <div className="grid border-t border-line/60" style={{ gridTemplateColumns: template, minWidth }}>
        <div className="px-4 py-2.5 text-sm text-ink-muted">Reasoning</div>
        {ds.map((d, i) => (
          <div key={i} className="px-4 py-2.5 text-xs text-ink-soft border-l border-line leading-relaxed">{d.reasoning || "—"}</div>
        ))}
      </div>
    </div>
  );
}
