import sqlite3
from typing import Dict, Any
from fastapi import APIRouter, Depends, Path
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.services.evidence_lineage_service import EvidenceLineageService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/lineage", tags=["Phase 9: Evidence & Explainability Lineage Layer"])

@router.get("/issue/{issue_id}", response_model=ApiResponse[Dict[str, Any]])
def get_issue_lineage(
    issue_id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ISSUE_READ))
):
    """
    Constructs the complete operational lineage DAG for an incident:
    Feedback -> Extraction -> Investigation Q&A -> Issue / Cluster -> Alert -> Priority -> Action -> Resolution
    """
    graph = EvidenceLineageService.build_issue_lineage_graph(conn, issue_id)
    return ApiResponse(success=True, data=graph)

@router.get("/alert/{alert_id}", response_model=ApiResponse[Dict[str, Any]])
def get_alert_evidence_and_lineage(
    alert_id: str = Path(...),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ALERT_READ))
):
    """Retrieve full supporting feedback quotes, mathematical metrics, and lineage DAG for an alert."""
    data = EvidenceLineageService.get_alert_evidence(conn, alert_id)
    return ApiResponse(success=True, data=data)
