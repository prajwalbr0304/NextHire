"use client";
import { IconMenu } from "./icons";

const TAB_LABEL: Record<string, string> = {
  candidates: "Candidates", insights: "Insights",
  role: "Role", integrity: "Integrity",
  governance: "Governance", compare: "Compare",
  pipeline: "Pipeline", nextai: "NextAi",
  audit: "Audit", settings: "Settings",
};

const TAB_TAGLINE: Record<string, string> = {
  candidates: "View and rank potential candidates",
  insights: "Analyze recruitment data and trends",
  role: "Manage job roles and requirements",
  integrity: "Ensure hiring process integrity",
  governance: "Oversee recruitment governance",
  compare: "Compare candidate profiles",
  pipeline: "Track candidate pipeline",
  nextai: "AI-powered recommendations",
  audit: "Review system logs and activities",
  settings: "Configure system preferences",
};

export default function TopBar({
  tabLabel, onMenuClick,
}: {
  tabLabel: string; onMenuClick?: () => void;
}) {
  return (
    <div className="h-20 sticky top-0 z-20 bg-canvas/80 backdrop-blur border-b border-line flex items-center justify-between px-4 sm:px-7 pt-2">
      <div className="flex items-center gap-3 min-w-0">
        <button onClick={onMenuClick} className="lg:hidden p-2 -ml-1 rounded-lg text-ink-soft hover:bg-gray-100 shrink-0" aria-label="Open navigation menu"><IconMenu className="h-5 w-5" /></button>
        <div className="flex flex-col justify-center min-w-0">
        <span className="text-lg font-bold text-ink">{TAB_LABEL[tabLabel] ?? tabLabel}</span>
        <span className="text-xs text-ink-muted">{TAB_TAGLINE[tabLabel] ?? ""}</span>
      </div>
      </div>
      <div className="flex items-center justify-end shrink-0">
        <img src="/N.svg" alt="Nexthire" className="h-16 w-auto" />
      </div>
    </div>
  );
}
