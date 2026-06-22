"use client";
import { IconSearch, IconSpark, IconChevron } from "./icons";

const TAB_LABEL: Record<string, string> = {
  leaderboard: "Leaderboard", analytics: "Score Analytics",
  compliance: "Compliance & Fairness", integrity: "Integrity Warden",
  jobintent: "Job Intent Explorer",
};

export default function TopBar({
  tabLabel, roles, role, setRole, search, setSearch, onRank, running,
}: {
  tabLabel: string; roles: string[]; role: string; setRole: (r: string) => void;
  search: string; setSearch: (s: string) => void; onRank: () => void; running: boolean;
}) {
  return (
    <div className="h-16 sticky top-0 z-20 bg-canvas/80 backdrop-blur border-b border-line flex items-center gap-4 px-7">
      <div className="text-sm text-ink-muted">
        <span className="text-ink-faint">Council</span>
        <span className="mx-2 text-ink-faint">/</span>
        <span className="font-semibold text-ink">{TAB_LABEL[tabLabel] ?? tabLabel}</span>
      </div>

      <div className="flex-1 max-w-md mx-auto relative">
        <IconSearch className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search candidates, IDs…"
          className="w-full bg-white border border-line rounded-lg pl-9 pr-3 py-2 text-sm placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
        />
      </div>

      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-2 w-2 rounded-full bg-positive" />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="appearance-none bg-white border border-line rounded-lg pl-7 pr-8 py-2 text-sm font-medium text-ink-soft focus:outline-none focus:ring-2 focus:ring-brand/30 cursor-pointer max-w-[230px] truncate"
        >
          {roles.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <IconChevron className="h-4 w-4 absolute right-2 top-1/2 -translate-y-1/2 rotate-90 text-ink-faint pointer-events-none" />
      </div>

      <button onClick={onRank} disabled={running} className="btn-primary disabled:opacity-60">
        <IconSpark className="h-4 w-4" />
        {running ? "Ranking…" : "Rank candidates"}
      </button>
    </div>
  );
}
