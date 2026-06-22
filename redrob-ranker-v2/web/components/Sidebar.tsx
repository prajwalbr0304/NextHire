"use client";
import { IconGrid, IconChart, IconShield, IconAlert, IconTarget, IconSettings, IconTerminal } from "./icons";

export type Tab = "leaderboard" | "analytics" | "compliance" | "integrity" | "jobintent" | "logs";

const items: { id: Tab; label: string; icon: (p: { className?: string }) => JSX.Element }[] = [
  { id: "leaderboard", label: "Leaderboard", icon: IconGrid },
  { id: "analytics", label: "Score Analytics", icon: IconChart },
  { id: "compliance", label: "Compliance & Fairness", icon: IconShield },
  { id: "integrity", label: "Integrity Warden", icon: IconAlert },
  { id: "jobintent", label: "Job Intent Explorer", icon: IconTarget },
  { id: "logs", label: "Logs", icon: IconTerminal },
];

export default function Sidebar({
  tab, setTab, ranked, honeypots,
}: { tab: Tab; setTab: (t: Tab) => void; ranked: number; honeypots: number }) {
  return (
    <aside className="w-[248px] shrink-0 h-screen sticky top-0 bg-white border-r border-line flex flex-col">
      <div className="px-5 py-5 flex items-center gap-3">
        <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-brand to-brand-light grid place-items-center text-white font-extrabold text-sm shadow-sm">C9</div>
        <div>
          <div className="font-bold text-[15px] leading-tight">Council</div>
          <div className="text-xs text-ink-faint">Candidate Intelligence</div>
        </div>
      </div>

      <nav className="px-3 mt-2 flex-1">
        <div className="px-3 text-[10px] font-bold tracking-widest text-ink-faint uppercase mb-1">Workspace</div>
        {items.map((it) => {
          const Icon = it.icon;
          const active = tab === it.id;
          const badge = it.id === "leaderboard" ? ranked : it.id === "integrity" ? honeypots : null;
          return (
            <div key={it.id} onClick={() => setTab(it.id)}
              className={`navitem ${active ? "navitem-active" : ""}`}>
              <Icon className="h-[18px] w-[18px]" />
              <span className="flex-1">{it.label}</span>
              {badge ? (
                <span className={`pill ${active ? "bg-brand/15 text-brand-dark" : "bg-gray-100 text-ink-muted"}`}>
                  {badge.toLocaleString()}
                </span>
              ) : null}
            </div>
          );
        })}

        <div className="px-3 text-[10px] font-bold tracking-widest text-ink-faint uppercase mb-1 mt-6">Account</div>
        <div className="navitem"><IconSettings className="h-[18px] w-[18px]" /><span>Settings</span></div>
      </nav>

      <div className="px-4 py-4 border-t border-line flex items-center gap-3">
        <div className="h-9 w-9 rounded-full bg-ink text-white grid place-items-center text-xs font-bold">PB</div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">Prajwal B.</div>
          <div className="text-xs text-ink-faint">Talent Ops · Admin</div>
        </div>
      </div>
    </aside>
  );
}
