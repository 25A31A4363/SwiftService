"""
R5 Operational Intelligence Platform - Request Tracing and Context Management
Provides W3C traceparent parsing, UUID request ID generation, and thread-safe ContextVars
for end-to-end distributed tracing and structured log correlation.
"""

import re
import uuid
import contextvars
from typing import Optional, Tuple, Dict

# Context variables for asynchronous request propagation
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
trace_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
span_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("span_id", default="")

# W3C traceparent regex: version-trace_id-parent_id-trace_flags
# e.g.: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
TRACEPARENT_REGEX = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def generate_trace_id() -> str:
    """Generate a 32-character hex trace ID."""
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """Generate a 16-character hex span ID."""
    return uuid.uuid4().hex[:16]


def generate_request_id() -> str:
    """Generate an enterprise request identifier."""
    return f"req-{uuid.uuid4().hex[:12]}"


def parse_traceparent(traceparent: Optional[str]) -> Optional[Tuple[str, str, str]]:
    """Parse a W3C traceparent header into (trace_id, parent_id, flags)."""
    if not traceparent:
        return None
    match = TRACEPARENT_REGEX.match(traceparent.strip().lower())
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None


def format_traceparent(trace_id: str, span_id: str, sample_flag: str = "01") -> str:
    """Format trace context into standard W3C traceparent header."""
    t_id = trace_id.rjust(32, "0")[:32]
    s_id = span_id.rjust(16, "0")[:16]
    return f"00-{t_id}-{s_id}-{sample_flag}"


def extract_or_generate_trace_context(headers: Dict[str, str]) -> Tuple[str, str, str]:
    """
    Extract trace_id and request_id from incoming request headers or generate new identifiers.
    Checks:
    1. W3C 'traceparent' header
    2. 'X-Trace-ID' / 'X-Correlation-ID'
    3. 'X-Request-ID'
    """
    traceparent_header = headers.get("traceparent") or headers.get("Traceparent")
    tp_parsed = parse_traceparent(traceparent_header)

    if tp_parsed:
        trace_id, parent_span, _ = tp_parsed
        span_id = generate_span_id()
    else:
        trace_id = (
            headers.get("x-trace-id")
            or headers.get("X-Trace-ID")
            or headers.get("x-correlation-id")
            or headers.get("X-Correlation-ID")
            or generate_trace_id()
        )
        span_id = generate_span_id()

    request_id = (
        headers.get("x-request-id")
        or headers.get("X-Request-ID")
        or generate_request_id()
    )

    return trace_id, span_id, request_id


def set_trace_context(trace_id: str, request_id: str, span_id: Optional[str] = None) -> None:
    """Bind tracing identifiers to the current execution context."""
    trace_id_ctx.set(trace_id)
    request_id_ctx.set(request_id)
    if span_id:
        span_id_ctx.set(span_id)


def get_current_request_id() -> str:
    """Retrieve current request ID from context or default."""
    return request_id_ctx.get() or "req-untracked"


def get_current_trace_id() -> str:
    """Retrieve current trace ID from context or default."""
    return trace_id_ctx.get() or "trace-untracked"


def get_current_span_id() -> str:
    """Retrieve current span ID from context or default."""
    return span_id_ctx.get() or "span-untracked"
