"""
R5 Operational Intelligence Platform - Feedback Service
Phase 3 Implementation: Multichannel Feedback Ingestion, Pluggable Connectors,
3-Stage Representation (Raw Input -> Normalized -> AI Interpretation),
Duplicate Protection, Multilingual Processing, and Bulk Import.
"""

import uuid
import json
import re
import csv
import io
import unicodedata
import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from backend.app.core.connectors import ConnectorRegistry
from backend.app.core.errors import ValidationError, NotFoundError, DuplicateFeedbackError
from backend.app.core.logger import logger
from backend.app.schemas.domain import FeedbackCreate, FollowUpCreate, FeedbackStatusUpdate, FeedbackReviewRequest
from backend.app.services.audit_service import AuditService
from backend.app.services.ai_understanding_service import AIUnderstandingService

# PII Detection Regular Expressions
PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
CARD_REGEX = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
SSN_REGEX = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')

# Multilingual Vocabulary Lexicons for Heuristic AI Stage
SPANISH_KEYWORDS = {'el', 'la', 'los', 'las', 'un', 'una', 'en', 'de', 'con', 'por', 'para', 'estante', 'leche', 'pasillo', 'tibio', 'agua', 'piso', 'frio', 'fuga', 'goteando', 'roto', 'limpieza', 'caja', 'charco', 'congelador', 'caducado', 'sucio'}
FRENCH_KEYWORDS = {'le', 'la', 'les', 'des', 'dans', 'pour', 'avec', 'congelateur', 'rayon', 'bruit', 'fuit', 'glissant', 'panne', 'froid', 'chaud', 'magasin', 'eau', 'caisse', 'urgent', 'degat'}
GERMAN_KEYWORDS = {'der', 'die', 'das', 'und', 'in', 'im', 'kuehlregal', 'wasser', 'kuehlung', 'ausfall', 'boden', 'dreckig', 'defekt', 'regal', 'kasse', 'flur', 'tropft'}

CRITICAL_HAZARD_TERMS = {'severe', 'puddle', 'leak', 'leaking', 'water', 'flood', 'slip', 'fall', 'fire', 'shock', 'spark', 'smoke', 'spoiled', 'rotten', '48f', 'warm', 'overflow', 'congelador', 'charco', 'fuga', 'goteando'}
NEGATIVE_SENTIMENT_TERMS = {'broken', 'loud', 'noise', 'freezing', 'freeze', 'bad', 'terrible', 'horrible', 'ruined', 'dirty', 'awful', 'emergency', 'fail', 'failure', 'complaint', 'stuck', 'error', 'slow', 'tibio', 'roto', 'panne'}
POSITIVE_SENTIMENT_TERMS = {'great', 'clean', 'fast', 'excellent', 'helpful', 'good', 'wonderful', 'fixed', 'resolved', 'impressed', 'friendly', 'neat'}


class FeedbackService:
    """Core domain service for multichannel feedback ingestion, normalization, and evaluation."""

    @classmethod
    def ingest_feedback(
        cls,
        conn: sqlite3.Connection,
        organization_id: Optional[str],
        payload: FeedbackCreate,
        operator_user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest single feedback record through the 3-Stage Pipeline:
        Raw Input (immutable) -> Normalized Representation -> AI-Derived Interpretation
        """
        cur = conn.cursor()

        # ---------------------------------------------------------------------
        # STAGE 1: INGESTION VIA CONNECTOR & RAW PRESERVATION
        # ---------------------------------------------------------------------
        connector = ConnectorRegistry.get(payload.channelType or payload.sourceType)
        connector_data = connector.parse_payload({
            "channelType": payload.channelType,
            "sourceType": payload.sourceType,
            "submitterType": payload.submitterType,
            "privacyClassification": payload.privacyClassification,
            "rawText": payload.rawText,
            "languageCode": payload.languageCode,
            "storeId": payload.storeId,
            "regionId": payload.regionId,
            "organizationId": payload.organizationId or organization_id,
            "departmentId": payload.departmentId,
            "submittedAt": payload.submittedAt,
            "metadata": payload.metadata
        })

        # Connector Level Validation
        connector.validate(connector_data)

        # ---------------------------------------------------------------------
        # STAGE 2: VALIDATION & CONTEXT RESOLUTION
        # ---------------------------------------------------------------------
        raw_text = connector_data["rawText"]
        if not raw_text or len(raw_text.strip()) < 3:
            raise ValidationError("Feedback rawText must contain at least 3 non-whitespace characters.")

        store_id = connector_data["storeId"]
        if not store_id and operator_user and operator_user.get("storeId"):
            store_id = operator_user["storeId"]

        if not store_id:
            raise ValidationError("Missing operational context: storeId must be provided.")

        # Resolve store context in database
        cur.execute("SELECT id, organization_id, region_id, name FROM stores WHERE id = ?;", (store_id,))
        store_row = cur.fetchone()
        if not store_row:
            raise ValidationError(f"Missing operational context: store '{store_id}' does not exist.")

        resolved_org_id = store_row["organization_id"]
        resolved_region_id = store_row["region_id"]
        store_name = store_row["name"]

        # Cross-organization scoping check
        if organization_id and resolved_org_id != organization_id:
            raise ValidationError("Operational boundary violation: store belongs to another organization.")

        # ---------------------------------------------------------------------
        # STAGE 3: NORMALIZATION & DUPLICATE PROTECTION
        # ---------------------------------------------------------------------
        # Unicode Normalization (NFKC) & Whitespace Collapsing
        normalized_text = unicodedata.normalize("NFKC", raw_text)
        normalized_text = re.sub(r'\s+', ' ', normalized_text).strip()

        # PII Detection and Classification
        has_pii = bool(
            PHONE_REGEX.search(raw_text) or
            CARD_REGEX.search(raw_text) or
            EMAIL_REGEX.search(raw_text) or
            SSN_REGEX.search(raw_text)
        )

        privacy_classification = connector_data["privacyClassification"]
        if has_pii:
            privacy_classification = "RESTRICTED_PII"

        # Duplicate Content Hash (SHA-256 of Store + Normalized Text Lowercase)
        content_hash = hashlib.sha256(f"{store_id}:{normalized_text.lower()}".encode('utf-8')).hexdigest()

        # Duplicate Check
        cur.execute("""
            SELECT id, processing_status, created_at 
            FROM feedback_items 
            WHERE store_id = ? AND content_hash = ? AND organization_id = ?
            ORDER BY created_at ASC LIMIT 1;
        """, (store_id, content_hash, resolved_org_id))
        duplicate_row = cur.fetchone()

        is_duplicate = False
        duplicate_of_id = None

        if duplicate_row:
            is_duplicate = True
            duplicate_of_id = duplicate_row["id"]
            if not payload.allowDuplicates:
                raise DuplicateFeedbackError(
                    original_id=duplicate_of_id,
                    message=f"Duplicate feedback rejected: identical message already recorded as '{duplicate_of_id}'."
                )

        # ---------------------------------------------------------------------
        # STAGE 4: AI-DERIVED OPERATIONAL INTERPRETATION (PHASE 4 ENGINE)
        # ---------------------------------------------------------------------
        import time
        start_time = time.time()
        is_degraded = False
        processing_error = None

        try:
            ai_understanding = AIUnderstandingService.extract_understanding(
                raw_text,
                normalized_text=normalized_text,
                language_code=connector_data["languageCode"]
            )
        except Exception as ai_exc:
            logger.warning(f"AI understanding engine unavailable or failed: {ai_exc}. Engaging graceful degradation fallback.")
            is_degraded = True
            processing_error = f"AI processing degraded: {str(ai_exc)}"
            ai_understanding = {
                "language": {"code": connector_data["languageCode"] if connector_data["languageCode"] != "auto" else "en", "confidence": 0.0, "uncertainty": True, "evidence": None, "uncertaintyReason": "Degraded baseline"},
                "normalizedInterpretation": normalized_text,
                "category": {"value": "UNKNOWN_OPERATIONAL", "confidence": 0.0, "uncertainty": True, "evidence": None, "uncertaintyReason": processing_error},
                "intent": {"value": "GENERAL_FEEDBACK", "confidence": 0.0, "uncertainty": True, "evidence": None, "uncertaintyReason": processing_error},
                "sentiment": {"score": 0.0, "label": "NEUTRAL", "confidence": 0.0, "uncertainty": True, "evidence": None, "uncertaintyReason": "Degraded baseline"},
                "urgency": {"value": "NORMAL", "score": 0.4, "confidence": 0.0, "uncertainty": True, "evidence": None, "uncertaintyReason": "Degraded baseline"},
                "entities": [],
                "overallUncertainty": True,
                "summary": f"Feedback received: {normalized_text[:80]}",
                "degraded": True,
                "aiError": str(ai_exc)
            }

        if ai_understanding.get("normalizedInterpretation"):
            normalized_text = ai_understanding["normalizedInterpretation"]

        detected_language = ai_understanding["language"]["code"]
        detected_intent = ai_understanding["intent"]["value"]
        sentiment_score = ai_understanding["sentiment"]["score"]
        urgency_val = ai_understanding["urgency"]["value"]
        urgency_score = 0.95 if urgency_val == "IMMEDIATE" else (0.80 if urgency_val == "WITHIN_HOUR" else 0.40)
        is_ambiguous = ai_understanding["overallUncertainty"]

        now_iso = datetime.now(timezone.utc).isoformat()
        submitted_at = connector_data["submittedAt"] or now_iso

        ai_interpretation = {
            **ai_understanding,
            "detectedLanguage": detected_language,
            "detectedIntent": detected_intent,
            "sentimentScore": sentiment_score,
            "urgencyScore": urgency_score,
            "extractedEntities": [e["text"] for e in ai_understanding["entities"]],
            "isDuplicate": is_duplicate,
            "duplicateOfId": duplicate_of_id,
            "summary": ai_understanding["summary"] or f"{detected_intent.replace('_', ' ').title()} observation at {store_name}",
            "analyzedAt": now_iso
        }

        feedback_id = f"fb-{uuid.uuid4().hex[:12]}"
        processing_status = "degraded" if is_degraded else "analyzed"
        status = "NEW"

        # ---------------------------------------------------------------------
        # STAGE 5: PERSISTENCE & IMMUTABLE RAW STORAGE
        # ---------------------------------------------------------------------
        cur.execute("""
            INSERT INTO feedback_items (
                id, organization_id, region_id, store_id, department_id,
                source_type, channel_type, submitter_type, privacy_classification,
                processing_status, status, raw_text, language_code, normalized_text,
                content_hash, is_duplicate, duplicate_of_id, ai_interpretation,
                processing_error, sentiment_score, is_ambiguous, has_pii,
                metadata, submitted_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feedback_id,
            resolved_org_id,
            resolved_region_id,
            store_id,
            connector_data["departmentId"],
            connector_data["sourceType"],
            connector_data["channelType"],
            connector_data["submitterType"],
            privacy_classification,
            processing_status,
            status,
            raw_text, # NEVER MUTATED
            detected_language,
            normalized_text,
            content_hash,
            1 if is_duplicate else 0,
            duplicate_of_id,
            json.dumps(ai_interpretation),
            processing_error,
            sentiment_score,
            1 if is_ambiguous else 0,
            1 if has_pii else 0,
            json.dumps(connector_data["metadata"]) if connector_data["metadata"] else None,
            submitted_at,
            now_iso,
            now_iso
        ))

        # Audit Log
        actor_id = (operator_user.get("id") or operator_user.get("userId")) if operator_user else None
        AuditService.record_audit(
            conn=conn,
            organization_id=resolved_org_id,
            user_id=actor_id,
            entity_type="FEEDBACK_ITEM",
            entity_id=feedback_id,
            action="FEEDBACK_INGESTED",
            justification=f"Ingested via {connector_data['channelType']} ({detected_language}): intent={detected_intent}, dup={is_duplicate}"
        )

        # Enqueue background reprocessing job if degraded
        if is_degraded:
            try:
                from backend.app.services.job_service import JobService
                JobService.enqueue_job(
                    conn=conn,
                    job_type="FEEDBACK_REPROCESSING",
                    payload={"feedbackId": feedback_id, "storeId": store_id, "organizationId": resolved_org_id}
                )
            except Exception as j_err:
                logger.warning(f"Failed to enqueue background reprocessing job: {j_err}")

        # Record ingestion monitoring metrics
        try:
            from backend.app.services.ingestion_monitoring_service import IngestionMonitoringService
            duration_ms = round((time.time() - start_time) * 1000, 2)
            IngestionMonitoringService.record_ingestion(
                channel=connector_data["channelType"],
                success=True,
                latency_ms=duration_ms,
                is_duplicate=is_duplicate,
                is_degraded=is_degraded
            )
        except Exception:
            pass

        # Sync dynamic investigation questions (Phase 5)
        try:
            from backend.app.services.investigation_service import InvestigationService
            InvestigationService.sync_investigation_questions(conn, feedback_id)
        except Exception as e:
            logger.warning(f"Failed to sync investigation questions for {feedback_id}: {e}")

        conn.commit()

        return cls.get_feedback_by_id(conn, feedback_id)

    @classmethod
    def ingest_bulk(
        cls,
        conn: sqlite3.Connection,
        organization_id: Optional[str],
        items: List[FeedbackCreate],
        reject_duplicates: bool = False,
        operator_user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process batch of feedback items with transaction isolation and comprehensive error accounting."""
        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        duplicates_count = 0

        for index, item in enumerate(items):
            try:
                # Override allowDuplicates if batch specifies reject_duplicates
                if reject_duplicates:
                    item.allowDuplicates = False

                record = cls.ingest_feedback(conn, organization_id, item, operator_user)
                if record.get("isDuplicate"):
                    duplicates_count += 1
                results.append(record)
            except Exception as err:
                try:
                    from backend.app.services.ingestion_monitoring_service import IngestionMonitoringService
                    IngestionMonitoringService.record_ingestion(
                        channel=item.channelType or "BULK_IMPORT",
                        success=False,
                        error_message=str(err)
                    )
                except Exception:
                    pass
                errors.append({
                    "index": index,
                    "rawText": item.rawText[:60] if item.rawText else "",
                    "errorMessage": str(err)
                })

        return {
            "totalProcessed": len(items),
            "succeeded": len(results),
            "failed": len(errors),
            "duplicatesDetected": duplicates_count,
            "items": results,
            "errors": errors
        }

    @classmethod
    def ingest_bulk_csv(
        cls,
        conn: sqlite3.Connection,
        organization_id: Optional[str],
        csv_content: str,
        default_store_id: Optional[str] = None,
        operator_user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Parse and ingest feedback items from CSV payload."""
        f = io.StringIO(csv_content.strip())
        reader = csv.DictReader(f)
        
        items_to_create: List[FeedbackCreate] = []
        parse_errors: List[Dict[str, Any]] = []

        for row_idx, row in enumerate(reader):
            raw_text = (row.get("rawText") or row.get("text") or row.get("message") or "").strip()
            if not raw_text:
                parse_errors.append({"row": row_idx + 1, "errorMessage": "Empty feedback text"})
                continue

            store_id = row.get("storeId") or default_store_id
            channel_type = row.get("channelType") or row.get("sourceType") or "BULK_IMPORT"
            submitter_type = row.get("submitterType") or "ANONYMOUS"
            language_code = row.get("languageCode") or "auto"
            privacy_classification = row.get("privacyClassification") or "INTERNAL"

            items_to_create.append(FeedbackCreate(
                storeId=store_id,
                rawText=raw_text,
                channelType=channel_type,
                sourceType=channel_type,
                submitterType=submitter_type,
                languageCode=language_code,
                privacyClassification=privacy_classification
            ))

        bulk_result = cls.ingest_bulk(conn, organization_id, items_to_create, reject_duplicates=False, operator_user=operator_user)
        bulk_result["errors"].extend(parse_errors)
        bulk_result["totalProcessed"] += len(parse_errors)
        bulk_result["failed"] += len(parse_errors)
        return bulk_result

    @classmethod
    def update_processing_status(
        cls,
        conn: sqlite3.Connection,
        feedback_id: str,
        status_update: FeedbackStatusUpdate,
        operator_user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update processing status (e.g. advance to 'reviewed' or 'failed') and operational lifecycle status."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM feedback_items WHERE id = ?;", (feedback_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("FeedbackItem", feedback_id)

        updates = []
        params = []
        now = datetime.now(timezone.utc).isoformat()

        if status_update.processingStatus:
            updates.append("processing_status = ?")
            params.append(status_update.processingStatus)

        if status_update.status:
            updates.append("status = ?")
            params.append(status_update.status)

        if status_update.reviewNotes:
            # Append review notes to metadata
            meta = json.loads(row["metadata"]) if row["metadata"] else {}
            meta["reviewNotes"] = status_update.reviewNotes
            meta["reviewedBy"] = operator_user.get("email") if operator_user else "manager"
            meta["reviewedAt"] = now
            updates.append("metadata = ?")
            params.append(json.dumps(meta))

        updates.append("updated_at = ?")
        params.append(now)

        params.append(feedback_id)
        cur.execute(f"UPDATE feedback_items SET {', '.join(updates)} WHERE id = ?;", params)

        actor_id = operator_user.get("id") if operator_user else "system"
        AuditService.record_audit(
            conn=conn,
            organization_id=row["organization_id"],
            user_id=actor_id,
            entity_type="FEEDBACK_ITEM",
            entity_id=feedback_id,
            action="FEEDBACK_STATUS_UPDATED",
            justification=f"Processing status: {status_update.processingStatus or row['processing_status']}, lifecycle: {status_update.status or row['status']}"
        )

        conn.commit()
        return cls.get_feedback_by_id(conn, feedback_id)

    @classmethod
    def submit_human_review_and_overrides(
        cls,
        conn: sqlite3.Connection,
        feedback_id: str,
        review_request: FeedbackReviewRequest,
        operator_user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record authorized human review and field overrides.
        Does NOT overwrite raw input or AI-derived facts; stores corrections separately
        with reviewer provenance and audit trail.
        """
        cur = conn.cursor()
        cur.execute("SELECT * FROM feedback_items WHERE id = ?;", (feedback_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("FeedbackItem", feedback_id)

        now_iso = datetime.now(timezone.utc).isoformat()
        reviewer_email = operator_user.get("email") if operator_user else "manager@apex.com"
        reviewer_id = operator_user.get("id") if operator_user else "system-reviewer"

        existing_ov = json.loads(row["human_overrides"]) if ("human_overrides" in row.keys() and row["human_overrides"]) else {}
        overrides_map = existing_ov.get("overrides", {})

        if review_request.overrides:
            for field, val in review_request.overrides.items():
                if isinstance(val, dict):
                    overrides_map[field] = {
                        "value": val.get("value"),
                        "reason": val.get("reason", review_request.reviewNotes or "Operator verified"),
                        "correctedBy": reviewer_email,
                        "correctedAt": now_iso
                    }
                else:
                    overrides_map[field] = {
                        "value": val,
                        "reason": review_request.reviewNotes or "Operator verified correction",
                        "correctedBy": reviewer_email,
                        "correctedAt": now_iso
                    }

        updated_human_overrides = {
            "overrides": overrides_map,
            "reviewedBy": reviewer_email,
            "reviewedAt": now_iso,
            "reviewNotes": review_request.reviewNotes or existing_ov.get("reviewNotes")
        }

        new_processing_status = review_request.processingStatus or "reviewed"
        new_status = review_request.status or row["status"]

        cur.execute("""
            UPDATE feedback_items
            SET processing_status = ?,
                status = ?,
                human_overrides = ?,
                reviewed_by = ?,
                reviewed_at = ?,
                review_notes = ?,
                updated_at = ?
            WHERE id = ?;
        """, (
            new_processing_status,
            new_status,
            json.dumps(updated_human_overrides),
            reviewer_id,
            now_iso,
            review_request.reviewNotes or (row["review_notes"] if "review_notes" in row.keys() else None),
            now_iso,
            feedback_id
        ))

        # Audit Log
        AuditService.record_audit(
            conn=conn,
            organization_id=row["organization_id"],
            user_id=reviewer_id,
            entity_type="FEEDBACK_ITEM",
            entity_id=feedback_id,
            action="FEEDBACK_REVIEWED_AND_OVERRIDDEN",
            justification=f"Human review submitted: {len(overrides_map)} fields corrected. Status: {new_processing_status}"
        )

        conn.commit()
        return cls.get_feedback_by_id(conn, feedback_id)

    @classmethod
    def reanalyze_feedback(
        cls,
        conn: sqlite3.Connection,
        feedback_id: str,
        operator_user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Trigger fresh AI Understanding extraction on an existing feedback item."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM feedback_items WHERE id = ?;", (feedback_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("FeedbackItem", feedback_id)

        raw_text = row["raw_text"]
        normalized_text = row["normalized_text"] or raw_text
        lang_hint = row["language_code"]

        now_iso = datetime.now(timezone.utc).isoformat()
        ai_understanding = AIUnderstandingService.extract_understanding(
            raw_text,
            normalized_text=normalized_text,
            language_code=lang_hint
        )
        detected_language = ai_understanding["language"]["code"]
        sentiment_score = ai_understanding["sentiment"]["score"]
        urgency_val = ai_understanding["urgency"]["value"]
        urgency_score = 0.95 if urgency_val == "IMMEDIATE" else (0.80 if urgency_val == "WITHIN_HOUR" else 0.40)
        is_ambiguous = ai_understanding["overallUncertainty"]

        ai_interpretation = {
            **ai_understanding,
            "detectedLanguage": detected_language,
            "detectedIntent": ai_understanding["intent"]["value"],
            "sentimentScore": sentiment_score,
            "urgencyScore": urgency_score,
            "extractedEntities": [e["text"] for e in ai_understanding["entities"]],
            "isDuplicate": bool(row["is_duplicate"]),
            "duplicateOfId": row["duplicate_of_id"],
            "summary": ai_understanding["summary"],
            "analyzedAt": now_iso
        }

        cur.execute("""
            UPDATE feedback_items
            SET ai_interpretation = ?,
                sentiment_score = ?,
                is_ambiguous = ?,
                language_code = ?,
                processing_status = 'analyzed',
                updated_at = ?
            WHERE id = ?;
        """, (
            json.dumps(ai_interpretation),
            sentiment_score,
            1 if is_ambiguous else 0,
            detected_language,
            now_iso,
            feedback_id
        ))

        actor_id = operator_user.get("id") if operator_user else "system"
        AuditService.record_audit(
            conn=conn,
            organization_id=row["organization_id"],
            user_id=actor_id,
            entity_type="FEEDBACK_ITEM",
            entity_id=feedback_id,
            action="FEEDBACK_REANALYZED",
            justification=f"AI Understanding re-analyzed: language={detected_language}, confidence={ai_understanding['overallConfidence']}"
        )

        conn.commit()
        return cls.get_feedback_by_id(conn, feedback_id)

    @classmethod
    def get_feedback_understanding(
        cls,
        conn: sqlite3.Connection,
        feedback_id: str
    ) -> Dict[str, Any]:
        """Return structured breakdown separating deterministic system facts from AI facts and human overrides."""
        cur = conn.cursor()
        cur.execute("""
            SELECT f.*, s.name as store_name, r.name as region_name, d.name as department_name
            FROM feedback_items f
            LEFT JOIN stores s ON f.store_id = s.id
            LEFT JOIN regions r ON f.region_id = r.id
            LEFT JOIN departments d ON f.department_id = d.id
            WHERE f.id = ?;
        """, (feedback_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("FeedbackItem", feedback_id)

        item = cls._row_to_dict(row)

        system_facts = {
            "feedbackId": item["id"],
            "organizationId": item["organizationId"],
            "regionId": item["regionId"],
            "regionName": item["regionName"],
            "storeId": item["storeId"],
            "storeName": item["storeName"],
            "departmentId": item["departmentId"],
            "departmentName": item["departmentName"],
            "channelType": item["channelType"],
            "sourceType": item["sourceType"],
            "submitterType": item["submitterType"],
            "submittedAt": item["submittedAt"],
            "createdAt": item["createdAt"],
            "contentHash": item["contentHash"],
            "hasPii": item["hasPii"],
            "privacyClassification": item["privacyClassification"],
            "isDuplicate": item["isDuplicate"],
            "duplicateOfId": item["duplicateOfId"]
        }

        ai_derived_facts = item["aiInterpretation"] or {}
        human_overrides = item["humanOverrides"]
        effective_interpretation = item["effectiveInterpretation"] or AIUnderstandingService.merge_with_human_overrides(ai_derived_facts, human_overrides)

        return {
            "feedbackId": item["id"],
            "systemFacts": system_facts,
            "aiDerivedFacts": ai_derived_facts,
            "humanOverrides": human_overrides,
            "effectiveInterpretation": effective_interpretation,
            "processingStatus": item["processingStatus"],
            "status": item["status"]
        }

    @classmethod
    def get_feedback(
        cls,
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        region_id: Optional[str] = None,
        department_id: Optional[str] = None,
        channel_type: Optional[str] = None,
        processing_status: Optional[str] = None,
        submitter_type: Optional[str] = None,
        language_code: Optional[str] = None,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """Query feedback records with multi-dimensional filtering, search, and pagination."""
        conditions = ["f.organization_id = ?"]
        params: List[Any] = [organization_id]

        if store_id:
            conditions.append("f.store_id = ?")
            params.append(store_id)
        if region_id:
            conditions.append("f.region_id = ?")
            params.append(region_id)
        if department_id:
            conditions.append("f.department_id = ?")
            params.append(department_id)
        if channel_type:
            conditions.append("(UPPER(f.channel_type) = UPPER(?) OR UPPER(f.source_type) = UPPER(?))")
            params.extend([channel_type, channel_type])
        if processing_status:
            conditions.append("f.processing_status = ?")
            params.append(processing_status)
        if submitter_type:
            conditions.append("f.submitter_type = ?")
            params.append(submitter_type)
        if language_code:
            conditions.append("f.language_code = ?")
            params.append(language_code)
        if q:
            conditions.append("(f.raw_text LIKE ? OR f.normalized_text LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])

        where_clause = " WHERE " + " AND ".join(conditions)

        cur = conn.cursor()
        count_sql = f"SELECT COUNT(*) FROM feedback_items f {where_clause};"
        cur.execute(count_sql, params)
        total_items = cur.fetchone()[0]

        offset = (page - 1) * page_size
        query_sql = f"""
            SELECT f.*, s.name as store_name, r.name as region_name, d.name as department_name
            FROM feedback_items f
            LEFT JOIN stores s ON f.store_id = s.id
            LEFT JOIN regions r ON f.region_id = r.id
            LEFT JOIN departments d ON f.department_id = d.id
            {where_clause}
            ORDER BY f.created_at DESC
            LIMIT ? OFFSET ?;
        """
        params.extend([page_size, offset])
        cur.execute(query_sql, params)
        rows = cur.fetchall()

        items = [cls._row_to_dict(r) for r in rows]
        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1

        return {
            "items": items,
            "meta": {
                "page": page,
                "pageSize": page_size,
                "totalItems": total_items,
                "totalPages": total_pages
            }
        }

    @classmethod
    def get_feedback_by_id(cls, conn: sqlite3.Connection, feedback_id: str) -> Dict[str, Any]:
        """Fetch single feedback record by identifier."""
        cur = conn.cursor()
        cur.execute("""
            SELECT f.*, s.name as store_name, r.name as region_name, d.name as department_name
            FROM feedback_items f
            LEFT JOIN stores s ON f.store_id = s.id
            LEFT JOIN regions r ON f.region_id = r.id
            LEFT JOIN departments d ON f.department_id = d.id
            WHERE f.id = ?;
        """, (feedback_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("FeedbackItem", feedback_id)
        return cls._row_to_dict(row)

    @classmethod
    def record_follow_up(
        cls,
        conn: sqlite3.Connection,
        payload: FollowUpCreate
    ) -> Dict[str, Any]:
        """Log clarification dialog turns for ambiguous feedback."""
        cur = conn.cursor()
        cur.execute("SELECT id FROM feedback_items WHERE id = ?;", (payload.feedbackItemId,))
        if not cur.fetchone():
            raise NotFoundError("FeedbackItem", payload.feedbackItemId)

        follow_up_id = f"fu-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            INSERT INTO follow_up_exchanges (id, feedback_item_id, turn_index, question, response, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (follow_up_id, payload.feedbackItemId, payload.turnIndex, payload.question, payload.response, now))

        # Clear ambiguous flag if answered
        if payload.response:
            cur.execute("UPDATE feedback_items SET is_ambiguous = 0, updated_at = ? WHERE id = ?;", (now, payload.feedbackItemId))

        conn.commit()

        return {
            "id": follow_up_id,
            "feedbackItemId": payload.feedbackItemId,
            "turnIndex": payload.turnIndex,
            "question": payload.question,
            "response": payload.response,
            "createdAt": now
        }

    # -------------------------------------------------------------------------
    # INTERNAL HEURISTIC PIPELINE HOOKS
    # -------------------------------------------------------------------------
    @staticmethod
    def _detect_language(text: str, user_hint: Optional[str]) -> str:
        if user_hint and user_hint.lower() not in ("auto", "unknown", ""):
            return user_hint.lower()

        # Check unicode script ranges
        if re.search(r'[\u0900-\u097F]', text):
            return "hi" # Hindi / Devanagari
        if re.search(r'[\u4E00-\u9FFF]', text):
            return "zh" # Chinese

        tokens = set(re.findall(r'[a-zA-Záéíóúñüçàèùâêîôûäöß]+', text.lower()))
        scores = {
            "es": len(tokens & SPANISH_KEYWORDS),
            "fr": len(tokens & FRENCH_KEYWORDS),
            "de": len(tokens & GERMAN_KEYWORDS)
        }
        best_lang, best_score = max(scores.items(), key=lambda item: item[1])
        if best_score > 0:
            return best_lang

        return "en"

    @staticmethod
    def _classify_intent_and_entities(text: str) -> Tuple[str, List[str]]:
        lower = text.lower()
        entities = []

        # Extract Aisle / Department / Equipment / Lane references
        aisle_m = re.findall(r'\b(?:aisle|pasillo|rayon)\s*([0-9a-zA-Z_-]+)\b', lower)
        for a in aisle_m:
            entities.append(f"Aisle {a.upper()}")

        lane_m = re.findall(r'\b(?:lane|caja|caisse)\s*([0-9]+)\b', lower)
        for lane_num in lane_m:
            entities.append(f"Lane #{lane_num}")

        cooler_m = re.findall(r'\b(?:cooler|freezer|chiller|congelador)\s*([0-9a-zA-Z_-]+)?\b', lower)
        for c in cooler_m:
            if c:
                entities.append(f"Cooler {c.upper()}")

        temp_m = re.findall(r'\b(\d{2,3})\s*(?:f|c|degrees|graden|grados)\b', lower)
        for t in temp_m:
            entities.append(f"Temp {t}°")

        # Classify Intent
        if any(w in lower for w in ['cooler', 'freezer', 'refrigerat', 'condens', 'congelador', 'tibio', 'warm', '48f', 'cold chain']):
            intent = "COLD_CHAIN_REFRIGERATION"
        elif any(w in lower for w in ['puddle', 'leak', 'water', 'slip', 'charco', 'fuga', 'goteando', 'wet floor', 'hazard']):
            intent = "SLIP_FALL_SAFETY"
        elif any(w in lower for w in ['scanner', 'barcode', 'lane', 'register', 'pos', 'checkout', 'freeze', 'caja']):
            intent = "POS_CHECKOUT_SYSTEMS"
        elif any(w in lower for w in ['spoiled', 'expired', 'mold', 'rotten', 'smell', 'caducado', 'odor']):
            intent = "FOOD_SAFETY_QUALITY"
        elif any(w in lower for w in ['dirty', 'restroom', 'cleaning', 'trash', 'limpieza', 'spill']):
            intent = "FACILITIES_SANITATION"
        elif any(w in lower for w in ['empty', 'out of stock', 'missing', 'restock', 'shelf']):
            intent = "INVENTORY_AVAILABILITY"
        else:
            intent = "GENERAL_STORE_OPERATIONS"

        return intent, entities

    @staticmethod
    def _calculate_sentiment(text: str) -> float:
        lower = text.lower()
        neg_count = sum(1 for term in NEGATIVE_SENTIMENT_TERMS if term in lower)
        pos_count = sum(1 for term in POSITIVE_SENTIMENT_TERMS if term in lower)
        crit_count = sum(1 for term in CRITICAL_HAZARD_TERMS if term in lower)

        if crit_count > 0:
            return round(-0.70 - min(0.25, (crit_count + neg_count) * 0.05), 2)
        if neg_count > pos_count:
            return round(max(-0.95, -0.40 - (neg_count * 0.15)), 2)
        if pos_count > neg_count:
            return round(min(0.95, 0.40 + (pos_count * 0.15)), 2)
        return 0.0

    @staticmethod
    def _calculate_urgency(text: str) -> float:
        lower = text.lower()
        if any(term in lower for term in ['fire', 'smoke', 'shock', 'spark', 'injury', 'blood', 'severely', 'flood']):
            return 0.98
        if any(term in lower for term in ['puddle', 'leak', '48f', 'slip', 'goteando', 'charco', 'warm', 'spoiled']):
            return 0.88
        if any(term in lower for term in ['scanner', 'freezing', 'freeze', 'broken', 'offline', 'out of stock']):
            return 0.55
        return 0.25

    @classmethod
    def _row_to_dict(cls, r: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite database row into standard API dictionary with Phase 4 extensions."""
        keys = r.keys()
        ai_data = json.loads(r["ai_interpretation"]) if ("ai_interpretation" in keys and r["ai_interpretation"]) else None
        human_ov = json.loads(r["human_overrides"]) if ("human_overrides" in keys and r["human_overrides"]) else None
        effective_data = AIUnderstandingService.merge_with_human_overrides(ai_data, human_ov) if ai_data else None

        return {
            "id": r["id"],
            "organizationId": r["organization_id"],
            "regionId": r["region_id"] if "region_id" in keys else None,
            "regionName": r["region_name"] if "region_name" in keys else None,
            "storeId": r["store_id"],
            "storeName": r["store_name"] if "store_name" in keys else None,
            "departmentId": r["department_id"],
            "departmentName": r["department_name"] if "department_name" in keys else None,
            "sourceType": r["source_type"],
            "channelType": r["channel_type"] if "channel_type" in keys else r["source_type"],
            "submitterType": r["submitter_type"] if "submitter_type" in keys else "CUSTOMER",
            "privacyClassification": r["privacy_classification"] if "privacy_classification" in keys else "INTERNAL",
            "processingStatus": r["processing_status"] if "processing_status" in keys else "analyzed",
            "status": r["status"] if "status" in keys else "NEW",
            "rawText": r["raw_text"],
            "languageCode": r["language_code"],
            "normalizedText": r["normalized_text"],
            "contentHash": r["content_hash"] if "content_hash" in keys else None,
            "isDuplicate": bool(r["is_duplicate"]) if "is_duplicate" in keys else False,
            "duplicateOfId": r["duplicate_of_id"] if "duplicate_of_id" in keys else None,
            "aiInterpretation": ai_data,
            "humanOverrides": human_ov,
            "effectiveInterpretation": effective_data,
            "reviewedBy": human_ov.get("reviewedBy") if (human_ov and human_ov.get("reviewedBy")) else (r["reviewed_by"] if "reviewed_by" in keys else None),
            "reviewedAt": r["reviewed_at"] if "reviewed_at" in keys else None,
            "reviewNotes": r["review_notes"] if "review_notes" in keys else None,
            "processingError": r["processing_error"] if "processing_error" in keys else None,
            "sentimentScore": r["sentiment_score"],
            "isAmbiguous": bool(r["is_ambiguous"]),
            "hasPii": bool(r["has_pii"]),
            "metadata": json.loads(r["metadata"]) if r["metadata"] else None,
            "investigationStatus": r["investigation_status"] if "investigation_status" in keys else "NOT_NEEDED",
            "enrichedText": r["enriched_text"] if "enriched_text" in keys else None,
            "submittedAt": r["submitted_at"] if "submitted_at" in keys and r["submitted_at"] else r["created_at"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"],
            # Phase 15 Multilingual Intelligence Hardening Fields
            "detectedLanguageInfo": (
                (ai_data.get("multilingualAnalysis", {}).get("detectedLanguage") if (ai_data and isinstance(ai_data.get("multilingualAnalysis"), dict)) else None) or
                (ai_data.get("detectedLanguage") if (ai_data and isinstance(ai_data.get("detectedLanguage"), dict)) else None) or
                (ai_data.get("language") if (ai_data and isinstance(ai_data.get("language"), dict)) else None) or
                {"code": r["language_code"] or "en", "name": r["language_code"] or "English", "script": "Latin"}
            ),
            "normalizedInterpretation": (ai_data.get("normalizedInterpretation") if ai_data else None) or r["normalized_text"],
            "extractedIssue": ai_data.get("extractedIssue") if ai_data else None,
            "multilingualConfidence": (ai_data.get("confidence") if ai_data else None) or (ai_data.get("multilingualAnalysis", {}).get("confidence") if ai_data else None),
            "spellingCorrections": ai_data.get("multilingualAnalysis", {}).get("spellingCorrections") if ai_data else None
        }
