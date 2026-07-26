"""Real FastMCP server (Part 2) exposing Eco-Loop's building tools over the
MCP protocol.

Run standalone:

    cd backend
    python -m app.mcp.server

Transport is controlled by MCP_TRANSPORT in .env:
  - "stdio" (default) — for local MCP clients (Claude Desktop, `mcp inspect`,
    LangGraph via `langchain-mcp-adapters`' `StdioServerParameters`).
  - "sse"  — serves over HTTP on MCP_HOST:MCP_PORT for network clients.

Why FastMCP: decorator-based tool registration with automatic JSON-schema
generation from type hints/docstrings (how an LLM discovers tool names,
args, and descriptions), plus first-class stdio + SSE transports.

Every tool below delegates to `MCPToolClient` (app/mcp/tools.py) — that
class is the single source of truth for tool behavior; this file only
adds the MCP protocol wrapper around it.
"""
from app.config import get_settings
from app.mcp.tools import get_mcp_client

try:
    from fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "fastmcp is not installed. Run `pip install fastmcp` (see requirements.txt), "
        "then retry `python -m app.mcp.server`."
    ) from exc

mcp = FastMCP("EcoLoop Building Tools")
client = get_mcp_client()


@mcp.tool()
def get_building_state(zone_name: str | None = None) -> dict:
    """Read the current building state (per-zone temperature, humidity,
    CO2, illuminance, occupancy) from the active EnergyPlus service
    (mock or real, per USE_MOCK_ENERGYPLUS).

    Args:
        zone_name: Optional specific zone to query. If None, returns all zones.
    """
    return client.get_building_state(zone_name)


@mcp.tool()
def get_weather(location: str | None = None) -> dict:
    """Read current outdoor weather conditions from the live building
    simulation clock.

    Args:
        location: Optional location label override.
    """
    return client.get_weather(location)


@mcp.tool()
def get_occupancy() -> dict:
    """Read current building occupancy count."""
    return client.get_occupancy()


@mcp.tool()
def run_simulation(idf_path: str | None = None, epw_path: str | None = None, is_baseline: bool = False) -> dict:
    """Run an EnergyPlus simulation (real or mock, per USE_MOCK_ENERGYPLUS).

    Args:
        idf_path: Optional override path to the IDF building model file.
        epw_path: Optional override path to the EPW weather file.
        is_baseline: Whether this run should be tagged as the baseline for
            later savings comparisons.
    """
    return client.run_simulation(idf_path, epw_path, is_baseline)


@mcp.tool()
def forecast_energy(steps: int = 8) -> dict:
    """Forecast building energy load for the next N 15-minute intervals,
    without advancing the real simulation clock.

    Args:
        steps: Number of 15-minute intervals to forecast (default 8 = 2 hours).
    """
    return client.forecast_energy(steps)


@mcp.tool()
def control_hvac(
    zone_name: str = "Core_ZN",
    mode: str = "auto",
    target_temp_c: float | None = None,
    fan_speed_pct: float | None = None,
    reason: str | None = None,
) -> dict:
    """Control HVAC for a building zone — sets mode and/or target
    temperature. Bounds-checked (18-28C) and takes effect on the next
    simulation tick.

    Args:
        zone_name: Target thermal zone name.
        mode: 'auto' (physics decides), 'cooling', 'heating', or 'off'.
        target_temp_c: New target temperature in Celsius (18-28).
        fan_speed_pct: Fan speed percentage (0-100).
        reason: Optional human-readable reason, logged for the dashboard.
    """
    return client.control_hvac(zone_name, mode, target_temp_c, fan_speed_pct, reason)


@mcp.tool()
def update_lighting(zone_name: str, dimming_pct: float) -> dict:
    """Update lighting dimming level for a building zone.

    Args:
        zone_name: Target thermal zone name.
        dimming_pct: Dimming level percentage (0-100).
    """
    return client.update_lighting(zone_name, dimming_pct)


@mcp.tool()
def update_setpoints(setpoints: dict) -> dict:
    """Batch-update HVAC setpoints across multiple zones.

    Args:
        setpoints: Dict mapping zone names to configs, e.g.
            {"Core_ZN": {"mode": "cooling", "target_temp_c": 24}}.
    """
    return client.update_setpoints(setpoints)


@mcp.tool()
def analyze_comfort(zone: str) -> dict:
    """Analyze thermal comfort (PMV/PPD, ASHRAE 55) for a building zone,
    computed from its current live temperature/humidity.

    Args:
        zone: Thermal zone name to analyze.
    """
    return client.analyze_comfort(zone)


@mcp.tool()
def get_energy_metrics() -> dict:
    """Get the current instantaneous energy breakdown (HVAC, lighting,
    equipment, carbon) from the live building simulation."""
    return client.get_energy_metrics()


@mcp.tool()
def get_historical_metrics(hours: int = 24, metric: str = "total") -> dict:
    """Retrieve historical metrics from the database.

    Args:
        hours: Number of hours of history to retrieve.
        metric: 'total' | 'hvac' | 'lighting' | 'comfort' | 'carbon'.
    """
    return client.get_historical_metrics(hours, metric)


@mcp.tool()
def generate_report(simulation_id: str | None = None, report_type: str = "optimization") -> dict:
    """Generate an optimization summary report comparing the two most
    recent simulations.

    Args:
        simulation_id: Optional simulation ID to associate the report with.
        report_type: 'optimization' | 'daily' | 'comparison'.
    """
    return client.generate_report(simulation_id, report_type)


if __name__ == "__main__":
    settings = get_settings()
    if settings.mcp_transport == "sse":
        mcp.run(transport="sse", host=settings.mcp_host, port=settings.mcp_port)
    else:
        mcp.run(transport="stdio")
