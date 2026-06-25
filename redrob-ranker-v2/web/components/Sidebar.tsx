"use client";
import { useState } from "react";
import { IconGrid, IconChart, IconShield, IconAlert, IconTarget, IconWrench, IconTerminal, IconChevron, IconBolt, IconUsers, IconBriefcase } from "./icons";

export type Tab = "candidates" | "insights" | "role" | "integrity" | "governance" | "compare" | "pipeline" | "nextai" | "audit" | "settings";

const items: { id: Tab; label: string; icon: (p: { className?: string }) => JSX.Element; badge?: number }[] = [
  { id: "candidates", label: "Candidates", icon: IconGrid },
  { id: "insights", label: "Insights", icon: IconChart },
  { id: "role", label: "Role", icon: IconTarget },
  { id: "integrity", label: "Integrity", icon: IconAlert },
  { id: "governance", label: "Governance", icon: IconShield },
  { id: "compare", label: "Compare", icon: IconUsers },
  { id: "pipeline", label: "Pipeline", icon: IconBriefcase },
  { id: "nextai", label: "NextAi", icon: IconBolt },
  { id: "audit", label: "Audit", icon: IconTerminal },
  { id: "settings", label: "Settings", icon: IconWrench },
];

export default function Sidebar({
  tab, setTab,
}: { tab: Tab; setTab: (t: Tab) => void }) {
  const [collapsed, setCollapsed] = useState(true);

  return (
    <aside className={`${collapsed ? "w-[72px]" : "w-[248px]"} shrink-0 h-screen sticky top-0 bg-white border-r border-line flex flex-col transition-all duration-200`}>
      <div className={`py-5 flex items-center gap-3 ${collapsed ? "justify-center px-2" : "px-5"}`}>
        <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-brand to-brand-light grid place-items-center text-white font-extrabold text-[10px] shadow-sm">Nh</div>
        {!collapsed && (
          <div>
            <div className="font-bold text-[15px] leading-tight">Nexthire</div>
            <div className="text-xs text-ink-faint">Precision in every hire</div>
          </div>
        )}
      </div>

      <nav className={`px-3 mt-2 flex-1 ${collapsed ? "px-2" : ""}`}>
        {items.map((it) => {
          const Icon = it.icon;
          const active = tab === it.id;
          return (
            <div key={it.id} onClick={() => setTab(it.id)}
              className={`navitem ${active ? "navitem-active" : ""} ${collapsed ? "justify-center px-0" : ""}`}
              title={collapsed ? it.label : undefined}>
              <Icon className={`${collapsed ? "h-5 w-5" : "h-[18px] w-[18px]"} shrink-0`} />
              {!collapsed && (
                <span className="flex-1">{it.label}</span>
              )}
            </div>
          );
        })}
      </nav>

      <div className={`border-t border-line flex items-center gap-3 ${collapsed ? "justify-center px-2 py-4" : "px-4 py-4"}`}>
        {collapsed ? (
          <div className="h-9 w-9 rounded-full bg-ink text-white grid place-items-center text-xs font-bold">PB</div>
        ) : (
          <>
            <div className="h-9 w-9 rounded-full bg-ink text-white grid place-items-center text-xs font-bold">PB</div>
            <div className="leading-tight">
              <div className="text-sm font-semibold">Prajwal B.</div>
              <div className="text-xs text-ink-faint">Talent Ops · Admin</div>
            </div>
          </>
        )}
      </div>

      <button 
        onClick={() => setCollapsed(!collapsed)}
        className={`absolute top-1/2 -translate-y-1/2 ${collapsed ? "left-[64px]" : "left-[240px]"} bg-white border border-line rounded-r-md p-1.5 shadow-sm hover:bg-gray-50 transition-all duration-200`}
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        <IconChevron className={`h-4 w-4 text-ink-muted transition-transform ${collapsed ? "rotate-0" : "rotate-180"}`} />
      </button>
    </aside>
  );
}
