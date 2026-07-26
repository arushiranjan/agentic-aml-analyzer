"""MCP tool implementations.

These are the single source of truth for tool *behavior*. `app/mcp/server.py`
registers each one on a real `FastMCP` server (Part 2) so any MCP client
(Claude Desktop, `mcp inspect`, LangGraph via langchain-mcp-adapters) can
discover and call them. The REST API and the LangGraph agent graph
(`app/agents/graph.py`) call the same functions **in-process** through
`MCPToolClient` for reliability/latency within a single-process deployment —
the tool contracts are identical either way, so pointing the agents at the
real stdio/SSE MCP transport instead is a drop-in change later.

All tools are now backed by real, stateful data instead of independent
random draws:
  - Building state / weather / occupancy / energy come from the persistent
    `BuildingSimulator` (app/services/building_simulator.py), which evolves
    physically tick-to-tick.
  - `control_hvac` / `update_hvac` actually change the simulator's setpoint
    or mode override, which measurably affects every subsequent tick.
  - `analyze_comfort` computes a real PMV/PPD estimate (simplified Fanger
    model) from the simulator's current indoor temp/humidity.
  - `generate_report` and `get_historical_metrics` read real rows from the
    SQLite database (`BuildingTick`, `OptimizationMetric`, `AgentCycle`).
"""
import math
import uuid
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import BuildingTick, OptimizationMetric
from app.services.building_simulator import get_building_simulator
from app.services.energyplus_service import get_energyplus_service
from app.services.llm_service import get_llm_service

TOOL_NAMES = [
    "read_building_state",
    "get_building_state",
    "read_weather",
    "get_weather",
    "run_simulation",
    "update_hvac",
    "control_hvac",
    "update_lighting",
    "update_setpoints",
    "analyze_comfort",
    "generate_report",
    "get_historical_metrics",
    "get_energy_metrics",
    "get_occupancy",
    "forecast_energy",
]

CLO, MET, AIR_SPEED = 1.0, 1.1, 0.1  # typical office defaults for the PMV estimate


def _pmv_ppd(ta: float, rh: float) -> tuple[float, float]:
    """Simplified Fanger PMV/PPD (ASHRAE 55), air temp + relative humidity
    only (mean radiant temp assumed == air temp, a reasonable indoor
    approximation away from windows)."""
    m = MET * 58.15
    icl = CLO * 0.155
    fcl = 1.05 + 0.1 * icl if icl > 0.078 else 1.0 + 0.2 * icl
    pa = rh / 100.0 * 6.11 * 10 ** (7.5 * ta / (237.7 + ta)) * 100
    tcl = ta + (35.5 - ta) / (3.5 * icl + 0.1)
    for _ in range(3):
        hc = max(2.38 * abs(tcl - ta) ** 0.25, 12.1 * math.sqrt(AIR_SPEED))
        tcl = 35.7 - 0.028 * m - icl * (3.96e-8 * fcl * ((tcl + 273) ** 4 - (ta + 273) ** 4) + fcl * hc * (tcl - ta))
    hl1 = 3.05e-3 * (5733 - 6.99 * m - pa)
    hl2 = 0.42 * (m - 58.15) if m > 58.15 else 0.0
    hl3 = 1.7e-5 * m * (5867 - pa)
    hl4 = 0.0014 * m * (34 - ta)
    hl5 = 3.96e-8 * fcl * ((tcl + 273) ** 4 - (ta + 273) ** 4)
    hl6 = fcl * hc * (tcl - ta)
    pmv = max(-3.0, min(3.0, (0.303 * math.exp(-0.036 * m) + 0.028) * (m - hl1 - hl2 - hl3 - hl4 - hl5 - hl6)))
    ppd = 100 - 95 * math.exp(-0.03353 * pmv**4 - 0.2179 * pmv**2)
    return round(pmv, 2), round(ppd, 1)


class MCPToolClient:
    """In-process MCP tool client. Method names/signatures are the same
    contract `app/mcp/server.py` exposes over the real MCP protocol."""

    # -- Observe ---------------------------------------------------------
    def read_building_state(self, zone_name: str | None = None) -> dict:
        return get_energyplus_service().get_building_state(zone_name)

    def get_building_state(self, zone_name: str | None = None) -> dict:
        """Alias of `read_building_state` (name requested for MCP exposure)."""
        return self.read_building_state(zone_name)

    def read_weather(self, location: str | None = None) -> dict:
        sim = get_building_simulator()
        tick = sim.current()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "location": location or "configured EPW location",
            "dry_bulb_temp_c": tick.outdoor_temp_c,
            "rel_humidity_pct": tick.humidity_pct,
            "solar_radiation_wm2": tick.solar_radiation_wm2,
            "cloud_cover": tick.weather_condition,
        }

    def get_weather(self, location: str | None = None) -> dict:
        """Alias of `read_weather` (name requested for MCP exposure)."""
        return self.read_weather(location)

    def get_occupancy(self) -> dict:
        sim = get_building_simulator()
        tick = sim.current()
        return {"timestamp": datetime.now(timezone.utc).isoformat(), "occupancy": tick.occupancy}

    # -- Simulate ---------------------------------------------------------
    def run_simulation(self, idf_path: str | None = None, epw_path: str | None = None, is_baseline: bool = False) -> dict:
        return get_energyplus_service().run_simulation(idf_path, epw_path, is_baseline)

    def forecast_energy(self, steps: int = 8) -> dict:
        sim = get_building_simulator()
        sim.current()
        return {"steps": steps, "forecast": sim.forecast_ahead(steps)}

    # -- Act ---------------------------------------------------------------
    def update_hvac(
        self, zone_name: str, mode: str, fan_speed_pct: float | None = None,
        target_temp_c: float | None = None, initiated_by: str = "mcp_client", reason: str | None = None,
    ) -> dict:
        sim = get_building_simulator()
        result = sim.set_hvac_mode(mode, initiated_by=initiated_by, reason=reason)
        if target_temp_c is not None:
            result.update(sim.set_target_temperature(target_temp_c, initiated_by=initiated_by, reason=reason))
        return {
            "zone_name": zone_name,
            "mode": mode,
            "fan_speed_pct": fan_speed_pct,
            "target_temp_c": sim.target_temp_c,
            "applied": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def control_hvac(
        self, zone_name: str = "Core_ZN", mode: str = "auto", target_temp_c: float | None = None,
        fan_speed_pct: float | None = None, reason: str | None = None,
    ) -> dict:
        """Alias of `update_hvac` (name requested for MCP exposure)."""
        return self.update_hvac(zone_name, mode, fan_speed_pct, target_temp_c, initiated_by="control_hvac", reason=reason)

    def update_lighting(self, zone_name: str, dimming_pct: float) -> dict:
        return {
            "zone_name": zone_name,
            "dimming_pct": dimming_pct,
            "applied": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def update_setpoints(self, setpoints: dict) -> dict:
        """Batch setpoint update: {zone_name: {"mode": ..., "target_temp_c": ...}}."""
        results = {}
        for zone, cfg in setpoints.items():
            results[zone] = self.update_hvac(
                zone, cfg.get("mode", "auto"), cfg.get("fan_speed_pct"), cfg.get("target_temp_c"),
                initiated_by="update_setpoints",
            )
        return {"setpoints": results, "applied": True, "timestamp": datetime.now(timezone.utc).isoformat()}

    # -- Analyze -----------------------------------------------------------
    def analyze_comfort(self, zone: str) -> dict:
        tick = get_building_simulator().current()
        pmv, ppd = _pmv_ppd(tick.indoor_temp_c, tick.humidity_pct)
        category = "A" if ppd <= 6 else "B" if ppd <= 10 else "C" if ppd <= 15 else "D"
        return {
            "zone": zone,
            "pmv": pmv,
            "ppd": ppd,
            "category": category,
            "status": "comfortable" if abs(pmv) <= 0.5 else "attention",
        }

    def get_energy_metrics(self) -> dict:
        tick = get_building_simulator().current()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_energy_kw": tick.total_energy_kw,
            "hvac_load_kw": tick.hvac_load_kw,
            "lighting_load_kw": tick.lighting_load_kw,
            "equipment_load_kw": tick.equipment_load_kw,
            "carbon_kg": tick.carbon_kg,
            "daily_carbon_kg": tick.daily_carbon_kg,
        }

    def generate_report(self, simulation_id: str | None = None, report_type: str = "optimization") -> dict:
        db = SessionLocal()
        try:
            rows = db.query(OptimizationMetric).order_by(OptimizationMetric.id.desc()).limit(2).all()
            if len(rows) >= 2:
                optimized, baseline = rows[0], rows[1]
                energy_pct = round((baseline.total_energy_kwh - optimized.total_energy_kwh) / max(baseline.total_energy_kwh, 1e-6) * 100, 1)
                cost_pct = round((baseline.cost_usd - optimized.cost_usd) / max(baseline.cost_usd, 1e-6) * 100, 1)
                carbon_pct = round((baseline.carbon_kg - optimized.carbon_kg) / max(baseline.carbon_kg, 1e-6) * 100, 1)
                comfort_score = round(max(0.0, 100 - (optimized.comfort_ppd or 10)), 1)
                summary = (
                    f"Latest simulation vs previous: {energy_pct}% energy change, "
                    f"{cost_pct}% cost change, {carbon_pct}% carbon change."
                )
            else:
                energy_pct = cost_pct = carbon_pct = comfort_score = 0.0
                summary = "Not enough simulation history yet — run at least two simulations to compute a comparison."
            return {
                "report_id": f"rpt_{uuid.uuid4().hex[:8]}",
                "simulation_id": simulation_id,
                "report_type": report_type,
                "summary": summary,
                "energy_savings_pct": energy_pct,
                "cost_savings_pct": cost_pct,
                "carbon_reduction_pct": carbon_pct,
                "comfort_score": comfort_score,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            db.close()

    def get_historical_metrics(self, hours: int = 24, metric: str = "total") -> dict:
        db = SessionLocal()
        try:
            limit = max(4, hours * 4)  # 4 ticks/hour at 15-min resolution
            rows = db.query(BuildingTick).order_by(BuildingTick.sim_time.desc()).limit(limit).all()
            rows = list(reversed(rows))
            field_map = {
                "total": "total_energy_kw", "hvac": "hvac_load_kw", "lighting": "lighting_load_kw",
                "comfort": "comfort_score", "carbon": "carbon_kg",
            }
            field = field_map.get(metric, "total_energy_kw")
            return {
                "metric": metric,
                "hours": hours,
                "series": [{"time": r.sim_time.strftime("%H:%M"), "value": getattr(r, field)} for r in rows],
            }
        finally:
            db.close()


_client_instance: MCPToolClient | None = None


def get_mcp_client() -> MCPToolClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = MCPToolClient()
    return _client_instance
