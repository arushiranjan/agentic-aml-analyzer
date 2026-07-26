// Types mirror backend/main.py + tools/*.py response shapes exactly.
// Keep these in sync if a backend field is renamed — nothing here changes
// backend behavior, it only describes it for the compiler.

export interface UploadResponse {
  dataset_id: string;
  rows: number;
  columns: string[];
  message: string;
}

export interface DatasetSummary {
  dataset_id: string;
  num_transactions: number;
  num_customers: number;
  num_beneficiaries: number;
  date_range: [string, string];
  has_device_id: boolean;
  has_merchant_category: boolean;
  model_trained: boolean;
  model_trained_at: string | null;
}

export interface SystemStatus {
  planner_status: string;
  planner_mode: "llm" | "keyword_fallback";
  available_tools: string[];
  rule_engine_status: string;
  rule_count: number;
  rules: string[];
  rule_importance: Record<string, number>;
}

export interface ModelStatus {
  dataset_id: string;
  trained: boolean;
  trained_at: string | null;
  feature_columns: string[];
  contamination_default: number;
  algorithm: string;
}

export interface RuleHit {
  rule: string;
  score: number;
  importance: number;
  reason: string;
}

export interface HistoryDelta {
  previous_score: number;
  previous_risk_level: string;
  previous_timestamp: string;
  change: number;
}

export interface RiskReportRow {
  customer_id: string;
  rule_score: number;
  ml_score: number;
  final_score: number;
  risk_level: "Low" | "Medium" | "High";
  confidence: number;
  confidence_breakdown: { rules_pct: number; ml_pct: number };
  rule_hits: RuleHit[];
  is_ml_anomaly: boolean;
  evidence: string[];
  weights_used: { rule_weight: number; ml_weight: number };
  history_delta?: HistoryDelta | null;
}

export interface ExplanationEntry {
  customer_id: string;
  risk_level: string;
  final_score: number;
  confidence_pct: number;
  rule_score: number;
  ml_score: number;
  is_ml_anomaly: boolean;
  evidence: string[];
  rule_hits: { rule: string; reason: string }[];
  explanation: string;
}

export interface GraphHit {
  customer_id: string;
  rule: string;
  score: number;
  reason: string;
}

export interface CentralityRow {
  customer_id: string;
  degree: number;
  pagerank: number;
  betweenness: number;
  passthrough_ratio: number;
}

export interface GraphResult {
  graph_hits: GraphHit[];
  centrality: CentralityRow[];
  message?: string;
}

export interface TransactionStats {
  count?: number;
  total_amount?: number;
  average_amount?: number;
  median_amount?: number;
  std_amount?: number;
  min_amount?: number;
  max_amount?: number;
  date_range?: [string, string];
  message?: string;
}

export interface DistributionData {
  amount_histogram: { counts: number[]; bin_edges: number[] };
  daily_txn_counts: { dates: string[]; counts: number[] };
  hourly_txn_counts: { hours: number[]; counts: number[] };
  channel_counts?: { labels: string[]; counts: number[] };
  country_counts?: { labels: string[]; counts: number[] };
}

export interface EdaResult {
  missing_values: Record<string, unknown>;
  transaction_stats: TransactionStats;
  distribution: DistributionData;
}

export interface PlanStep {
  tool: string;
  why: string;
}

export interface Plan {
  goal: string;
  steps: PlanStep[];
  tools: string[];
  filters: Record<string, unknown>;
  customer_id: string | null;
  reasoning: string;
  source: "llm" | "fallback";
}

export interface ExecutorResults {
  tools_executed: string[];
  warning?: string;
  eda?: EdaResult;
  features?: { features: Record<string, unknown>[] };
  graph?: GraphResult;
  rules?: { rule_results: unknown[]; raw_hits: unknown[] };
  ml?: { ml_results: { customer_id: string; ml_score: number; is_anomaly: boolean }[]; model_status?: string };
  risk_score?: { risk_report: RiskReportRow[] };
  explanation?: { explanations: ExplanationEntry[] };
}

export interface ChatResponse {
  query: string;
  plan: Plan;
  results: ExecutorResults;
}

export interface TimelineEvent {
  timestamp: string;
  amount: number;
  beneficiary_id: string;
  gap_seconds_since_prev: number | null;
}

export interface TimelineResult {
  customer_id: string;
  events: TimelineEvent[];
  caption: string;
}

export interface HistorySnapshot {
  timestamp: string;
  final_score: number;
  risk_level: string;
}

export interface CustomerDetails extends ExecutorResults {
  customer_stats: Record<string, unknown>;
  history: HistorySnapshot[];
}

export interface GraphVizNode {
  source?: string;
}

export interface GraphVizResult {
  nodes: string[];
  edges: { source: string; target: string; amount: number }[];
}

/** One entry in the Investigation page's session history — stores the
 *  FULL response, not a placeholder string, so past investigations remain
 *  fully visible when you look back at them (fixes the old Streamlit
 *  "See results above" bug). */
export interface InvestigationEntry {
  id: string;
  query: string;
  timestamp: string;
  response: ChatResponse;
}
