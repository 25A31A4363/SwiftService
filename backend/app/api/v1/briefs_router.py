import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path

from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.domain import (
    OperationalBriefResponse,
    BriefGenerateRequest
)
from backend.app.services.brief_service import BriefService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/briefs", tags=["Phase 14: AI Operational Intelligence Briefs"])


@router.post("/generate", response_model=ApiResponse[OperationalBriefResponse])
def generate_operational_brief(
    payload: Optional[BriefGenerateRequest] = None,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ANALYTICS_EXPORT))
):
    """
    Generate a concise, evidence-grounded operational intelligence brief for executive leadership.
    All numerical claims originate strictly from deterministic database aggregations.
    Claims are labeled with epistemic status: OBSERVATION, HYPOTHESIS, RECOMMENDATION, UNKNOWN.
    """
    org_id = user.get("organizationId", "org-apex-01")
    store_id = payload.storeId if payload else None
    region_id = payload.regionId if payload else None
    timeframe_type = (payload.timeframeType or "DAILY").upper() if payload else "DAILY"
    start_date = payload.startDate if payload else None
    end_date = payload.endDate if payload else None

    # Enforce store scope for store-level roles
    if user.get("role") in ("STORE_MANAGER", "MAINTENANCE_TEAM") and user.get("storeId"):
        store_id = user.get("storeId")

    brief = BriefService.generate_brief(
        conn=conn,
        organization_id=org_id,
        store_id=store_id,
        region_id=region_id,
        timeframe_type=timeframe_type,
        start_date=start_date,
        end_date=end_date,
        user_id=user.get("id")
    )
    return ApiResponse(success=True, data=brief)


@router.get("/latest", response_model=ApiResponse[Optional[OperationalBriefResponse]])
def get_latest_brief(
    storeId: Optional[str] = Query(None, description="Optional store filter"),
    timeframeType: Optional[str] = Query(None, description="DAILY | WEEKLY | CUSTOM"),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ANALYTICS_READ))
):
    """Retrieve the most recent operational intelligence brief."""
    org_id = user.get("organizationId", "org-apex-01")
    if user.get("role") in ("STORE_MANAGER", "MAINTENANCE_TEAM") and user.get("storeId"):
        storeId = user.get("storeId")

    brief = BriefService.get_latest_brief(
        conn=conn,
        organization_id=org_id,
        store_id=storeId,
        timeframe_type=timeframeType.upper() if timeframeType else None
    )
    if not brief:
        # Generate on-demand if none exists yet
        brief = BriefService.generate_brief(
            conn=conn,
            organization_id=org_id,
            store_id=storeId,
            timeframe_type=timeframeType.upper() if timeframeType else "DAILY",
            user_id=user.get("id")
        )
    return ApiResponse(success=True, data=brief)


@router.get("", response_model=ApiResponse[List[OperationalBriefResponse]])
def list_briefs(
    storeId: Optional[str] = Query(None, description="Optional store filter"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ANALYTICS_READ))
):
    """List historical operational intelligence briefs for executive audit."""
    org_id = user.get("organizationId", "org-apex-01")
    if user.get("role") in ("STORE_MANAGER", "MAINTENANCE_TEAM") and user.get("storeId"):
        storeId = user.get("storeId")

    briefs, meta = BriefService.list_briefs_paginated(
        conn=conn,
        organization_id=org_id,
        store_id=storeId,
        page=page,
        limit=limit
    )
    return ApiResponse(success=True, data=briefs, meta=meta)


@router.get("/{briefId}", response_model=ApiResponse[OperationalBriefResponse])
def get_brief_by_id(
    briefId: str = Path(..., description="Unique brief identifier"),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ANALYTICS_READ))
):
    """Retrieve an operational intelligence brief by ID with all 10 sections."""
    brief = BriefService.get_brief_by_id(conn, briefId)
    return ApiResponse(success=True, data=brief)
