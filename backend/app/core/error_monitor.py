"""
R5 Operational Intelligence Platform - Error Monitoring Registry
Aggregates real-time error counts, error codes, HTTP statuses, and maintains a rolling
ring buffer of recent sanitized error incidents for observability and diagnostics.
"""

import time
import collections
import threading
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from backend.app.core.security_hardening import LogScrubber


class ErrorMonitor:
    def __init__(self, max_recent_errors: int = 50):
        self.max_recent_errors = max_recent_errors
        self._lock = threading.RLock()
        self._recent_errors: collections.deque[Dict[str, Any]] = collections.deque(maxlen=max_recent_errors)
        self._counts_by_code: Dict[str, int] = collections.defaultdict(int)
        self._counts_by_status: Dict[int, int] = collections.defaultdict(int)
        self._counts_by_path: Dict[str, int] = collections.defaultdict(int)
        self._total_errors: int = 0
        self._start_time = time.time()

    def record_error(
        self,
        code: str,
        status_code: int,
        message: str,
        path: Optional[str] = None,
        method: Optional[str] = None,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> None:
        with self._lock:
            self._total_errors += 1
            self._counts_by_code[code] += 1
            self._counts_by_status[status_code] += 1
            if path:
                self._counts_by_path[path] += 1

            sanitized_msg = LogScrubber.scrub(message)

            self._recent_errors.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "code": code,
                "statusCode": status_code,
                "message": sanitized_msg[:200],
                "path": path or "unknown",
                "method": method or "UNKNOWN",
                "requestId": request_id,
                "traceId": trace_id
            })

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            uptime = round(time.time() - self._start_time, 2)
            return {
                "totalErrors": self._total_errors,
                "uptimeSeconds": uptime,
                "errorsByCode": dict(self._counts_by_code),
                "errorsByStatus": {str(k): v for k, v in self._counts_by_status.items()},
                "topErrorPaths": sorted(
                    [{"path": p, "count": c} for p, c in self._counts_by_path.items()],
                    key=lambda x: int(str(x["count"])),
                    reverse=True
                )[:10],
                "recentErrorsCount": len(self._recent_errors)
            }

    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(list(self._recent_errors)))[:limit]

    def reset(self) -> None:
        with self._lock:
            self._recent_errors.clear()
            self._counts_by_code.clear()
            self._counts_by_status.clear()
            self._counts_by_path.clear()
            self._total_errors = 0


error_monitor = ErrorMonitor()
