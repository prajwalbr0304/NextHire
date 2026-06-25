import type {
  Analytics, Compliance, Detail, Honeypots, JobIntent, Leaderboard, Log, Status, Summary,
} from "./types";

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
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
  honeypots: () => get<Honeypots>("/api/honeypots?limit=200"),
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