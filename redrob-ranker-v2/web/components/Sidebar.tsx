"use client";
import { useState } from "react";
import { IconGrid, IconChart, IconShield, IconAlert, IconTarget, IconTerminal, IconChevron, IconUsers, IconBriefcase, IconClose } from "./icons";

export type Tab = "candidates" | "insights" | "role" | "integrity" | "governance" | "compare" | "pipeline" | "audit" | "settings";

const items: { id: Tab; label: string; icon: (p: { className?: string }) => JSX.Element; badge?: number }[] = [
  { id: "candidates", label: "Candidates", icon: IconGrid },
  { id: "insights", label: "Insights", icon: IconChart },
  { id: "role", label: "Role", icon: IconTarget },
  { id: "integrity", label: "Integrity", icon: IconAlert },
  { id: "governance", label: "Governance", icon: IconShield },
  { id: "compare", label: "Compare", icon: IconUsers },
  { id: "pipeline", label: "Pipeline", icon: IconBriefcase },
  { id: "audit", label: "Audit", icon: IconTerminal },
];

export default function Sidebar({
  tab, setTab, mobileOpen = false, onMobileClose,
}: { tab: Tab; setTab: (t: Tab) => void; mobileOpen?: boolean; onMobileClose?: () => void }) {
  const [collapsed, setCollapsed] = useState(true);

  const selectTab = (t: Tab) => { setTab(t); onMobileClose?.(); };

  return (
    <>
      {/* Mobile backdrop */}
      <div
        aria-hidden
        onClick={onMobileClose}
        className={`fixed inset-0 z-40 bg-ink/40 backdrop-blur-[2px] lg:hidden transition-opacity duration-200 ${
          mobileOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      />

      <aside
        className={`fixed lg:sticky top-0 z-50 h-screen shrink-0 bg-white border-r border-line flex flex-col transition-all duration-200
          w-[248px] ${collapsed ? "lg:w-[72px]" : "lg:w-[248px]"}
          ${mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
      >
        {/* Brand + mobile close */}
        <div className={`py-5 flex items-center gap-3 px-5 ${collapsed ? "lg:justify-center lg:px-2" : ""}`}>
          <img src="/N.svg" alt="Nexthire" className="h-12 w-12 rounded-xl object-contain shrink-0" />
          <div className={collapsed ? "lg:hidden" : ""}>
            <div className="font-bold text-[15px] leading-tight">Nexthire</div>
            <div className="text-xs text-ink-faint">Precision in every hire</div>
          </div>
          <button
            onClick={onMobileClose}
            className="ml-auto lg:hidden p-1.5 rounded-lg text-ink-muted hover:bg-gray-100"
            title="Close menu"
          >
            <IconClose className="h-5 w-5" />
          </button>
        </div>

        <nav className={`px-3 mt-2 flex-1 overflow-y-auto ${collapsed ? "lg:px-2" : ""}`}>
          {items.map((it) => {
            const Icon = it.icon;
            const active = tab === it.id;
            return (
              <div key={it.id} onClick={() => selectTab(it.id)}
                className={`navitem ${active ? "navitem-active" : ""} ${collapsed ? "lg:justify-center lg:px-0" : ""}`}
                title={collapsed ? it.label : undefined}>
                <Icon className="h-[18px] w-[18px] shrink-0" />
                <span className={`flex-1 ${collapsed ? "lg:hidden" : ""}`}>{it.label}</span>
              </div>
            );
          })}
        </nav>


        {/* Desktop collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={`hidden lg:block absolute top-1/2 -translate-y-1/2 ${collapsed ? "left-[64px]" : "left-[240px]"} bg-white border border-line rounded-r-md p-1.5 shadow-sm hover:bg-gray-50 transition-all duration-200`}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <IconChevron className={`h-4 w-4 text-ink-muted transition-transform ${collapsed ? "rotate-0" : "rotate-180"}`} />
        </button>
      </aside>
    </>
  );
}
