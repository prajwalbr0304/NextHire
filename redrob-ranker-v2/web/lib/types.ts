export type Council = {
  semantic_seer: number; name_rectifier: number; evidence_scout: number;
  mask_piercer: number; path_reader: number; terrain_master: number;
};

export type Row = {
  rank: number; candidate_id: string; score: number; title: string;
  company: string; yoe: number | null; location: string; country: string;
  council: Council; verified_title: boolean; product: boolean;
  location_match: boolean; active: boolean; notice_days: number;
};

export type Detail = Row & {
  summary: string; reasoning: string;
  rationales: Record<string, string>;
  verified_skills: string[]; all_skills: string[];
  education: { degree: string; field: string; institution: string; tier: string }[];
  career: { title: string; company: string; months: number; start: string; end: string; description: string }[];
};

export type Status = {
  status: "idle" | "running" | "done" | "error";
  message: string; role: string | null; file: string | null;
  file_size_mb: number | null; ingested: number; ranked: number;
  honeypots: number; runtime: number;
};

export type WeightPct = { key: string; label: string; pct: number };

export type Summary = {
  ranked: number; ingested: number; strong_matches: number; honeypots: number;
  notice_pct: number; runtime: number; role: string | null; file: string | null;
  file_size_mb: number | null; weights: WeightPct[];
};

export type Leaderboard = { items: Row[]; total: number; page: number; size: number; pages: number };

export type Analytics = {
  score_hist: { bucket: string; count: number }[];
  yoe_hist: { bucket: string; count: number }[];
  company: { product: number; services: number; mixed: number };
  council_avg: { key: string; label: string; avg: number }[];
};

export type Compliance = {
  fairness: Record<string, { disparate_impact_ratio: number; passes_four_fifths: boolean;
    groups: Record<string, { pool_share: number; selected_share: number; selection_rate: number }> }>;
  audit: Record<string, unknown>;
};

export type Honeypots = { items: { candidate_id: string; title: string; reasons: string[] }[]; total: number };

export type Log = {
  seq?: number; ts: string; level: "info" | "success" | "warn" | "error";
  source: "frontend" | "backend"; msg: string;
};

export type JobIntent = {
  role_title: string; must_have: string[]; nice_to_have: string[];
  positive_titles: string[]; negative_titles: string[];
  product_industries: string[]; services_companies: string[]; query_text: string;
};
