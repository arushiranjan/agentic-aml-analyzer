"""Response shapes for the Part 5 telemetry endpoints (app/api/routes/telemetry.py).
Not enforced via `response_model` (see the rest of the API — Phase 1 keeps
routes returning plain dicts), but documents the contract for the frontend
API client / OpenAPI docs.
"""
from pydantic import BaseModel


class BuildingTickOut(BaseModel):
    sim_time: str
    occupancy: int
    outdoor_temp_c: float
    indoor_temp_c: float
    humidity_pct: float
    weather_condition: str
    solar_radiation_wm2: float
    hvac_mode: str
    hvac_status: str
    hvac_load_kw: float
    lighting_load_kw: float
    equipment_load_kw: float
    total_energy_kw: float
    comfort_score: float
    carbon_kg: float


class SimulationHistoryResponse(BaseModel):
    count: int
    ticks: list[BuildingTickOut]


class AgentCycleStepOut(BaseModel):
    agent: str
    timestamp: str | None
    reasoning: str
    confidence: float | None
    latency_ms: float | None
    tool_calls: list[str]


class AgentCycleOut(BaseModel):
    cycle_id: str
    timestamp: str | None
    status: str
    decision: str
    confidence: float
    duration_ms: float
    tools_used: list[str]
    generated_actions: list[dict]
    validation_result: dict
    steps: list[AgentCycleStepOut]


class AgentsHistoryResponse(BaseModel):
    count: int
    cycles: list[AgentCycleOut]


class WeatherResponse(BaseModel):
    sim_time: str
    outdoor_temp_c: float
    condition: str
    humidity_pct: float
    solar_radiation_wm2: float
    forecast: list[dict]


class OccupancyResponse(BaseModel):
    sim_time: str
    current: int
    today_profile: list[dict]


class EnergyHistoryResponse(BaseModel):
    series: list[dict]
    peak_demand_kw: float
    daily_consumption_kwh: list[dict]
    weekly_consumption_kwh: float


class CarbonHistoryResponse(BaseModel):
    today_carbon_kg: float
    current_carbon_kg: float
    carbon_intensity_kg_per_kwh: float
    rolling_average_kg: float
    estimated_savings_pct: float
    sustainability_score: int
    series: list[dict]


class BuildingLiveResponse(BaseModel):
    sim_time: str
    indoor_temp_c: float
    outdoor_temp_c: float
    humidity_pct: float
    occupancy: int
    hvac_status: str
    hvac_mode: str
    lighting_load_kw: float
    equipment_load_kw: float
    weather_condition: str
    solar_radiation_wm2: float
    floor_summary: list[dict]
    overall_health_score: int
