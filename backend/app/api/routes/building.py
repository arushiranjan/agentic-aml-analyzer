"""Building state routes: /api/v1/building/state."""
from fastapi import APIRouter, Query

from app.mcp.tools import get_mcp_client

router = APIRouter(prefix="/api/v1/building", tags=["building"])


@router.get("/state")
def building_state(zone_name: str | None = Query(default=None)) -> dict:
    return get_mcp_client().read_building_state(zone_name)
