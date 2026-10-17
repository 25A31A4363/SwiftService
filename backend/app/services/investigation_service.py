import uuid
import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.app.core.errors import NotFoundError
from backend.app.services.ai_understanding_service import AIUnderstandingService
from backend.app.services.audit_service import AuditService

CATEGORY_QUESTION_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "FACILITIES_MAINTENANCE": [
        {
            "key": "clarify_capacity",
            "field": "operationalImpact",
            "text": "Is cooling or equipment function completely unavailable or operating with reduced capacity?",
            "type": "choice",
            "options": ["Completely unavailable / offline", "Running with reduced capacity / warm", "Intermittent operation", "Unsure"],
            "reason": "Clarifies operational impact extent and refrigeration/cooling urgency."
        },
        {
            "key": "clarify_scope",
            "field": "location",
            "text": "Is the issue affecting one department or the entire store?",
            "type": "choice",
            "options": ["Single department/aisle", "Produce/Perishables area", "Entire store / sales floor", "Backroom / warehouse"],
            "reason": "Missing physical scope prevents routing technicians to the right zone."
        },
        {
            "key": "clarify_temporal",
            "field": "temporalInfo",
            "text": "When did the problem begin or when was it first noticed?",
            "type": "choice",
            "options": ["Just started (< 1 hour)", "Within last 2-4 hours", "Since earlier today", "Multiple days", "Unknown"],
            "reason": "Onset timeline is critical for determining temperature degradation and inventory spoilage risk."
        },
        {
            "key": "clarify_population",
            "field": "customerImpact",
            "text": "Are customers or employees actively affected by this issue?",
            "type": "choice",
            "options": ["Customers actively complaining", "Staff working conditions degraded", "Both customers and staff affected", "No immediate human impact"],
            "reason": "Assesses human impact and store comfort thresholds."
        },
        {
            "key": "clarify_safety_concern",
            "field": "safetyRelevance",
            "text": "Is there any safety concern (such as water leaks from condensation, burning smell, or electrical sparks)?",
            "type": "choice",
            "options": ["Water leaking / slip hazard", "Burning odor / electrical sparks", "Excessive noise / vibration", "No safety concern observed"],
            "reason": "Safety relevance check ensures emergency power shutoff or cordoning if hazardous."
        }
    ],
    "CHECKOUT_POS": [
        {
            "key": "clarify_pos_scope",
            "field": "operationalImpact",
            "text": "Is the checkout terminal completely frozen, rejecting payment cards, or barcode scanner failure?",
            "type": "choice",
            "options": ["Terminal screen frozen", "Card reader / NFC rejecting payments", "Barcode scanner not reading", "Receipt printer jam"],
            "reason": "Differentiates hardware, software, or payment gateway failures for IT routing."
        },
        {
            "key": "clarify_pos_location",
            "field": "location",
            "text": "Which lane, self-pay kiosk, or register number is experiencing the fault?",
            "type": "text",
            "options": None,
            "reason": "Directs frontline IT engineer to the specific physical terminal."
        },
        {
            "key": "clarify_pos_temporal",
            "field": "temporalInfo",
            "text": "When did the checkout terminal begin failing?",
            "type": "choice",
            "options": ["Just occurred (< 15 mins)", "Last hour", "Intermittent all day"],
            "reason": "Determines checkout throughput impact and queue buildup."
        }
    ],
    "EQUIPMENT_FAILURE": [
        {
            "key": "clarify_scope",
            "field": "operationalImpact",
            "text": "Is the equipment completely offline or operating with reduced capacity?",
            "type": "choice",
            "options": ["Completely offline / broken", "Running with reduced capacity", "Intermittent failure", "Unsure"],
            "reason": "Clarifies operational impact scope and dispatch priority."
        },
        {
            "key": "clarify_location",
            "field": "location",
            "text": "Which aisle, zone, or department is the affected equipment located in?",
            "type": "text",
            "options": None,
            "reason": "Missing physical location prevents routing technician to the correct zone."
        },
        {
            "key": "clarify_temporal",
            "field": "temporalInfo",
            "text": "When did this equipment failure begin or when was it first noticed?",
            "type": "choice",
            "options": ["Just started (< 1 hour)", "Within last 2-4 hours", "Since earlier today", "Multiple days", "Unknown"],
            "reason": "Onset timeline is critical for determining failure progression and inventory spoilage risk."
        }
    ],
    "SAFETY_HAZARD": [
        {
            "key": "clarify_safety_risk",
            "field": "safetyRelevance",
            "text": "Is there an immediate physical safety hazard to customers or employees (e.g. slip risk, exposed electrical wires, fumes)?",
            "type": "choice",
            "options": ["Immediate customer slip/fall risk", "Staff safety hazard", "Potential risk if left unattended", "No direct safety hazard"],
            "reason": "High priority: Safety relevance uncertainty requires immediate verification for SLA escalation."
        },
        {
            "key": "clarify_location",
            "field": "location",
            "text": "Where is the safety hazard located (specific aisle, entrance, or restroom)?",
            "type": "text",
            "options": None,
            "reason": "Precise hazard coordinates required to cordon off the area."
        }
    ],
    "INVENTORY_STOCK": [
        {
            "key": "clarify_affected_item",
            "field": "affectedEntity",
            "text": "Which specific product, SKU, or display section is out of stock or affected?",
            "type": "text",
            "options": None,
            "reason": "Inventory restocking requires specific item or shelf identification."
        },
        {
            "key": "clarify_scope",
            "field": "operationalImpact",
            "text": "Is the entire display empty or just specific variants?",
            "type": "choice",
            "options": ["Entire shelf/display empty", "Specific flavor/size missing", "Damaged goods on display"],
            "reason": "Clarifies whether warehouse replenishment or vendor reorder is needed."
        }
    ],
    "OPERATIONAL_HYGIENE": [
        {
            "key": "clarify_location",
            "field": "location",
            "text": "What specific area of the store requires sanitation or maintenance (e.g., restroom, checkout, entrance)?",
            "type": "text",
            "options": None,
            "reason": "Custodial dispatch requires explicit zone targeting."
        },
        {
            "key": "clarify_safety_risk",
            "field": "safetyRelevance",
            "text": "Does this cleanliness issue involve a liquid spill or biological contamination requiring hazard protocols?",
            "type": "choice",
            "options": ["Liquid spill / slip hazard", "Trash overflow / debris", "Restroom maintenance", "Biological hazard"],
            "reason": "Identifies if safety containment PPE is required before dispatch."
        }
    ],
    "CLEANLINESS_FACILITY": [
        {
            "key": "clarify_location",
            "field": "location",
            "text": "What specific area of the store requires sanitation or maintenance (e.g., restroom, checkout, entrance)?",
            "type": "text",
            "options": None,
            "reason": "Custodial dispatch requires explicit zone targeting."
        },
        {
            "key": "clarify_safety_risk",
            "field": "safetyRelevance",
            "text": "Does this cleanliness issue involve a liquid spill or biological contamination requiring hazard protocols?",
            "type": "choice",
            "options": ["Liquid spill / slip hazard", "Trash overflow / debris", "Restroom maintenance", "Biological hazard"],
            "reason": "Identifies if safety containment PPE is required before dispatch."
        }
    ],
    "CUSTOMER_SERVICE": [
        {
            "key": "clarify_staff_interaction",
            "field": "affectedEntity",
            "text": "Which department or service desk did this customer service interaction occur at?",
            "type": "text",
            "options": None,
            "reason": "Routes feedback to department leadership for coaching or follow-up."
        },
        {
            "key": "clarify_customer_impact",
            "field": "customerImpact",
            "text": "Did the customer leave without completing their purchase or request escalation to a manager?",
            "type": "choice",
            "options": ["Walked out without purchase", "Spoke with manager on duty", "Customer completed purchase with dissatisfaction", "Other"],
            "reason": "Assesses revenue risk and customer retention severity."
        }
    ]
}

# Generic fallback questions for unknown categories or broad missing context
GENERIC_QUESTIONS: List[Dict[str, Any]] = [
    {
        "key": "clarify_location",
        "field": "location",
        "text": "Where in the facility or store is this issue occurring?",
        "type": "text",
        "options": None,
        "reason": "Location is unspecified in feedback text."
    },
    {
        "key": "clarify_severity",
        "field": "severity",
        "text": "How severe is the disruption to normal store operations?",
        "type": "choice",
        "options": ["Critical - Operations halted / Emergency", "High - Significant customer impact", "Medium - Workaround possible", "Low - Minor inconvenience"],
        "reason": "Severity score is uncertain or unstated in feedback."
    },
    {
        "key": "clarify_safety",
        "field": "safetyRelevance",
        "text": "Is there any safety hazard, injury risk, or environmental spill involved?",
        "type": "choice",
        "options": ["Yes - active safety risk", "No safety risk", "Unsure"],
        "reason": "Safety relevance is uncertain."
    }
]

class InvestigationService:
    @staticmethod
    def detect_missing_information(interpretation: Dict[str, Any]) -> List[str]:
        """Detect which critical operational fields lack sufficient grounded evidence or are unknown."""
        missing = []
        if not interpretation:
            return ["category", "location", "affectedEntity", "severity", "urgency"]

        # Check location
        loc = interpretation.get("location", {})
        if loc.get("value") in [None, "unknown", ""] or loc.get("uncertainty") is True:
            missing.append("location")

        # Check affected entity
        ent = interpretation.get("affectedEntity", {})
        if ent.get("value") in [None, "unknown", ""] or ent.get("uncertainty") is True:
            missing.append("affectedEntity")

        # Check temporal onset
        temp = interpretation.get("temporalInfo") or interpretation.get("temporalInformation", {})
        if temp.get("value") in [None, "unknown", ""] or temp.get("uncertainty") is True:
            # Only flag temporalInfo if category requires timeline clarification
            if interpretation.get("issueCategory", {}).get("value") in ["FACILITIES_MAINTENANCE", "EQUIPMENT_FAILURE"]:
                missing.append("temporalInfo")

        # Check safety relevance uncertainty
        safety = interpretation.get("safetyRelevance", {})
        if safety.get("uncertainty") is True or safety.get("confidence", 0.0) < 0.65:
            missing.append("safetyRelevance")

        # Check severity / operational impact uncertainty
        sev = interpretation.get("severity", {})
        if sev.get("value") in [None, "unknown", ""] or sev.get("confidence", 0.0) < 0.60:
            missing.append("severity")

        op_impact = interpretation.get("operationalImpact", {})
        if op_impact.get("value") in [None, "unknown", ""] or op_impact.get("uncertainty") is True:
            missing.append("operationalImpact")

        return missing

    @staticmethod
    def evaluate_investigation_need(
        interpretation: Dict[str, Any]
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Evaluate if dynamic follow-up questions are needed.
        Returns: (investigation_status, list_of_targeted_questions)
        Stops asking questions if sufficient information already exists.
        """
        if not interpretation:
            return "IN_PROGRESS", GENERIC_QUESTIONS[:2]

        missing_fields = InvestigationService.detect_missing_information(interpretation)
        category = interpretation.get("issueCategory", {}).get("value", "unknown")

        # If core actionable fields (location and affectedEntity) are both present, context is SUFFICIENT
        actionable_missing = [f for f in missing_fields if f in ["location", "affectedEntity"]]
        overall_conf = interpretation.get("overallConfidence", 0.0)
        if len(actionable_missing) == 0 or (len(missing_fields) <= 1 and overall_conf >= 0.75):
            return "SUFFICIENT", []

        # Candidate questions based on category
        templates = CATEGORY_QUESTION_TEMPLATES.get(category, GENERIC_QUESTIONS)
        targeted = []

        for q in templates:
            target_field = q.get("field")
            if target_field in missing_fields:
                targeted.append(q)

        # Supplement with generic questions if needed, but keep minimal (capped at max 3 questions)
        if len(targeted) < 2:
            for g in GENERIC_QUESTIONS:
                if g.get("field") in missing_fields and not any(t["key"] == g["key"] for t in targeted):
                    targeted.append(g)

        # Limit to max 3 prioritized questions
        prioritized = targeted[:3]
        if not prioritized:
            return "SUFFICIENT", []

        return "IN_PROGRESS", prioritized

    @staticmethod
    def sync_investigation_questions(
        conn: sqlite3.Connection,
        feedback_id: str
    ) -> Dict[str, Any]:
        """
        Evaluate feedback item and create dynamic investigation questions if needed.
        Preserves existing answered or dismissed questions.
        """
        cur = conn.cursor()
        cur.execute("SELECT * FROM feedback_items WHERE id = ?;", (feedback_id,))
        fb = cur.fetchone()
        if not fb:
            raise NotFoundError("FeedbackItem", feedback_id)

        # Parse interpretation
        interp = {}
        if fb["ai_interpretation"]:
            try:
                interp = json.loads(fb["ai_interpretation"])
            except Exception:
                interp = {}

        # If human overrides exist, overlay them
        overrides = {}
        if fb["human_overrides"]:
            try:
                overrides = json.loads(fb["human_overrides"])
                interp = AIUnderstandingService.merge_with_human_overrides(interp, overrides)
            except Exception:
                pass

        inv_status, questions_to_ask = InvestigationService.evaluate_investigation_need(interp)

        now = datetime.now(timezone.utc).isoformat()

        # Check existing questions
        cur.execute("SELECT * FROM investigation_questions WHERE feedback_item_id = ?;", (feedback_id,))
        existing_rows = cur.fetchall()
        existing_keys = {r["question_key"]: r for r in existing_rows}

        # If any existing questions are answered, check if that already satisfies missing context
        _answered_count = sum(1 for r in existing_rows if r["status"] == "ANSWERED")

        # Insert new questions that don't already exist
        priority_rank = 1
        for q in questions_to_ask:
            q_key = q["key"]
            if q_key not in existing_keys:
                q_id = f"invq-{uuid.uuid4().hex[:10]}"
                options_json = json.dumps(q.get("options")) if q.get("options") else None
                cur.execute("""
                    INSERT INTO investigation_questions (
                        id, feedback_item_id, question_key, question_text,
                        question_type, options, reason, priority, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?);
                """, (
                    q_id, feedback_id, q_key, q["text"],
                    q.get("type", "text"), options_json, q["reason"],
                    priority_rank, now, now
                ))
            priority_rank += 1

        # Update feedback_items investigation status
        cur.execute("""
            UPDATE feedback_items
            SET investigation_status = ?, updated_at = ?
            WHERE id = ?;
        """, (inv_status, now, feedback_id))

        return InvestigationService.get_investigation_summary(conn, feedback_id)

    @staticmethod
    def get_investigation_summary(
        conn: sqlite3.Connection,
        feedback_id: str
    ) -> Dict[str, Any]:
        """Fetch all questions, missing fields, and enrichment status for a feedback item."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM feedback_items WHERE id = ?;", (feedback_id,))
        fb = cur.fetchone()
        if not fb:
            raise NotFoundError("FeedbackItem", feedback_id)

        interp = {}
        if fb["ai_interpretation"]:
            try:
                interp = json.loads(fb["ai_interpretation"])
            except Exception:
                interp = {}

        missing_fields = InvestigationService.detect_missing_information(interp)

        cur.execute("""
            SELECT * FROM investigation_questions
            WHERE feedback_item_id = ?
            ORDER BY priority ASC, created_at ASC;
        """, (feedback_id,))
        rows = cur.fetchall()

        questions = []
        for r in rows:
            opts = None
            if r["options"]:
                try:
                    opts = json.loads(r["options"])
                except Exception:
                    opts = None
            questions.append({
                "id": r["id"],
                "feedbackItemId": r["feedback_item_id"],
                "questionKey": r["question_key"],
                "questionText": r["question_text"],
                "questionType": r["question_type"],
                "options": opts,
                "reason": r["reason"],
                "priority": r["priority"],
                "status": r["status"],
                "answer": r["answer"],
                "answeredBy": r["answered_by"],
                "answeredAt": r["answered_at"],
                "createdAt": r["created_at"],
                "updatedAt": r["updated_at"]
            })

        return {
            "feedbackItemId": feedback_id,
            "investigationStatus": fb["investigation_status"] or "NOT_NEEDED",
            "missingFields": missing_fields,
            "questions": questions,
            "hasEnrichedText": bool(fb["enriched_text"]),
            "enrichedText": fb["enriched_text"]
        }

    @staticmethod
    def record_answer(
        conn: sqlite3.Connection,
        question_id: str,
        answer: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit a response to an investigation question and automatically enrich and re-analyze."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM investigation_questions WHERE id = ?;", (question_id,))
        q = cur.fetchone()
        if not q:
            raise NotFoundError("InvestigationQuestion", question_id)

        feedback_id = q["feedback_item_id"]
        now = datetime.now(timezone.utc).isoformat()

        cur.execute("""
            UPDATE investigation_questions
            SET answer = ?, status = 'ANSWERED', answered_by = ?, answered_at = ?, updated_at = ?
            WHERE id = ?;
        """, (answer, user_id, now, now, question_id))

        # Check feedback organization for audit
        cur.execute("SELECT organization_id FROM feedback_items WHERE id = ?;", (feedback_id,))
        fb_row = cur.fetchone()
        org_id = fb_row["organization_id"] if fb_row else "default"

        AuditService.record_audit(
            conn=conn,
            organization_id=org_id,
            user_id=user_id,
            entity_type="INVESTIGATION_QUESTION",
            entity_id=question_id,
            action="ANSWER_RECORDED",
            new_state={"questionKey": q["question_key"], "answer": answer}
        )

        # Trigger enrichment and re-analysis
        InvestigationService.enrich_and_reanalyze(conn, feedback_id, user_id)

        return InvestigationService.get_investigation_summary(conn, feedback_id)

    @staticmethod
    def add_custom_question(
        conn: sqlite3.Connection,
        feedback_id: str,
        question_text: str,
        reason: str = "Operator requested additional operational details",
        question_type: str = "text",
        options: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Operator manually adds a targeted question to the investigation session."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM feedback_items WHERE id = ?;", (feedback_id,))
        fb = cur.fetchone()
        if not fb:
            raise NotFoundError("FeedbackItem", feedback_id)

        q_id = f"invq-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()
        options_json = json.dumps(options) if options else None

        cur.execute("""
            INSERT INTO investigation_questions (
                id, feedback_item_id, question_key, question_text,
                question_type, options, reason, priority, status,
                created_at, updated_at
            ) VALUES (?, ?, 'custom_operator_question', ?, ?, ?, ?, 1, 'PENDING', ?, ?);
        """, (
            q_id, feedback_id, question_text, question_type,
            options_json, reason, now, now
        ))

        cur.execute("""
            UPDATE feedback_items
            SET investigation_status = 'IN_PROGRESS', updated_at = ?
            WHERE id = ?;
        """, (now, feedback_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=fb["organization_id"],
            user_id=user_id,
            entity_type="INVESTIGATION_QUESTION",
            entity_id=q_id,
            action="CUSTOM_QUESTION_ADDED",
            new_state={"questionText": question_text, "reason": reason}
        )

        return InvestigationService.get_investigation_summary(conn, feedback_id)

    @staticmethod
    def dismiss_question(
        conn: sqlite3.Connection,
        question_id: str,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dismiss an unnecessary or irrelevant question."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM investigation_questions WHERE id = ?;", (question_id,))
        q = cur.fetchone()
        if not q:
            raise NotFoundError("InvestigationQuestion", question_id)

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            UPDATE investigation_questions
            SET status = 'DISMISSED', updated_at = ?
            WHERE id = ?;
        """, (now, question_id))

        # Check if any pending questions remain
        feedback_id = q["feedback_item_id"]
        cur.execute("""
            SELECT COUNT(*) as pending_count FROM investigation_questions
            WHERE feedback_item_id = ? AND status = 'PENDING';
        """, (feedback_id,))
        pending = cur.fetchone()["pending_count"]

        if pending == 0:
            cur.execute("""
                UPDATE feedback_items
                SET investigation_status = 'SUFFICIENT', updated_at = ?
                WHERE id = ?;
            """, (now, feedback_id))

        return InvestigationService.get_investigation_summary(conn, feedback_id)

    @staticmethod
    def enrich_and_reanalyze(
        conn: sqlite3.Connection,
        feedback_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assemble raw text + answered clarification Q&A into an enriched canonical representation,
        re-run grounded AI understanding, and update feedback_items.
        """
        cur = conn.cursor()
        cur.execute("SELECT * FROM feedback_items WHERE id = ?;", (feedback_id,))
        fb = cur.fetchone()
        if not fb:
            raise NotFoundError("FeedbackItem", feedback_id)

        # Get all answered questions
        cur.execute("""
            SELECT question_text, answer FROM investigation_questions
            WHERE feedback_item_id = ? AND status = 'ANSWERED' AND answer IS NOT NULL
            ORDER BY priority ASC, updated_at ASC;
        """, (feedback_id,))
        qa_pairs = cur.fetchall()

        raw_text = fb["raw_text"]
        if qa_pairs:
            qa_str = " ".join([f"[Clarification] Q: {p['question_text']} A: {p['answer']}." for p in qa_pairs])
            enriched_text = f"{raw_text} {qa_str}"
        else:
            enriched_text = raw_text

        # Re-run AI understanding on enriched text
        new_interp = AIUnderstandingService.extract_understanding(enriched_text, fb["language_code"] or "en")

        # Preserve human overrides if any
        overrides = {}
        if fb["human_overrides"]:
            try:
                overrides = json.loads(fb["human_overrides"])
            except Exception:
                overrides = {}

        effective = AIUnderstandingService.merge_with_human_overrides(new_interp, overrides)

        # Evaluate if remaining context is now sufficient
        missing = InvestigationService.detect_missing_information(effective)
        new_inv_status = "SUFFICIENT" if len(missing) == 0 or effective.get("overallConfidence", 0.0) >= 0.85 else "IN_PROGRESS"

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            UPDATE feedback_items
            SET enriched_text = ?,
                ai_interpretation = ?,
                investigation_status = ?,
                updated_at = ?
            WHERE id = ?;
        """, (
            enriched_text,
            json.dumps(new_interp),
            new_inv_status,
            now,
            feedback_id
        ))

        AuditService.record_audit(
            conn=conn,
            organization_id=fb["organization_id"],
            user_id=user_id,
            entity_type="FEEDBACK_ITEM",
            entity_id=feedback_id,
            action="FEEDBACK_ENRICHED_AND_REANALYZED",
            new_state={
                "enrichedText": enriched_text,
                "overallConfidence": new_interp.get("overallConfidence"),
                "investigationStatus": new_inv_status
            }
        )

        return InvestigationService.get_investigation_summary(conn, feedback_id)
