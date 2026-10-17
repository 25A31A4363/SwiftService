import sqlite3
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Request, UploadFile, File, status, HTTPException

from backend.app.db.database import get_db
from backend.app.api.deps import get_current_user, require_permission
from backend.app.core.rbac import Permission
from backend.app.core.security_hardening import (
    PromptInjectionGuard,
    PIIMinimizer,
    RateLimiter,
    SecureUploadValidator,
    InputSanitizer
)
from backend.app.services.ai_governance_service import AIModelGateway
from backend.app.services.retention_service import RetentionService
from backend.app.services.security_audit_service import SecurityAuditService
from backend.app.schemas.security import (
    PromptValidationRequest,
    AIExecuteRequest,
    AIOverrideRequest,
    RetentionPolicyRequest,
    RetentionPurgeRequest
)

router = APIRouter()

def _get_org_id(user: dict) -> str:
    return user.get("organizationId") or user.get("organization_id") or "org-apex"

def _enforce_rate_limit(request: Request, user_id: str, tier: str, conn: sqlite3.Connection, org_id: Optional[str] = None):
    client_ip = request.client.host if request.client else "127.0.0.1"
    key = f"{user_id}:{client_ip}"
    allowed, remaining, retry_after = RateLimiter.check_rate_limit(key, tier=tier)
    if not allowed:
        SecurityAuditService.record_event(
            conn=conn,
            event_type="RATE_LIMIT_EXCEEDED",
            severity="MEDIUM",
            organization_id=org_id,
            user_id=user_id,
            source_ip=client_ip,
            path=str(request.url.path),
            details={"tier": tier, "retryAfter": retry_after}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for tier '{tier}'. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )

@router.post("/validate-prompt", response_model=Dict[str, Any])
def validate_prompt(
    req: PromptValidationRequest,
    current_user: dict = Depends(require_permission(Permission.GOVERNANCE_READ))
):
    """
    Validates a prompt against prompt-injection attacks and returns
    sanitized and PII-redacted text representations.
    """
    cleaned_input = InputSanitizer.sanitize_string(req.prompt)
    injection = PromptInjectionGuard.inspect_prompt(cleaned_input)
    pii_redacted, pii_count, pii_categories = PIIMinimizer.redact_pii(injection["sanitized_text"])

    return {
        "success": True,
        "isInjection": injection["is_injection"],
        "riskScore": injection["risk_score"],
        "flaggedPatterns": injection["flagged_patterns"],
        "sanitizedPrompt": injection["sanitized_text"],
        "piiRedactedPrompt": pii_redacted,
        "piiCount": pii_count,
        "piiCategories": pii_categories
    }

@router.post("/ai/execute", response_model=Dict[str, Any])
def execute_ai_reasoning(
    req: AIExecuteRequest,
    request: Request,
    current_user: dict = Depends(require_permission(Permission.GOVERNANCE_READ)),
    conn: sqlite3.Connection = Depends(get_db)
):
    """
    Executes prompt through the AI Governance Gateway with:
    - Rate limit enforcement
    - Prompt injection blocking
    - PII minimization & redaction before model invocation
    - Audit logging
    - Output confidence and evidence validation
    """
    org_id = _get_org_id(current_user)
    user_id = str(current_user.get("id", ""))
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Rate limiting on AI tier
    _enforce_rate_limit(request, user_id, "AI", conn, org_id)

    # Clean input
    clean_prompt = InputSanitizer.sanitize_string(req.prompt)

    result = AIModelGateway.execute(
        conn=conn,
        organization_id=org_id,
        prompt=clean_prompt,
        user_id=user_id,
        provider_name=req.providerName or "LOCAL_DETERMINISTIC",
        context=req.context,
        options=req.options,
        source_ip=client_ip
    )

    return {
        "success": True,
        "data": result
    }

@router.post("/governance/override", response_model=Dict[str, Any])
def override_ai_decision(
    req: AIOverrideRequest,
    current_user: dict = Depends(require_permission(Permission.GOVERNANCE_MANAGE)),
    conn: sqlite3.Connection = Depends(get_db)
):
    """
    Records a human override of an AI decision or confidence assessment with justification.
    """
    user_id = str(current_user.get("id", ""))
    override_record = AIModelGateway.record_human_override(
        conn=conn,
        governance_log_id=req.governanceLogId,
        user_id=user_id,
        override_reason=req.overrideReason,
        new_confidence=req.newConfidence,
        notes=req.notes
    )

    return {
        "success": True,
        "message": "AI decision overridden successfully with human justification.",
        "data": override_record
    }

@router.get("/governance/logs", response_model=Dict[str, Any])
def list_governance_logs(
    provider: Optional[str] = None,
    only_overridden: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(require_permission(Permission.GOVERNANCE_READ)),
    conn: sqlite3.Connection = Depends(get_db)
):
    """
    Retrieves auditable AI governance logs including token usage, confidence, and human overrides.
    """
    org_id = _get_org_id(current_user)
    logs_data = AIModelGateway.list_governance_logs(
        conn=conn,
        organization_id=org_id,
        provider_name=provider,
        only_overridden=only_overridden,
        limit=limit,
        offset=offset
    )
    return {
        "success": True,
        "data": logs_data
    }

@router.get("/retention/policies", response_model=Dict[str, Any])
def get_retention_policies(
    current_user: dict = Depends(require_permission(Permission.RETENTION_MANAGE)),
    conn: sqlite3.Connection = Depends(get_db)
):
    org_id = _get_org_id(current_user)
    policies = RetentionService.list_policies(conn, org_id)
    return {
        "success": True,
        "data": policies
    }

@router.post("/retention/policies", response_model=Dict[str, Any])
def configure_retention_policy(
    req: RetentionPolicyRequest,
    current_user: dict = Depends(require_permission(Permission.RETENTION_MANAGE)),
    conn: sqlite3.Connection = Depends(get_db)
):
    org_id = _get_org_id(current_user)
    policy = RetentionService.set_policy(
        conn=conn,
        organization_id=org_id,
        entity_type=req.entityType,
        retention_days=req.retentionDays,
        action_on_expire=req.actionOnExpire,
        is_active=req.isActive
    )
    return {
        "success": True,
        "message": f"Retention policy configured for {req.entityType}.",
        "data": policy
    }

@router.post("/retention/purge", response_model=Dict[str, Any])
def execute_retention_purge(
    req: RetentionPurgeRequest,
    current_user: dict = Depends(require_permission(Permission.RETENTION_MANAGE)),
    conn: sqlite3.Connection = Depends(get_db)
):
    org_id = _get_org_id(current_user)
    user_id = current_user.get("id")
    purge_summary = RetentionService.execute_purge(
        conn=conn,
        organization_id=org_id,
        user_id=user_id,
        dry_run=req.dryRun
    )
    return {
        "success": True,
        "data": purge_summary
    }

@router.post("/upload", response_model=Dict[str, Any])
async def upload_file_secure(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db)
):
    """
    Secure file upload endpoint:
    - Path traversal protection
    - Executable extension blocklist
    - Magic byte MIME header validation
    - File size limits
    """
    content = await file.read()
    val_res = SecureUploadValidator.validate_file(file.filename or "unknown.bin", content)

    if not val_res["is_valid"]:
        # Record security audit event
        SecurityAuditService.record_event(
            conn=conn,
            event_type="UNSAFE_UPLOAD_ATTEMPT",
            severity="HIGH",
            organization_id=_get_org_id(current_user),
            user_id=current_user.get("id"),
            path="/security/upload",
            details={
                "filename": file.filename,
                "error": val_res["error"],
                "fileSize": len(content)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=val_res["error"]
        )

    return {
        "success": True,
        "message": "File verified and accepted securely.",
        "data": {
            "safeFilename": val_res["safe_filename"],
            "sizeBytes": val_res["size"],
            "isValid": True
        }
    }

@router.get("/audit/events", response_model=Dict[str, Any])
def list_security_audit_events(
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(require_permission(Permission.SECURITY_AUDIT)),
    conn: sqlite3.Connection = Depends(get_db)
):
    org_id = _get_org_id(current_user)
    events_data = SecurityAuditService.list_events(
        conn=conn,
        organization_id=org_id,
        event_type=event_type,
        severity=severity,
        limit=limit,
        offset=offset
    )
    return {
        "success": True,
        "data": events_data
    }
