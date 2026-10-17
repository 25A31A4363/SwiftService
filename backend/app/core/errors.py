from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.error_monitor import error_monitor
from backend.app.core.tracing import get_current_trace_id

class AppError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details

class BadRequestError(AppError):
    def __init__(self, message: str = "Bad request", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="BAD_REQUEST",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )

class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} '{identifier}' not found",
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": identifier}
        )

class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class ForbiddenError(AppError):
    def __init__(self, message: str = "Insufficient permissions for this action"):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN
        )

class ConflictError(AppError):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )

class DuplicateFeedbackError(ConflictError):
    def __init__(self, original_id: str, message: str = "Duplicate feedback detected for this store"):
        super().__init__(
            message=message,
            details={"originalId": original_id, "isDuplicate": True}
        )

class ValidationError(AppError):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details=details
        )

def format_error_response(
    code: str,
    message: str,
    details: Optional[Any] = None,
    path: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": path,
            "requestId": request_id
        }
    }


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) if hasattr(request, "state") else None
    error_monitor.record_error(
        code=exc.code,
        status_code=exc.status_code,
        message=exc.message,
        path=str(request.url.path),
        method=request.method,
        request_id=request_id,
        trace_id=get_current_trace_id()
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            path=str(request.url.path),
            request_id=request_id
        )
    )

async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) if hasattr(request, "state") else None
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        errors.append({
            "field": field,
            "message": err.get("msg", "Invalid value"),
            "type": err.get("type", "value_error")
        })
    error_monitor.record_error(
        code="VALIDATION_ERROR",
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        message=f"Validation failed on {len(errors)} fields",
        path=str(request.url.path),
        method=request.method,
        request_id=request_id,
        trace_id=get_current_trace_id()
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=format_error_response(
            code="VALIDATION_ERROR",
            message="Request input validation failed",
            details=errors,
            path=str(request.url.path),
            request_id=request_id
        )
    )

async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) if hasattr(request, "state") else None
    code = "HTTP_ERROR"
    if exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 409:
        code = "CONFLICT"
    elif exc.status_code == 429:
        code = "RATE_LIMIT_EXCEEDED"

    error_monitor.record_error(
        code=code,
        status_code=exc.status_code,
        message=str(exc.detail),
        path=str(request.url.path),
        method=request.method,
        request_id=request_id,
        trace_id=get_current_trace_id()
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            code=code,
            message=str(exc.detail),
            path=str(request.url.path),
            request_id=request_id
        ),
        headers=getattr(exc, "headers", None)
    )

def _sanitize_error_detail(exc_str: str) -> str:
    """Sanitize internal errors to prevent leaking database schemas, queries, or paths."""
    sensitive_keywords = ["sqlite3", "syntax error", "table", "column", "select ", "insert ", "update ", "delete ", "c:\\", "/users/", "password"]
    exc_lower = exc_str.lower()
    if any(k in exc_lower for k in sensitive_keywords):
        return "Internal server processing error. Details recorded in secure audit log."
    return exc_str

async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from backend.app.core.logger import logger
    request_id = getattr(request.state, "request_id", None) if hasattr(request, "state") else None
    
    error_monitor.record_error(
        code="INTERNAL_SERVER_ERROR",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=str(exc),
        path=str(request.url.path),
        method=request.method,
        request_id=request_id,
        trace_id=get_current_trace_id()
    )

    # Secure server-side logging
    logger.error(f"Unhandled exception [request_id={request_id}]: {str(exc)}", exc_info=True)
    
    # Client-facing hardened response
    safe_detail = _sanitize_error_detail(str(exc)) if settings_debug(request) else None
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred",
            details=safe_detail,
            path=str(request.url.path),
            request_id=request_id
        )
    )

def settings_debug(request: Request) -> bool:
    from backend.app.core.config import settings
    return settings.DEBUG
