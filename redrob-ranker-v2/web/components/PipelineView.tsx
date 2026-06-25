"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Shortlist, TaskCandidate, TaskSummary } from "@/lib/types";
import { IconChevron, IconPlus, IconTrash, IconLayers, IconDatabase, IconCheck, IconRefresh } from "./icons";

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

function AddToShortlist({ shortlists, onAdd }: { shortlists: Shortlist[]; onAdd: (slId: string) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    function onDoc(e: MouseEvent) { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);
  return (
    <div className="relative" ref={ref}>
      <button onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
        className="px-2.5 py-1 rounded-md text-xs font-medium bg-brand-wash text-brand-dark hover:bg-brand/10 flex items-center gap-1">
        <IconPlus className="h-3.5 w-3.5" /> Add
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-44 bg-white border border-line rounded-lg shadow-pop py-1 z-20">
          <div className="px-3 py-1.5 text-[11px] font-semibold text-ink-faint uppercase tracking-wide">Add to shortlist</div>
          {shortlists.length === 0 && <div className="px-3 py-2 text-xs text-ink-faint">No shortlists yet</div>}
          {shortlists.map((sl) => (
            <button key={sl.id} onClick={(e) => { e.stopPropagation(); onAdd(sl.id); setOpen(false); }}
              className="w-full text-left px-3 py-1.5 text-sm hover:bg-gray-50 flex items-center gap-2">
              <IconLayers className="h-3.5 w-3.5 text-ink-faint" /> {sl.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function PipelineView() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [taskId, setTaskId] = useState("");
  const [candidates, setCandidates] = useState<TaskCandidate[]>([]);
  const [shortlists, setShortlists] = useState<Shortlist[]>([]);
  const [loading, setLoading] = useState(false);
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
    setLoading(true);
    Promise.all([api.taskCandidates(id, "top200"), api.shortlists(id)])
      .then(([c, s]) => { setCandidates(c.items || []); setShortlists(s.items || []); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  const refreshShortlists = () => api.shortlists(taskId).then((s) => setShortlists(s.items || [])).catch(() => {});

  const createShortlist = async () => {
    const name = newName.trim() || `Shortlist ${shortlists.length + 1}`;
    setBusy(true);
    try { await api.createShortlist(taskId, name); setNewName(""); await refreshShortlists(); }
    finally { setBusy(false); }
  };

  const addMember = async (slId: string, c: TaskCandidate) => {
    try {
      await api.addMember(slId, {
        candidate_id: c.candidate_id, rank: c.rank, score: c.score,
        current_title: c.current_title || undefined, current_company: c.current_company || undefined,
        years_experience: c.years_experience ?? undefined, task_id: taskId,
      } as any);
      await refreshShortlists();
    } catch { /* ignore */ }
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
        <div className="grid lg:grid-cols-5 gap-4">
          {/* Candidates */}
          <div className="card overflow-hidden lg:col-span-3">
            <div className="px-4 py-3 border-b border-line bg-gray-50/60 flex items-center justify-between">
              <div className="font-semibold text-sm">Task candidates (top {candidates.length})</div>
              <span className="text-xs text-ink-faint">click “Add” to place into a shortlist</span>
            </div>
            <div className="max-h-[560px] overflow-auto divide-y divide-line">
              {loading && <div className="p-6 text-center text-ink-faint text-sm">Loading candidates…</div>}
              {!loading && candidates.map((c) => (
                <div key={c.candidate_id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50">
                  <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold shrink-0">{c.rank}</span>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium truncate">{c.current_title || "—"}</div>
                    <div className="text-xs text-ink-faint font-mono truncate">{c.candidate_id}{c.current_company ? ` · ${c.current_company}` : ""}</div>
                  </div>
                  <span className="text-sm font-bold tabular-nums w-9 text-right">{Number(c.score).toFixed(0)}</span>
                  <AddToShortlist shortlists={shortlists} onAdd={(slId) => addMember(slId, c)} />
                </div>
              ))}
              {!loading && !candidates.length && <div className="p-6 text-center text-ink-faint text-sm">No stored candidates for this task.</div>}
            </div>
          </div>

          {/* Shortlists */}
          <div className="lg:col-span-2 space-y-4">
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
                  <button onClick={() => deleteShortlist(sl.id)} className="p-1 rounded hover:bg-gray-100 text-ink-faint hover:text-danger" title="Delete shortlist">
                    <IconTrash className="h-3.5 w-3.5" />
                  </button>
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
        </div>
      )}
    </div>
  );
}
