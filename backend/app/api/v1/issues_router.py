import sqlite3
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, status
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.domain import (
    IssueCreate, IssueResponse, IssueStatusUpdate, IssuePriorityOverride, EvidenceResponse
)
from backend.app.services.issue_service import IssueService
from backend.app.api.deps import get_current_user, require_permission
from backend.app.core.rbac import Permission, Role, has_permission
from backend.app.core.errors import ForbiddenError

router = APIRouter(prefix="/issues", tags=["Operational Incidents & Issues"])

@router.post("", response_model=ApiResponse[IssueResponse], status_code=status.HTTP_201_CREATED)
def create_issue(
    payload: IssueCreate,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_TRIAGE))
):
    org_id = str(user.get("organizationId", ""))
    result = IssueService.create_issue(conn, org_id, payload, user_id=str(user.get("id", "")))
    return ApiResponse(success=True, data=result)

@router.get("", response_model=ApiResponse[List[IssueResponse]])
def get_issues(
    storeId: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priorityTier: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_READ))
):
    org_id = str(user.get("organizationId", ""))
    if user.get("role") in ("STORE_MANAGER", "MAINTENANCE_TEAM") and user.get("storeId"):
        storeId = user.get("storeId")

    data, meta = IssueService.get_issues_paginated(conn, org_id, storeId, status, priorityTier, page, limit)
    return ApiResponse(success=True, data=data, meta=meta)

@router.get("/{id}", response_model=ApiResponse[IssueResponse])
def get_issue(
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_READ))
):
    data = IssueService.get_issue_by_id(conn, id)
    return ApiResponse(success=True, data=data)

@router.patch("/{id}/status", response_model=ApiResponse[IssueResponse])
def update_status(
    payload: IssueStatusUpdate,
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    user_role = user.get("role", "")
    if user_role == Role.MAINTENANCE_TEAM.value:
        if payload.status not in ("IN_PROGRESS", "REMEDIATED"):
            raise ForbiddenError("Maintenance team can only transition issue status to 'IN_PROGRESS' or 'REMEDIATED'")
    elif not has_permission(user_role, Permission.ISSUE_TRIAGE):
        raise ForbiddenError(f"Role '{user_role}' lacks required permission 'issue:triage'")

    result = IssueService.update_issue_status(conn, id, payload, user_id=str(user.get("id", "")))
    return ApiResponse(success=True, data=result)

@router.post("/{id}/override-priority", response_model=ApiResponse[IssueResponse])
def override_priority(
    payload: IssuePriorityOverride,
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_OVERRIDE))
):
    result = IssueService.override_priority(conn, id, payload, user_id=str(user.get("id", "")))
    return ApiResponse(success=True, data=result)

@router.get("/{id}/evidence", response_model=ApiResponse[List[EvidenceResponse]])
def get_issue_evidence(
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_READ))
):
    cur = conn.cursor()
    cur.execute("SELECT * FROM evidence WHERE issue_id = ? ORDER BY created_at DESC;", (id,))
    rows = cur.fetchall()
    evidence_items = [{
        "id": r["id"],
        "organizationId": r["organization_id"],
        "issueId": r["issue_id"],
        "feedbackItemId": r["feedback_item_id"],
        "verbatimQuote": r["verbatim_quote"],
        "sourceMetadata": json.loads(r["source_metadata"]) if r["source_metadata"] else {},
        "confidenceScore": r["confidence_score"],
        "createdAt": r["created_at"]
    } for r in rows]
    return ApiResponse(success=True, data=evidence_items)

@router.post("/{id}/recalculate-priority", response_model=ApiResponse[IssueResponse])
def recalculate_issue_priority(
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_TRIAGE))
):
    """
    Recalculate transparent, explainable priority score across severity, urgency,
    operational impact, safety, acceleration, and cross-store spread.
    """
    issue = IssueService.get_issue_by_id(conn, id)
    from backend.app.services.prioritization_service import PrioritizationService
    res = PrioritizationService.calculate_explainable_priority(
        severity=issue["severityScore"],
        urgency=issue["urgencyScore"],
        operational_impact=issue["impactScopeScore"],
        is_safety_hazard=issue["severityScore"] >= 0.85,
        growth_velocity=issue.get("anomalyVelocityZScore") or 0.0,
        stores_affected_count=issue.get("geographicSpreadCount") or 1,
        recurrence_count=issue.get("recurrenceCount") or 0,
        confidence=issue["confidenceScore"],
        observation_count=issue["feedbackCount"]
    )

    now = datetime.now(timezone.utc).isoformat()
    cur = conn.cursor()
    cur.execute("""
        UPDATE issues
        SET priority_score = ?, priority_tier = ?, factor_breakdown = ?,
            prioritization_explanation = ?, updated_at = ?
        WHERE id = ?;
    """, (
        res["priorityScore"], res["priorityTier"],
        json.dumps(res["factorContributions"]),
        res["explainableSummary"],
        now, id
    ))
    conn.commit()
    updated = IssueService.get_issue_by_id(conn, id)
    return ApiResponse(success=True, data=updated)

@router.get("/{id}/lineage", response_model=ApiResponse[Dict[str, Any]])
def get_issue_lineage(
    id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_READ))
):
    """
    Retrieve full traceable lineage graph from raw feedback to verified outcome.
    Categorizes every node into FACT, HYPOTHESIS, RECOMMENDATION, or UNKNOWN.
    """
    from backend.app.services.evidence_lineage_service import EvidenceLineageService
    graph = EvidenceLineageService.build_issue_lineage_graph(conn, id)
    return ApiResponse(success=True, data=graph)

