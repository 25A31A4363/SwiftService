"""
R5 Operational Intelligence Platform - Multichannel Ingestion Monitoring Service
Tracks real-time throughput, error rates, duplicates, AI degradation, and health status
across all frontline ingestion connectors.
"""

import sqlite3
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from backend.app.core.connectors import ConnectorRegistry


class IngestionMonitoringService:
    _lock = threading.RLock()
    _channel_metrics: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _init_channel(cls, channel: str) -> None:
        if channel not in cls._channel_metrics:
            cls._channel_metrics[channel] = {
                "channel": channel,
                "totalReceived": 0,
                "totalSucceeded": 0,
                "totalFailed": 0,
                "duplicatesDetected": 0,
                "degradedCount": 0,
                "totalLatencyMs": 0.0,
                "lastIngestedAt": None,
                "lastErrorMessage": None
            }

    @classmethod
    def record_ingestion(
        cls,
        channel: str,
        success: bool,
        latency_ms: float = 0.0,
        is_duplicate: bool = False,
        is_degraded: bool = False,
        error_message: Optional[str] = None
    ) -> None:
        with cls._lock:
            ch = (channel or "MANUAL_ENTRY").upper()
            cls._init_channel(ch)
            m = cls._channel_metrics[ch]

            m["totalReceived"] += 1
            m["totalLatencyMs"] += latency_ms
            if success:
                m["totalSucceeded"] += 1
                m["lastIngestedAt"] = datetime.now(timezone.utc).isoformat()
            else:
                m["totalFailed"] += 1
                m["lastErrorMessage"] = error_message

            if is_duplicate:
                m["duplicatesDetected"] += 1
            if is_degraded:
                m["degradedCount"] += 1

    @classmethod
    def get_channel_metrics(cls, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        """
        Return comprehensive ingestion metrics combining in-memory session telemetry
        and persisted database statistics.
        """
        with cls._lock:
            # Ensure all registered channels are initialized
            for ch in ConnectorRegistry.supported_channels():
                cls._init_channel(ch)

            channels_data = []
            total_ingested = 0
            total_failed = 0
            total_duplicates = 0
            total_degraded = 0

            # Pull database totals if connection available
            db_counts = {}
            if conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT channel_type, COUNT(*) as cnt,
                           SUM(CASE WHEN is_duplicate = 1 THEN 1 ELSE 0 END) as dup_cnt,
                           SUM(CASE WHEN processing_status = 'degraded' THEN 1 ELSE 0 END) as deg_cnt
                    FROM feedback_items
                    GROUP BY channel_type;
                """)
                for r in cur.fetchall():
                    db_counts[r["channel_type"]] = {
                        "dbTotal": r["cnt"],
                        "dbDuplicates": r["dup_cnt"] or 0,
                        "dbDegraded": r["deg_cnt"] or 0
                    }

            for ch_name, stats in cls._channel_metrics.items():
                rcv = stats["totalReceived"]
                succ = stats["totalSucceeded"]
                fail = stats["totalFailed"]
                avg_lat = round(stats["totalLatencyMs"] / rcv, 2) if rcv > 0 else 0.0
                fail_rate = round((fail / rcv) * 100.0, 2) if rcv > 0 else 0.0

                # Health classification
                if rcv == 0:
                    health = "IDLE"
                elif fail_rate > 10.0:
                    health = "DEGRADED"
                elif fail_rate > 30.0:
                    health = "ERROR"
                else:
                    health = "HEALTHY"

                db_info = db_counts.get(ch_name, {})

                ch_summary = {
                    "channel": ch_name,
                    "health": health,
                    "sessionReceived": rcv,
                    "sessionSucceeded": succ,
                    "sessionFailed": fail,
                    "sessionFailureRatePct": fail_rate,
                    "sessionDuplicates": stats["duplicatesDetected"],
                    "sessionDegraded": stats["degradedCount"],
                    "avgLatencyMs": avg_lat,
                    "lastIngestedAt": stats["lastIngestedAt"],
                    "lastErrorMessage": stats["lastErrorMessage"],
                    "persistedTotalCount": db_info.get("dbTotal", 0),
                    "persistedDuplicateCount": db_info.get("dbDuplicates", 0),
                    "persistedDegradedCount": db_info.get("dbDegraded", 0)
                }
                channels_data.append(ch_summary)

                total_ingested += succ
                total_failed += fail
                total_duplicates += stats["duplicatesDetected"]
                total_degraded += stats["degradedCount"]

            return {
                "channels": sorted(channels_data, key=lambda x: x["channel"]),
                "summary": {
                    "totalIngestedSession": total_ingested,
                    "totalFailedSession": total_failed,
                    "totalDuplicatesSession": total_duplicates,
                    "totalDegradedSession": total_degraded,
                    "overallHealth": "HEALTHY" if total_failed == 0 or (total_failed / max(1, total_ingested + total_failed) < 0.05) else "DEGRADED"
                }
            }
