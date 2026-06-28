"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Honeypots, HoneypotItem } from "@/lib/types";
import {
  IconShield, IconSearch, IconChevron, IconDots, IconDownload,
  IconAlert, IconCheck, IconClose, IconEye, IconFilter,
} from "./icons";

const SEV: Record<string, { label: string; badge: string; border: string; dot: string; rank: number }> = {
  critical: { label: "Critical", badge: "bg-red-100 text-red-700 border-red-200", border: "border-l-red-500", dot: "bg-red-500", rank: 0 },
  high: { label: "High", badge: "bg-orange-100 text-orange-700 border-orange-200", border: "border-l-orange-500", dot: "bg-orange-500", rank: 1 },
  medium: { label: "Medium", badge: "bg-amber-100 text-amber-700 border-amber-200", border: "border-l-amber-500", dot: "bg-amber-500", rank: 2 },
};
const sevOf = (s: string) => SEV[s] ?? SEV.medium;

const GRID = "grid-cols-[150px_minmax(150px,1.1fr)_minmax(290px,1.4fr)_minmax(120px,0.8fr)_230px_104px_52px]";

function download(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

function exportCsv(items: HoneypotItem[]) {
  const headers = ["Candidate ID", "Title", "Violation", "Flagged", "Claimed", "Baseline", "Delta", "Severity"];
  const rows = items.map((it) => [it.candidate_id, it.title, it.violation_type, it.flagged_skill ?? "",
    it.claimed_value, it.baseline_value, it.delta ?? "", it.severity]);
  const csv = [headers, ...rows].map((r) => r.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(",")).join("\r\n");
  download("integrity_exclusions.csv", csv, "text/csv;charset=utf-8");
}

function StatCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent: string }) {
  return (
    <div className="card p-4">
      <div className="text-[11px] font-bold uppercase tracking-wider text-ink-faint">{label}</div>
      <div className={`font-extrabold tracking-tight mt-1 ${value.length > 12 ? "text-base leading-snug" : "text-[26px] truncate"}`} style={{ color: accent }} title={value}>{value}</div>
      {sub && <div className="text-xs text-ink-faint mt-0.5">{sub}</div>}
    </div>
  );
}

function RowMenu({ item, onAction }: { item: HoneypotItem; onAction: (a: string, it: HoneypotItem) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const fn = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", fn);
    return () => document.removeEventListener("mousedown", fn);
  }, [open]);
  const act = (a: string) => { onAction(a, item); setOpen(false); };
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} className="p-1.5 rounded-md text-ink-faint hover:text-ink hover:bg-gray-100" title="Actions">
        <IconDots className="h-4 w-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-line rounded-xl shadow-pop z-30 py-1">
          <button onClick={() => act("view")} className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center gap-2">
            <IconEye className="h-3.5 w-3.5 text-ink-faint" /> View details
          </button>
          <button onClick={() => act("override")} className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center gap-2">
            <IconCheck className="h-3.5 w-3.5 text-ink-faint" /> Override block
          </button>
          <button onClick={() => act("report")} className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center gap-2">
            <IconAlert className="h-3.5 w-3.5 text-ink-faint" /> Report false positive
          </button>
        </div>
      )}
    </div>
  );
}

function StatusChip({ status }: { status: string }) {
  const map: Record<string, string> = {
    blocked: "bg-red-50 text-red-600 border-red-200",
    overridden: "bg-gray-100 text-ink-muted border-gray-200",
    reported: "bg-blue-50 text-blue-700 border-blue-200",
  };
  const label = status === "overridden" ? "Overridden" : status === "reported" ? "Reported" : "Blocked";
  return <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${map[status]}`}>
    <span className={`h-1.5 w-1.5 rounded-full ${status === "blocked" ? "bg-red-500" : status === "reported" ? "bg-blue-500" : "bg-gray-400"}`} />{label}
  </span>;
}

export default function IntegrityView({ h, onLog }: { h: Honeypots | null; onLog?: (msg: string) => void }) {
  const [query, setQuery] = useState("");
  const [vfilter, setVfilter] = useState("all");
  const [sort, setSort] = useState<"severe" | "recent">("severe");
  const [expanded, setExpanded] = useState<string[]>([]);
  const [statusMap, setStatusMap] = useState<Record<string, string>>({});
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 50;

  const items = h?.items ?? [];
  const vtypes = useMemo(() => {
    const counts = h?.violation_counts ?? [];
    if (counts.length) return counts.map((c) => c.type);
    return Array.from(new Set(items.map((i) => i.violation_type)));
  }, [h, items]);

  const filtered = useMemo(() => {
    let out = items.filter((it) => {
      const q = query.trim().toLowerCase();
      const matchesQ = !q || it.candidate_id.toLowerCase().includes(q) || (it.title || "").toLowerCase().includes(q);
      const matchesV = vfilter === "all" || it.violation_type === vfilter;
      return matchesQ && matchesV;
    });
    out = [...out];
    if (sort === "severe") out.sort((a, b) => sevOf(a.severity).rank - sevOf(b.severity).rank);
    else out.reverse();
    return out;
  }, [items, query, vfilter, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paged = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  useEffect(() => { setPage(1); }, [query, vfilter, sort]);

  const handleAction = (a: string, it: HoneypotItem) => {
    if (a === "override") { setStatusMap((m) => ({ ...m, [it.candidate_id]: "overridden" })); onLog?.(`Integrity block overridden for ${it.candidate_id}`); }
    else if (a === "report") { setStatusMap((m) => ({ ...m, [it.candidate_id]: "reported" })); onLog?.(`Flagged ${it.candidate_id} as a false positive for review`); }
    else if (a === "view") { setExpanded((e) => e.includes(it.candidate_id) ? e.filter((x) => x !== it.candidate_id) : [...e, it.candidate_id]); }
  };

  // Empty state — no violations in the run
  if (h && h.total === 0) {
    return (
      <div className="card p-12 text-center">
        <div className="h-14 w-14 rounded-2xl bg-positive/10 text-positive grid place-items-center mx-auto mb-3">
          <IconShield className="h-7 w-7" />
        </div>
        <div className="font-semibold text-ink">No violations detected in this run</div>
        <div className="text-sm text-ink-muted mt-1">The Integrity Warden found no logically impossible profiles.</div>
        <div className="text-xs text-ink-faint mt-2">Last check · {new Date().toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="card p-5 flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-3">
          <div className="h-11 w-11 rounded-xl bg-red-50 text-red-600 grid place-items-center shrink-0">
            <IconShield className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-ink leading-tight">Integrity &amp; Honeypot Detection</h2>
            <p className="text-sm text-ink-muted mt-0.5 max-w-xl">Automated exclusion of candidates with logically impossible or fraudulent resume signals.</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-positive/10 text-positive border border-positive/20">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-positive opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-positive" />
          </span>
          Warden active
        </span>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <StatCard label="Total flagged this run" value={(h?.total ?? 0).toLocaleString()} sub="excluded from ranking" accent="#e25950" />
        <StatCard label="Showing in view" value={filtered.length.toLocaleString()} sub={vfilter === "all" && !query ? "all flagged profiles" : `of ${(h?.total ?? 0).toLocaleString()} flagged`} accent="#1a1f36" />
        <StatCard label="Most common violation" value={h?.most_common_violation ?? "—"} accent="#d97706" />
        <StatCard label="Resume inflation rate" value={`${h?.inflation_rate ?? 0}%`} sub="flagged / total pool" accent="#e25950" />
      </div>

      {/* Filter + search row */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="relative w-full sm:max-w-xs">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint"><IconSearch className="h-4 w-4" /></span>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by candidate ID or title…"
            className="w-full bg-white border border-line rounded-lg pl-10 pr-4 py-2 text-sm placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand" />
        </div>
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
          <div className="relative">
            <IconFilter className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-faint pointer-events-none" />
            <select value={vfilter} onChange={(e) => setVfilter(e.target.value)}
              className="appearance-none bg-white border border-line rounded-lg pl-8 pr-8 py-2 text-sm font-medium text-ink-soft focus:outline-none focus:ring-2 focus:ring-brand/30 cursor-pointer">
              <option value="all">All violations</option>
              {vtypes.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <IconChevron className="h-4 w-4 absolute right-2 top-1/2 -translate-y-1/2 rotate-90 text-ink-faint pointer-events-none" />
          </div>
          <div className="relative">
            <select value={sort} onChange={(e) => setSort(e.target.value as "severe" | "recent")}
              className="appearance-none bg-white border border-line rounded-lg pl-3 pr-8 py-2 text-sm font-medium text-ink-soft focus:outline-none focus:ring-2 focus:ring-brand/30 cursor-pointer">
              <option value="severe">Most severe first</option>
              <option value="recent">Most recent first</option>
            </select>
            <IconChevron className="h-4 w-4 absolute right-2 top-1/2 -translate-y-1/2 rotate-90 text-ink-faint pointer-events-none" />
          </div>
          <button onClick={() => exportCsv(filtered)} className="btn bg-white border border-line text-ink-soft hover:bg-gray-50">
            <IconDownload className="h-4 w-4" /> Export
          </button>
        </div>
      </div>

      {/* Exclusion log table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <div className="min-w-[1120px]">
            {/* Header */}
            <div className={`grid ${GRID} items-center gap-3 px-4 py-2.5 border-b border-line bg-gray-50/70 text-[11px] font-semibold tracking-wide text-ink-faint uppercase`}>
              <div>Candidate ID</div>
              <div>Last known title</div>
              <div>Violation type</div>
              <div>Flagged skill</div>
              <div>Claimed vs baseline</div>
              <div className="text-center">Severity</div>
              <div className="text-center">Action</div>
            </div>
            {/* Rows */}
            {paged.map((it, i) => {
              const sev = sevOf(it.severity);
              const status = statusMap[it.candidate_id] ?? "blocked";
              const isOpen = expanded.includes(it.candidate_id);
              return (
                <div key={it.candidate_id} className={`border-l-4 ${sev.border} border-b border-line/70 ${i % 2 ? "bg-gray-50/40" : "bg-white"} ${status === "overridden" ? "opacity-60" : ""} hover:bg-brand-wash/40 transition-colors`}>
                  <div className={`grid ${GRID} items-center gap-3 px-4 py-3`}>
                    <div className="min-w-0">
                      <div className="font-mono text-xs text-ink-soft truncate">{it.candidate_id}</div>
                      <div className="mt-1"><StatusChip status={status} /></div>
                    </div>
                    <div className="text-sm text-ink-soft truncate" title={it.title}>{it.title || "—"}</div>
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`h-2 w-2 rounded-full shrink-0 ${sev.dot}`} />
                      <span className="text-sm text-ink whitespace-nowrap" title={it.violation_type}>{it.violation_type}</span>
                    </div>
                    <div className="text-sm text-ink-soft truncate" title={it.flagged_skill ?? ""}>{it.flagged_skill ?? "—"}</div>
                    <div className="flex items-center gap-2">
                      <div className="min-w-0">
                        <div className="text-[10px] uppercase tracking-wide text-ink-faint">{it.claimed_label}</div>
                        <div className="text-sm font-semibold text-ink truncate">{it.claimed_value}</div>
                      </div>
                      <span className="text-ink-faint text-xs">vs</span>
                      <div className="min-w-0">
                        <div className="text-[10px] uppercase tracking-wide text-ink-faint">{it.baseline_label}</div>
                        <div className="text-sm font-semibold text-ink-soft truncate">{it.baseline_value}</div>
                      </div>
                      {it.delta && <span className="ml-auto inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-bold bg-red-50 text-red-600 border border-red-200 shrink-0">{it.delta}</span>}
                    </div>
                    <div className="flex justify-center">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border ${sev.badge}`}>{sev.label}</span>
                    </div>
                    <div className="flex justify-center">
                      <RowMenu item={it} onAction={handleAction} />
                    </div>
                  </div>
                  {isOpen && (
                    <div className="px-4 pb-3 -mt-1">
                      <div className="rounded-lg bg-gray-50 border border-line px-3 py-2.5">
                        <div className="text-[11px] font-bold uppercase tracking-wide text-ink-faint mb-1">Warden findings</div>
                        <ul className="space-y-1">
                          {(it.reasons.length ? it.reasons : ["No additional detail recorded."]).map((r, ri) => (
                            <li key={ri} className="text-sm text-ink-soft flex gap-2"><span className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${sev.dot}`} />{r}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            {filtered.length === 0 && (
              <div className="px-4 py-10 text-center text-sm text-ink-faint">No flagged profiles match the current filters.</div>
            )}
          </div>
        </div>
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 border-t border-line bg-gray-50/50 text-xs text-ink-faint flex-wrap">
          <span>
            {filtered.length ? `${(safePage - 1) * PAGE_SIZE + 1}–${(safePage - 1) * PAGE_SIZE + paged.length}` : 0} of {filtered.length.toLocaleString()} {vfilter === "all" && !query ? "flagged" : "matching"} profiles
          </span>
          <div className="flex items-center gap-1.5">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={safePage <= 1}
              className="px-2.5 py-1 rounded-md border border-line bg-white text-ink-soft hover:bg-gray-50 disabled:opacity-40 disabled:hover:bg-white flex items-center gap-1">
              <IconChevron className="h-3.5 w-3.5 rotate-180" /> Prev
            </button>
            <span className="px-2 tabular-nums">Page {safePage} of {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={safePage >= totalPages}
              className="px-2.5 py-1 rounded-md border border-line bg-white text-ink-soft hover:bg-gray-50 disabled:opacity-40 disabled:hover:bg-white flex items-center gap-1">
              Next <IconChevron className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
