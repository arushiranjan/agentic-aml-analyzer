export interface DashboardMetrics {
  timestamp: string;
  energy_usage_kw: number;
  energy_series: { time: string; value: number }[];
  hvac_status: string;
  hvac_mode: string;
  indoor_temp_c: number;
  outdoor_temp_c: number;
  temperature_series: { time: string; indoor: number; outdoor: number }[];
  comfort_score: number;
  carbon_kg_today: number;
  cost_usd_today: number;
  ai_decision: string;
  ai_confidence: number;
  optimization_status: string;
  simulation_status: string;
  last_simulation_at: string | null;
}

export interface SystemStatus {
  database: { status: string; tables: number; url: string };
  energyplus: { status: string; version?: string; path?: string; last_run?: string | null };
  ollama: { status: string; model?: string; url?: string };
  mcp: { status: string; tools: number; tool_names: string[] };
  simulation: { status: string; last_run?: string | null };
}

export interface AgentCycleStep {
  agent: string;
  action: string;
  result: string;
  detail: string;
  confidence?: number;
  latency_ms?: number;
}

export interface AgentCycleResult {
  cycle_id: string;
  status: string;
  decision: string;
  confidence: number;
  steps: AgentCycleStep[];
  duration_ms: number;
  timestamp: string;
}

export interface SimulationResult {
  simulation_id: string;
  status: string;
  duration_seconds: number;
  output_path: string;
  metrics: Record<string, number>;
}

// --- Part 5 telemetry types (minimum shape needed by the new pages) ---

export interface BuildingLive {
  sim_time: string;
  indoor_temp_c: number;
  outdoor_temp_c: number;
  humidity_pct: number;
  occupancy: number;
  hvac_status: string;
  hvac_mode: string;
  lighting_load_kw: number;
  equipment_load_kw: number;
  weather_condition: string;
  solar_radiation_wm2: number;
  floor_summary: {
    name: string;
    temperature_c: number;
    humidity_pct: number;
    co2_ppm: number;
    illuminance_lux: number;
    occupancy: number;
    status: string;
  }[];
  overall_health_score: number;
}

export interface EnergyHistory {
  series: { time: string; hvac: number; lighting: number; plug: number; total: number }[];
  peak_demand_kw: number;
  daily_consumption_kwh: { date: string; kwh: number }[];
  weekly_consumption_kwh: number;
}

export interface CarbonHistory {
  today_carbon_kg: number;
  current_carbon_kg: number;
  carbon_intensity_kg_per_kwh: number;
  rolling_average_kg: number;
  estimated_savings_pct: number;
  sustainability_score: number;
  series: { time: string; carbon_kg: number }[];
}

export interface AgentCycleStepDetail {
  agent: string;
  timestamp: string | null;
  reasoning: string;
  confidence: number | null;
  latency_ms: number | null;
  tool_calls: string[];
}

export interface AgentCycleHistoryItem {
  cycle_id: string;
  timestamp: string | null;
  status: string;
  decision: string;
  confidence: number;
  duration_ms: number;
  tools_used: string[];
  generated_actions: Record<string, string>[];
  validation_result: Record<string, unknown>;
  steps: AgentCycleStepDetail[];
}

export interface AgentsHistory {
  count: number;
  cycles: AgentCycleHistoryItem[];
}

export interface SimulationHistory {
  count: number;
  ticks: {
    sim_time: string;
    occupancy: number;
    outdoor_temp_c: number;
    indoor_temp_c: number;
    humidity_pct: number;
    hvac_mode: string;
    total_energy_kw: number;
    comfort_score: number;
    carbon_kg: number;
  }[];
}

export interface WeatherNow {
  sim_time: string;
  outdoor_temp_c: number;
  condition: string;
  humidity_pct: number;
  solar_radiation_wm2: number;
  forecast: { time: string; temp_c: number; condition: string; solar_wm2: number }[];
}

export interface OccupancyNow {
  sim_time: string;
  current: number;
  today_profile: { time: string; occupancy: number }[];
}

// --- Quantitative Savings Dashboard types ---

export interface ComparisonMetricSnapshot {
  simulation_id: string;
  total_energy_kwh: number;
  hvac_energy_kwh: number;
  lighting_energy_kwh: number;
  cooling_energy_kwh?: number;
  heating_energy_kwh?: number;
  peak_demand_kw?: number;
  cost_usd: number;
  carbon_kg: number;
  comfort_pmv: number | null;
  comfort_ppd?: number | null;
  avg_indoor_temp_c: number | null;
  timestamp: string;
}

export interface ComparisonResult {
  energy_saved_kwh: number;
  energy_saved_percent: number | null;
  hvac_saved_percent: number | null;
  cooling_saved_percent: number | null;
  heating_saved_percent: number | null;
  carbon_reduction_percent: number | null;
  avg_temp_diff_c: number | null;
  pmv_diff: number | null;
  ppd_diff: number | null;
  comfort_maintained: boolean;
}

export interface OptimizationComparison {
  baseline: ComparisonMetricSnapshot;
  optimized: ComparisonMetricSnapshot;
  comparison: ComparisonResult;
  report_id: number;
  created_at?: string;
  summary?: string;
}

export interface ComparisonHistoryItem {
  report_id: number;
  created_at: string | null;
  summary: string;
  comparison: ComparisonResult;
}

  simulation: { polling_interval_seconds: number; simulation_tick_minutes: number };
  optimization: {
    comfort_priority: number;
    max_retries: number;
    max_actions_per_cycle: number;
    cycle_interval_minutes: number;
    min_savings_threshold: number;
    optimization_mode: string;
  };
  llm: { model: string; mode: string; temperature: number; context_window: number };
  energyplus: { mode: string; idf_path: string; epw_path: string };
  read_only: boolean;
}
