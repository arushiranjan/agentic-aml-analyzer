import type {
  AgentCycleResult,
  AgentsHistory,
  BuildingLive,
  CarbonHistory,
  ComparisonHistoryItem,
  DashboardMetrics,
  EnergyHistory,
  OccupancyNow,
  OptimizationComparison,
  SettingsView,
  SimulationHistory,
  SimulationResult,
  SystemStatus,
  WeatherNow,
} from "@/types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { ...init, cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${path}`);
  }
  return res.json() as Promise<T>;
}

export const getDashboardMetrics = () => req<DashboardMetrics>("/api/v1/dashboard/metrics");

export const getSystemStatus = () => req<SystemStatus>("/api/v1/system/status");

export const getHealth = () => req<{ status: string; uptime: string; version: string }>("/api/v1/system/health");

export const runSimulation = (isBaseline = false) =>
  req<SimulationResult>("/api/v1/simulation/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_baseline: isBaseline }),
  });

export const runAgentCycle = () => req<AgentCycleResult>("/api/v1/agents/run-cycle", { method: "POST" });

// --- Part 5 telemetry endpoints ---

export const getBuildingLive = () => req<BuildingLive>("/api/v1/building/live");

export const getEnergyHistory = (limit = 48) => req<EnergyHistory>(`/api/v1/energy/history?limit=${limit}`);

export const getCarbonHistory = (limit = 48) => req<CarbonHistory>(`/api/v1/carbon/history?limit=${limit}`);

export const getAgentsHistory = (limit = 20) => req<AgentsHistory>(`/api/v1/agents/history?limit=${limit}`);

export const getSimulationHistory = (limit = 48) => req<SimulationHistory>(`/api/v1/simulation/history?limit=${limit}`);

export const getWeather = () => req<WeatherNow>("/api/v1/weather");

export const getOccupancy = () => req<OccupancyNow>("/api/v1/occupancy");

export const getSettingsView = () => req<SettingsView>("/api/v1/system/settings");

// --- Quantitative Savings comparison endpoints ---

export const getLatestComparison = () =>
  req<OptimizationComparison>("/api/v1/optimization/comparison/latest");

export const getComparisonHistory = (limit = 20) =>
  req<{ history: ComparisonHistoryItem[] }>(`/api/v1/optimization/comparison/history?limit=${limit}`);

export const getComparisonExportUrl = (format: "json" | "csv") =>
  `/api/v1/optimization/comparison/export?format=${format}`;
