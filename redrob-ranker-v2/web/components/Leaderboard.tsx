"use client";
import type { Leaderboard as LB, Row, Shortlist } from "@/lib/types";
import { IconChevron, IconEye, IconBalance, IconCheck, IconPlus, IconLayers } from "./icons";
import { useState, useRef, useEffect } from "react";

const GRID_COLS = "grid-cols-[60px_minmax(150px,1fr)_minmax(240px,1.25fr)_80px_120px_130px_230px]";

// Format notice period as compact badge
function NoticeBadge({ days }: { days: number }) {
  if (days === 0) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
        Immediate
      </span>
    );
  }
  const label = days <= 30 ? "30d" : days <= 60 ? "60d" : "90d+";
  const colorClass = days <= 30 
    ? "bg-blue-50 text-blue-700 border-blue-200"
    : days <= 60 
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : "bg-red-50 text-red-700 border-red-200";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {label}
    </span>
  );
}

// Shortlist dropdown (lists shortlists for the task) + compare + view profile (eye)
function ActionMenu({
  row, onView, isCompared, onToggleCompare, shortlists, onAddToShortlist, onCreateShortlist,
}: {
  row: Row; onView: (id: string) => void;
  isCompared?: boolean; onToggleCompare?: (id: string) => void;
  shortlists?: Shortlist[];
  onAddToShortlist?: (shortlistId: string, row: Row) => void;
  onCreateShortlist?: (name: string) => Promise<Shortlist | null>;
}) {
  const candidateId = row.candidate_id;
  const [localShortlisted, setLocalShortlisted] = useState(false);
  const [open, setOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const supported = !!onAddToShortlist; // Supabase-backed shortlists available

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const memberOf = (sl: Shortlist) => sl.members?.some((m) => m.candidate_id === candidateId) ?? false;
  const inAnyList = (shortlists ?? []).some(memberOf);
  const isShortlisted = supported ? inAnyList : localShortlisted;

  const handleCreate = async () => {
    const name = newName.trim();
    if (!name || !onCreateShortlist) return;
    setBusy(true);
    const sl = await onCreateShortlist(name);
    setNewName("");
    if (sl && onAddToShortlist) onAddToShortlist(sl.id, row);
    setBusy(false);
  };

  return (
    <div className="flex items-center gap-1.5">
      {/* Shortlist control */}
      <div className="relative" ref={ref}>
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (supported) setOpen((o) => !o);
            else setLocalShortlisted((s) => !s);
          }}
          className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors flex items-center gap-1 ${
            isShortlisted
              ? "bg-emerald-100 text-emerald-700 border border-emerald-200"
              : "bg-gray-100 text-gray-600 border border-gray-200 hover:bg-emerald-50 hover:text-emerald-600 hover:border-emerald-200"
          }`}
        >
          {isShortlisted ? "Shortlisted" : "Shortlist"}
          {supported && <IconChevron className={`w-3 h-3 rotate-90 transition-transform ${open ? "-rotate-90" : ""}`} />}
        </button>

        {supported && open && (
          <div className="absolute left-0 top-full mt-1.5 w-56 bg-white border border-gray-200 rounded-xl shadow-lg z-30 overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="px-3 py-2 text-[11px] font-semibold text-gray-400 uppercase tracking-wide border-b border-gray-100">
              Add to shortlist
            </div>
            <div className="max-h-52 overflow-auto py-1">
              {(shortlists ?? []).length === 0 && (
                <div className="px-3 py-2 text-xs text-gray-400">No shortlists yet — create one below.</div>
              )}
              {(shortlists ?? []).map((sl) => {
                const added = memberOf(sl);
                return (
                  <button
                    key={sl.id}
                    disabled={added}
                    onClick={() => { if (!added) onAddToShortlist?.(sl.id, row); }}
                    className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 ${added ? "text-emerald-600 cursor-default" : "text-gray-700 hover:bg-gray-50"}`}
                  >
                    {added ? <IconCheck className="w-3.5 h-3.5 shrink-0" /> : <IconLayers className="w-3.5 h-3.5 text-gray-400 shrink-0" />}
                    <span className="flex-1 truncate">{sl.name}</span>
                    <span className="text-[11px] text-gray-400">{added ? "Added" : sl.count}</span>
                  </button>
                );
              })}
            </div>
            {onCreateShortlist && (
              <div className="px-3 py-2.5 border-t border-gray-100 flex items-center gap-2">
                <input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleCreate(); }}
                  placeholder="New shortlist…"
                  className="flex-1 min-w-0 bg-white border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-brand/30"
                />
                <button
                  onClick={handleCreate}
                  disabled={busy || !newName.trim()}
                  className="p-1.5 rounded-md bg-brand text-white disabled:opacity-40 shrink-0"
                  title="Create & add"
                >
                  <IconPlus className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {onToggleCompare && (
        <button
          onClick={(e) => { e.stopPropagation(); onToggleCompare(candidateId); }}
          title={isCompared ? "Remove from compare" : "Add to compare (max 4)"}
          className={`p-1.5 rounded-md border transition-colors ${isCompared ? "bg-brand text-white border-brand" : "bg-white text-gray-500 border-gray-200 hover:bg-gray-50"}`}
        >
          <IconBalance className="w-4 h-4" />
        </button>
      )}
      <button
        onClick={(e) => { e.stopPropagation(); onView(candidateId); }}
        title="View profile"
        className="p-1.5 rounded-md border border-gray-200 bg-white text-gray-500 hover:text-brand hover:border-brand/40 hover:bg-brand-wash transition-colors"
      >
        <IconEye className="w-4 h-4" />
      </button>
    </div>
  );
}

export default function Leaderboard({
  data, page, setPage, onSelect, compareIds, onToggleCompare,
  shortlists, onAddToShortlist, onCreateShortlist,
}: {
  data: LB; page: number; setPage: (p: number) => void; onSelect: (id: string) => void;
  compareIds?: string[]; onToggleCompare?: (id: string) => void;
  shortlists?: Shortlist[];
  onAddToShortlist?: (shortlistId: string, row: Row) => void;
  onCreateShortlist?: (name: string) => Promise<Shortlist | null>;
}) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <div className="min-w-[1100px]">
      {/* Header */}
      <div className={`grid ${GRID_COLS} items-center gap-4 px-5 py-3 border-b border-gray-200 bg-gray-50/50 text-[11px] font-semibold tracking-wide text-gray-500 uppercase`}>
        <div className="text-center">Rank</div>
        <div className="text-center">Candidate ID</div>
        <div>Current Role</div>
        <div className="text-center">Score</div>
        <div className="text-center">Experience</div>
        <div className="text-center">Notice Period</div>
        <div><span className="inline-block w-[92px] text-center">Actions</span></div>
      </div>
      
      {/* Body */}
      <div className="divide-y divide-gray-100">
        {data.items.map((r) => (
          <div 
            key={r.candidate_id} 
            data-testid="lb-row" 
            onClick={() => onSelect(r.candidate_id)}
            className={`grid ${GRID_COLS} items-center gap-4 px-5 py-3 cursor-pointer transition-colors ${compareIds?.includes(r.candidate_id) ? "bg-brand-wash" : "hover:bg-gray-50"}`}
          >
            {/* Rank */}
            <div className="text-center">
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                {r.rank}
              </span>
            </div>
            
            {/* Candidate ID */}
            <div className="min-w-0 text-center">
              <div className="font-mono text-xs text-gray-500 truncate">
                {r.candidate_id}
              </div>
            </div>
            
            {/* Current Role */}
            <div className="min-w-0">
              <div className="font-semibold text-gray-900 truncate text-sm">{r.title}</div>
              <div className="text-xs text-gray-500 truncate mt-0.5">
                {r.company}{r.location ? ` · ${r.location}` : ""}
              </div>
            </div>
            
            {/* Score */}
            <div className="text-center">
              <span className="text-sm font-bold text-gray-900">
                {r.score.toFixed(0)}
              </span>
            </div>
            
            {/* Experience */}
            <div className="text-center">
              <span className="text-sm font-medium text-gray-700">
                {r.yoe !== null ? `${r.yoe.toFixed(1)} yrs` : "—"}
              </span>
            </div>
            
            {/* Notice Period */}
            <div className="flex justify-center">
              <NoticeBadge days={r.notice_days} />
            </div>
            
            {/* Actions */}
            <div className="flex items-center justify-start gap-1.5" onClick={(e) => e.stopPropagation()}>
              <ActionMenu
                row={r}
                onView={onSelect}
                isCompared={compareIds?.includes(r.candidate_id)}
                onToggleCompare={onToggleCompare}
                shortlists={shortlists}
                onAddToShortlist={onAddToShortlist}
                onCreateShortlist={onCreateShortlist}
              />
            </div>
          </div>
        ))}
      </div>

        </div>
      </div>
      {/* Pagination */}
      <div className="flex items-center justify-between px-5 py-3 border-t border-gray-200 bg-gray-50/50 text-sm">
        <div className="text-gray-500">
          Showing {(data.page - 1) * data.size + 1}–{Math.min(data.page * data.size, data.total)} of {data.total.toLocaleString()}
        </div>
        <div className="flex items-center gap-1">
          <button 
            disabled={page <= 1} 
            onClick={() => setPage(page - 1)}
            className="p-2 rounded hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <IconChevron className="h-4 w-4 rotate-180" />
          </button>
          <span className="px-3 text-gray-600">Page {data.page} of {data.pages}</span>
          <button 
            disabled={page >= data.pages} 
            onClick={() => setPage(page + 1)}
            className="p-2 rounded hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <IconChevron className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}