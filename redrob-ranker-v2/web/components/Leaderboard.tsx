"use client";
import type { Leaderboard as LB, Row } from "@/lib/types";
import { IconChevron, IconCheck, IconDots, IconEye, IconCompare, IconStar } from "./icons";
import { useState, useRef, useEffect } from "react";

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

// Compact action menu with dropdown
function ActionMenu({ candidateId, onView }: { candidateId: string; onView: (id: string) => void }) {
  const [shortlisted, setShortlisted] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative flex items-center justify-end gap-2 w-full" ref={menuRef}>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setShortlisted(!shortlisted);
        }}
        className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
          shortlisted 
            ? "bg-emerald-100 text-emerald-700 border border-emerald-200" 
            : "bg-gray-100 text-gray-600 border border-gray-200 hover:bg-emerald-50 hover:text-emerald-600 hover:border-emerald-200"
        }`}
      >
        {shortlisted ? "Shortlisted" : "Shortlist"}
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setMenuOpen(!menuOpen);
        }}
        className="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
      >
        <IconDots className="w-4 h-4" />
      </button>
      {menuOpen && (
        <div className="absolute right-0 top-full mt-1 w-40 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-10">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onView(candidateId);
              setMenuOpen(false);
            }}
            className="w-full px-3 py-2 text-left text-xs text-gray-700 hover:bg-gray-50 flex items-center gap-2"
          >
            <IconEye className="w-3.5 h-3.5" />
            View Profile
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setMenuOpen(false);
            }}
            className="w-full px-3 py-2 text-left text-xs text-gray-700 hover:bg-gray-50 flex items-center gap-2"
          >
            <IconCompare className="w-3.5 h-3.5" />
            Compare
          </button>
        </div>
      )}
    </div>
  );
}

export default function Leaderboard({
  data, page, setPage, onSelect,
}: { data: LB; page: number; setPage: (p: number) => void; onSelect: (id: string) => void }) {
  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div className="flex items-center px-4 py-3 border-b border-gray-200 bg-gray-50/50 text-[11px] font-semibold tracking-wide text-gray-500 uppercase" style={{ gap: '12px' }}>
        <div className="text-center" style={{ width: '40px' }}>Rank</div>
        <div style={{ width: '160px' }}>Candidate ID</div>
        <div style={{ width: '280px' }}>Current Role</div>
        <div className="text-right" style={{ width: '60px' }}>Score</div>
        <div className="text-center" style={{ width: '100px' }}>Experience</div>
        <div className="text-center" style={{ width: '100px' }}>Notice Period</div>
        <div className="text-center" style={{ width: '140px' }}>Actions</div>
      </div>
      
      {/* Body */}
      <div className="divide-y divide-gray-100">
        {data.items.map((r) => (
          <div 
            key={r.candidate_id} 
            data-testid="lb-row" 
            onClick={() => onSelect(r.candidate_id)}
            className="flex items-center px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
            style={{ gap: '12px' }}
          >
            {/* Rank */}
            <div className="text-center" style={{ width: '40px' }}>
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold">
                {r.rank}
              </span>
            </div>
            
            {/* Candidate ID */}
            <div style={{ width: '160px' }}>
              <div className="font-mono text-xs text-gray-500 truncate">
                {r.candidate_id}
              </div>
            </div>
            
            {/* Current Role */}
            <div style={{ width: '280px' }}>
              <div className="font-semibold text-gray-900 truncate text-sm">{r.title}</div>
              <div className="text-xs text-gray-500 truncate mt-0.5">
                {r.company}{r.location ? ` · ${r.location}` : ""}
              </div>
            </div>
            
            {/* Score */}
            <div className="text-right" style={{ width: '60px' }}>
              <span className="text-sm font-bold text-gray-900">
                {r.score.toFixed(0)}
              </span>
            </div>
            
            {/* Experience */}
            <div className="text-center" style={{ width: '100px' }}>
              <span className="text-sm font-medium text-gray-700">
                {r.yoe !== null ? `${r.yoe.toFixed(1)} yrs` : "—"}
              </span>
            </div>
            
            {/* Notice Period */}
            <div className="text-center" style={{ width: '100px' }}>
              <NoticeBadge days={r.notice_days} />
            </div>
            
            {/* Actions */}
            <div className="text-center" style={{ width: '140px' }} onClick={(e) => e.stopPropagation()}>
              <ActionMenu candidateId={r.candidate_id} onView={onSelect} />
            </div>
          </div>
        ))}
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
