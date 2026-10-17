"""
Phase 10: Intelligent Operational Routing API Router

Exposes endpoints for:
- Automatic deterministic routing
- Manual reassignment & human override
- Operational escalation & accelerated SLA
- Routing history & ownership tracking
- Human triage queue for ambiguous issues
- Deterministic routing simulation
"""

import sqlite3
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Path

from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.domain import (
    RoutingDecisionResponse,
    IssueReassignRequest,
    IssueEscalateRequest,
    RoutingSimulationRequest,
    TriageQueueItemResponse
)
from backend.app.services.routing_service import RoutingService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/routing", tags=["Phase 10: Intelligent Operational Routing"])


@router.post("/issues/{issue_id}/route", response_model=ApiResponse[RoutingDecisionResponse])
def route_issue(
    issue_id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_ASSIGN))
):
    """
    Execute automatic deterministic operational routing for an issue.
    Evaluates category, store, region, ownership rules, specialization, severity, and safety.
    If confidence is low, routes to Human Triage Queue.
    """
    decision = RoutingService.route_issue(conn, issue_id, user_id=user.get("id"))
    return ApiResponse(success=True, data=decision)


@router.post("/issues/{issue_id}/reassign", response_model=ApiResponse[RoutingDecisionResponse])
def reassign_issue(
    payload: IssueReassignRequest,
    issue_id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_ASSIGN))
):
    """
    Human operator manually reassigns an issue to a different operational team or user.
    Records provenance, justification, and marks the decision as a human override.
    """
    decision = RoutingService.reassign_issue(
        conn=conn,
        issue_id=issue_id,
        target_team_id=payload.targetTeamId,
        target_user_id=payload.targetUserId,
        override_reason=payload.reassignmentReason,
        user_id=str(user.get("id", ""))
    )
    return ApiResponse(success=True, data=decision)


@router.post("/issues/{issue_id}/escalate", response_model=ApiResponse[RoutingDecisionResponse])
def escalate_issue(
    payload: IssueEscalateRequest,
    issue_id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_ASSIGN))
):
    """
    Escalate an issue to secondary operational tier or executive ownership.
    Accelerates the SLA deadline and records escalation provenance.
    """
    decision = RoutingService.escalate_issue(
        conn=conn,
        issue_id=issue_id,
        escalation_reason=payload.escalationReason,
        target_team_id=payload.targetTeamId,
        user_id=str(user.get("id", ""))
    )
    return ApiResponse(success=True, data=decision)


@router.get("/issues/{issue_id}/history", response_model=ApiResponse[List[RoutingDecisionResponse]])
def get_issue_routing_history(
    issue_id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_READ))
):
    """Retrieve the complete chronological routing and reassignment history for an issue."""
    history = RoutingService.get_issue_routing_history(conn, issue_id)
    return ApiResponse(success=True, data=history)


@router.get("/triage-queue", response_model=ApiResponse[List[TriageQueueItemResponse]])
def get_triage_queue(
    storeId: Optional[str] = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_TRIAGE))
):
    """
    Retrieve issues routed to the Human Triage Queue due to ambiguous classification,
    conflicting specializations, or low confidence, preventing operational misrouting.
    """
    org_id = str(user.get("organizationId", ""))
    items = RoutingService.get_triage_queue(conn, org_id, store_id=storeId)
    return ApiResponse(success=True, data=items)


@router.post("/simulate", response_model=ApiResponse[Dict[str, Any]])
def simulate_routing(
    payload: RoutingSimulationRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_READ))
):
    """
    Preview deterministic routing determination for given parameters without persisting.
    Useful for testing routing rules and operational ownership configuration.
    """
    org_id = str(user.get("organizationId", ""))
    decision = RoutingService.determine_routing(
        conn=conn,
        organization_id=org_id,
        store_id=payload.storeId,
        category=payload.category,
        priority_tier="P2_HIGH",
        severity_score=payload.severity or 0.5,
        is_safety_hazard=payload.isSafetyHazard or False,
        department_id=payload.departmentId
    )
    return ApiResponse(success=True, data=decision)
