import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from backend.app.db.database import get_db
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.domain import AuditLogResponse
from backend.app.services.audit_service import AuditService
from backend.app.api.deps import require_permission
from backend.app.core.rbac import Permission

router = APIRouter(prefix="/audit-logs", tags=["Audit & Governance"])

@router.get("", response_model=ApiResponse[List[AuditLogResponse]])
def get_audit_logs(
    entityType: Optional[str] = Query(None),
    entityId: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(require_permission(Permission.AUDIT_READ))
):
    org_id = str(user.get("organizationId", ""))
    data, meta = AuditService.get_audit_logs_paginated(conn, org_id, entityType, entityId, page, limit)
    return ApiResponse(success=True, data=data, meta=meta)
