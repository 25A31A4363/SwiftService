import sqlite3
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.domain import (
    AlertResponse,
    AlertEscalateRequest,
    AlertDismissRequest,
    EmergingDetectionRequest
)
from backend.app.services.emerging_detection_service import EmergingDetectionService
from backend.app.services.evidence_lineage_service import EvidenceLineageService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/alerts", tags=["Phase 7: Operational Alerts & Emerging Issue Detection"])

@router.get("", response_model=ApiResponse[List[AlertResponse]])
def get_alerts(
    storeId: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    isAcknowledged: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ALERT_READ))
):
    org_id = str(user.get("organizationId", ""))
    if user.get("role") in ("STORE_MANAGER", "MAINTENANCE_TEAM") and user.get("storeId"):
        storeId = user.get("storeId")

    data, meta = EmergingDetectionService.list_alerts_paginated(conn, org_id, storeId, status, page, limit)
    return ApiResponse(success=True, data=data, meta=meta)

@router.get("/{id}", response_model=ApiResponse[AlertResponse])
def get_alert_by_id(
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ALERT_READ))
):
    result = EmergingDetectionService.get_alert_by_id(conn, id)
    return ApiResponse(success=True, data=result)

@router.post("/detect", response_model=ApiResponse[List[AlertResponse]])
def detect_emerging_issues(
    payload: Optional[EmergingDetectionRequest] = None,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ALERT_ACKNOWLEDGE))
):
    """Run deterministic anomaly and velocity detection against historical baselines."""
    org_id = str(user.get("organizationId", ""))
    st_id = payload.storeId if payload else None
    recent_h = payload.recentWindowHours if (payload and payload.recentWindowHours) else 24
    base_d = payload.baselineWindowDays if (payload and payload.baselineWindowDays) else 14
    min_ev = payload.minEvidenceThreshold if (payload and payload.minEvidenceThreshold) else 2
    z_thresh = payload.zscoreThreshold if (payload and payload.zscoreThreshold) else 1.8

    alerts = EmergingDetectionService.detect_emerging_issues(
        conn=conn,
        organization_id=org_id,
        store_id=st_id,
        recent_hours=recent_h,
        baseline_days=base_d,
        min_evidence_threshold=min_ev,
        zscore_threshold=z_thresh,
        user_id=user.get("id")
    )
    return ApiResponse(success=True, data=alerts)

@router.post("/{id}/acknowledge", response_model=ApiResponse[AlertResponse])
def acknowledge_alert(
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ALERT_ACKNOWLEDGE))
):
    result = EmergingDetectionService.acknowledge_alert(conn, id, user.get("id"))
    return ApiResponse(success=True, data=result)

@router.post("/{id}/escalate", response_model=ApiResponse[AlertResponse])
def escalate_alert(
    payload: AlertEscalateRequest,
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ALERT_ACKNOWLEDGE))
):
    """Escalate alert to an operational team for urgent intervention."""
    result = EmergingDetectionService.escalate_alert(
        conn=conn,
        alert_id=id,
        target_team_id=payload.targetTeamId,
        notes=payload.notes,
        user_id=user.get("id")
    )
    return ApiResponse(success=True, data=result)

@router.post("/{id}/dismiss", response_model=ApiResponse[AlertResponse])
def dismiss_alert(
    payload: AlertDismissRequest,
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ALERT_ACKNOWLEDGE))
):
    """Dismiss false positive alert with justification."""
    result = EmergingDetectionService.dismiss_alert(
        conn=conn,
        alert_id=id,
        reason=payload.reason,
        user_id=user.get("id")
    )
    return ApiResponse(success=True, data=result)

@router.get("/{id}/evidence", response_model=ApiResponse[Dict[str, Any]])
def get_alert_evidence(
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ALERT_READ))
):
    """Inspect full empirical evidence, member feedback quotes, and explainability breakdown."""
    data = EvidenceLineageService.get_alert_evidence(conn, id)
    return ApiResponse(success=True, data=data)
