import type {
  Analytics, Compliance, Detail, Honeypots, JobIntent, Leaderboard, Log, Status, Summary,
  TaskSummary, TaskCandidate, Shortlist, ShortlistMember,
} from "./types";

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

async function post<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function del<T>(url: string): Promise<T> {
  const r = await fetch(url, { method: "DELETE" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export const api = {
  roles: () => get<{ roles: string[]; default_file: string; default_file_exists: boolean }>("/api/roles"),
  status: () => get<Status>("/api/status"),
  summary: () => get<Summary>("/api/summary"),
  staged: () => get<{ name: string | null; size_mb: number | null; path: string | null }>("/api/staged"),
  leaderboard: (page: number, size = 100, q = "") =>
    get<Leaderboard>(`/api/leaderboard?page=${page}&size=${size}&q=${encodeURIComponent(q)}`),
  candidate: (id: string) => get<Detail>(`/api/candidate/${id}`),
  analytics: () => get<Analytics>("/api/analytics"),
  compliance: () => get<Compliance>("/api/compliance"),
  honeypots: () => get<Honeypots>("/api/honeypots?limit=100000"),
  jobIntent: () => get<JobIntent>("/api/job-intent"),
  rank: async (body: Record<string, unknown>) => {
    const r = await fetch("/api/rank", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  logs: () => get<{ logs: Log[] }>("/api/logs"),

  // --- Supabase-backed tasks & shortlists (Pipeline page) ---
  dbStatus: () => get<{ enabled: boolean; url: string | null; has_key: boolean }>("/api/db-status"),
  tasks: () => get<{ enabled: boolean; tasks: TaskSummary[]; error?: string }>("/api/tasks"),
  task: (id: string) => get<Record<string, unknown>>(`/api/tasks/${id}`),
  taskCandidates: (id: string, category = "top200") =>
    get<{ items: TaskCandidate[] }>(`/api/tasks/${id}/candidates?category=${category}&limit=200`),
  shortlists: (taskId: string) => get<{ items: Shortlist[] }>(`/api/tasks/${taskId}/shortlists`),
  createShortlist: (taskId: string, name: string) =>
    post<Shortlist>("/api/shortlists", { task_id: taskId, name }),
  deleteShortlist: (id: string) => del<{ ok: boolean }>(`/api/shortlists/${id}`),
  addMember: (shortlistId: string, member: Partial<ShortlistMember> & { candidate_id: string }) =>
    post<ShortlistMember>(`/api/shortlists/${shortlistId}/members`, member),
  removeMember: (memberId: number) => del<{ ok: boolean }>(`/api/shortlist-members/${memberId}`),

  stage: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch("/api/stage", { method: "POST", body: fd });
    if (!r.ok) {
      const errorText = await r.text();
      throw new Error(errorText || "File upload failed");
    }
    return r.json() as Promise<{ filename: string; size_mb: number }>;
  },
  exportUrl: (n: number) => `/api/export?n=${n}`,
};