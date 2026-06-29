"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Sidebar, { Tab } from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import Kpis from "@/components/Kpis";
import Controls, { Weights, Params } from "@/components/Controls";
import Leaderboard from "@/components/Leaderboard";
import CandidateDrawer from "@/components/CandidateDrawer";
import Logs from "@/components/Logs";
import { Empty } from "@/components/Views";
import InsightsView from "@/components/InsightsView";
import GovernanceView from "@/components/GovernanceView";
import CompareView from "@/components/CompareView";
import PipelineView from "@/components/PipelineView";
import RoleView from "@/components/RoleView";
import IntegrityView from "@/components/IntegrityView";
import { api } from "@/lib/api";
import type {
  Analytics, Compliance, Detail, Honeypots, JobIntent, Leaderboard as LB, Log, Status, Summary, Shortlist, Row,
} from "@/lib/types";
import { IconDownload, IconUpload, IconChevron, IconDonut, IconClose, IconUsers, IconSpark, IconAlert, IconClock, IconBolt, IconSearch, IconCheck, IconRefresh, IconFilter, IconMenu } from "@/components/icons";

type Filters = { minScore: number; minYoe: number; maxYoe: number; notice: string[] };
const DEFAULT_FILTERS: Filters = { minScore: 0, minYoe: 0, maxYoe: 50, notice: [] };

const TABS: { id: Tab; label: string }[] = [
  { id: "candidates", label: "Candidates" }, { id: "insights", label: "Insights" },
  { id: "role", label: "Role" }, { id: "integrity", label: "Integrity" },
  { id: "governance", label: "Governance" }, { id: "compare", label: "Compare" },
  { id: "pipeline", label: "Pipeline" },   { id: "audit", label: "Audit" }, { id: "settings", label: "Settings" },
];

function nowTs() {
  const d = new Date(); const p = (n: number, l = 2) => String(n).padStart(l, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}`;
}

const DEFAULT_W: Weights = {
  semantic_seer: 0.13, name_rectifier: 0.20, evidence_scout: 0.24,
  mask_piercer: 0.14, path_reader: 0.12, terrain_master: 0.17,
};
const DEFAULT_P: Params = {
  yoe_ideal: [6, 8], yoe_ok: [5, 9], notice_pref: 30, integrity: true, availability: true,
};

export default function Page() {
  const [roles, setRoles] = useState<string[]>([]);
  const [role, setRole] = useState("");
  const [status, setStatus] = useState<Status>({ status: "idle", message: "", role: null, file: null, file_size_mb: null, ingested: 0, ranked: 0, honeypots: 0, runtime: 0 });
  const [summary, setSummary] = useState<Summary | null>(null);
  const [tab, setTab] = useState<Tab>("candidates");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [lb, setLb] = useState<LB | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [compliance, setCompliance] = useState<Compliance | null>(null);
  const [honeypots, setHoneypots] = useState<Honeypots | null>(null);
  const [jobIntent, setJobIntent] = useState<JobIntent | null>(null);
  const [selId, setSelId] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [exportN, setExportN] = useState(100);
  const [shortlists, setShortlists] = useState<Shortlist[]>([]);
  const [dbEnabled, setDbEnabled] = useState(false);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [showFilter, setShowFilter] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [customExport, setCustomExport] = useState("");
  const filterRef = useRef<HTMLDivElement>(null);
  const exportRef = useRef<HTMLDivElement>(null);
  const [weights, setWeights] = useState<Weights>(DEFAULT_W);
  const [params, setParams] = useState<Params>(DEFAULT_P);
  const [dirty, setDirty] = useState(false);
  const [hasRanked, setHasRanked] = useState(false);
  const [staged, setStaged] = useState<{ name: string; size_mb: number } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [showUploadError, setShowUploadError] = useState(false);
  const [uploadErrorMessage, setUploadErrorMessage] = useState("");
  const [feLogs, setFeLogs] = useState<Log[]>([]);
  const [beLogs, setBeLogs] = useState<Log[]>([]);
  const [showWeightsModal, setShowWeightsModal] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  const ready = status.status === "done" && (summary?.ranked ?? 0) > 0;

  const flog = useCallback((level: Log["level"], msg: string) => {
    setFeLogs((prev) => [...prev, { ts: nowTs(), level, source: "frontend", msg }]);
  }, []);

  const mergedLogs = useMemo(
    () => [...feLogs, ...beLogs].sort((a, b) => a.ts.localeCompare(b.ts)),
    [feLogs, beLogs]
  );

  const activeFilterCount = useMemo(() => {
    let n = 0;
    if (filters.minScore > 0) n++;
    if (filters.minYoe > 0 || filters.maxYoe < 50) n++;
    if (filters.notice.length) n++;
    return n;
  }, [filters]);

  const noticeBucket = (days: number) =>
    days === 0 ? "immediate" : days <= 30 ? "30" : days <= 60 ? "60" : "90";

  const filteredLb = useMemo(() => {
    if (!lb) return null;
    if (activeFilterCount === 0) return lb;
    const items = lb.items.filter((r) => {
      if (r.score < filters.minScore) return false;
      const y = r.yoe ?? 0;
      if (y < filters.minYoe || y > filters.maxYoe) return false;
      if (filters.notice.length && !filters.notice.includes(noticeBucket(r.notice_days))) return false;
      return true;
    });
    return { ...lb, items };
  }, [lb, filters, activeFilterCount]);

  // close filter/export dropdowns on outside click
  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) setShowFilter(false);
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setShowExport(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const toggleNotice = (b: string) =>
    setFilters((f) => ({ ...f, notice: f.notice.includes(b) ? f.notice.filter((x) => x !== b) : [...f.notice, b] }));

  const runExport = (n: number) => { if (n > 0) { setExportN(n); window.open(api.exportUrl(n), "_blank"); setShowExport(false); } };

  const taskId = dbEnabled ? (status.task_id || null) : null;

  const refreshShortlists = useCallback(() => {
    if (!taskId) { setShortlists([]); return; }
    api.shortlists(taskId).then((s) => setShortlists(s.items || [])).catch(() => setShortlists([]));
  }, [taskId]);

  const addToShortlist = useCallback(async (shortlistId: string, row: Row) => {
    if (!taskId) return;
    try {
      await api.addMember(shortlistId, {
        candidate_id: row.candidate_id, rank: row.rank, score: row.score,
        current_title: row.title || undefined, current_company: row.company || undefined,
        years_experience: row.yoe ?? undefined, task_id: taskId,
      } as any);
      flog("success", `Added ${row.candidate_id} to shortlist`);
      refreshShortlists();
    } catch (e: any) { flog("error", `Could not add to shortlist: ${e?.message || e}`); }
  }, [taskId, refreshShortlists, flog]);

  const createShortlist = useCallback(async (name: string): Promise<Shortlist | null> => {
    if (!taskId) return null;
    try {
      const sl = await api.createShortlist(taskId, name);
      flog("success", `Created shortlist "${name}"`);
      refreshShortlists();
      return sl;
    } catch (e: any) { flog("error", `Could not create shortlist: ${e?.message || e}`); return null; }
  }, [taskId, refreshShortlists, flog]);

  const changeWeights = (w: Weights) => { setWeights(w); setDirty(true); };
  const changeParams = (p: Params) => { setParams(p); setDirty(true); };
  const changeRole = (r: string) => { setRole(r); setDirty(true); };

  const toggleCompare = useCallback((id: string) => {
    setCompareIds((prev) => {
      if (prev.includes(id)) { flog("info", `Removed ${id} from compare`); return prev.filter((x) => x !== id); }
      if (prev.length >= 4) { flog("warn", "Compare holds a maximum of 4 candidates — remove one first."); return prev; }
      flog("info", `Added ${id} to compare (${prev.length + 1}/4)`);
      return [...prev, id];
    });
  }, [flog]);

  // init
  useEffect(() => {
    flog("info", "Frontend ready · Next.js dashboard connected to /api proxy");
    api.roles().then((r) => {
      setRoles(r.roles);
      // Don't auto-select any role on initial load - show "Select job role" placeholder
      flog("success", `Loaded ${r.roles.length} job roles · default dataset ${r.default_file_exists ? "found" : "missing"}`);
    }).catch(() => flog("error", "Could not reach backend /api/roles"));
    api.status().then((s) => { setStatus(s); if (s.status === "done") refreshAll(); }).catch(() => {});
    // Restore staged file info on page refresh
    api.staged().then((stagedData) => {
      if (stagedData.name && stagedData.size_mb) {
        setStaged({ name: stagedData.name, size_mb: stagedData.size_mb });
        // Also set hasRanked to true if there was a previous ranking (status is done)
        api.status().then((s) => {
          if (s.status === "done") {
            setHasRanked(true);
            refreshAll();
          }
        }).catch(() => {});
      }
    }).catch(() => {});
    api.logs().then((r) => setBeLogs(r.logs)).catch(() => {});
    api.dbStatus().then((d) => setDbEnabled(!!d.enabled)).catch(() => setDbEnabled(false));
    return () => { if (poll.current) clearInterval(poll.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // poll backend logs while running or while the Audit tab is open
  useEffect(() => {
    if (!(status.status === "running" || tab === "audit")) return;
    const id = setInterval(() => { api.logs().then((r) => setBeLogs(r.logs)).catch(() => {}); }, 1500);
    api.logs().then((r) => setBeLogs(r.logs)).catch(() => {});
    return () => clearInterval(id);
  }, [status.status, tab]);

  // drag-and-drop / browse upload
  const onFile = useCallback(async (file: File) => {
    const mb = (file.size / 1e6).toFixed(1);
    flog("info", `Staging '${file.name}' (${mb} MB)…`);
    setUploading(true);
    setShowUploadError(false);
    setUploadErrorMessage("");
    try {
      const r = await api.stage(file);
      setStaged({ name: r.filename, size_mb: r.size_mb });
      setDirty(true);
      flog("success", `Uploaded '${r.filename}' (${r.size_mb} MB) — ready to rank`);
      api.logs().then((x) => setBeLogs(x.logs)).catch(() => {});
    } catch (e: any) {
      flog("error", `Upload failed: ${e.message || e.toString() || "Unknown error occurred"}`);
      // Show error in UI
      const errorMessage = e.message || e.toString() || "Unknown error occurred";
      setShowUploadError(true);
      setUploadErrorMessage(errorMessage);
      console.error("Upload failed:", errorMessage);
    } finally { setUploading(false); }
  }, [flog]);

  const refreshAll = useCallback(async () => {
    try {
      const s = await api.summary(); setSummary(s);
      const l = await api.leaderboard(1, 100, ""); setLb(l); setPage(1);
      setAnalytics(null); setCompliance(null); setHoneypots(null); setJobIntent(null);
    } catch { /* ignore */ }
  }, []);

  const onRank = useCallback(async () => {
    if (!role) return;
    if (!staged) {
      setShowUploadError(true);
      setUploadErrorMessage("Upload a candidate file before ranking.");
      flog("error", "Cannot rank: upload a candidate file first.");
      return;
    }
    flog("info", `POST /api/rank · role='${role}' · dataset=${staged.name}`);
    try {
      await api.rank({
        role, weights,
        yoe_ideal: params.yoe_ideal, yoe_ok: params.yoe_ok,
        notice_pref: params.notice_pref,
        integrity: params.integrity, availability: params.availability,
      });
      setStatus((s) => ({ ...s, status: "running", message: "Starting…" }));
      flog("info", "Backend accepted the job — polling /api/status every 1.5s…");
      if (poll.current) clearInterval(poll.current);
      poll.current = setInterval(async () => {
        const s = await api.status(); setStatus(s);
        if (s.status === "done") {
          if (poll.current) clearInterval(poll.current);
          setDirty(false); 
          setHasRanked(true); // Mark that we've ranked at least once
          flog("success", `Ranking done in ${s.runtime}s — loading leaderboard`);
          refreshAll();
          // Supabase persistence + shortlist seeding finishes just after "done"; re-fetch shortly.
          if (dbEnabled) setTimeout(() => refreshShortlists(), 1500);
        }
        if (s.status === "error") {
          if (poll.current) clearInterval(poll.current);
          flog("error", `Backend error: ${s.message}`);
        }
      }, 1500);
    } catch (e) { flog("error", `Rank request failed: ${e}`); }
  }, [role, weights, params, staged, refreshAll, flog, dbEnabled, refreshShortlists]);

  // leaderboard paging + search
  useEffect(() => {
    if (!ready) return;
    const t = setTimeout(() => { api.leaderboard(page, 100, search).then(setLb).catch(() => {}); }, search ? 300 : 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, search, ready]);

  // lazy load per-tab data
  useEffect(() => {
    if (!ready) return;
    if (tab === "insights") api.analytics().then(setAnalytics).catch(() => {});
    if (tab === "governance" && !compliance) api.compliance().then(setCompliance).catch(() => {});
    if (tab === "integrity") api.honeypots().then(setHoneypots).catch(() => {});
    if (tab === "role" && !jobIntent) api.jobIntent().then(setJobIntent).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, ready]);

  // load shortlists for the current ranking task (Supabase-backed)
  useEffect(() => {
    if (ready && taskId) refreshShortlists();
    else setShortlists([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, taskId]);

  // candidate detail
  useEffect(() => {
    if (!selId) { setDetail(null); return; }
    setDetail(null);
    flog("info", `GET /api/candidate/${selId} — opening profile`);
    api.candidate(selId).then(setDetail).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selId]);

  const running = status.status === "running";

  // Simple file upload component
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFile(file);
    }
  };

  return (
    <div className="flex"> 
      <Sidebar tab={tab} setTab={setTab} mobileOpen={mobileNavOpen} onMobileClose={() => setMobileNavOpen(false)} />
      <main className="flex-1 min-w-0"> 
        {tab === "candidates" && <TopBar tabLabel={tab} onMenuClick={() => setMobileNavOpen(true)} />}
        <div className="px-4 sm:px-6 lg:px-7 py-4 sm:py-6 space-y-5">
          {/* Mobile top bar with hamburger (candidates tab carries it in TopBar) */}
          {tab !== "candidates" && (
            <div className="lg:hidden flex items-center gap-3">
              <button
                onClick={() => setMobileNavOpen(true)}
                className="p-2 -ml-1 rounded-lg border border-line bg-white text-ink-soft hover:bg-gray-50"
                aria-label="Open navigation menu"
              >
                <IconMenu className="h-5 w-5" />
              </button>
              <span className="font-extrabold tracking-tight text-ink">Nexthire</span>
            </div>
          )}
          {/* title row - changes based on active tab */}
          <div className="flex items-end justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-[clamp(1.25rem,1rem+1.4vw,1.75rem)] font-extrabold tracking-tight">
                {tab === "candidates" ? "Rank and Shortlist" : 
                 tab === "insights" ? "Insights & Analytics" :
                 tab === "integrity" ? "Integrity & Honeypot Detection" :
                 tab === "governance" ? "Governance & Compliance" :
                 tab === "role" ? "Role Management" :
                 tab === "compare" ? "Candidate Comparison" :
                 tab === "pipeline" ? "Pipeline Overview" :
                 tab === "nextai" ? "NextAI Assistant" :
                 tab === "audit" ? "Audit Logs" :
                 tab === "settings" ? "Settings" : "Dashboard"}
              </h1>
              <p className="text-sm text-ink-muted mt-1">
                {tab === "candidates" ? (
                  ready
                    ? <>{summary!.ranked.toLocaleString()} candidates scored against <span className="font-semibold text-ink-soft">{summary!.role}</span> · updated just now</>
                    : running ? <>{status.message || "Ranking…"} {status.ingested ? `· ${status.ingested.toLocaleString()} ingested` : ""}</>
                    : <>Upload a file, select a role, and click <span className="font-semibold">Rank candidates</span> to begin.</>
                ) : tab === "insights" ? (
                  <>View recruitment analytics and trends</>
                ) : tab === "integrity" ? (
                  <>Monitor honeypot candidates and integrity checks</>
                ) : tab === "governance" ? (
                  <>Review compliance and governance data</>
                ) : tab === "role" ? (
                  <>Manage job roles and requirements</>
                ) : tab === "compare" ? (
                  <>Compare candidate profiles side by side</>
                ) : tab === "pipeline" ? (
                  <>Track candidate pipeline progress</>
                ) : tab === "nextai" ? (
                  <>AI-powered recruitment assistant</>
                ) : tab === "audit" ? (
                  <>View system activity logs</>
                ) : tab === "settings" ? (
                  <>Configure application settings</>
                ) : null}
              </p>
            </div>
          </div>

          {/* Upload Controls - Only visible on Candidates page */}
          {tab === "candidates" && (
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-3 flex-wrap">
                {/* Simple Upload Button - Shows "Uploaded ✓" with filename after staging, or upload state */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json,.jsonl"
                  className="hidden"
                  onChange={handleFileChange}
                />
                <button
                  onClick={handleUploadClick}
                  disabled={running || uploading}
                  className={`btn-primary flex items-center gap-2 disabled:opacity-50 ${staged ? "bg-positive/10 border-positive text-positive hover:bg-positive/20" : ""}`}
                >
                  {uploading ? (
                    <>
                      <IconUpload className="h-4 w-4 animate-pulse" />
                      Uploading...
                    </>
                  ) : staged ? (
                    <>
                      <IconCheck className="h-4 w-4" />
                      Uploaded ✓
                    </>
                  ) : (
                    <>
                      <IconUpload className="h-4 w-4" />
                      Upload
                    </>
                  )}
                </button>
                
                {/* Show file name and size if staged */}
                {staged && (
                  <span className="text-sm text-ink-muted">
                    {staged.name} ({staged.size_mb} MB)
                  </span>
                )}

                {/* Role Selection Dropdown - Now persists selection after ranking */}
                <div className="relative">
                  <span className={`pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-2 w-2 rounded-full ${role ? "bg-positive" : "bg-gray-200"}`} />
                  <select
                    value={role}
                    onChange={(e) => changeRole(e.target.value)}
                    disabled={running}
                    className="appearance-none bg-white border border-line rounded-lg pl-7 pr-8 py-2 text-sm font-medium text-black focus:outline-none focus:ring-2 focus:ring-brand/30 cursor-pointer min-w-[180px] disabled:opacity-50"
                  >
                    {!role && <option value="" disabled>Select job role</option>}
                    {roles.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                  <IconChevron className="h-4 w-4 absolute right-2 top-1/2 -translate-y-1/2 rotate-90 text-ink-faint pointer-events-none" />
                </div>

                {/* Rank Candidates Button - Shows "Re-rank" only when role/weights are changed AFTER initial ranking */}
                <button
                  onClick={onRank}
                  disabled={running || !role || !staged}
                  title={!staged ? "Upload a candidate file first" : undefined}
                  className="btn-primary disabled:opacity-50 flex items-center gap-2"
                >
                  {running ? "Ranking..." : (hasRanked && dirty) ? (
                    <>
                      <IconRefresh className="h-4 w-4" />
                      Re-rank
                    </>
                  ) : "Rank Candidates"}
                </button>

                {/* Error message */}
                {showUploadError && uploadErrorMessage && (
                  <span className="text-sm text-danger">{uploadErrorMessage}</span>
                )}
              </div>

              {/* Adjust Weights Button with Donut Icon - Right aligned */}
              <div className="flex items-center gap-2">
                {/* Start New Task Button - appears only after ranking */}
                {hasRanked && (
                  <button
                    onClick={() => { setRole(""); setStaged(null); setSummary(null); setLb(null); setHasRanked(false); setDirty(false); setStatus({ status: "idle", message: "", role: null, file: null, file_size_mb: null, ingested: 0, ranked: 0, honeypots: 0, runtime: 0 }); }}
                    disabled={running}
                    className="btn flex items-center gap-2 bg-white border border-line text-ink-soft hover:bg-gray-50 disabled:opacity-50"
                  >
                    <IconRefresh className="h-4 w-4" />
                    Start New Task
                  </button>
                )}
                
                {/* Adjust Weights Button with Donut Icon - Right aligned */}
                <button
                  onClick={() => setShowWeightsModal(true)}
                  disabled={running}
                  className="btn-primary flex items-center gap-2 disabled:opacity-50"
                >
                  <IconDonut className="h-4 w-4" />
                  Adjust Weights
                </button>
              </div>
            </div>
          )}

          {/* KPIs - Only visible on Candidates page */}
          {tab === "candidates" && (ready && summary ? <Kpis s={summary} /> : <KpiSkeleton running={running} />)}

          {/* Search bar - visible from start */}
          {tab === "candidates" && (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="relative w-full sm:max-w-md sm:flex-1">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint">
                  <IconSearch className="h-4 w-4" />
                </span>
                <input
                  type="text"
                  placeholder="Search candidates by name or ID..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-white border border-line rounded-lg pl-10 pr-4 py-2 text-sm placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
                />
              </div>

              {/* Page Navigator */}
              {lb && lb.pages > 1 && (
                <div className="flex items-center gap-1">
                  <button 
                    disabled={page <= 1} 
                    onClick={() => setPage(page - 1)}
                    className="btn-ghost px-2 py-1.5 disabled:opacity-40"
                  >
                    <IconChevron className="h-4 w-4 rotate-180" />
                  </button>
                  <span className="px-2 text-sm text-ink-muted">
                    {lb.page} / {lb.pages}
                  </span>
                  <button 
                    disabled={page >= lb.pages} 
                    onClick={() => setPage(page + 1)}
                    className="btn-ghost px-2 py-1.5 disabled:opacity-40"
                  >
                    <IconChevron className="h-4 w-4" />
                  </button>
                </div>
              )}
              
              <div className="flex items-center gap-3">
                {/* Filter Button + Panel */}
                <div className="relative" ref={filterRef}>
                  <button
                    onClick={() => { setShowFilter((s) => !s); setShowExport(false); }}
                    className={`btn flex items-center gap-2 border ${activeFilterCount > 0 ? "bg-brand-wash border-brand/40 text-brand-dark" : "bg-white border-line text-ink-soft hover:bg-gray-50"}`}
                  >
                    <IconFilter className="h-4 w-4" />
                    Filter
                    {activeFilterCount > 0 && (
                      <span className="ml-0.5 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-brand text-white text-[10px] font-bold">
                        {activeFilterCount}
                      </span>
                    )}
                  </button>
                  {showFilter && (
                    <div className="absolute right-0 top-full mt-1.5 w-72 bg-white border border-line rounded-xl shadow-pop z-20 overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2.5 border-b border-line bg-gray-50/60">
                        <span className="text-xs font-semibold text-ink-soft uppercase tracking-wide">Filters</span>
                        <button onClick={() => setFilters(DEFAULT_FILTERS)} className="text-xs text-brand hover:underline">Clear all</button>
                      </div>
                      <div className="p-4 space-y-4">
                        {/* Min score */}
                        <div>
                          <div className="flex items-center justify-between mb-1.5">
                            <label className="text-xs font-medium text-ink-soft">Minimum score</label>
                            <span className="text-xs font-bold tabular-nums text-brand">{filters.minScore}</span>
                          </div>
                          <input type="range" min={0} max={100} step={1} value={filters.minScore}
                            onChange={(e) => setFilters((f) => ({ ...f, minScore: Number(e.target.value) }))}
                            className="w-full accent-brand cursor-pointer" />
                        </div>
                        {/* Experience range */}
                        <div>
                          <label className="text-xs font-medium text-ink-soft block mb-1.5">Experience (years)</label>
                          <div className="flex items-center gap-2">
                            <input type="number" min={0} max={50} value={filters.minYoe}
                              onChange={(e) => setFilters((f) => ({ ...f, minYoe: Math.max(0, Number(e.target.value) || 0) }))}
                              className="w-full bg-white border border-line rounded-lg px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30" placeholder="Min" />
                            <span className="text-ink-faint text-xs">to</span>
                            <input type="number" min={0} max={50} value={filters.maxYoe}
                              onChange={(e) => setFilters((f) => ({ ...f, maxYoe: Number(e.target.value) || 0 }))}
                              className="w-full bg-white border border-line rounded-lg px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30" placeholder="Max" />
                          </div>
                        </div>
                        {/* Notice period */}
                        <div>
                          <label className="text-xs font-medium text-ink-soft block mb-1.5">Notice period</label>
                          <div className="flex flex-wrap gap-1.5">
                            {[{ id: "immediate", label: "Immediate" }, { id: "30", label: "≤ 30d" }, { id: "60", label: "≤ 60d" }, { id: "90", label: "90d+" }].map((opt) => (
                              <button key={opt.id} onClick={() => toggleNotice(opt.id)}
                                className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${filters.notice.includes(opt.id) ? "bg-brand text-white border-brand" : "bg-white text-ink-soft border-line hover:bg-gray-50"}`}>
                                {opt.label}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                      <div className="px-4 py-2.5 border-t border-line bg-gray-50/60 text-xs text-ink-faint">
                        {filteredLb ? `${filteredLb.items.length} of ${lb?.items.length ?? 0} on this page match` : ""}
                      </div>
                    </div>
                  )}
                </div>

                {/* Export Button with Dropdown */}
                <div className="relative" ref={exportRef}>
                  <button
                    onClick={() => { setShowExport((s) => !s); setShowFilter(false); }}
                    className="btn flex items-center gap-2 bg-white border border-line text-ink-soft hover:bg-gray-50"
                  >
                    <IconDownload className="h-4 w-4" />
                    Export {exportN > 0 && `(${exportN})`}
                  </button>
                  {showExport && (
                    <div className="absolute right-0 top-full mt-1.5 w-56 bg-white border border-line rounded-xl shadow-pop z-20 overflow-hidden">
                      <div className="px-3 py-2 text-xs font-semibold text-ink-faint uppercase tracking-wide border-b border-line">
                        Export candidates
                      </div>
                      <div className="py-1">
                        {[10, 25, 50, 100, 200, 500].map((n) => (
                          <button
                            key={n}
                            onClick={() => runExport(n)}
                            className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center justify-between ${exportN === n ? 'text-brand font-medium' : 'text-ink-soft'}`}
                          >
                            Top {n} candidates
                            {exportN === n && <IconCheck className="h-4 w-4" />}
                          </button>
                        ))}
                      </div>
                      {/* Custom count */}
                      <div className="px-3 py-2.5 border-t border-line">
                        <label className="text-[11px] font-semibold text-ink-faint uppercase tracking-wide block mb-1.5">Custom amount</label>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            min={1}
                            value={customExport}
                            onChange={(e) => setCustomExport(e.target.value)}
                            onKeyDown={(e) => { if (e.key === "Enter") runExport(parseInt(customExport, 10)); }}
                            placeholder="e.g. 75"
                            className="w-full bg-white border border-line rounded-lg px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
                          />
                          <button
                            onClick={() => runExport(parseInt(customExport, 10))}
                            disabled={!customExport || parseInt(customExport, 10) < 1}
                            className="btn-primary px-3 py-1.5 text-sm disabled:opacity-50 shrink-0"
                          >
                            Export
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {tab === "audit" ? (
            <Logs logs={mergedLogs} running={running} />
          ) : (
            <div>
              {tab === "pipeline" ? <PipelineView />
                : tab === "compare" ? <CompareView ids={compareIds} setIds={setCompareIds} ready={ready} cols={4} />
                : !ready ? (tab === "candidates" ? <LeaderboardEmptyHeader /> : <Empty />)
                : tab === "candidates" ? (filteredLb ? <Leaderboard data={filteredLb} page={page} setPage={setPage} onSelect={setSelId} compareIds={compareIds} onToggleCompare={toggleCompare} shortlists={shortlists} onAddToShortlist={taskId ? addToShortlist : undefined} onCreateShortlist={taskId ? createShortlist : undefined} /> : <Empty />)
                : tab === "insights" ? <InsightsView a={analytics} />
                : tab === "governance" ? <GovernanceView c={compliance} />
                : tab === "integrity" ? <IntegrityView h={honeypots} onLog={(m) => flog("info", m)} />
                : tab === "role" ? <RoleView j={jobIntent} onRank={onRank} running={running} onReindex={() => api.jobIntent().then(setJobIntent).catch(() => {})} />
                : <Empty />}
            </div>
          )}
        </div>
      </main>

      {/* Adjust Weights Modal Popup */}
      {showWeightsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div 
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowWeightsModal(false)}
          />
          
          {/* Modal Content */}
          <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-brand to-brand-light">
              <div className="flex items-center gap-3">
                <IconDonut className="h-5 w-5 text-white" />
                <h2 className="text-lg font-semibold text-white">Adjust the Council of Nine</h2>
              </div>
              <button 
                onClick={() => setShowWeightsModal(false)}
                className="p-1 rounded-lg hover:bg-white/20 transition-colors"
              >
                <IconClose className="h-5 w-5 text-white" />
              </button>
            </div>
            
            {/* Modal Body - Controls */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
              <Controls
                weights={weights} setWeights={changeWeights}
                params={params} setParams={changeParams}
                onApply={() => { onRank(); setShowWeightsModal(false); }} 
                running={running} dirty={dirty} />
            </div>
          </div>
        </div>
      )}

      {selId && <CandidateDrawer d={detail} loading={!detail} onClose={() => setSelId(null)} />}
    </div>
  );
}

function Detail2({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1.5 text-sm border-t border-line first:border-0">
      <span className="text-ink-faint">{label}</span>
      <span className="font-medium text-ink-soft text-right truncate max-w-[60%]">{value}</span>
    </div>
  );
}

function KpiSkeleton({ running }: { running: boolean }) {
  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] gap-3.5">
      {/* Candidates ranked */}
      <div className="card p-4">
        <div className="flex items-center gap-2 text-ink-muted text-[13px] font-medium">
          <span className="text-ink-faint"><IconUsers className="h-4 w-4" /></span>Candidates ranked
        </div>
        <div className={`mt-2 text-[28px] font-extrabold tracking-tight text-ink`}>0</div>
        <div className="text-xs text-ink-faint mt-0.5">of 0 ingested</div>
      </div>
      {/* Strong matches */}
      <div className="card p-4">
        <div className="flex items-center gap-2 text-ink-muted text-[13px] font-medium">
          <span className="text-ink-faint"><IconSpark className="h-4 w-4" /></span>Strong matches
        </div>
        <div className={`mt-2 text-[28px] font-extrabold tracking-tight text-positive`}>0</div>
        <div className="text-xs text-ink-faint mt-0.5">score ≥ 85 · tier 1</div>
      </div>
      {/* Honeypots flagged */}
      <div className="card p-4">
        <div className="flex items-center gap-2 text-ink-muted text-[13px] font-medium">
          <span className="text-ink-faint"><IconAlert className="h-4 w-4" /></span>Honeypots flagged
        </div>
        <div className={`mt-2 text-[28px] font-extrabold tracking-tight text-warn`}>0</div>
        <div className="text-xs text-ink-faint mt-0.5">excluded from ranking</div>
      </div>
      {/* Notice ≤ 30 days */}
      <div className="card p-4">
        <div className="flex items-center gap-2 text-ink-muted text-[13px] font-medium">
          <span className="text-ink-faint"><IconClock className="h-4 w-4" /></span>Notice ≤ 30 days
        </div>
        <div className={`mt-2 text-[28px] font-extrabold tracking-tight text-ink`}>0%</div>
        <div className="text-xs text-ink-faint mt-0.5">of top 100</div>
      </div>
      {/* Runtime */}
      <div className="card p-4">
        <div className="flex items-center gap-2 text-ink-muted text-[13px] font-medium">
          <span className="text-ink-faint"><IconBolt className="h-4 w-4" /></span>Runtime
        </div>
        <div className={`mt-2 text-[28px] font-extrabold tracking-tight text-brand`}>0s</div>
        <div className="text-xs text-ink-faint mt-0.5">CPU · offline</div>
      </div>
    </div>
  );
}

function LeaderboardEmptyHeader() {
  const cols = "grid-cols-[60px_minmax(150px,1fr)_minmax(240px,1.25fr)_80px_120px_130px_230px]";
  return (
    <div className="card overflow-x-auto">
      <div className={`grid ${cols} items-center gap-4 px-5 py-3 border-b border-gray-200 bg-gray-50/50 text-[11px] font-semibold tracking-wide text-gray-500 uppercase`}>
        <div className="text-center">Rank</div>
        <div className="text-center">Candidate ID</div>
        <div>Current Role</div>
        <div className="text-center">Score</div>
        <div className="text-center">Experience</div>
        <div className="text-center">Notice Period</div>
        <div><span className="inline-block w-[92px] text-center">Actions</span></div>
      </div>
      <div className="divide-y divide-gray-100">
        {/* Empty state with placeholder rows */}
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className={`grid ${cols} items-center gap-4 px-5 py-3.5`}>
            <div className="text-center">
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-ink-faint text-xs font-semibold">—</span>
            </div>
            <div className="min-w-0 text-center"><div className="font-mono text-xs text-ink-faint">—</div></div>
            <div className="min-w-0">
              <div className="font-semibold text-ink-faint truncate text-sm">—</div>
              <div className="text-xs text-ink-faint truncate mt-0.5">—</div>
            </div>
            <div className="text-center text-sm font-bold text-ink-faint">—</div>
            <div className="text-center text-sm text-ink-faint">—</div>
            <div className="flex justify-center"><span className="pill bg-gray-100 text-ink-faint">—</span></div>
            <div className="flex justify-start gap-1.5">
              <span className="h-7 w-20 rounded-full bg-gray-100" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}