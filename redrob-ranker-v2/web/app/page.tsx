"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Sidebar, { Tab } from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import IngestBanner from "@/components/IngestBanner";
import Kpis from "@/components/Kpis";
import Donut from "@/components/Donut";
import Controls, { Weights, Params } from "@/components/Controls";
import Leaderboard from "@/components/Leaderboard";
import CandidateDrawer from "@/components/CandidateDrawer";
import Logs from "@/components/Logs";
import { AnalyticsView, ComplianceView, IntegrityView, JobIntentView, Empty } from "@/components/Views";
import { api } from "@/lib/api";
import type {
  Analytics, Compliance, Detail, Honeypots, JobIntent, Leaderboard as LB, Log, Status, Summary,
} from "@/lib/types";
import { IconRefresh, IconDownload } from "@/components/icons";

const TABS: { id: Tab; label: string }[] = [
  { id: "leaderboard", label: "Leaderboard" }, { id: "analytics", label: "Analytics" },
  { id: "compliance", label: "Compliance" }, { id: "integrity", label: "Integrity" },
  { id: "jobintent", label: "Job Intent" }, { id: "logs", label: "Logs" },
];

function nowTs() {
  const d = new Date(); const p = (n: number, l = 2) => String(n).padStart(l, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}`;
}

const DEFAULT_W: Weights = {
  semantic_seer: 0.16, name_rectifier: 0.20, evidence_scout: 0.22,
  mask_piercer: 0.14, path_reader: 0.12, terrain_master: 0.16,
};
const DEFAULT_P: Params = {
  yoe_ideal: [6, 8], yoe_ok: [5, 9], notice_pref: 30, integrity: true, availability: true,
};
const W_LABEL: Record<string, string> = {
  semantic_seer: "Semantic Seer", name_rectifier: "Name-Rectifier", evidence_scout: "Evidence Scout",
  mask_piercer: "Mask-Piercer", path_reader: "Path-Reader", terrain_master: "Terrain Master",
};

export default function Page() {
  const [roles, setRoles] = useState<string[]>([]);
  const [role, setRole] = useState("");
  const [status, setStatus] = useState<Status>({ status: "idle", message: "", role: null, file: null, file_size_mb: null, ingested: 0, ranked: 0, honeypots: 0, runtime: 0 });
  const [summary, setSummary] = useState<Summary | null>(null);
  const [tab, setTab] = useState<Tab>("leaderboard");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [lb, setLb] = useState<LB | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [compliance, setCompliance] = useState<Compliance | null>(null);
  const [honeypots, setHoneypots] = useState<Honeypots | null>(null);
  const [jobIntent, setJobIntent] = useState<JobIntent | null>(null);
  const [selId, setSelId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [exportN, setExportN] = useState(100);
  const [weights, setWeights] = useState<Weights>(DEFAULT_W);
  const [params, setParams] = useState<Params>(DEFAULT_P);
  const [dirty, setDirty] = useState(false);
  const [staged, setStaged] = useState<{ name: string; size_mb: number } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [showUploadError, setShowUploadError] = useState(false);
  const [uploadErrorMessage, setUploadErrorMessage] = useState("");
  const [feLogs, setFeLogs] = useState<Log[]>([]);
  const [beLogs, setBeLogs] = useState<Log[]>([]);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  const ready = status.status === "done" && (summary?.ranked ?? 0) > 0;

  const flog = useCallback((level: Log["level"], msg: string) => {
    setFeLogs((prev) => [...prev, { ts: nowTs(), level, source: "frontend", msg }]);
  }, []);

  const mergedLogs = useMemo(
    () => [...feLogs, ...beLogs].sort((a, b) => a.ts.localeCompare(b.ts)),
    [feLogs, beLogs]
  );

  // live donut from the adjustable weights (updates as sliders move)
  const liveWeights = useMemo(() => {
    const total = Object.values(weights).reduce((a, b) => a + b, 0) || 1;
    return (Object.keys(weights) as (keyof Weights)[]).map((k) => ({
      key: k, label: W_LABEL[k], pct: Math.round((weights[k] / total) * 100),
    }));
  }, [weights]);

  const changeWeights = (w: Weights) => { setWeights(w); setDirty(true); };
  const changeParams = (p: Params) => { setParams(p); setDirty(true); };
  const changeRole = (r: string) => { setRole(r); setDirty(true); };

  // init
  useEffect(() => {
    flog("info", "Frontend ready · Next.js dashboard connected to /api proxy");
    api.roles().then((r) => {
      setRoles(r.roles); setRole((cur) => cur || r.roles[0]);
      flog("success", `Loaded ${r.roles.length} job roles · default dataset ${r.default_file_exists ? "found" : "missing"}`);
    }).catch(() => flog("error", "Could not reach backend /api/roles"));
    api.status().then((s) => { setStatus(s); if (s.status === "done") refreshAll(); }).catch(() => {});
    api.logs().then((r) => setBeLogs(r.logs)).catch(() => {});
    return () => { if (poll.current) clearInterval(poll.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // poll backend logs while running or while the Logs tab is open
  useEffect(() => {
    if (!(status.status === "running" || tab === "logs")) return;
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
    flog("info", `POST /api/rank · role='${role}' · dataset=${staged ? staged.name : "default"}`);
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
          setDirty(false); flog("success", `Ranking done in ${s.runtime}s — loading leaderboard`);
          refreshAll();
        }
        if (s.status === "error") {
          if (poll.current) clearInterval(poll.current);
          flog("error", `Backend error: ${s.message}`);
        }
      }, 1500);
    } catch (e) { flog("error", `Rank request failed: ${e}`); }
  }, [role, weights, params, staged, refreshAll, flog]);

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
    if (tab === "analytics" && !analytics) api.analytics().then(setAnalytics).catch(() => {});
    if (tab === "compliance" && !compliance) api.compliance().then(setCompliance).catch(() => {});
    if (tab === "integrity" && !honeypots) api.honeypots().then(setHoneypots).catch(() => {});
    if (tab === "jobintent" && !jobIntent) api.jobIntent().then(setJobIntent).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, ready]);

  // candidate detail
  useEffect(() => {
    if (!selId) { setDetail(null); return; }
    setDetail(null);
    flog("info", `GET /api/candidate/${selId} — opening profile`);
    api.candidate(selId).then(setDetail).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selId]);

  const running = status.status === "running";

  return (
    <div className="flex">
      <Sidebar tab={tab} setTab={setTab} ranked={summary?.ranked ?? 0} honeypots={summary?.honeypots ?? 0} />
      <main className="flex-1 min-w-0">
        <TopBar tabLabel={tab} roles={roles} role={role} setRole={changeRole}
          search={search} setSearch={setSearch} onRank={onRank} running={running} />

        <div className="px-7 py-6 space-y-5">
          {/* Toast Notifications */}
          {/* title row */}
          <div className="flex items-end justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight">Ranked shortlist</h1>
              <p className="text-sm text-ink-muted mt-1">
                {ready
                  ? <>{summary!.ranked.toLocaleString()} candidates scored against <span className="font-semibold text-ink-soft">{summary!.role}</span> · updated just now</>
                  : running ? <>{status.message || "Ranking…"} {status.ingested ? `· ${status.ingested.toLocaleString()} ingested` : ""}</>
                  : <>Pick a role and click <span className="font-semibold">Rank candidates</span> to begin.</>}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={onRank} disabled={running} className="btn-ghost disabled:opacity-50">
                <IconRefresh className="h-4 w-4" /> Re-rank
              </button>
              <div className="flex items-center rounded-lg border border-line bg-white overflow-hidden">
                <input type="number" min={1} value={exportN}
                  onChange={(e) => setExportN(Math.max(1, Number(e.target.value) || 1))}
                  className="w-20 px-3 py-2 text-sm focus:outline-none" />
                <a href={ready ? api.exportUrl(exportN) : undefined}
                  onClick={() => { if (ready) flog("info", `GET /api/export?n=${exportN} — downloading Excel`); }}
                  className={`btn ${ready ? "bg-white text-ink-soft hover:bg-gray-50" : "text-ink-faint pointer-events-none"} border-l border-line rounded-none`}>
                  <IconDownload className="h-4 w-4" /> Export
                </a>
              </div>
            </div>
          </div>

          <IngestBanner status={status} staged={staged} uploading={uploading} onFile={onFile} 
            showError={showUploadError} errorMessage={uploadErrorMessage} />

          {ready && summary ? <Kpis s={summary} /> : <KpiSkeleton running={running} />}

          {/* inner tabs */}
          <div className="flex items-center gap-1 border-b border-line">
            {TABS.map((t) => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`px-4 py-2.5 text-sm font-medium -mb-px border-b-2 transition ${
                  tab === t.id ? "border-brand text-brand-dark" : "border-transparent text-ink-muted hover:text-ink"}`}>
                {t.label}
              </button>
            ))}
          </div>

          {tab === "logs" ? (
            <Logs logs={mergedLogs} running={running} />
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-5 items-start">
              <div className="min-w-0">
                {!ready ? <Empty />
                  : tab === "leaderboard" ? (lb ? <Leaderboard data={lb} page={page} setPage={setPage} onSelect={setSelId} /> : <Empty />)
                  : tab === "analytics" ? <AnalyticsView a={analytics!} />
                  : tab === "compliance" ? <ComplianceView c={compliance!} />
                  : tab === "integrity" ? <IntegrityView h={honeypots!} />
                  : <JobIntentView j={jobIntent!} />}
              </div>
              <div className="space-y-4">
                <Donut weights={liveWeights} />
                <Controls
                  weights={weights} setWeights={changeWeights}
                  params={params} setParams={changeParams}
                  onApply={onRank} running={running} dirty={dirty} />
                {ready && summary && (
                  <div className="card p-5">
                    <div className="font-semibold mb-3">Run details</div>
                    <Detail2 label="Dataset" value={summary.file ?? "—"} />
                    <Detail2 label="Size" value={summary.file_size_mb ? `${summary.file_size_mb} MB` : "—"} />
                    <Detail2 label="Role" value={summary.role ?? "—"} />
                    <Detail2 label="Runtime" value={`${summary.runtime}s · CPU`} />
                    <Detail2 label="Honeypots" value={String(summary.honeypots)} />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>

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
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="card p-4">
          <div className="h-3 w-24 bg-gray-100 rounded" />
          <div className={`h-7 w-16 bg-gray-100 rounded mt-3 ${running ? "animate-pulse" : ""}`} />
          <div className="h-3 w-20 bg-gray-100 rounded mt-2" />
        </div>
      ))}
    </div>
  );
}
