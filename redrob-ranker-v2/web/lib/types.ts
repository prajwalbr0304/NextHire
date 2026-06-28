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

export type Insight = { label: string; detail: string };
export type RiskFactor = { label: string; severity: "low" | "medium" | "high" };
export type ScoreBreakdownItem = { key: string; label: string; score: number; weight: number; points: number };
export type MissingQual = { label: string; kind: "skill" | "experience" };
export type SimilarRole = { role: string; match: number };

export type Detail = Row & {
  summary: string; reasoning: string;
  rationales: Record<string, string>;
  verified_skills: string[]; all_skills: string[];
  education: { degree: string; field: string; institution: string; tier: string }[];
  career: { title: string; company: string; months: number; start: string; end: string; description: string }[];
  strengths?: Insight[];
  weaknesses?: Insight[];
  risk?: { score: number; level: "low" | "medium" | "high"; factors: RiskFactor[] };
  missing_qualifications?: MissingQual[];
  must_have_coverage?: number;
  must_have_total?: number;
  must_have_covered?: number;
  score_breakdown?: ScoreBreakdownItem[];
  similar_roles?: SimilarRole[];
};

export type Status = {
  status: "idle" | "running" | "done" | "error";
  message: string; role: string | null; file: string | null;
  file_size_mb: number | null; ingested: number; ranked: number;
  honeypots: number; runtime: number;
  task_id?: string | null; task_name?: string | null; persisted?: boolean;
};

export type WeightPct = { key: string; label: string; pct: number };

export type Summary = {
  ranked: number; ingested: number; strong_matches: number; honeypots: number;
  notice_pct: number; runtime: number; role: string | null; file: string | null;
  file_size_mb: number | null; weights: WeightPct[];
};

export type Leaderboard = { items: Row[]; total: number; page: number; size: number; pages: number };

export type Bucket = { bucket: string; count: number };
export type Labeled = { label: string; count: number };

export type Analytics = {
  score_hist: Bucket[];
  yoe_hist: Bucket[];
  company: { product: number; services: number; mixed: number };
  council_avg: { key: string; label: string; avg: number }[];
  top_skills: { name: string; count: number; verified: number }[];
  skills_heatmap: { skills: string[]; levels: string[]; matrix: number[][] };
  education: { degrees: Labeled[]; fields: Labeled[]; tiers: Labeled[] };
  tiers: Labeled[];
  funnel: { stage: string; count: number }[];
  locations: Labeled[];
};

export type FairnessGroup = {
  pool_share: number; selected_share: number; selection_rate: number;
  n_pool?: number; avg_score?: number;
};
export type FairnessAttr = {
  disparate_impact_ratio: number; passes_four_fifths: boolean;
  statistical_parity_diff?: number; score_gap?: number; selected_n?: number;
  groups: Record<string, FairnessGroup>;
};
export type BiasFlag = {
  attribute: string; severity: "high" | "medium" | "low";
  metric: string; value: number; message: string;
};
export type ScoringInfo = {
  formula: string; explanation: string;
  weights: WeightPct[];
  council: { key: string; label: string; description: string; weight: number; avg: number }[];
  gates: { name: string; type: string; detail: string }[];
};
export type Compliance = {
  fairness: Record<string, { disparate_impact_ratio: number; passes_four_fifths: boolean;
    groups: Record<string, { pool_share: number; selected_share: number; selection_rate: number }> }>;
  metrics: Record<string, FairnessAttr>;
  bias_flags: BiasFlag[];
  overall: { passes: boolean; n_flags: number; summary: string };
  scoring: ScoringInfo;
  audit: Record<string, unknown>;
};

export type TaskSummary = {
  task_id: string; name: string | null; role: string | null;
  file_name: string | null; ranked: number; honeypots: number;
  strong_matches: number; created_at: string;
};

export type TaskCandidate = {
  id?: number; rank: number; candidate_id: string; score: number;
  current_title: string | null; current_company: string | null;
  years_experience: number | null; location: string | null; country: string | null;
  verified_skills: string | null; council: Record<string, number> | null;
  notice_days: number | null; reasoning: string | null; category?: string;
};

export type ShortlistMember = {
  id: number; shortlist_id: string; candidate_id: string; rank: number | null;
  score: number | null; current_title: string | null; current_company: string | null;
  years_experience: number | null;
};

export type Shortlist = {
  id: string; task_id: string; name: string; created_at: string;
  members: ShortlistMember[]; count: number;
};

export type HoneypotItem = {
  candidate_id: string; title: string; company?: string;
  violation_key: string; violation_type: string;
  flagged_skill: string | null;
  claimed_label: string; claimed_value: string;
  baseline_label: string; baseline_value: string;
  delta: string | null;
  severity: "critical" | "high" | "medium";
  reasons: string[];
};
export type Honeypots = {
  items: HoneypotItem[];
  total: number; showing?: number;
  most_common_violation?: string; inflation_rate?: number;
  violation_counts?: { type: string; count: number }[];
};

export type Log = {
  seq?: number; ts: string; level: "info" | "success" | "warn" | "error";
  source: "frontend" | "backend"; msg: string;
};

export type RoleConfidence = {
  score: number; label: string;
  skill_coverage: number; title_clarity: number; noise_rejection: number;
  status: string; status_ok: boolean; model_version: string;
};
export type RoleStats = {
  candidates_in_pool: number; must_have_count: number; nice_to_have_count: number;
  positive_title_count: number; blocked_title_count: number;
};
export type RoleRetrieval = {
  embedding_model: string; embedding_backend: string; vector_store: string;
  top_k: number; rerank_size: number; dense_dim: number;
};
export type RoleWeight = { key: string; label: string; pct: number };
export type SignalConflict = { signal: string; severity: string; message: string };
export type RoleActivity = { type: string; ts: string; label: string };

export type JobIntent = {
  role_title: string; must_have: string[]; nice_to_have: string[];
  positive_titles: string[]; negative_titles: string[];
  product_industries: string[]; services_companies: string[]; query_text: string;
  role_id?: string; last_indexed?: string;
  confidence?: RoleConfidence; stats?: RoleStats; retrieval?: RoleRetrieval;
  weights?: RoleWeight[]; signal_conflicts?: SignalConflict[]; activity_log?: RoleActivity[];
};
