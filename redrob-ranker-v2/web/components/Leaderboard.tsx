"use client";
import type { Leaderboard as LB, Row } from "@/lib/types";
import { IconChevron } from "./icons";

const CK = ["semantic_seer", "name_rectifier", "evidence_scout", "mask_piercer", "path_reader", "terrain_master"] as const;
const CCOLOR: Record<string, string> = {
  semantic_seer: "#635bff", name_rectifier: "#f59e0b", evidence_scout: "#10b981",
  mask_piercer: "#ec4899", path_reader: "#06b6d4", terrain_master: "#8b5cf6",
};

function CouncilBars({ row }: { row: Row }) {
  return (
    <div className="flex items-end gap-[3px] h-7">
      {CK.map((k) => {
        const v = row.council[k] ?? 0;
        return <span key={k} title={`${k}: ${(v * 100).toFixed(0)}%`}
          className="w-[5px] rounded-sm" style={{ height: `${Math.max(8, v * 100)}%`, background: CCOLOR[k] }} />;
      })}
    </div>
  );
}

function Signals({ row }: { row: Row }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {row.verified_title && <span className="pill bg-positive/10 text-positive">Verified title</span>}
      {row.product && <span className="pill bg-brand/10 text-brand-dark">Product co.</span>}
      {row.location_match && <span className="pill bg-gray-100 text-ink-muted">Location</span>}
      {row.active ? <span className="pill bg-positive/10 text-positive">Active</span>
        : <span className="pill bg-gray-100 text-ink-faint">Dormant</span>}
      <span className={`pill ${row.notice_days <= 30 ? "bg-positive/10 text-positive" : "bg-amber-50 text-warn"}`}>
        Notice {row.notice_days}d
      </span>
    </div>
  );
}

export default function Leaderboard({
  data, page, setPage, onSelect,
}: { data: LB; page: number; setPage: (p: number) => void; onSelect: (id: string) => void }) {
  return (
    <div className="card overflow-hidden">
      <div className="grid grid-cols-[64px_1fr_180px_120px_minmax(220px,1fr)] gap-4 px-5 py-3 border-b border-line text-[11px] font-bold tracking-wide text-ink-faint uppercase">
        <div>Rank</div><div>Candidate</div><div>Composite</div><div>Council</div><div>Signals</div>
      </div>
      <div className="divide-y divide-line">
        {data.items.map((r) => (
          <div key={r.candidate_id} data-testid="lb-row" onClick={() => onSelect(r.candidate_id)}
            className="grid grid-cols-[64px_1fr_180px_120px_minmax(220px,1fr)] gap-4 px-5 py-3.5 items-center hover:bg-brand-wash/40 cursor-pointer transition">
            <div className="text-ink-faint font-semibold tabular-nums">#{r.rank}</div>
            <div className="min-w-0">
              <div className="font-semibold text-ink truncate">{r.title}</div>
              <div className="text-xs text-ink-faint truncate">
                {r.candidate_id} · {r.yoe ?? "—"} yrs{r.location ? ` · ${r.location}` : ""}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${r.score}%`, background: "linear-gradient(90deg,#7a73ff,#635bff)" }} />
              </div>
              <span className="text-sm font-bold tabular-nums w-9 text-right">{r.score.toFixed(0)}</span>
            </div>
            <CouncilBars row={r} />
            <Signals row={r} />
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between px-5 py-3 border-t border-line text-sm">
        <div className="text-ink-faint">
          Showing {(data.page - 1) * data.size + 1}–{Math.min(data.page * data.size, data.total)} of {data.total.toLocaleString()}
        </div>
        <div className="flex items-center gap-1">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)}
            className="btn-ghost px-2.5 py-1.5 disabled:opacity-40"><IconChevron className="h-4 w-4 rotate-180" /></button>
          <span className="px-3 text-ink-muted">Page {data.page} / {data.pages}</span>
          <button disabled={page >= data.pages} onClick={() => setPage(page + 1)}
            className="btn-ghost px-2.5 py-1.5 disabled:opacity-40"><IconChevron className="h-4 w-4" /></button>
        </div>
      </div>
    </div>
  );
}
