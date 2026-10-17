import time
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.core.tracing import (
    set_trace_context,
    extract_or_generate_trace_context,
    format_traceparent,
)
from backend.app.core.idempotency import IdempotencyManager
from backend.app.core.errors import (
    AppError,
    app_error_handler,
    validation_error_handler,
    http_error_handler,
    generic_error_handler,
)
from backend.app.db.database import init_db, get_connection
from backend.app.db.seed import seed_database
from backend.app.api.v1.api_router import api_v1_router

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting R5 Operational Intelligence Platform...")
    init_db()
    seed_database(force=False)
    logger.info("R5 Platform initialization complete. System online.")
    yield
    # Shutdown
    logger.info("Shutting down R5 Platform...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0-phase1",
    description="Enterprise Physical Operational Intelligence Core (Closed-Loop Feedback -> Action -> Outcome)",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Tracing, Idempotency & Observability Middleware
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    # 1. Trace Context Extraction and Binding
    trace_id, span_id, request_id = extract_or_generate_trace_context(dict(request.headers))
    set_trace_context(trace_id, request_id, span_id)
    request.state.request_id = request_id
    request.state.trace_id = trace_id
    start_time = time.time()

    # 2. Check Idempotency for mutation operations
    idempotency_key = IdempotencyManager.get_idempotency_key(request)
    body_bytes = b""
    if idempotency_key and request.method in ("POST", "PUT", "PATCH"):
        body_bytes = await request.body()
        conn = get_connection()
        try:
            cached_res = IdempotencyManager.check_idempotency(
                conn=conn,
                key=idempotency_key,
                path=request.url.path,
                method=request.method,
                body_bytes=body_bytes
            )
            if cached_res is not None:
                cached_status, cached_headers, cached_body = cached_res
                process_time = round((time.time() - start_time) * 1000, 2)
                resp_headers = dict(cached_headers)
                resp_headers.update({
                    "X-Request-ID": request_id,
                    "X-Trace-ID": trace_id,
                    "traceparent": format_traceparent(trace_id, span_id),
                    "X-Response-Time-Ms": str(process_time),
                    "X-Cache-Lookup": "IDEMPOTENT-HIT",
                    "X-Idempotency-Key": idempotency_key,
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "X-XSS-Protection": "1; mode=block",
                    "Referrer-Policy": "strict-origin-when-cross-origin"
                })
                return Response(
                    content=cached_body,
                    status_code=cached_status,
                    media_type="application/json",
                    headers=resp_headers
                )
        except AppError as app_err:
            from backend.app.core.errors import app_error_handler
            return await app_error_handler(request, app_err)
        finally:
            conn.close()

    # 3. Execute downstream handler
    response: Response = await call_next(request)

    process_time = round((time.time() - start_time) * 1000, 2)

    # 4. Record Idempotency on Successful Mutation
    if idempotency_key and request.method in ("POST", "PUT", "PATCH") and (200 <= response.status_code < 300):
        # Read response body safely whether streaming or standard
        body_iter = getattr(response, "body_iterator", None)
        if body_iter is not None:
            resp_chunks = [chunk async for chunk in body_iter]
            full_body = b"".join(resp_chunks)

            # Re-attach body iterator so downstream client receives payload
            async def reiterator():
                yield full_body
            setattr(response, "body_iterator", reiterator())
        else:
            full_body = getattr(response, "body", b"")

        conn = get_connection()
        try:
            IdempotencyManager.record_idempotency(
                conn=conn,
                key=idempotency_key,
                path=request.url.path,
                method=request.method,
                body_bytes=body_bytes,
                status_code=response.status_code,
                response_body=full_body.decode("utf-8", errors="replace"),
                headers=dict(response.headers)
            )
            response.headers["X-Cache-Lookup"] = "IDEMPOTENT-STORE"
            response.headers["X-Idempotency-Key"] = idempotency_key
        except Exception as e:
            logger.warning(f"Failed to record idempotency key '{idempotency_key}': {e}")
        finally:
            conn.close()

    # 5. Security & Observability Headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Trace-ID"] = trace_id
    response.headers["traceparent"] = format_traceparent(trace_id, span_id)
    response.headers["X-Response-Time-Ms"] = str(process_time)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response

# Error Handlers
app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, generic_error_handler)

# Versioned API routes
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# Static & Frontend Serving
static_path = FRONTEND_DIR / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/", include_in_schema=False)
async def serve_spa():
    index_html = FRONTEND_DIR / "index.html"
    if index_html.exists():
        return FileResponse(str(index_html))
    return {"message": "R5 Operational Intelligence Platform API Online. Visit /docs for OpenAPI documentation."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
