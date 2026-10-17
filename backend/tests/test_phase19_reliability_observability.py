"""
Phase 19: Production Reliability and Observability Test Suite
Tests:
- Structured logging & request tracing with W3C traceparent and contextvars
- AI resilience & graceful degradation (never corrupt operational data)
- Multichannel ingestion monitoring & multi-source resilience
- Database-backed idempotency protection (Idempotency-Key)
- Background processing, retries with exponential backoff, dead-letter failed jobs
- In-memory TTL caching with hit/miss telemetry & invalidation
- Health checks, Kubernetes readiness/liveness probes, deep diagnostic checks
- Real-time error monitoring registry & circuit breakers
- Standardized pagination (PaginationMeta) across all operational list endpoints
"""

import uuid
import json
import time
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.database import get_connection
from backend.app.core.tracing import (
    extract_or_generate_trace_context,
    format_traceparent,
    parse_traceparent,
    set_trace_context,
    get_current_trace_id,
    get_current_request_id
)
from backend.app.core.cache import TTLCache
from backend.app.core.circuit_breaker import CircuitBreaker, CircuitState
from backend.app.core.error_monitor import ErrorMonitor
from backend.app.core.idempotency import IdempotencyManager
from backend.app.services.job_service import JobService
from backend.app.services.ingestion_monitoring_service import IngestionMonitoringService
from backend.app.services.ai_governance_service import AIModelGateway, AIProviderInterface, AIGovernedResult
from backend.app.services.emerging_detection_service import EmergingDetectionService
from backend.app.services.feedback_service import FeedbackService
from backend.app.schemas.domain import FeedbackCreate


client = TestClient(app)

ADMIN_AUTH = {
    "organizationId": "org-apex-01",
    "role": "ORGANIZATION_ADMIN",
    "userId": "usr-admin",
    "email": "orgadmin@apex.com"
}


def get_auth_token():
    from backend.app.core.security import create_access_token
    return create_access_token({
        "userId": "usr-admin",
        "email": "orgadmin@apex.com",
        "role": "ORGANIZATION_ADMIN",
        "organizationId": "org-apex-01"
    })


class TestPhase19ReliabilityAndObservability:

    @pytest.fixture(autouse=True)
    def setup_headers(self):
        token = get_auth_token()
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.headers["Content-Type"] = "application/json"

    # =========================================================================
    # 1. REQUEST TRACING & STRUCTURED LOGGING
    # =========================================================================
    def test_request_tracing_headers_propagation(self):
        """Verify middleware propagates X-Request-ID, X-Trace-ID, and W3C traceparent."""
        custom_req_id = f"req-{uuid.uuid4().hex[:12]}"
        custom_traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

        headers = {
            **self.headers,
            "X-Request-ID": custom_req_id,
            "traceparent": custom_traceparent
        }

        res = client.get("/api/v1/health", headers=headers)
        assert res.status_code == 200

        # Verify response headers
        assert res.headers.get("X-Request-ID") == custom_req_id
        assert "X-Trace-ID" in res.headers
        assert res.headers["X-Trace-ID"] == "4bf92f3577b34da6a3ce929d0e0e4736"
        assert "traceparent" in res.headers
        assert "4bf92f3577b34da6a3ce929d0e0e4736" in res.headers["traceparent"]
        assert "X-Response-Time-Ms" in res.headers

    def test_w3c_traceparent_parser_and_formatter(self):
        """Test unit parsing and generation of W3C traceparent headers."""
        raw_tp = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        parsed = parse_traceparent(raw_tp)
        assert parsed is not None
        trace_id, parent_span, flags = parsed
        assert trace_id == "0af7651916cd43dd8448eb211c80319c"
        assert parent_span == "b7ad6b7169203331"
        assert flags == "01"

        formatted = format_traceparent(trace_id, "1234567812345678", "01")
        assert formatted.startswith("00-0af7651916cd43dd8448eb211c80319c-1234567812345678-01")

    # =========================================================================
    # 2. DATABASE-BACKED IDEMPOTENCY
    # =========================================================================
    def test_idempotency_prevents_duplicate_mutations(self):
        """
        Verify that repeating a mutation request with the same Idempotency-Key
        returns the cached response without creating duplicate database records.
        """
        idem_key = f"idem-key-{uuid.uuid4().hex}"
        unique_text = f"Spill in Dairy Aisle near cooler #{uuid.uuid4().hex[:6]}"

        payload = {
            "storeId": "store-104",
            "channelType": "MANUAL_ENTRY",
            "sourceType": "MANUAL_ENTRY",
            "submitterType": "STORE_ASSOCIATE",
            "rawText": unique_text,
            "languageCode": "en",
            "allowDuplicates": True
        }

        headers = {
            **self.headers,
            "Idempotency-Key": idem_key
        }

        # First Call: Ingestion executes and stores idempotency record
        res1 = client.post("/api/v1/feedback", json=payload, headers=headers)
        assert res1.status_code == 201
        data1 = res1.json()["data"]
        feedback_id1 = data1["id"]
        assert res1.headers.get("X-Cache-Lookup") == "IDEMPOTENT-STORE"

        # Second Call: Identical key & payload returns cached response immediately
        res2 = client.post("/api/v1/feedback", json=payload, headers=headers)
        assert res2.status_code == 201
        data2 = res2.json()["data"]
        assert data2["id"] == feedback_id1
        assert res2.headers.get("X-Cache-Lookup") == "IDEMPOTENT-HIT"
        assert res2.headers.get("X-Idempotency-Key") == idem_key

        # Verify only ONE feedback item exists in database
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM feedback_items WHERE raw_text = ?;", (unique_text,))
            count = cur.fetchone()[0]
        finally:
            conn.close()
        assert count == 1

    def test_idempotency_conflict_on_mismatched_payload(self):
        """Verify reusing the same Idempotency-Key with different payload raises 409 Conflict."""
        idem_key = f"idem-key-conflict-{uuid.uuid4().hex}"

        headers = {**self.headers, "Idempotency-Key": idem_key}

        payload1 = {
            "storeId": "store-104",
            "rawText": "First request message text 123",
            "channelType": "MANUAL_ENTRY"
        }
        res1 = client.post("/api/v1/feedback", json=payload1, headers=headers)
        assert res1.status_code == 201

        # Mismatched payload with identical key
        payload2 = {
            "storeId": "store-104",
            "rawText": "DIFFERING PAYLOAD TEXT CONTENT 456",
            "channelType": "MANUAL_ENTRY"
        }
        res2 = client.post("/api/v1/feedback", json=payload2, headers=headers)
        assert res2.status_code == 409
        err = res2.json()["error"]
        assert err["code"] == "CONFLICT"
        assert "Idempotency conflict" in err["message"]

    # =========================================================================
    # 3. HEALTH, READINESS & LIVENESS CHECKS
    # =========================================================================
    def test_liveness_probe(self):
        """Verify /health/live returns 200 OK and confirms process responsiveness."""
        res = client.get("/api/v1/health/live")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "alive"
        assert data["uptimeSeconds"] >= 0

    def test_readiness_probe(self):
        """Verify /health/ready confirms database connection and journal mode."""
        res = client.get("/api/v1/health/ready")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "ready"
        assert data["database"]["connected"] is True
        assert data["filesystem"]["writable"] is True

    def test_deep_health_inspection(self):
        """Verify /health/deep reports database, AI circuit breakers, and background job counts."""
        res = client.get("/api/v1/health/deep")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "database" in data
        assert "aiCircuitBreakers" in data
        assert "backgroundJobs" in data
        assert "ingestionHealth" in data
        assert "cache" in data

    # =========================================================================
    # 4. AI RESILIENCE & GRACEFUL DEGRADATION
    # =========================================================================
    def test_graceful_degradation_on_ai_failure_never_corrupts_data(self, monkeypatch):
        """
        Critical Rule: Never allow AI failure to corrupt operational data.
        If the AI understanding service throws an exception or provider is down,
        the raw operational feedback must be preserved 100% intact with degraded status,
        and a background reprocessing job must be enqueued.
        """
        from backend.app.services.ai_understanding_service import AIUnderstandingService

        def faulty_extractor(*args, **kwargs):
            raise ConnectionError("AI Cloud Inference Gateway Connection Timed Out (504)")

        monkeypatch.setattr(AIUnderstandingService, "extract_understanding", faulty_extractor)

        verbatim_text = f"CRITICAL: Spill in Aisle 4 causing customer slip risk #{uuid.uuid4().hex[:6]}"
        payload = FeedbackCreate(
            storeId="store-104",
            rawText=verbatim_text,
            channelType="MANUAL_ENTRY",
            sourceType="MANUAL_ENTRY",
            submitterType="STORE_ASSOCIATE",
            languageCode="en",
            allowDuplicates=True
        )

        conn = get_connection()
        try:
            record = FeedbackService.ingest_feedback(
                conn=conn,
                organization_id="org-apex-01",
                payload=payload,
                operator_user=ADMIN_AUTH
            )
        finally:
            conn.close()

        # Operational data MUST be safely ingested without corruption
        assert record is not None
        assert record["rawText"] == verbatim_text
        assert record["processingStatus"] == "degraded"
        assert "AI processing degraded" in (record.get("processingError") or "")

        # Verify a background reprocessing job was enqueued
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM background_jobs
                WHERE job_type = 'FEEDBACK_REPROCESSING'
                ORDER BY created_at DESC LIMIT 1;
            """)
            job_row = cur.fetchone()
        finally:
            conn.close()

        assert job_row is not None
        job_payload = json.loads(job_row["payload"])
        assert job_payload["feedbackId"] == record["id"]

    def test_circuit_breaker_trips_to_open_on_consecutive_ai_failures(self):
        """Test circuit breaker trips after repeated failures and fast-fails."""
        cb = CircuitBreaker("test_provider_cb", failure_threshold=3, recovery_timeout_seconds=2.0)
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

        cb.record_failure(Exception("Fail 1"))
        assert cb.state == CircuitState.CLOSED
        cb.record_failure(Exception("Fail 2"))
        assert cb.state == CircuitState.CLOSED
        cb.record_failure(Exception("Fail 3"))
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

        # Reset returns to normal
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_ai_model_gateway_fallback_and_invalid_response_sanitization(self):
        """Verify AIModelGateway falls back gracefully when external provider throws."""
        class FailingProvider(AIProviderInterface):
            @property
            def provider_name(self) -> str:
                return "FAILING_TEST_PROVIDER"
            @property
            def model_name(self) -> str:
                return "failing-model-v1"
            def generate(self, sanitized_prompt, context=None, options=None):
                raise RuntimeError("External AI provider 500 internal server error")

        AIModelGateway.register_provider("FAILING_TEST_PROVIDER", FailingProvider())

        conn = get_connection()
        try:
            res = AIModelGateway.execute(
                conn=conn,
                organization_id="org-apex-01",
                prompt="Investigate refrigeration anomaly",
                provider_name="FAILING_TEST_PROVIDER"
            )
        finally:
            conn.close()

        assert res["status"] == "DEGRADED_FALLBACK"
        assert res["isDegraded"] is True
        assert res["result"]["confidence"] >= 0.0

    # =========================================================================
    # 5. MULTICHANNEL INGESTION MONITORING
    # =========================================================================
    def test_ingestion_monitoring_metrics_endpoint(self):
        """Verify ingestion metrics are tracked per channel and queryable via API."""
        IngestionMonitoringService.record_ingestion("CUSTOMER_COMPLAINT", success=True, latency_ms=45.0)
        IngestionMonitoringService.record_ingestion("CUSTOMER_COMPLAINT", success=False, error_message="Text too short")

        res = client.get("/api/v1/observability/ingestion", headers=self.headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert "channels" in data
        assert "summary" in data

        complaint_channel = next((c for c in data["channels"] if c["channel"] == "CUSTOMER_COMPLAINT"), None)
        assert complaint_channel is not None
        assert complaint_channel["sessionReceived"] >= 2
        assert complaint_channel["sessionFailed"] >= 1

    def test_bulk_ingestion_resilience_partial_failure(self):
        """Verify that malformed data in a batch does not abort valid items."""
        conn = get_connection()
        try:
            items = [
                FeedbackCreate(storeId="store-104", rawText="Valid operational observation 1", channelType="MANUAL_ENTRY"),
                FeedbackCreate(storeId="store-104", rawText="x", channelType="MANUAL_ENTRY"), # Malformed (too short)
                FeedbackCreate(storeId="store-104", rawText="Valid operational observation 2", channelType="MANUAL_ENTRY"),
            ]

            result = FeedbackService.ingest_bulk(conn, "org-apex-01", items)
        finally:
            conn.close()

        assert result["totalProcessed"] == 3
        assert result["succeeded"] == 2
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["index"] == 1

    # =========================================================================
    # 6. BACKGROUND PROCESSING & FAILED-JOB RETRIES
    # =========================================================================
    def test_background_job_retry_lifecycle_and_dead_letter_failure(self):
        """
        Verify background jobs retry with exponential backoff on failure,
        and move to FAILED dead-letter status when exceeding max_retries.
        """
        # Register a test job handler that intentionally fails
        attempt_tracker = []
        def failing_job_handler(conn, payload):
            attempt_tracker.append(time.time())
            raise ValueError("Test job execution intentional failure")

        JobService.register_handler("TEST_FAILING_JOB", failing_job_handler)

        conn = get_connection()
        try:
            job = JobService.enqueue_job(
                conn=conn,
                job_type="TEST_FAILING_JOB",
                payload={"testKey": "testVal"},
                max_retries=2,
                backoff_seconds=1
            )
            job_id = job["id"]

            # 1st Attempt: Fails and transitions to RETRYING
            res1 = JobService.process_next_job(conn, job_id=job_id)
            assert res1 is not None
            assert res1["id"] == job_id
            assert res1["status"] == "RETRYING"
            assert res1["attempts"] == 1

            # Advance scheduled_at for test execution
            cur = conn.cursor()
            cur.execute("UPDATE background_jobs SET scheduled_at = ? WHERE id = ?;", (
                "2020-01-01T00:00:00", job_id
            ))
            conn.commit()

            # 2nd Attempt: Exceeds max_retries (2) and transitions to dead-letter FAILED
            res2 = JobService.process_next_job(conn, job_id=job_id)
            assert res2 is not None
            assert res2["status"] == "FAILED"
            assert res2["attempts"] == 2
            assert "Test job execution intentional failure" in res2["lastError"]

            # Verify failed jobs endpoint returns it
            failed_jobs = JobService.get_failed_jobs(conn)
            assert any(j["id"] == job_id for j in failed_jobs["items"])

            # Manual retry resets job to PENDING
            retried = JobService.retry_failed_job(conn, job_id)
            assert retried["status"] == "PENDING"
            assert retried["attempts"] == 0
        finally:
            conn.close()

    # =========================================================================
    # 7. IN-MEMORY TTL CACHING
    # =========================================================================
    def test_ttl_cache_operations_and_telemetry(self):
        """Verify TTL cache handles set, get, expiration, eviction, and hit metrics."""
        cache = TTLCache(max_size=3, default_ttl_seconds=10.0)

        cache.set("k1", "v1")
        cache.set("k2", "v2")

        assert cache.get("k1") == "v1" # Hit
        assert cache.get("k2") == "v2" # Hit
        assert cache.get("k_missing") is None # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hitRatioPct"] > 60.0

        # Prefix invalidation
        cache.set("store:1:info", "data1")
        cache.set("store:2:info", "data2")
        cache.invalidate_prefix("store:")
        assert cache.get("store:1:info") is None

    # =========================================================================
    # 8. ERROR MONITORING REGISTRY
    # =========================================================================
    def test_error_monitor_registry_metrics(self):
        """Verify error monitor tracks error codes and maintains recent error circular buffer."""
        em = ErrorMonitor(max_recent_errors=10)
        em.record_error(code="VALIDATION_ERROR", status_code=422, message="Invalid store ID", path="/api/v1/feedback")
        em.record_error(code="NOT_FOUND", status_code=404, message="Store not found", path="/api/v1/stores/999")

        metrics = em.get_metrics()
        assert metrics["totalErrors"] == 2
        assert metrics["errorsByCode"]["VALIDATION_ERROR"] == 1
        assert metrics["errorsByCode"]["NOT_FOUND"] == 1

        recent = em.get_recent_errors(limit=5)
        assert len(recent) == 2
        assert recent[0]["code"] == "NOT_FOUND" # Most recent first

    # =========================================================================
    # 9. STANDARDIZED PAGINATION (PaginationMeta)
    # =========================================================================
    def test_pagination_meta_across_list_endpoints(self):
        """Verify standard pagination metadata is returned across list endpoints."""
        endpoints = [
            "/api/v1/issues?page=1&limit=5",
            "/api/v1/audit-logs?page=1&limit=5",
            "/api/v1/alerts?page=1&limit=5",
            "/api/v1/briefs?page=1&limit=5",
            "/api/v1/jobs?page=1&limit=5",
            "/api/v1/observability/ai-logs?page=1&limit=5"
        ]

        for ep in endpoints:
            res = client.get(ep, headers=self.headers)
            assert res.status_code == 200, f"Failed on endpoint {ep}"
            body = res.json()
            assert "data" in body
            assert isinstance(body["data"], list)
            assert "meta" in body
            meta = body["meta"]
            assert meta["page"] == 1
            assert meta["limit"] == 5
            assert "total" in meta
            assert "totalPages" in meta

    # =========================================================================
    # 10. INSUFFICIENT HISTORICAL DATA HANDLING
    # =========================================================================
    def test_insufficient_historical_data_graceful_handling(self):
        """Verify velocity baseline calculation handles empty or sparse data gracefully."""
        conn = get_connection()
        try:
            fake_store_id = f"store-empty-{uuid.uuid4().hex[:6]}"

            baseline = EmergingDetectionService.calculate_historical_baseline(
                conn=conn,
                store_id=fake_store_id,
                category="REFRIGERATION_FAILURE",
                baseline_days=14,
                recent_hours=24
            )
        finally:
            conn.close()

        assert baseline["status"] == "INSUFFICIENT_BASELINE"
        assert baseline["observations"] == 0
        assert baseline["dailyMean"] == 0.0
        assert "minimum" in baseline["reason"].lower()
