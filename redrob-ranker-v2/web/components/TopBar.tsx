"use client";

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
  tabLabel,
}: {
  tabLabel: string;
}) {
  return (
    <div className="h-20 sticky top-0 z-20 bg-canvas/80 backdrop-blur border-b border-line flex items-center justify-between px-7 pt-2">
      <div className="flex flex-col justify-center">
        <span className="text-lg font-bold text-ink">{TAB_LABEL[tabLabel] ?? tabLabel}</span>
        <span className="text-xs text-ink-muted">{TAB_TAGLINE[tabLabel] ?? ""}</span>
      </div>
      <div className="flex flex-col items-end justify-center">
        <span className="text-lg font-bold text-black">Nexthire</span>
        <span className="text-xs text-ink-muted">Precision in every hire</span>
      </div>
    </div>
  );
}
