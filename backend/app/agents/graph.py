"""LangGraph agent orchestration — real StateGraph (Part 3).

Builds and compiles a `langgraph.graph.StateGraph` wiring the 9 agents
from docs/agents.md:

    sensor -> weather -> building_state -> reasoning -> planner -> control
        -> validation --pass--> reporting -> END
        validation --fail (retry < MAX_RETRIES)--> reasoning
        validation --fail (retry >= MAX_RETRIES)--> reporting (reports the failure)

Every node calls the *actual* MCP tools (`app.mcp.tools.MCPToolClient`,
the same functions FastMCP exposes in `app/mcp/server.py`), which in turn
read/write the real, physically-evolving `BuildingSimulator` state and the
SQLite database. Nothing here is random-number-generator mock data.

`run_mock_cycle()` is kept as the public entry point name (unchanged, per
"do not redesign the APIs" — `app/api/routes/dashboard.py` imports this
exact name) but its body now compiles and invokes the real graph below.
"""
import time
import uuid
from datetime import datetime, timezone
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.config import get_settings
from app.mcp.tools import get_mcp_client
from app.services.building_simulator import get_building_simulator
from app.services.llm_service import get_llm_service

AGENT_SEQUENCE = [
    "sensor_agent",
    "weather_agent",
    "building_state_agent",
    "reasoning_agent",
    "planner_agent",
    "control_agent",
    "validation_agent",
    "reporting_agent",
]


class CycleState(TypedDict, total=False):
    cycle_id: str
    start_time: float
    steps: list[dict]
    tools_used: list[str]
    building_state: dict
    weather: dict
    building_tick: object
    decision: dict
    reasoning_text: str
    confidence: float
    planned_actions: list[dict]
    control_result: dict
    validation_result: dict
    retry_count: int
    report: dict
    status: str


def _decide_action(state) -> dict:
    """Rule-based contextual planner: inspects the current building state
    and picks one concrete recommendation. Reused unchanged from the
    Phase-1 implementation — this logic already reasons about live
    simulator state, not random data."""
    if state.occupancy == 0 and state.hvac_load_kw > 1.0:
        return {
            "action": "reduce_hvac",
            "label": "Reduce HVAC",
            "mode": "off",
            "detail": f"Zone is unoccupied but HVAC load is {state.hvac_load_kw} kW ({state.hvac_mode}); "
                      f"stepping back toward idle to cut energy use with no comfort impact.",
        }
    if state.comfort_score < 65 and state.occupancy > 0:
        if state.humidity_pct > 55:
            return {
                "action": "increase_ventilation",
                "label": "Increase ventilation",
                "mode": "auto",
                "detail": f"Comfort score is {state.comfort_score}/100 with humidity at {state.humidity_pct}% "
                          f"and {state.occupancy} occupants; increasing fresh-air ventilation should help.",
            }
        return {
            "action": "adjust_setpoint",
            "label": "Adjust HVAC setpoint",
            "mode": "auto",
            "target_temp_c": 22.0,
            "detail": f"Comfort score is {state.comfort_score}/100 with indoor temp {state.indoor_temp_c}\u00b0C "
                      f"against a 22.0\u00b0C target; nudging the setpoint should restore comfort.",
        }
    if state.solar_radiation_wm2 < 150 and state.occupancy > 0 and state.hvac_mode == "idle":
        return {
            "action": "dim_lighting",
            "label": "Dim lighting",
            "mode": "auto",
            "detail": f"Low solar gain ({state.solar_radiation_wm2} W/m\u00b2) but occupancy is only "
                      f"{state.occupancy}; daylight-linked dimming can trim lighting load.",
        }
    if state.outdoor_temp_c > 27 and state.hvac_mode != "cooling" and 5 <= state.sim_time.hour <= 10:
        return {
            "action": "pre_cool",
            "label": "Pre-cool building",
            "mode": "cooling",
            "detail": f"Outdoor temperature is trending up ({state.outdoor_temp_c}\u00b0C) ahead of peak occupancy; "
                      f"pre-cooling now avoids a larger HVAC spike later.",
        }
    return {
        "action": "maintain",
        "label": "Maintain current settings",
        "mode": "auto",
        "detail": f"Comfort score is {state.comfort_score}/100 and total load is {state.total_energy_kw} kW \u2014 "
                  f"within target, no action needed this cycle.",
    }


def sensor_agent(state: CycleState) -> dict:
    mcp = get_mcp_client()
    sim = get_building_simulator()
    building_tick = sim.force_tick()
    building_state = mcp.get_building_state()
    steps = state["steps"] + [{
        "agent": "sensor_agent", "action": "get_building_state", "result": "ok",
        "detail": f"{len(building_state['zones'])} zones read; occupancy {building_tick.occupancy}",
    }]
    return {
        "building_tick": building_tick,
        "building_state": building_state,
        "steps": steps,
        "tools_used": state["tools_used"] + ["get_building_state"],
    }


def weather_agent(state: CycleState) -> dict:
    mcp = get_mcp_client()
    weather = mcp.get_weather()
    tick = state["building_tick"]
    steps = state["steps"] + [{
        "agent": "weather_agent", "action": "get_weather", "result": "ok",
        "detail": f"outdoor {tick.outdoor_temp_c}\u00b0C, {tick.weather_condition}",
    }]
    return {"weather": weather, "steps": steps, "tools_used": state["tools_used"] + ["get_weather"]}


def building_state_agent(state: CycleState) -> dict:
    tick = state["building_tick"]
    steps = state["steps"] + [{
        "agent": "building_state_agent", "action": "aggregate_state", "result": "ok",
        "detail": f"health score {state['building_state']['overall_health_score']}, "
                  f"comfort {tick.comfort_score}/100, HVAC {tick.hvac_mode}",
    }]
    return {"steps": steps}


def reasoning_agent(state: CycleState) -> dict:
    tick = state["building_tick"]
    llm = get_llm_service()
    decision = _decide_action(tick)
    prompt = (
        f"Building state: occupancy={tick.occupancy}, indoor={tick.indoor_temp_c}C, "
        f"outdoor={tick.outdoor_temp_c}C, comfort={tick.comfort_score}, "
        f"hvac_mode={tick.hvac_mode}. Candidate action: {decision['label']}."
    )
    reasoning = llm.complete(prompt=prompt)
    steps = state["steps"] + [{
        "agent": "reasoning_agent", "action": "llm_reasoning", "result": "ok",
        "detail": f"{decision['detail']} {reasoning['text']}",
        "confidence": reasoning["confidence"], "latency_ms": reasoning["latency_ms"],
    }]
    return {
        "decision": decision, "reasoning_text": reasoning["text"], "confidence": reasoning["confidence"],
        "steps": steps, "retry_count": state.get("retry_count", 0),
    }


def planner_agent(state: CycleState) -> dict:
    decision = state["decision"]
    tick = state["building_tick"]
    planned_actions = [{
        "zone": "Core_ZN", "action": decision["action"], "label": decision["label"],
        "mode": decision.get("mode", tick.hvac_mode), "target_temp_c": decision.get("target_temp_c"),
    }]
    steps = state["steps"] + [{
        "agent": "planner_agent", "action": "plan_actions", "result": "ok",
        "detail": f"1 action planned: {decision['label']}",
    }]
    return {"planned_actions": planned_actions, "steps": steps}


def control_agent(state: CycleState) -> dict:
    mcp = get_mcp_client()
    action = state["planned_actions"][0]
    control_result = mcp.control_hvac(
        zone_name=action["zone"], mode=action["mode"], target_temp_c=action.get("target_temp_c"),
        reason=state["decision"]["label"],
    )
    steps = state["steps"] + [{
        "agent": "control_agent", "action": "control_hvac", "result": "ok",
        "detail": f"applied '{state['decision']['label']}' to {action['zone']} (mode={control_result['mode']})",
    }]
    return {
        "control_result": control_result, "steps": steps,
        "tools_used": state["tools_used"] + ["control_hvac"],
    }


def validation_agent(state: CycleState) -> dict:
    mcp = get_mcp_client()
    tick = state["building_tick"]
    comfort = mcp.analyze_comfort(zone="Core_ZN")
    validation_pass = comfort["status"] == "comfortable" or tick.occupancy == 0
    validation_result = {
        "pass": validation_pass, "pmv": comfort["pmv"], "category": comfort["category"],
        "comfort_score": tick.comfort_score,
    }
    steps = state["steps"] + [{
        "agent": "validation_agent", "action": "analyze_comfort",
        "result": "pass" if validation_pass else "fail",
        "detail": f"PMV {comfort['pmv']}, category {comfort['category']}",
    }]
    retry_count = state.get("retry_count", 0) + (0 if validation_pass else 1)
    return {
        "validation_result": validation_result, "steps": steps, "retry_count": retry_count,
        "tools_used": state["tools_used"] + ["analyze_comfort"],
    }


def should_retry(state: CycleState) -> str:
    settings = get_settings()
    if state["validation_result"]["pass"]:
        return "reporting_agent"
    if state.get("retry_count", 0) >= settings.max_retries:
        return "reporting_agent"
    return "reasoning_agent"


def reporting_agent(state: CycleState) -> dict:
    mcp = get_mcp_client()
    report = mcp.generate_report(report_type="optimization")
    steps = state["steps"] + [{
        "agent": "reporting_agent", "action": "generate_report", "result": "ok",
        "detail": f"est. {report['energy_savings_pct']}% energy savings",
    }]
    status = "completed" if state["validation_result"]["pass"] else "reverted"
    return {
        "report": report, "steps": steps, "status": status,
        "tools_used": state["tools_used"] + ["generate_report"],
    }


def build_graph():
    workflow = StateGraph(CycleState)
    workflow.add_node("sensor_agent", sensor_agent)
    workflow.add_node("weather_agent", weather_agent)
    workflow.add_node("building_state_agent", building_state_agent)
    workflow.add_node("reasoning_agent", reasoning_agent)
    workflow.add_node("planner_agent", planner_agent)
    workflow.add_node("control_agent", control_agent)
    workflow.add_node("validation_agent", validation_agent)
    workflow.add_node("reporting_agent", reporting_agent)

    workflow.set_entry_point("sensor_agent")
    workflow.add_edge("sensor_agent", "weather_agent")
    workflow.add_edge("weather_agent", "building_state_agent")
    workflow.add_edge("building_state_agent", "reasoning_agent")
    workflow.add_edge("reasoning_agent", "planner_agent")
    workflow.add_edge("planner_agent", "control_agent")
    workflow.add_edge("control_agent", "validation_agent")
    workflow.add_conditional_edges(
        "validation_agent", should_retry, {"reporting_agent": "reporting_agent", "reasoning_agent": "reasoning_agent"}
    )
    workflow.add_edge("reporting_agent", END)
    return workflow.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_mock_cycle() -> dict:
    """Runs one real closed-loop pass through the compiled LangGraph agent
    graph (name kept for backward compatibility — see module docstring).
    Returns the same shape `app/api/routes/dashboard.py` already expects:
    {cycle_id, status, decision, confidence, steps, duration_ms, timestamp,
    tools_used, generated_actions, validation_result, building_tick}."""
    start = time.time()
    cycle_id = f"cycle_{uuid.uuid4().hex[:8]}"
    graph = get_graph()

    initial_state: CycleState = {
        "cycle_id": cycle_id, "steps": [], "tools_used": [], "retry_count": 0,
    }
    final_state = graph.invoke(initial_state, config={"recursion_limit": 50})

    duration_ms = round((time.time() - start) * 1000, 1)
    decision = final_state["decision"]

    return {
        "cycle_id": cycle_id,
        "status": final_state.get("status", "completed"),
        "decision": f"{decision['label']} \u2014 {decision['detail']}",
        "confidence": final_state.get("confidence", 0.0),
        "steps": final_state["steps"],
        "duration_ms": duration_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tools_used": final_state["tools_used"],
        "generated_actions": final_state["planned_actions"],
        "validation_result": final_state["validation_result"],
        "building_tick": final_state["building_tick"],
    }
