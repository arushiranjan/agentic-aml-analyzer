# Backend API Design — Eco-Loop Building Agents

## Overview

The backend API is built with **FastAPI** and serves as the gateway between the Next.js frontend, the LangGraph agent system, and the EnergyPlus simulation engine. All endpoints follow REST conventions with consistent error handling and Pydantic validation.

- **Base URL**: `http://localhost:8000`
- **API Prefix**: `/api/v1`
- **Documentation**: Auto-generated at `/docs` (Swagger UI) and `/redoc`
- **Format**: JSON
- **Authentication**: None (local development)

---

## Endpoint Reference

### System

| Method | Endpoint | Description | Response |
|---|---|---|---|
| `GET` | `/api/v1/system/health` | Health check — returns service status | `{status: "healthy", uptime: "..."}` |
| `GET` | `/api/v1/system/status` | Component status check | See below |

**`GET /api/v1/system/status` Response**:
```json
{
    "database": {"status": "online", "tables": 8, "size_mb": 2.4},
    "energyplus": {"status": "installed", "version": "24.1.0", "path": "..."},
    "ollama": {"status": "running", "model": "qwen3:8b", "url": "..."},
    "mcp": {"status": "ready", "tools": 9},
    "simulation": {"status": "idle", "last_run": "2026-07-26T10:00:00"}
}
```

---

### Building State

| Method | Endpoint | Description | Query Params |
|---|---|---|---|
| `GET` | `/api/v1/building/state` | Current building state | `zone_name?` |
| `GET` | `/api/v1/building/state/history` | Historical building states | `hours?=24, zone_name?` |

**`GET /api/v1/building/state` Response**:
```json
{
    "timestamp": "2026-07-26T10:00:00",
    "zones": [
        {
            "name": "Core_ZN",
            "temperature_c": 23.4,
            "humidity_pct": 45.0,
            "co2_ppm": 620,
            "illuminance_lux": 420,
            "occupancy": 12,
            "status": "comfortable"
        }
    ],
    "overall_health_score": 82
}
```

---

### Sensors

| Method | Endpoint | Description | Query Params |
|---|---|---|---|
| `GET` | `/api/v1/sensors/` | Current sensor readings | `zone_name?` |
| `GET` | `/api/v1/sensors/history` | Sensor history | `hours?=24, zone_name?, page?=1, limit?=100` |

---

### Weather

| Method | Endpoint | Description | Query Params |
|---|---|---|---|
| `GET` | `/api/v1/weather/current` | Current weather conditions | — |
| `GET` | `/api/v1/weather/history` | Weather history | `hours?=24` |

**`GET /api/v1/weather/current` Response**:
```json
{
    "timestamp": "2026-07-26T10:00:00",
    "dry_bulb_temp_c": 28.3,
    "wet_bulb_temp_c": 19.2,
    "rel_humidity_pct": 45.0,
    "wind_speed_ms": 3.2,
    "wind_direction_deg": 315,
    "solar_radiation_wm2": 620,
    "cloud_cover": "partly_cloudy"
}
```

---

### Simulation

| Method | Endpoint | Description | Query Params / Body |
|---|---|---|---|
| `POST` | `/api/v1/simulation/run` | Trigger new simulation | `{idf_path?, epw_path?, is_baseline?}` |
| `GET` | `/api/v1/simulation/{id}` | Get simulation details | — |
| `GET` | `/api/v1/simulation/history` | Simulation history | `page?=1, limit?=20, status?` |

**`POST /api/v1/simulation/run` Request**:
```json
{
    "idf_path": "energyplus/models/SmallOffice.idf",
    "epw_path": "energyplus/weather/USA_IL_Chicago.epw",
    "is_baseline": false
}
```

**`POST /api/v1/simulation/run` Response**:
```json
{
    "simulation_id": "sim_abc123",
    "status": "completed",
    "duration_seconds": 30.1,
    "output_path": "energyplus/output/sim_abc123/",
    "metrics": {
        "total_energy_kwh": 142.3,
        "hvac_energy_kwh": 98.7,
        "lighting_energy_kwh": 22.1,
        "peak_demand_kw": 45.2
    }
}
```

---

### Energy Metrics

| Method | Endpoint | Description | Query Params |
|---|---|---|---|
| `GET` | `/api/v1/energy/metrics` | Current energy metrics | — |
| `GET` | `/api/v1/energy/history` | Energy metric history | `hours?=24, metric?=total` |

---

### Comfort

| Method | Endpoint | Description | Query Params |
|---|---|---|---|
| `GET` | `/api/v1/comfort/metrics` | Current comfort (PMV/PPD) | `zone_name?` |

**`GET /api/v1/comfort/metrics` Response**:
```json
{
    "zones": [
        {
            "name": "Core_ZN",
            "pmv": 0.3,
            "ppd": 7.0,
            "category": "A",
            "status": "comfortable"
        }
    ],
    "overall_pmv": 0.25,
    "overall_ppd": 6.2
}
```

---

### Optimization

| Method | Endpoint | Description | Query Params |
|---|---|---|---|
| `GET` | `/api/v1/optimization/compare` | Baseline vs optimized | `simulation_id?` |
| `GET` | `/api/v1/optimization/savings` | Calculated savings | `hours?=24` |

**`GET /api/v1/optimization/compare` Response**:
```json
{
    "baseline": {
        "total_energy_kwh": 165.0,
        "cost_usd": 24.75,
        "carbon_kg": 82.5,
        "comfort_pmv": 0.4
    },
    "optimized": {
        "total_energy_kwh": 142.3,
        "cost_usd": 21.35,
        "carbon_kg": 71.2,
        "comfort_pmv": 0.25
    },
    "savings": {
        "energy_kwh": 22.7,
        "energy_pct": 13.8,
        "cost_usd": 3.40,
        "cost_pct": 13.7,
        "carbon_kg": 11.3,
        "carbon_pct": 13.7,
        "comfort_improved": true
    }
}
```

---

### Agents

| Method | Endpoint | Description | Query Params |
|---|---|---|---|
| `POST` | `/api/v1/agents/run-cycle` | Trigger one optimization cycle | — |
| `GET` | `/api/v1/agents/reasoning` | Recent reasoning logs | `limit?=10, agent_name?` |
| `GET` | `/api/v1/agents/decisions` | Decision timeline | `hours?=24` |

**`GET /api/v1/agents/reasoning` Response**:
```json
{
    "reasoning": [
        {
            "id": 42,
            "timestamp": "2026-07-26T10:00:06",
            "agent_name": "reasoning_agent",
            "reasoning": "Zone 3 is overcooled by 1.5°C...",
            "planned_actions": [...],
            "tool_calls": ["read_building_state", "get_historical_metrics"],
            "confidence": 0.87,
            "latency_ms": 3200
        }
    ]
}
```

---

### Reports

| Method | Endpoint | Description | Query Params |
|---|---|---|---|
| `GET` | `/api/v1/reports/` | List reports | `page?=1, limit?=10, type?` |
| `GET` | `/api/v1/reports/{id}` | Get specific report | — |

---

### WebSocket

| Protocol | Endpoint | Description |
|---|---|---|
| `WS` | `/api/v1/ws/live` | Real-time dashboard updates |

**WebSocket Message Types**:
```typescript
type WSMessage = {
    type: "sensor_update" | "simulation_complete" | "agent_reasoning" | 
          "optimization_result" | "system_status" | "alert";
    timestamp: string;
    payload: Record<string, any>;
};
```

---

## Error Handling

All errors follow a consistent format:

```json
{
    "detail": {
        "code": "SIMULATION_FAILED",
        "message": "EnergyPlus simulation failed with severe errors",
        "errors": ["Zone Core_ZN has no HVAC equipment"],
        "timestamp": "2026-07-26T10:00:42"
    }
}
```

### HTTP Status Codes

| Code | Usage |
|---|---|
| `200` | Successful request |
| `201` | Resource created (simulation started) |
| `400` | Invalid request parameters |
| `404` | Resource not found |
| `422` | Validation error (Pydantic) |
| `500` | Internal server error |
| `503` | Service unavailable (EnergyPlus/Ollama not running) |

---

## CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Rate Limiting

For the hackathon PoC, no rate limiting is applied. In production:
- `/agents/run-cycle`: 1 request per minute
- All other endpoints: 60 requests per minute
