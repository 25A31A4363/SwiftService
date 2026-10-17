import abc
import hashlib
import time
import uuid
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.app.core.security_hardening import PromptInjectionGuard, PIIMinimizer
from backend.app.services.security_audit_service import SecurityAuditService
from backend.app.core.errors import ValidationError

class AIGovernedResult:
    def __init__(
        self,
        output_text: str,
        confidence: float,
        evidence: List[str],
        uncertainty: bool,
        uncertainty_reason: Optional[str] = None,
        structured_data: Optional[Dict[str, Any]] = None,
        tokens_used: int = 0
    ):
        self.output_text = output_text
        self.confidence = max(0.0, min(1.0, float(confidence)))
        self.evidence = evidence or []
        self.uncertainty = uncertainty
        self.uncertainty_reason = uncertainty_reason
        self.structured_data = structured_data or {}
        self.tokens_used = tokens_used

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outputText": self.output_text,
            "confidence": round(self.confidence, 3),
            "evidence": self.evidence,
            "uncertainty": self.uncertainty,
            "uncertaintyReason": self.uncertainty_reason,
            "structuredData": self.structured_data,
            "tokensUsed": self.tokens_used
        }


class AIProviderInterface(abc.ABC):
    """Abstract interface decoupling business logic from concrete AI model backends."""

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        pass

    @abc.abstractmethod
    def generate(
        self,
        sanitized_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> AIGovernedResult:
        """Execute inference on sanitized prompt."""
        pass


class DeterministicLocalProvider(AIProviderInterface):
    """
    In-memory deterministic operational intelligence provider.
    Runs completely within organizational trust boundary with zero external egress.
    Guarantees no external data leakage.
    """

    @property
    def provider_name(self) -> str:
        return "LOCAL_DETERMINISTIC"

    @property
    def model_name(self) -> str:
        return "r5-deterministic-rule-v1"

    def generate(
        self,
        sanitized_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> AIGovernedResult:
        ctx = context or {}
        store_id = ctx.get("store_id", "GLOBAL")
        evidence = ctx.get("evidence", [])
        
        # Calculate deterministic confidence based on verified evidence count
        if not evidence:
            confidence = 0.55
            uncertainty = True
            uncertainty_reason = "Limited deterministic evidence available in operational context."
        else:
            confidence = min(0.98, 0.70 + (len(evidence) * 0.08))
            uncertainty = False
            uncertainty_reason = None

        output = (
            f"[Deterministic Analysis for {store_id}]: "
            f"Evaluated input with {len(evidence)} verified operational evidence points. "
            f"Confidence: {round(confidence * 100, 1)}%."
        )

        tokens = max(15, len(sanitized_prompt.split()) + len(output.split()))

        return AIGovernedResult(
            output_text=output,
            confidence=confidence,
            evidence=evidence,
            uncertainty=uncertainty,
            uncertainty_reason=uncertainty_reason,
            structured_data={"processedBy": self.model_name, "contextKeys": list(ctx.keys())},
            tokens_used=tokens
        )


class ExternalSecureLLMProvider(AIProviderInterface):
    """
    Enterprise-grade external LLM provider simulation.
    Requires strictly sanitized prompts with all PII scrubbed beforehand.
    """

    def __init__(self, model_name: str = "enterprise-claude-or-gemini-v1"):
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "EXTERNAL_ENTERPRISE_LLM"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(
        self,
        sanitized_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> AIGovernedResult:
        ctx = context or {}
        evidence = ctx.get("evidence", ["EVID-SEC-EXT-01"])

        # Check prompt grounding
        confidence = 0.92 if evidence else 0.65
        uncertainty = len(evidence) == 0
        uncertainty_reason = "External model generation without verified ground-truth links" if uncertainty else None

        output = f"[Enterprise LLM Summary]: Synthesized insights based on sanitized prompt. Grounded in {len(evidence)} signals."
        tokens = len(sanitized_prompt.split()) * 2 + len(output.split())

        return AIGovernedResult(
            output_text=output,
            confidence=confidence,
            evidence=evidence,
            uncertainty=uncertainty,
            uncertainty_reason=uncertainty_reason,
            structured_data={"provider": self.provider_name, "model": self.model_name},
            tokens_used=tokens
        )


class AIModelGateway:
    """
    Central governance gateway for AI execution:
    1. Prompt Injection Inspection (Rejects or flags prompt injections)
    2. PII Minimization & Redaction (Zero sensitive data sent to external providers)
    3. Provider Selection & Abstraction
    4. Output Validation (confidence, evidence, uncertainty checks)
    5. Audit Logging to `ai_governance_logs`
    6. Human Override Handling
    """

    _providers: Dict[str, AIProviderInterface] = {
        "LOCAL_DETERMINISTIC": DeterministicLocalProvider(),
        "EXTERNAL_ENTERPRISE_LLM": ExternalSecureLLMProvider(),
    }

    _circuit_breakers: Dict[str, Any] = {}

    @classmethod
    def register_provider(cls, name: str, provider: AIProviderInterface) -> None:
        cls._providers[name] = provider

    @classmethod
    def get_circuit_breaker(cls, provider_name: str):
        from backend.app.core.circuit_breaker import CircuitBreaker
        if provider_name not in cls._circuit_breakers:
            cls._circuit_breakers[provider_name] = CircuitBreaker(name=f"ai_{provider_name}")
        return cls._circuit_breakers[provider_name]

    @classmethod
    def execute(
        cls,
        conn: sqlite3.Connection,
        organization_id: str,
        prompt: str,
        user_id: Optional[str] = None,
        provider_name: str = "LOCAL_DETERMINISTIC",
        context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        source_ip: Optional[str] = None
    ) -> Dict[str, Any]:
        from backend.app.core.tracing import get_current_request_id
        from backend.app.core.logger import logger
        start_time = time.time()
        request_id = get_current_request_id()

        # Step 1: Prompt Injection Guard
        injection_result = PromptInjectionGuard.inspect_prompt(prompt)
        if injection_result["is_injection"]:
            # Record security incident
            SecurityAuditService.record_event(
                conn=conn,
                event_type="PROMPT_INJECTION_ATTEMPT",
                severity="HIGH",
                organization_id=organization_id,
                user_id=user_id,
                source_ip=source_ip,
                path="/security/ai/execute",
                details={
                    "flaggedPatterns": injection_result["flagged_patterns"],
                    "riskScore": injection_result["risk_score"]
                }
            )
            if injection_result["risk_score"] >= 0.7:
                raise ValidationError(
                    f"Prompt rejected: high-risk prompt injection patterns detected ({injection_result['flagged_patterns']}).",
                    details=injection_result
                )

        # Step 2: PII Minimization & Redaction
        # Rule: No sensitive information should be unnecessarily sent to external AI providers
        redacted_prompt, pii_count, pii_categories = PIIMinimizer.redact_pii(
            injection_result["sanitized_text"]
        )

        # Step 3: Provider Abstraction & Circuit Breaker Check
        cb = cls.get_circuit_breaker(provider_name)
        target_provider_name = provider_name
        status = "SUCCESS"
        error_msg = None

        if provider_name != "LOCAL_DETERMINISTIC" and not cb.can_execute():
            logger.warning(f"Circuit breaker for '{provider_name}' is OPEN. Fast fallback to LOCAL_DETERMINISTIC.")
            target_provider_name = "LOCAL_DETERMINISTIC"
            status = "DEGRADED_FALLBACK"

        provider = cls._providers.get(target_provider_name, cls._providers["LOCAL_DETERMINISTIC"])

        # Step 4: Prompt Hashing for Auditability (never store plaintext prompt with secrets)
        prompt_hash = hashlib.sha256(redacted_prompt.encode("utf-8")).hexdigest()

        # Step 5: Execute Inference with Resilient Fallback Protection
        try:
            result = provider.generate(
                sanitized_prompt=redacted_prompt,
                context=context,
                options=options
            )
            cb.record_success()
        except Exception as gen_err:
            cb.record_failure(gen_err)
            error_msg = str(gen_err)
            logger.warning(f"AI provider '{target_provider_name}' failed: {gen_err}. Engaging graceful degradation fallback.")
            status = "DEGRADED_FALLBACK"

            # Fallback to local deterministic provider
            fallback_provider = cls._providers["LOCAL_DETERMINISTIC"]
            try:
                result = fallback_provider.generate(
                    sanitized_prompt=redacted_prompt,
                    context=context,
                    options=options
                )
                provider = fallback_provider
            except Exception as fb_err:
                status = "DEGRADED"
                error_msg = f"{error_msg} | Fallback failed: {str(fb_err)}"
                result = AIGovernedResult(
                    output_text="[AI Degraded Baseline]: Processed under local operational heuristic rules.",
                    confidence=0.0,
                    evidence=[],
                    uncertainty=True,
                    uncertainty_reason=f"AI generation unavailable: {error_msg}",
                    structured_data={"degraded": True, "error": error_msg},
                    tokens_used=10
                )

        # Step 6: Output Validation & Defensive Bounds Checking
        if not isinstance(result, AIGovernedResult):
            result = AIGovernedResult(
                output_text=str(result) if result else "[Empty AI response; degraded]",
                confidence=0.0,
                evidence=[],
                uncertainty=True,
                uncertainty_reason="Invalid response type from model"
            )

        if not (0.0 <= result.confidence <= 1.0):
            result.confidence = max(0.0, min(1.0, float(result.confidence or 0.0)))

        if not result.output_text:
            result.output_text = "[Empty AI response: safe heuristic fallback]"
            result.uncertainty = True
            result.uncertainty_reason = "Model generated empty text"

        if result.evidence is None:
            result.evidence = []

        latency_ms = round((time.time() - start_time) * 1000, 2)
        prompt_tokens = max(1, len(redacted_prompt.split()))
        output_tokens = max(1, len(result.output_text.split()))

        # Step 7: Record AI Governance Log with Status & Tracing
        log_id = f"ai-gov-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ai_governance_logs (
                id, organization_id, user_id, provider_name, model_name,
                prompt_hash, pii_redacted, prompt_tokens, output_tokens,
                latency_ms, confidence, uncertainty, uncertainty_reason,
                is_overridden, override_by, override_reason, created_at,
                request_id, status, error_message, task_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, ?, ?, ?, ?, 'INFERENCE');
        """, (
            log_id, organization_id, user_id, provider.provider_name, provider.model_name,
            prompt_hash, pii_count, prompt_tokens, output_tokens,
            latency_ms, result.confidence, 1 if result.uncertainty else 0,
            result.uncertainty_reason, now, request_id, status, error_msg
        ))
        conn.commit()

        return {
            "governanceLogId": log_id,
            "provider": provider.provider_name,
            "model": provider.model_name,
            "promptHash": prompt_hash,
            "piiRedactedCount": pii_count,
            "piiCategoriesRedacted": pii_categories,
            "latencyMs": latency_ms,
            "status": status,
            "isDegraded": status != "SUCCESS",
            "errorMessage": error_msg,
            "result": result.to_dict(),
            "timestamp": now
        }

    @classmethod
    def record_human_override(
        cls,
        conn: sqlite3.Connection,
        governance_log_id: str,
        user_id: str,
        override_reason: str,
        new_confidence: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a human operator override of an AI decision or confidence score.
        """
        if not override_reason or len(override_reason.strip()) < 5:
            raise ValidationError("Override reason must provide clear human justification (min 5 chars).")

        cur = conn.cursor()
        cur.execute("""
            SELECT id, organization_id, provider_name, confidence, is_overridden
            FROM ai_governance_logs
            WHERE id = ?;
        """, (governance_log_id,))
        row = cur.fetchone()
        if not row:
            raise ValidationError(f"AI Governance log '{governance_log_id}' not found.")

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            UPDATE ai_governance_logs
            SET is_overridden = 1,
                override_by = ?,
                override_reason = ?
            WHERE id = ?;
        """, (user_id, override_reason.strip(), governance_log_id))
        conn.commit()

        # Record Security Audit Event for governance auditability
        SecurityAuditService.record_event(
            conn=conn,
            event_type="AI_HUMAN_OVERRIDE",
            severity="MEDIUM",
            organization_id=row["organization_id"],
            user_id=user_id,
            path=f"/security/governance/override/{governance_log_id}",
            details={
                "governanceLogId": governance_log_id,
                "provider": row["provider_name"],
                "previousConfidence": row["confidence"],
                "newConfidence": new_confidence,
                "overrideReason": override_reason,
                "notes": notes
            }
        )

        return {
            "governanceLogId": governance_log_id,
            "isOverridden": True,
            "overrideBy": user_id,
            "overrideReason": override_reason,
            "updatedAt": now
        }

    @classmethod
    def list_governance_logs(
        cls,
        conn: sqlite3.Connection,
        organization_id: str,
        provider_name: Optional[str] = None,
        only_overridden: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        cur = conn.cursor()
        conditions = ["organization_id = ?"]
        params: List[Any] = [organization_id]

        if provider_name:
            conditions.append("provider_name = ?")
            params.append(provider_name)
        if only_overridden:
            conditions.append("is_overridden = 1")

        where_str = " WHERE " + " AND ".join(conditions)

        cur.execute(f"SELECT COUNT(*) as cnt FROM ai_governance_logs{where_str};", tuple(params))
        total = cur.fetchone()["cnt"]

        params.extend([limit, offset])
        cur.execute(f"""
            SELECT id, organization_id, user_id, provider_name, model_name,
                   prompt_hash, pii_redacted, prompt_tokens, output_tokens,
                   latency_ms, confidence, uncertainty, uncertainty_reason,
                   is_overridden, override_by, override_reason, created_at
            FROM ai_governance_logs
            {where_str}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?;
        """, tuple(params))
        rows = cur.fetchall()

        logs = [
            {
                "id": r["id"],
                "organizationId": r["organization_id"],
                "userId": r["user_id"],
                "providerName": r["provider_name"],
                "modelName": r["model_name"],
                "promptHash": r["prompt_hash"],
                "piiRedacted": r["pii_redacted"],
                "tokens": {"prompt": r["prompt_tokens"], "output": r["output_tokens"]},
                "latencyMs": r["latency_ms"],
                "confidence": r["confidence"],
                "uncertainty": bool(r["uncertainty"]),
                "uncertaintyReason": r["uncertainty_reason"],
                "isOverridden": bool(r["is_overridden"]),
                "overrideBy": r["override_by"],
                "overrideReason": r["override_reason"],
                "createdAt": r["created_at"]
            }
            for r in rows
        ]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": logs
        }
