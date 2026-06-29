"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Shortlist, TaskSummary } from "@/lib/types";
import { IconChevron, IconPlus, IconTrash, IconLayers, IconDatabase, IconCheck, IconRefresh, IconDownload } from "./icons";

function downloadFile(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

const csvCell = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;

function exportShortlist(sl: Shortlist, format: "csv" | "json") {
  const safeName = (sl.name || "shortlist").replace(/[^a-z0-9]+/gi, "_").toLowerCase();
  if (format === "json") {
    downloadFile(`${safeName}.json`, JSON.stringify(sl.members, null, 2), "application/json");
    return;
  }
  const headers = ["Rank", "Candidate ID", "Title", "Company", "Years Experience", "Score"];
  const rows = [...sl.members]
    .sort((a, b) => (a.rank ?? 1e9) - (b.rank ?? 1e9))
    .map((m) => [m.rank ?? "", m.candidate_id, m.current_title ?? "", m.current_company ?? "", m.years_experience ?? "", m.score ?? ""]);
  const csv = [headers, ...rows].map((r) => r.map(csvCell).join(",")).join("\r\n");
  downloadFile(`${safeName}.csv`, csv, "text/csv;charset=utf-8");
}

function ExportShortlist({ shortlist }: { shortlist: Shortlist }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    function onDoc(e: MouseEvent) { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);
  const disabled = shortlist.members.length === 0;
  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => !disabled && setOpen((o) => !o)}
        disabled={disabled}
        title={disabled ? "Add candidates to export" : "Export shortlist"}
        className="p-1 rounded hover:bg-gray-100 text-ink-faint hover:text-brand disabled:opacity-40 disabled:hover:text-ink-faint"
      >
        <IconDownload className="h-3.5 w-3.5" />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-40 bg-white border border-line rounded-lg shadow-pop py-1 z-20">
          <div className="px-3 py-1.5 text-[11px] font-semibold text-ink-faint uppercase tracking-wide">Export as</div>
          <button onClick={() => { exportShortlist(shortlist, "csv"); setOpen(false); }}
            className="w-full text-left px-3 py-1.5 text-sm hover:bg-gray-50 flex items-center gap-2">
            <IconDownload className="h-3.5 w-3.5 text-ink-faint" /> CSV (.csv)
          </button>
          <button onClick={() => { exportShortlist(shortlist, "json"); setOpen(false); }}
            className="w-full text-left px-3 py-1.5 text-sm hover:bg-gray-50 flex items-center gap-2">
            <IconDownload className="h-3.5 w-3.5 text-ink-faint" /> JSON (.json)
          </button>
        </div>
      )}
    </div>
  );
}

function SetupNotice() {
  return (
    <div className="card p-6">
      <div className="flex items-center gap-3 mb-3">
        <div className="h-10 w-10 rounded-xl bg-amber-50 text-warn grid place-items-center"><IconDatabase className="h-5 w-5" /></div>
        <div>
          <div className="font-semibold">Supabase is not configured</div>
          <div className="text-sm text-ink-muted">Connect a database to store tasks and build shortlists.</div>
        </div>
      </div>
      <ol className="text-sm text-ink-soft space-y-1.5 list-decimal pl-5">
        <li>Open the Supabase SQL Editor and run <code className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">supabase_schema.sql</code> (in the project root).</li>
        <li>Ensure the project <code className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">.env</code> has <code className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">NEXT_PUBLIC_SUPABASE_URL</code> and a service-role key.</li>
        <li>Restart the API server, then run a ranking — the task and its results are stored automatically.</li>
      </ol>
    </div>
  );
}


export default function PipelineView() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [taskId, setTaskId] = useState("");
  const [shortlists, setShortlists] = useState<Shortlist[]>([]);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.tasks().then((r) => {
      setEnabled(r.enabled);
      setTasks(r.tasks || []);
      if (r.tasks?.length) selectTask(r.tasks[0].task_id);
    }).catch(() => setEnabled(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectTask = (id: string) => {
    setTaskId(id);
    api.shortlists(id).then((s) => setShortlists(s.items || [])).catch(() => {});
  };

  const refreshShortlists = () => api.shortlists(taskId).then((s) => setShortlists(s.items || [])).catch(() => {});

  const createShortlist = async () => {
    const name = newName.trim() || `Shortlist ${shortlists.length + 1}`;
    setBusy(true);
    try { await api.createShortlist(taskId, name); setNewName(""); await refreshShortlists(); }
    finally { setBusy(false); }
  };

  const removeMember = async (memberId: number) => { await api.removeMember(memberId).catch(() => {}); refreshShortlists(); };
  const deleteShortlist = async (id: string) => { await api.deleteShortlist(id).catch(() => {}); refreshShortlists(); };

  if (enabled === false) return <SetupNotice />;
  if (enabled === null) return <div className="card p-10 text-center text-ink-faint">Connecting to database…</div>;

  const selected = tasks.find((t) => t.task_id === taskId);

  return (
    <div className="space-y-4">
      {/* Task selector */}
      <div className="card p-5">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-brand-wash text-brand grid place-items-center"><IconDatabase className="h-5 w-5" /></div>
            <div>
              <div className="font-semibold">Pipeline</div>
              <div className="text-xs text-ink-faint mt-0.5">Pick a stored ranking task, then build shortlists from its candidates.</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <select value={taskId} onChange={(e) => selectTask(e.target.value)}
                className="appearance-none bg-white border border-line rounded-lg pl-3 pr-9 py-2 text-sm font-medium text-ink min-w-[280px] focus:outline-none focus:ring-2 focus:ring-brand/30 cursor-pointer">
                {!tasks.length && <option value="">No tasks stored yet</option>}
                {tasks.map((t) => (
                  <option key={t.task_id} value={t.task_id}>{t.name || t.role || t.task_id} — {t.task_id}</option>
                ))}
              </select>
              <IconChevron className="h-4 w-4 absolute right-2.5 top-1/2 -translate-y-1/2 rotate-90 text-ink-faint pointer-events-none" />
            </div>
            <button onClick={() => api.tasks().then((r) => setTasks(r.tasks || [])).catch(() => {})}
              className="btn bg-white border border-line text-ink-soft hover:bg-gray-50" title="Refresh tasks">
              <IconRefresh className="h-4 w-4" />
            </button>
          </div>
        </div>
        {selected && (
          <div className="flex flex-wrap gap-2 mt-4">
            <span className="pill bg-gray-100 text-ink-muted">Role: {selected.role || "—"}</span>
            <span className="pill bg-gray-100 text-ink-muted">{selected.ranked?.toLocaleString()} ranked</span>
            <span className="pill bg-positive/10 text-positive">{selected.strong_matches?.toLocaleString()} strong</span>
            <span className="pill bg-amber-50 text-warn">{selected.honeypots?.toLocaleString()} honeypots</span>
            <span className="pill bg-gray-100 text-ink-faint font-mono">{selected.task_id}</span>
          </div>
        )}
      </div>

      {!tasks.length ? (
        <div className="card p-10 text-center text-ink-faint">
          No ranking tasks stored yet. Run a ranking on the <span className="font-semibold text-ink-soft">Candidates</span> tab — it will be saved here automatically.
        </div>
      ) : (
        <div className="space-y-4">
            <div className="card p-4">
              <div className="font-semibold text-sm mb-2 flex items-center gap-2"><IconLayers className="h-4 w-4 text-brand" /> Create shortlist</div>
              <div className="flex items-center gap-2">
                <input value={newName} onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && createShortlist()}
                  placeholder={`Shortlist ${shortlists.length + 1}`}
                  className="flex-1 bg-white border border-line rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30" />
                <button onClick={createShortlist} disabled={busy} className="btn-primary disabled:opacity-50">
                  <IconPlus className="h-4 w-4" /> Add
                </button>
              </div>
            </div>

            {shortlists.map((sl) => (
              <div key={sl.id} className="card overflow-hidden">
                <div className="px-4 py-2.5 border-b border-line bg-gray-50/60 flex items-center justify-between">
                  <div className="font-semibold text-sm flex items-center gap-2">
                    <IconLayers className="h-4 w-4 text-brand" /> {sl.name}
                    <span className="pill bg-brand-wash text-brand-dark">{sl.count}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <ExportShortlist shortlist={sl} />
                    <button onClick={() => deleteShortlist(sl.id)} className="p-1 rounded hover:bg-gray-100 text-ink-faint hover:text-danger" title="Delete shortlist">
                      <IconTrash className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                <div className="divide-y divide-line max-h-56 overflow-auto">
                  {sl.members.length === 0 && <div className="px-4 py-3 text-xs text-ink-faint">Empty — add candidates from the left.</div>}
                  {sl.members.map((m) => (
                    <div key={m.id} className="flex items-center gap-2 px-4 py-2">
                      <IconCheck className="h-3.5 w-3.5 text-positive shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="text-sm truncate">{m.current_title || m.candidate_id}</div>
                        <div className="text-[11px] text-ink-faint font-mono truncate">{m.candidate_id}</div>
                      </div>
                      {m.score != null && <span className="text-xs font-semibold tabular-nums">{Number(m.score).toFixed(0)}</span>}
                      <button onClick={() => removeMember(m.id)} className="p-1 rounded hover:bg-gray-100 text-ink-faint hover:text-danger">
                        <IconTrash className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
