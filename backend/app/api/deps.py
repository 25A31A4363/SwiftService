import sqlite3
from typing import Dict, Any, Optional, Callable
from fastapi import Depends, Header
from backend.app.db.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.core.errors import UnauthorizedError, ForbiddenError
from backend.app.core.rbac import Permission, has_permission, can_access_store
from backend.app.services.auth_service import AuthService

def get_current_user(
    authorization: Optional[str] = Header(None),
    conn: sqlite3.Connection = Depends(get_db)
) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header. Expected 'Bearer <token>'.")

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "userId" not in payload:
        raise UnauthorizedError("Token is invalid or has expired.")

    user = AuthService.get_user_by_id(conn, payload["userId"])
    if not user["isActive"]:
        raise UnauthorizedError("User account is inactive.")

    return user

def require_permission(permission: Permission) -> Callable:
    def dependency(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = user.get("role", "")
        if not has_permission(user_role, permission):
            raise ForbiddenError(f"Role '{user_role}' lacks required permission '{permission.value}'")
        return user
    return dependency

def enforce_store_access(
    store_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db)
) -> str:
    cur = conn.cursor()
    cur.execute("SELECT id, region_id FROM stores WHERE id = ?;", (store_id,))
    store = cur.fetchone()
    if not store:
        return store_id

    if not can_access_store(user, store["id"], store["region_id"]):
        raise ForbiddenError(f"User is restricted from accessing Store '{store_id}'")
    return store_id
