import logging
import sys
import json
from datetime import datetime, timezone
from backend.app.core.config import settings
from backend.app.core.security_hardening import LogScrubber
from backend.app.core.tracing import get_current_request_id, get_current_trace_id

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        raw_msg = record.getMessage()
        safe_msg = LogScrubber.scrub(raw_msg)
        
        # Resolve trace and request identifiers from record or execution context
        request_id = getattr(record, "request_id", None) or get_current_request_id()
        trace_id = getattr(record, "trace_id", None) or get_current_trace_id()

        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": safe_msg,
        }

        if request_id and request_id != "req-untracked":
            log_obj["request_id"] = request_id
        if trace_id and trace_id != "trace-untracked":
            log_obj["trace_id"] = trace_id

        # Attach custom extra fields if provided
        for key in ("component", "duration_ms", "status_code", "path", "method", "user_id"):
            if hasattr(record, key):
                val = getattr(record, key)
                if val is not None:
                    log_obj[key] = val

        if record.exc_info:
            raw_exc = self.formatException(record.exc_info)
            log_obj["exception"] = LogScrubber.scrub(raw_exc)

        return json.dumps(log_obj)

def get_logger(name: str = "r5") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    return logger

logger = get_logger()
