"""Quantitative Savings comparison routes.

- GET /api/v1/optimization/comparison/latest   latest baseline vs optimized comparison
- GET /api/v1/optimization/comparison/history   last N comparison reports (summary only)
- GET /api/v1/optimization/comparison/export    downloadable JSON or CSV of the latest comparison
"""
import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.optimization_service import get_comparison_history, get_latest_comparison

router = APIRouter(prefix="/api/v1/optimization", tags=["optimization"])


@router.get("/comparison/latest")
def comparison_latest(db: Session = Depends(get_db)) -> dict:
    payload = get_latest_comparison(db)
    if not payload:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NO_COMPARISON_YET",
                "message": "No AI cycle has been run yet. Click 'Run AI Cycle' to generate a baseline vs optimized comparison.",
            },
        )
    return payload


@router.get("/comparison/history")
def comparison_history(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)) -> dict:
    return {"history": get_comparison_history(db, limit=limit)}


def _flatten_for_csv(payload: dict) -> list[dict]:
    baseline, optimized, comparison = payload.get("baseline", {}), payload.get("optimized", {}), payload.get("comparison", {})
    rows = []
    metric_keys = [
        "simulation_id", "total_energy_kwh", "hvac_energy_kwh", "lighting_energy_kwh",
        "cooling_energy_kwh", "heating_energy_kwh", "peak_demand_kw", "cost_usd", "carbon_kg",
        "comfort_pmv", "comfort_ppd", "avg_indoor_temp_c", "timestamp",
    ]
    for key in metric_keys:
        rows.append({"metric": key, "baseline": baseline.get(key), "optimized": optimized.get(key)})
    for key, value in comparison.items():
        if key == "comfort_bounds":
            continue
        rows.append({"metric": key, "baseline": "", "optimized": value})
    return rows


@router.get("/comparison/export")
def comparison_export(format: str = Query(default="json", pattern="^(json|csv)$"), db: Session = Depends(get_db)):
    payload = get_latest_comparison(db)
    if not payload:
        raise HTTPException(status_code=404, detail={"code": "NO_COMPARISON_YET", "message": "No comparison available to export yet."})

    if format == "json":
        buf = io.StringIO(json.dumps(payload, indent=2))
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=savings_report_{payload.get('report_id', 'latest')}.json"},
        )

    rows = _flatten_for_csv(payload)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["metric", "baseline", "optimized"])
    writer.writeheader()
    writer.writerows(rows)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=savings_report_{payload.get('report_id', 'latest')}.csv"},
    )
