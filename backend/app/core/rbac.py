from enum import Enum
from typing import Set, Dict, Optional, Any

class Role(str, Enum):
    ORGANIZATION_ADMIN = "ORGANIZATION_ADMIN"
    OPERATIONS_MANAGER = "OPERATIONS_MANAGER"
    REGIONAL_MANAGER = "REGIONAL_MANAGER"
    STORE_MANAGER = "STORE_MANAGER"
    MAINTENANCE_TEAM = "MAINTENANCE_TEAM"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"

class Permission(str, Enum):
    # Org & Structure
    ORG_READ = "org:read"
    ORG_MANAGE = "org:manage"
    REGION_READ = "region:read"
    REGION_MANAGE = "region:manage"
    STORE_READ = "store:read"
    STORE_MANAGE = "store:manage"
    TEAM_READ = "team:read"
    TEAM_MANAGE = "team:manage"
    USER_READ = "user:read"
    USER_MANAGE = "user:manage"

    # Feedback
    FEEDBACK_READ = "feedback:read"
    FEEDBACK_SUBMIT = "feedback:submit"
    FEEDBACK_EXPORT = "feedback:export"

    # Issues
    ISSUE_READ = "issue:read"
    ISSUE_TRIAGE = "issue:triage"
    ISSUE_ASSIGN = "issue:assign"
    ISSUE_OVERRIDE = "issue:override"
    ISSUE_CLOSE = "issue:close"

    # Alerts
    ALERT_READ = "alert:read"
    ALERT_ACKNOWLEDGE = "alert:acknowledge"

    # Actions
    ACTION_READ = "action:read"
    ACTION_APPROVE = "action:approve"
    ACTION_REJECT = "action:reject"
    ACTION_OVERRIDE = "action:override"
    ACTION_EXECUTE = "action:execute"

    # Resolutions
    RESOLUTION_READ = "resolution:read"
    RESOLUTION_CREATE = "resolution:create"
    RESOLUTION_VERIFY = "resolution:verify"

    # Audit & Analytics
    AUDIT_READ = "audit:read"
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"

    # Security & AI Governance (Phase 16)
    GOVERNANCE_READ = "governance:read"
    GOVERNANCE_MANAGE = "governance:manage"
    SECURITY_AUDIT = "security:audit"
    RETENTION_MANAGE = "retention:manage"

ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ORGANIZATION_ADMIN: {p for p in Permission},
    Role.OPERATIONS_MANAGER: {
        Permission.ORG_READ,
        Permission.REGION_READ, Permission.REGION_MANAGE,
        Permission.STORE_READ, Permission.STORE_MANAGE,
        Permission.TEAM_READ, Permission.TEAM_MANAGE,
        Permission.USER_READ,
        Permission.FEEDBACK_READ, Permission.FEEDBACK_SUBMIT, Permission.FEEDBACK_EXPORT,
        Permission.ISSUE_READ, Permission.ISSUE_TRIAGE, Permission.ISSUE_ASSIGN, Permission.ISSUE_OVERRIDE, Permission.ISSUE_CLOSE,
        Permission.ALERT_READ, Permission.ALERT_ACKNOWLEDGE,
        Permission.ACTION_READ, Permission.ACTION_APPROVE, Permission.ACTION_REJECT, Permission.ACTION_OVERRIDE, Permission.ACTION_EXECUTE,
        Permission.RESOLUTION_READ, Permission.RESOLUTION_CREATE, Permission.RESOLUTION_VERIFY,
        Permission.AUDIT_READ, Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT,
        Permission.GOVERNANCE_READ, Permission.GOVERNANCE_MANAGE, Permission.SECURITY_AUDIT, Permission.RETENTION_MANAGE,
    },
    Role.REGIONAL_MANAGER: {
        Permission.ORG_READ,
        Permission.REGION_READ,
        Permission.STORE_READ,
        Permission.TEAM_READ,
        Permission.USER_READ,
        Permission.FEEDBACK_READ, Permission.FEEDBACK_SUBMIT, Permission.FEEDBACK_EXPORT,
        Permission.ISSUE_READ, Permission.ISSUE_TRIAGE, Permission.ISSUE_ASSIGN, Permission.ISSUE_OVERRIDE, Permission.ISSUE_CLOSE,
        Permission.ALERT_READ, Permission.ALERT_ACKNOWLEDGE,
        Permission.ACTION_READ, Permission.ACTION_APPROVE, Permission.ACTION_REJECT, Permission.ACTION_OVERRIDE,
        Permission.RESOLUTION_READ, Permission.RESOLUTION_VERIFY,
        Permission.AUDIT_READ, Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT,
        Permission.GOVERNANCE_READ,
    },
    Role.STORE_MANAGER: {
        Permission.ORG_READ,
        Permission.REGION_READ,
        Permission.STORE_READ,
        Permission.TEAM_READ,
        Permission.FEEDBACK_READ, Permission.FEEDBACK_SUBMIT,
        Permission.ISSUE_READ, Permission.ISSUE_TRIAGE, Permission.ISSUE_ASSIGN, Permission.ISSUE_OVERRIDE,
        Permission.ALERT_READ, Permission.ALERT_ACKNOWLEDGE,
        Permission.ACTION_READ, Permission.ACTION_APPROVE, Permission.ACTION_REJECT, Permission.ACTION_OVERRIDE, Permission.ACTION_EXECUTE,
        Permission.RESOLUTION_READ, Permission.RESOLUTION_CREATE, Permission.RESOLUTION_VERIFY,
        Permission.AUDIT_READ, Permission.ANALYTICS_READ,
        Permission.GOVERNANCE_READ,
    },
    Role.MAINTENANCE_TEAM: {
        Permission.STORE_READ,
        Permission.TEAM_READ,
        Permission.FEEDBACK_READ, Permission.FEEDBACK_SUBMIT,
        Permission.ISSUE_READ,
        Permission.ALERT_READ, Permission.ALERT_ACKNOWLEDGE,
        Permission.ACTION_READ, Permission.ACTION_EXECUTE,
        Permission.RESOLUTION_READ, Permission.RESOLUTION_CREATE,
    },
    Role.ANALYST: {
        Permission.ORG_READ,
        Permission.REGION_READ,
        Permission.STORE_READ,
        Permission.TEAM_READ,
        Permission.FEEDBACK_READ, Permission.FEEDBACK_EXPORT,
        Permission.ISSUE_READ,
        Permission.ALERT_READ,
        Permission.ACTION_READ,
        Permission.RESOLUTION_READ,
        Permission.AUDIT_READ, Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT,
        Permission.GOVERNANCE_READ, Permission.SECURITY_AUDIT,
    },
    Role.VIEWER: {
        Permission.ORG_READ,
        Permission.REGION_READ,
        Permission.STORE_READ,
        Permission.FEEDBACK_READ,
        Permission.ISSUE_READ,
        Permission.ALERT_READ,
        Permission.ACTION_READ,
        Permission.RESOLUTION_READ,
        Permission.ANALYTICS_READ,
    },
}

def has_permission(role: str, permission: Permission, conn: Optional[Any] = None) -> bool:
    try:
        r = Role(role)
        if permission in ROLE_PERMISSIONS.get(r, set()):
            return True
    except ValueError:
        pass

    # Dynamic check for custom database roles
    try:
        from backend.app.db.database import get_connection
        close_conn = False
        c = conn
        if c is None:
            c = get_connection()
            close_conn = True

        cur = c.cursor()
        cur.execute("""
            SELECT 1 FROM role_permissions rp
            JOIN roles r ON rp.role_id = r.id
            WHERE r.name = ? AND rp.permission = ?;
        """, (role, permission.value))
        res = cur.fetchone() is not None
        if close_conn:
            c.close()
        return res
    except Exception:
        return False

def can_access_store(user: Dict[str, Any], store_id: str, region_id: Optional[str] = None) -> bool:
    role = user.get("role")
    if role in (Role.ORGANIZATION_ADMIN, Role.OPERATIONS_MANAGER, Role.ANALYST, Role.VIEWER):
        return True
    if role == Role.REGIONAL_MANAGER:
        return user.get("region_id") == region_id if region_id else True
    if role in (Role.STORE_MANAGER, Role.MAINTENANCE_TEAM):
        return user.get("store_id") == store_id
    return False
