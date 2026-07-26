from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    """Aggregated, single-call payload for the dashboard's top-level cards
    and charts (instructions.md: "Mock Dashboard Metrics API")."""

    timestamp: str
    energy_usage_kw: float
    energy_series: list[dict]  # [{time, value}]
    hvac_status: str
    hvac_mode: str
    indoor_temp_c: float
    outdoor_temp_c: float
    temperature_series: list[dict]  # [{time, indoor, outdoor}]
    comfort_score: int
    carbon_kg_today: float
    cost_usd_today: float
    ai_decision: str
    ai_confidence: float
    optimization_status: str
    simulation_status: str
    last_simulation_at: str | None = None


class SimulationRunRequest(BaseModel):
    idf_path: str | None = None
    epw_path: str | None = None
    is_baseline: bool = False


class SimulationRunResponse(BaseModel):
    simulation_id: str
    status: str
    duration_seconds: float
    output_path: str
    metrics: dict


class AgentCycleResponse(BaseModel):
    cycle_id: str
    status: str
    decision: str
    confidence: float
    steps: list[dict]
    duration_ms: float
    tools_used: list[str] = []
    generated_actions: list[dict] = []
    validation_result: dict = {}
