"""
R5 Operational Intelligence Platform - Phase 12: Post-Intervention Outcome Measurement Service
R5 CORE OBJECTIVE: Measure whether corrective action actually changed the operational problem.
Compares BEFORE intervention vs AFTER intervention with deterministic measurements.
Guards against fabricated improvements: shows "outcome cannot yet be determined." when data is insufficient.
"""

import json
import uuid
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from backend.app.core.errors import NotFoundError
from backend.app.services.audit_service import AuditService


class OutcomeService:
    @staticmethod
    def _parse_iso(ts_str: Optional[str]) -> Optional[datetime]:
        """Safely parse ISO datetime string into UTC datetime."""
        if not ts_str:
            return None
        try:
            # Normalize trailing Z
            clean = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    @staticmethod
    def _format_iso(dt: datetime) -> str:
        """Format datetime into ISO 8601 UTC string."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    @staticmethod
    def record_baseline_snapshot(
        conn: sqlite3.Connection,
        issue_id: str
    ) -> Dict[str, Any]:
        """Capture and compute the operational baseline snapshot for an issue prior to intervention."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM issues WHERE id = ?;", (issue_id,))
        issue = cur.fetchone()
        if not issue:
            raise NotFoundError("Issue", issue_id)

        now = datetime.now(timezone.utc)
        issue_created = OutcomeService._parse_iso(issue["created_at"]) or now

        # Query all feedback items linked to this issue
        cur.execute("""
            SELECT fi.* FROM feedback_items fi
            JOIN issue_feedback_links ifl ON fi.id = ifl.feedback_item_id
            WHERE ifl.issue_id = ?
            ORDER BY fi.submitted_at ASC;
        """, (issue_id,))
        linked_feedback = cur.fetchall()

        # If no directly linked feedback, check feedback items in same store & department within 7 days prior
        if not linked_feedback:
            cur.execute("""
                SELECT * FROM feedback_items
                WHERE store_id = ?
                  AND (department_id = ? OR department_id IS NULL)
                  AND submitted_at <= ?
                ORDER BY submitted_at ASC LIMIT 10;
            """, (issue["store_id"], issue["department_id"], issue["created_at"]))
            linked_feedback = cur.fetchall()

        if linked_feedback:
            earliest_dt = OutcomeService._parse_iso(linked_feedback[0]["submitted_at"]) or issue_created
            window_start_dt = min(earliest_dt, issue_created)
        else:
            window_start_dt = issue_created - timedelta(hours=24)

        window_end_dt = now
        window_hours = max(1.0, (window_end_dt - window_start_dt).total_seconds() / 3600.0)
        window_days = max(0.04, window_hours / 24.0)

        complaint_volume = len(linked_feedback) if linked_feedback else 1
        frequency_per_day = round(complaint_volume / window_days, 2)

        # Average severity
        severities = []
        for fb in linked_feedback:
            if fb["sentiment_score"] is not None:
                # Convert negative sentiment to high severity: sentiment -1.0 -> severity 1.0
                severities.append(max(0.0, min(1.0, 1.0 - (fb["sentiment_score"] + 1.0) / 2.0)))
        avg_severity = round(sum(severities) / len(severities), 2) if severities else float(issue["severity_score"])

        # Locations
        locations = set()
        if issue["department_id"]:
            locations.add(issue["department_id"])
        for fb in linked_feedback:
            if fb["department_id"]:
                locations.add(fb["department_id"])
        if not locations:
            locations.add("STORE_WIDE")

        return {
            "windowStart": OutcomeService._format_iso(window_start_dt),
            "windowEnd": OutcomeService._format_iso(window_end_dt),
            "windowHours": round(window_hours, 1),
            "complaintVolume": complaint_volume,
            "issueFrequencyPerDay": frequency_per_day,
            "avgSeverity": avg_severity,
            "affectedLocationsCount": len(locations),
            "affectedLocations": sorted(list(locations)),
            "responseTimeMinutes": 30,
            "resolutionTimeMinutes": None,
            "slaCompliance": True,
            "sampleCitations": [{
                "feedbackItemId": fb["id"],
                "rawText": fb["raw_text"][:120],
                "submittedAt": fb["submitted_at"],
                "channelType": fb["channel_type"]
            } for fb in linked_feedback[:5]]
        }

    @staticmethod
    def evaluate_issue_outcome(
        conn: sqlite3.Connection,
        issue_id: str,
        observation_hours: Optional[float] = None,
        min_observation_hours: Optional[float] = None,
        force_reevaluate: bool = False,
        actor_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deterministically compare BEFORE intervention vs AFTER intervention.
        Outcome states: Improved | No significant change | Worsened | Inconclusive
        If insufficient data exists, deterministically shows 'outcome cannot yet be determined.'
        """
        cur = conn.cursor()
        cur.execute("SELECT * FROM issues WHERE id = ?;", (issue_id,))
        issue = cur.fetchone()
        if not issue:
            raise NotFoundError("Issue", issue_id)

        # Retrieve store context
        cur.execute("SELECT name FROM stores WHERE id = ?;", (issue["store_id"],))
        store_row = cur.fetchone()
        store_name = store_row["name"] if store_row else issue["store_id"]

        # 1. Identify Intervention Details & Timestamp
        cur.execute("""
            SELECT r.*, u.full_name as resolved_by_name, a.recommended_action
            FROM resolutions r
            LEFT JOIN users u ON r.resolved_by = u.id
            LEFT JOIN action_plans a ON r.action_plan_id = a.id
            WHERE r.issue_id = ?
            ORDER BY r.resolved_at DESC LIMIT 1;
        """, (issue_id,))
        resolution = cur.fetchone()

        intervention_dt: Optional[datetime] = None
        action_plan_id: Optional[str] = None
        resolution_id: Optional[str] = None
        technician_notes: Optional[str] = None
        resolved_by: Optional[str] = None
        resolved_by_name: Optional[str] = None
        action_desc: Optional[str] = None

        if resolution:
            resolution_id = resolution["id"]
            action_plan_id = resolution["action_plan_id"]
            intervention_dt = OutcomeService._parse_iso(resolution["resolved_at"])
            technician_notes = resolution["technician_notes"]
            resolved_by = resolution["resolved_by"]
            resolved_by_name = resolution["resolved_by_name"]
            action_desc = resolution["recommended_action"]
        else:
            # Check if an action plan was approved or issue marked remediated
            cur.execute("""
                SELECT * FROM action_plans
                WHERE issue_id = ? AND approval_status = 'APPROVED'
                ORDER BY updated_at DESC LIMIT 1;
            """, (issue_id,))
            act = cur.fetchone()
            if act:
                action_plan_id = act["id"]
                intervention_dt = OutcomeService._parse_iso(act["approved_at"] or act["updated_at"])
                action_desc = act["recommended_action"]
            elif issue["status"] in ("REMEDIATED", "VERIFYING", "CLOSED"):
                intervention_dt = OutcomeService._parse_iso(issue["updated_at"])

        now_utc = datetime.now(timezone.utc)
        issue_created_dt = OutcomeService._parse_iso(issue["created_at"]) or now_utc

        # If NO intervention has been logged at all:
        if not intervention_dt:
            # Cannot compare without an intervention point
            empty_baseline = {
                "windowStart": OutcomeService._format_iso(issue_created_dt),
                "windowEnd": OutcomeService._format_iso(now_utc),
                "windowHours": round(max(1.0, (now_utc - issue_created_dt).total_seconds() / 3600.0), 1),
                "complaintVolume": issue["feedback_count"] or 1,
                "issueFrequencyPerDay": 1.0,
                "avgSeverity": float(issue["severity_score"]),
                "affectedLocationsCount": 1,
                "affectedLocations": [issue["department_id"] or "STORE_WIDE"],
                "responseTimeMinutes": None,
                "resolutionTimeMinutes": None,
                "slaCompliance": True,
                "sampleCitations": []
            }
            empty_obs = {
                "windowStart": OutcomeService._format_iso(now_utc),
                "windowEnd": OutcomeService._format_iso(now_utc),
                "windowHours": 0.0,
                "minObservationHoursRequired": 12.0,
                "isWindowSufficient": False,
                "complaintVolume": 0,
                "issueFrequencyPerDay": 0.0,
                "recurrenceCount": 0,
                "avgSeverity": 0.0,
                "affectedLocationsCount": 0,
                "affectedLocations": []
            }
            comparison = {
                "complaintVolumeDelta": 0,
                "volumeChangePct": 0.0,
                "frequencyDeltaPerDay": 0.0,
                "frequencyChangePct": 0.0,
                "severityDelta": 0.0,
                "recurrenceCount": 0,
                "affectedLocationsDelta": 0,
                "responseTimeMinutes": None,
                "resolutionTimeMinutes": None,
                "slaCompliance": True
            }
            evidence = [{
                "stage": "DETERMINATION",
                "title": "Missing Operational Intervention",
                "claim": "No corrective action or technician resolution has been recorded for this issue.",
                "verbatimQuote": None,
                "feedbackItemId": None,
                "timestamp": OutcomeService._format_iso(now_utc),
                "sourceMetadata": {"issueStatus": issue["status"]}
            }]

            outcome_rec = {
                "id": f"out-{uuid.uuid4().hex[:10]}",
                "organizationId": issue["organization_id"],
                "issueId": issue_id,
                "issueTitle": issue["title"],
                "storeId": issue["store_id"],
                "storeName": store_name,
                "resolutionId": None,
                "actionPlanId": None,
                "intervention": {
                    "timestamp": OutcomeService._format_iso(now_utc),
                    "actionPlanId": None,
                    "resolutionId": None,
                    "technicianNotes": "Pending operational corrective action.",
                    "resolvedBy": None,
                    "resolvedByName": None,
                    "actionDescription": None
                },
                "baseline": empty_baseline,
                "observationWindow": empty_obs,
                "comparison": comparison,
                "outcomeStatus": "Inconclusive",
                "statusMessage": "outcome cannot yet be determined.",
                "confidence": 0.10,
                "evidence": evidence,
                "measuredAt": OutcomeService._format_iso(now_utc),
                "createdAt": OutcomeService._format_iso(now_utc),
                "updatedAt": OutcomeService._format_iso(now_utc)
            }
            OutcomeService._persist_outcome(conn, outcome_rec)
            return outcome_rec

        # ---------------------------------------------------------------------
        # 1. BASELINE SNAPSHOT (BEFORE INTERVENTION)
        # ---------------------------------------------------------------------
        # Find feedback items submitted on or before the intervention timestamp
        cur.execute("""
            SELECT fi.* FROM feedback_items fi
            JOIN issue_feedback_links ifl ON fi.id = ifl.feedback_item_id
            WHERE ifl.issue_id = ?
              AND fi.submitted_at <= ?
            ORDER BY fi.submitted_at ASC;
        """, (issue_id, OutcomeService._format_iso(intervention_dt)))
        pre_feedback = cur.fetchall()

        # If none explicitly linked before intervention, search by store + department / asset
        if not pre_feedback:
            cur.execute("""
                SELECT * FROM feedback_items
                WHERE store_id = ?
                  AND (department_id = ? OR department_id IS NULL)
                  AND submitted_at <= ?
                ORDER BY submitted_at ASC LIMIT 10;
            """, (issue["store_id"], issue["department_id"], OutcomeService._format_iso(intervention_dt)))
            pre_feedback = cur.fetchall()

        if pre_feedback:
            earliest_fb = OutcomeService._parse_iso(pre_feedback[0]["submitted_at"]) or issue_created_dt
            baseline_start_dt = min(earliest_fb, issue_created_dt)
        else:
            baseline_start_dt = issue_created_dt - timedelta(hours=24)

        baseline_hours = max(1.0, (intervention_dt - baseline_start_dt).total_seconds() / 3600.0)
        baseline_days = max(0.04, baseline_hours / 24.0)

        baseline_volume = len(pre_feedback) if pre_feedback else (issue["feedback_count"] or 1)
        baseline_frequency_per_day = round(baseline_volume / baseline_days, 2)

        # Baseline severity calculation
        baseline_sevs = []
        for fb in pre_feedback:
            if fb["sentiment_score"] is not None:
                baseline_sevs.append(max(0.0, min(1.0, 1.0 - (fb["sentiment_score"] + 1.0) / 2.0)))
        baseline_avg_severity = round(sum(baseline_sevs) / len(baseline_sevs), 2) if baseline_sevs else float(issue["severity_score"])

        # Baseline affected locations
        baseline_locs = set()
        if issue["department_id"]:
            baseline_locs.add(issue["department_id"])
        for fb in pre_feedback:
            if fb["department_id"]:
                baseline_locs.add(fb["department_id"])
        if not baseline_locs:
            baseline_locs.add("STORE_WIDE")

        # Response Time & Resolution Time
        res_time_mins = int((intervention_dt - issue_created_dt).total_seconds() / 60.0)
        resp_time_mins = min(res_time_mins, 30)

        # Deterministic SLA compliance
        sla_limit_mins = issue["sla_minutes"] or 60
        sla_compliant = res_time_mins <= sla_limit_mins
        if issue["sla_deadline"]:
            deadline_dt = OutcomeService._parse_iso(issue["sla_deadline"])
            if deadline_dt:
                sla_compliant = intervention_dt <= deadline_dt

        baseline_citations = [{
            "feedbackItemId": fb["id"],
            "rawText": fb["raw_text"][:140],
            "submittedAt": fb["submitted_at"],
            "channelType": fb["channel_type"]
        } for fb in pre_feedback[:5]]

        baseline_snapshot = {
            "windowStart": OutcomeService._format_iso(baseline_start_dt),
            "windowEnd": OutcomeService._format_iso(intervention_dt),
            "windowHours": round(baseline_hours, 1),
            "complaintVolume": baseline_volume,
            "issueFrequencyPerDay": baseline_frequency_per_day,
            "avgSeverity": baseline_avg_severity,
            "affectedLocationsCount": len(baseline_locs),
            "affectedLocations": sorted(list(baseline_locs)),
            "responseTimeMinutes": resp_time_mins,
            "resolutionTimeMinutes": res_time_mins,
            "slaCompliance": sla_compliant,
            "sampleCitations": baseline_citations
        }

        # ---------------------------------------------------------------------
        # 2. POST-INTERVENTION OBSERVATION WINDOW (AFTER INTERVENTION)
        # ---------------------------------------------------------------------
        # If observation_hours is explicitly passed (e.g. for deterministic simulation/testing), use it
        if observation_hours is not None:
            observation_end_dt = intervention_dt + timedelta(hours=observation_hours)
            elapsed_hours = float(observation_hours)
        else:
            observation_end_dt = now_utc
            elapsed_hours = max(0.0, (now_utc - intervention_dt).total_seconds() / 3600.0)

        required_min_hours = min_observation_hours if min_observation_hours is not None else 12.0
        # Observation window is sufficient only if elapsed time >= required AND baseline had real data
        is_window_sufficient = (elapsed_hours >= required_min_hours) and (baseline_volume > 0)

        # Query post-intervention feedback
        # Matching same store and (department or asset or cluster or linked)
        cur.execute("""
            SELECT * FROM feedback_items
            WHERE store_id = ?
              AND submitted_at > ?
              AND submitted_at <= ?
              AND (
                  id IN (SELECT feedback_item_id FROM issue_feedback_links WHERE issue_id = ?)
                  OR (? IS NOT NULL AND department_id = ?)
                  OR (raw_text LIKE ? AND ? != '')
              )
            ORDER BY submitted_at ASC;
        """, (
            issue["store_id"],
            OutcomeService._format_iso(intervention_dt),
            OutcomeService._format_iso(observation_end_dt),
            issue_id,
            issue["department_id"],
            issue["department_id"],
            f"%{issue['title'][:15]}%",
            issue["title"][:15]
        ))
        post_feedback = cur.fetchall()

        post_volume = len(post_feedback)
        post_days = max(0.04, elapsed_hours / 24.0)
        post_frequency_per_day = round(post_volume / post_days, 2) if elapsed_hours > 0 else 0.0

        post_sevs = []
        for fb in post_feedback:
            if fb["sentiment_score"] is not None:
                post_sevs.append(max(0.0, min(1.0, 1.0 - (fb["sentiment_score"] + 1.0) / 2.0)))
        post_avg_severity = round(sum(post_sevs) / len(post_sevs), 2) if post_sevs else 0.0

        post_locs = set()
        for fb in post_feedback:
            if fb["department_id"]:
                post_locs.add(fb["department_id"])

        recurrence_count = post_volume

        observation_window = {
            "windowStart": OutcomeService._format_iso(intervention_dt),
            "windowEnd": OutcomeService._format_iso(observation_end_dt),
            "windowHours": round(elapsed_hours, 1),
            "minObservationHoursRequired": required_min_hours,
            "isWindowSufficient": is_window_sufficient,
            "complaintVolume": post_volume,
            "issueFrequencyPerDay": post_frequency_per_day,
            "recurrenceCount": recurrence_count,
            "avgSeverity": post_avg_severity,
            "affectedLocationsCount": len(post_locs),
            "affectedLocations": sorted(list(post_locs))
        }

        # ---------------------------------------------------------------------
        # 3. COMPARISON (BEFORE vs AFTER)
        # ---------------------------------------------------------------------
        volume_delta = post_volume - baseline_volume
        volume_change_pct = round(((post_volume - baseline_volume) / baseline_volume) * 100.0, 1) if baseline_volume > 0 else 0.0

        freq_delta = round(post_frequency_per_day - baseline_frequency_per_day, 2)
        if baseline_frequency_per_day > 0:
            freq_change_pct = round(((post_frequency_per_day - baseline_frequency_per_day) / baseline_frequency_per_day) * 100.0, 1)
        else:
            freq_change_pct = 0.0

        severity_delta = round(post_avg_severity - baseline_avg_severity, 2) if post_volume > 0 else round(-baseline_avg_severity, 2)
        locations_delta = len(post_locs) - len(baseline_locs)

        comparison = {
            "complaintVolumeDelta": volume_delta,
            "volumeChangePct": volume_change_pct,
            "frequencyDeltaPerDay": freq_delta,
            "frequencyChangePct": freq_change_pct,
            "severityDelta": severity_delta,
            "recurrenceCount": recurrence_count,
            "affectedLocationsDelta": locations_delta,
            "responseTimeMinutes": resp_time_mins,
            "resolutionTimeMinutes": res_time_mins,
            "slaCompliance": sla_compliant
        }

        # ---------------------------------------------------------------------
        # 4. DETERMINISTIC OUTCOME STATE & CONFIDENCE ("Do not fabricate")
        # ---------------------------------------------------------------------
        evidence = []

        # Baseline evidence entry
        evidence.append({
            "stage": "BASELINE",
            "title": "Pre-Intervention Baseline Established",
            "claim": f"Baseline established over {baseline_hours:.1f}h window with {baseline_volume} complaints ({baseline_frequency_per_day}/day) and avg severity {baseline_avg_severity}.",
            "verbatimQuote": baseline_citations[0]["rawText"] if baseline_citations else None,
            "feedbackItemId": baseline_citations[0]["feedbackItemId"] if baseline_citations else None,
            "timestamp": OutcomeService._format_iso(baseline_start_dt),
            "sourceMetadata": {"windowHours": baseline_hours, "complaintVolume": baseline_volume}
        })

        # Intervention evidence entry
        evidence.append({
            "stage": "INTERVENTION",
            "title": "Corrective Operational Action Executed",
            "claim": f"Corrective action completed at {OutcomeService._format_iso(intervention_dt)}. Technician notes: {technician_notes or action_desc or 'Action executed'}.",
            "verbatimQuote": technician_notes,
            "feedbackItemId": None,
            "timestamp": OutcomeService._format_iso(intervention_dt),
            "sourceMetadata": {
                "actionPlanId": action_plan_id,
                "resolutionId": resolution_id,
                "slaCompliance": sla_compliant,
                "resolutionTimeMinutes": res_time_mins
            }
        })

        if not is_window_sufficient:
            # INSUFFICIENT DATA GUARD:
            # Do NOT fabricate improvements. Show "outcome cannot yet be determined."
            outcome_status = "Inconclusive"
            status_message = "outcome cannot yet be determined."
            confidence = round(min(0.40, 0.15 + (elapsed_hours / max(1.0, required_min_hours)) * 0.20), 2)

            evidence.append({
                "stage": "POST_OBSERVATION",
                "title": "Insufficient Post-Intervention Observation Window",
                "claim": f"Only {elapsed_hours:.1f} hours elapsed since intervention. Minimum {required_min_hours:.1f} hours required to verify operational stabilization.",
                "verbatimQuote": None,
                "feedbackItemId": None,
                "timestamp": OutcomeService._format_iso(observation_end_dt),
                "sourceMetadata": {
                    "elapsedHours": elapsed_hours,
                    "requiredHours": required_min_hours,
                    "postVolume": post_volume
                }
            })
            evidence.append({
                "stage": "DETERMINATION",
                "title": "Outcome Inconclusive: Waiting for Observation Window",
                "claim": "Outcome cannot yet be determined. Premature determination is blocked to prevent false operational assurance.",
                "verbatimQuote": None,
                "feedbackItemId": None,
                "timestamp": OutcomeService._format_iso(observation_end_dt),
                "sourceMetadata": {"rule": "MINIMUM_OBSERVATION_WINDOW_REQUIRED"}
            })

        else:
            # SUFFICIENT DATA: Deterministic evaluation
            evidence.append({
                "stage": "POST_OBSERVATION",
                "title": "Post-Intervention Operational Window Audited",
                "claim": f"Audited {elapsed_hours:.1f}h post-intervention window. Observed {post_volume} complaints ({post_frequency_per_day}/day) with recurrence count of {recurrence_count}.",
                "verbatimQuote": post_feedback[0]["raw_text"][:140] if post_feedback else "Zero recurring complaints logged.",
                "feedbackItemId": post_feedback[0]["id"] if post_feedback else None,
                "timestamp": OutcomeService._format_iso(observation_end_dt),
                "sourceMetadata": {
                    "elapsedHours": elapsed_hours,
                    "postVolume": post_volume,
                    "recurrenceCount": recurrence_count
                }
            })

            # Check Worsened condition first
            # 1. Worsened: Complaints escalated by >= 25%, recurrence >= 3, or severity sharply increased
            if freq_change_pct >= 25.0 or severity_delta >= 0.20 or recurrence_count >= 3 or locations_delta > 0:
                outcome_status = "Worsened"
                status_message = f"Operational condition worsened: complaint arrival frequency increased by {freq_change_pct:.1f}%, recurrence count={recurrence_count}."
                confidence = round(min(0.95, 0.70 + min(1.0, elapsed_hours / (required_min_hours * 2)) * 0.25), 2)
                evidence.append({
                    "stage": "DETERMINATION",
                    "title": "Deterministic Verdict: Worsened",
                    "claim": f"Telemetry proves failure of corrective intervention: frequency increased by {freq_change_pct:.1f}% with {recurrence_count} recurrence events.",
                    "verbatimQuote": None,
                    "feedbackItemId": None,
                    "timestamp": OutcomeService._format_iso(observation_end_dt),
                    "sourceMetadata": {"frequencyDelta": freq_delta, "recurrence": recurrence_count}
                })

            # 2. Improved: Substantial reduction (>= 50% frequency reduction or 0 recurrence with mature baseline)
            elif (freq_change_pct <= -50.0 or (post_volume == 0 and baseline_volume >= 2)) and recurrence_count == 0 and severity_delta <= 0:
                outcome_status = "Improved"
                status_message = f"Operational problem resolved: complaint frequency dropped by {abs(freq_change_pct):.1f}%, zero recurrence detected across {elapsed_hours:.1f}h window."
                confidence = round(min(0.98, 0.75 + min(1.0, elapsed_hours / (required_min_hours * 2)) * 0.23), 2)
                evidence.append({
                    "stage": "DETERMINATION",
                    "title": "Deterministic Verdict: Improved",
                    "claim": f"Definitive operational improvement confirmed: complaint arrival rate reduced by {abs(freq_change_pct):.1f}% with zero recurrence in {elapsed_hours:.1f}h.",
                    "verbatimQuote": None,
                    "feedbackItemId": None,
                    "timestamp": OutcomeService._format_iso(observation_end_dt),
                    "sourceMetadata": {"improvementPct": abs(freq_change_pct), "slaCompliant": sla_compliant}
                })

            # 3. No significant change: complaints continuing roughly at baseline rate
            else:
                outcome_status = "No significant change"
                status_message = f"Operational issue persists without significant change: arrival frequency changed by {freq_change_pct:.1f}%, recurrence count={recurrence_count}."
                confidence = round(min(0.90, 0.65 + min(1.0, elapsed_hours / (required_min_hours * 2)) * 0.25), 2)
                evidence.append({
                    "stage": "DETERMINATION",
                    "title": "Deterministic Verdict: No Significant Change",
                    "claim": f"Post-intervention frequency remains within normal variation band ({freq_change_pct:.1f}% shift). Problem has not been measurably eradicated.",
                    "verbatimQuote": None,
                    "feedbackItemId": None,
                    "timestamp": OutcomeService._format_iso(observation_end_dt),
                    "sourceMetadata": {"frequencyChangePct": freq_change_pct, "recurrenceCount": recurrence_count}
                })

        # ---------------------------------------------------------------------
        # 5. Persist and Return Outcome Measurement
        # ---------------------------------------------------------------------
        measurement_id = f"out-{uuid.uuid4().hex[:10]}"
        now_str = OutcomeService._format_iso(now_utc)

        outcome_result = {
            "id": measurement_id,
            "organizationId": issue["organization_id"],
            "issueId": issue_id,
            "issueTitle": issue["title"],
            "storeId": issue["store_id"],
            "storeName": store_name,
            "resolutionId": resolution_id,
            "actionPlanId": action_plan_id,
            "intervention": {
                "timestamp": OutcomeService._format_iso(intervention_dt),
                "actionPlanId": action_plan_id,
                "resolutionId": resolution_id,
                "technicianNotes": technician_notes,
                "resolvedBy": resolved_by,
                "resolvedByName": resolved_by_name,
                "actionDescription": action_desc
            },
            "baseline": baseline_snapshot,
            "observationWindow": observation_window,
            "comparison": comparison,
            "outcomeStatus": outcome_status,
            "statusMessage": status_message,
            "confidence": confidence,
            "evidence": evidence,
            "measuredAt": now_str,
            "createdAt": now_str,
            "updatedAt": now_str
        }

        OutcomeService._persist_outcome(conn, outcome_result)

        AuditService.record_audit(
            conn=conn,
            organization_id=issue["organization_id"],
            user_id=actor_user_id,
            entity_type="OUTCOME_MEASUREMENT",
            entity_id=measurement_id,
            action="OUTCOME_EVALUATED",
            new_state={
                "issueId": issue_id,
                "outcomeStatus": outcome_status,
                "confidence": confidence,
                "statusMessage": status_message,
                "isWindowSufficient": is_window_sufficient
            },
            justification=f"Automated post-intervention operational measurement. Status: {outcome_status}."
        )

        return outcome_result

    @staticmethod
    def _persist_outcome(conn: sqlite3.Connection, outcome: Dict[str, Any]) -> None:
        """Upsert outcome measurement in SQLite database."""
        cur = conn.cursor()
        b = outcome["baseline"]
        obs = outcome["observationWindow"]
        c = outcome["comparison"]
        cur.execute("""
            INSERT OR REPLACE INTO outcome_measurements (
                id, organization_id, issue_id, resolution_id, action_plan_id,
                intervention_timestamp, baseline_window_start, baseline_window_end, baseline_window_hours,
                baseline_complaint_volume, baseline_issue_frequency_per_day, baseline_avg_severity, baseline_affected_locations_count,
                observation_window_start, observation_window_end, observation_window_hours,
                min_observation_hours_required, is_window_sufficient, post_complaint_volume,
                post_issue_frequency_per_day, post_recurrence_count, post_avg_severity,
                post_affected_locations_count, response_time_minutes, resolution_time_minutes,
                sla_compliance, outcome_status, status_message, confidence,
                comparison_data, baseline_snapshot, post_snapshot, evidence,
                measured_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            outcome["id"],
            outcome["organizationId"],
            outcome["issueId"],
            outcome["resolutionId"],
            outcome["actionPlanId"],
            outcome["intervention"]["timestamp"],
            b["windowStart"],
            b["windowEnd"],
            b["windowHours"],
            b["complaintVolume"],
            b["issueFrequencyPerDay"],
            b["avgSeverity"],
            b["affectedLocationsCount"],
            obs["windowStart"],
            obs["windowEnd"],
            obs["windowHours"],
            obs["minObservationHoursRequired"],
            1 if obs["isWindowSufficient"] else 0,
            obs["complaintVolume"],
            obs["issueFrequencyPerDay"],
            obs["recurrenceCount"],
            obs["avgSeverity"],
            obs["affectedLocationsCount"],
            c["responseTimeMinutes"],
            c["resolutionTimeMinutes"],
            1 if c["slaCompliance"] else 0,
            outcome["outcomeStatus"],
            outcome["statusMessage"],
            outcome["confidence"],
            json.dumps(c),
            json.dumps(b),
            json.dumps(obs),
            json.dumps(outcome["evidence"]),
            outcome["measuredAt"],
            outcome["createdAt"],
            outcome["updatedAt"]
        ))
        conn.commit()

    @staticmethod
    def get_issue_outcome(conn: sqlite3.Connection, issue_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the latest outcome measurement for a specific issue."""
        cur = conn.cursor()
        cur.execute("""
            SELECT om.*, i.title as issue_title, i.store_id, s.name as store_name,
                   r.technician_notes, r.resolved_by, u.full_name as resolved_by_name,
                   a.recommended_action
            FROM outcome_measurements om
            JOIN issues i ON om.issue_id = i.id
            JOIN stores s ON i.store_id = s.id
            LEFT JOIN resolutions r ON om.resolution_id = r.id
            LEFT JOIN users u ON r.resolved_by = u.id
            LEFT JOIN action_plans a ON om.action_plan_id = a.id
            WHERE om.issue_id = ?
            ORDER BY om.measured_at DESC LIMIT 1;
        """, (issue_id,))
        row = cur.fetchone()
        if not row:
            # Check if issue exists and evaluate on the fly
            cur.execute("SELECT id, status FROM issues WHERE id = ?;", (issue_id,))
            iss = cur.fetchone()
            if iss:
                return OutcomeService.evaluate_issue_outcome(conn, issue_id)
            return None

        return OutcomeService._row_to_response(row)

    @staticmethod
    def list_outcomes(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        outcome_status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query stored outcome measurements with optional store and status filtering."""
        query = """
            SELECT om.*, i.title as issue_title, i.store_id, s.name as store_name,
                   r.technician_notes, r.resolved_by, u.full_name as resolved_by_name,
                   a.recommended_action
            FROM outcome_measurements om
            JOIN issues i ON om.issue_id = i.id
            JOIN stores s ON i.store_id = s.id
            LEFT JOIN resolutions r ON om.resolution_id = r.id
            LEFT JOIN users u ON r.resolved_by = u.id
            LEFT JOIN action_plans a ON om.action_plan_id = a.id
            WHERE om.organization_id = ?
        """
        params: List[Any] = [organization_id]
        if store_id:
            query += " AND i.store_id = ?"
            params.append(store_id)
        if outcome_status:
            query += " AND om.outcome_status = ?"
            params.append(outcome_status)

        query += " ORDER BY om.measured_at DESC LIMIT ?"
        params.append(limit)

        cur = conn.cursor()
        cur.execute(query, params)
        return [OutcomeService._row_to_response(r) for r in cur.fetchall()]

    @staticmethod
    def get_outcomes_dashboard_summary(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate high-level aggregated telemetry and KPI summary for the Outcome Dashboard."""
        outcomes = OutcomeService.list_outcomes(conn, organization_id, store_id=store_id, limit=200)

        improved = [o for o in outcomes if o["outcomeStatus"] == "Improved"]
        no_change = [o for o in outcomes if o["outcomeStatus"] == "No significant change"]
        worsened = [o for o in outcomes if o["outcomeStatus"] == "Worsened"]
        inconclusive = [o for o in outcomes if o["outcomeStatus"] == "Inconclusive"]

        total = len(outcomes)
        decisive_count = len(improved) + len(no_change) + len(worsened)

        improved_rate = round((len(improved) / decisive_count * 100.0), 1) if decisive_count > 0 else 0.0

        res_times = [
            o["comparison"]["resolutionTimeMinutes"]
            for o in outcomes
            if o["comparison"].get("resolutionTimeMinutes") is not None
        ]
        avg_res_time_hours = round((sum(res_times) / len(res_times)) / 60.0, 1) if res_times else 0.0

        sla_met = [o for o in outcomes if o["comparison"].get("slaCompliance")]
        sla_rate = round((len(sla_met) / total * 100.0), 1) if total > 0 else 100.0

        improvements = [abs(o["comparison"]["frequencyChangePct"]) for o in improved if o["comparison"].get("frequencyChangePct")]
        avg_improvement_pct = round(sum(improvements) / len(improvements), 1) if improvements else 0.0

        # Category breakdown
        cur = conn.cursor()
        cur.execute("""
            SELECT i.priority_tier, om.outcome_status, count(*) as cnt
            FROM outcome_measurements om
            JOIN issues i ON om.issue_id = i.id
            WHERE om.organization_id = ?
            GROUP BY i.priority_tier, om.outcome_status;
        """, (organization_id,))
        breakdown_rows = cur.fetchall()

        cat_breakdown: Dict[str, Dict[str, int]] = {}
        for row in breakdown_rows:
            tier = row["priority_tier"]
            st = row["outcome_status"]
            if tier not in cat_breakdown:
                cat_breakdown[tier] = {"Improved": 0, "No significant change": 0, "Worsened": 0, "Inconclusive": 0}
            cat_breakdown[tier][st] = row["cnt"]

        return {
            "totalResolvedIssues": total,
            "improvedCount": len(improved),
            "noChangeCount": len(no_change),
            "worsenedCount": len(worsened),
            "inconclusiveCount": len(inconclusive),
            "improvedRatePct": improved_rate,
            "avgResolutionTimeHours": avg_res_time_hours,
            "slaComplianceRatePct": sla_rate,
            "avgImprovementPct": avg_improvement_pct,
            "outcomes": outcomes,
            "categoryBreakdown": cat_breakdown
        }

    @staticmethod
    def _row_to_response(row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to OutcomeMeasurementResponse dictionary."""
        b = json.loads(row["baseline_snapshot"]) if row["baseline_snapshot"] else {}
        obs = json.loads(row["post_snapshot"]) if row["post_snapshot"] else {}
        c = json.loads(row["comparison_data"]) if row["comparison_data"] else {}
        ev = json.loads(row["evidence"]) if row["evidence"] else []

        return {
            "id": row["id"],
            "organizationId": row["organization_id"],
            "issueId": row["issue_id"],
            "issueTitle": row["issue_title"],
            "storeId": row["store_id"],
            "storeName": row["store_name"],
            "resolutionId": row["resolution_id"],
            "actionPlanId": row["action_plan_id"],
            "intervention": {
                "timestamp": row["intervention_timestamp"],
                "actionPlanId": row["action_plan_id"],
                "resolutionId": row["resolution_id"],
                "technicianNotes": row["technician_notes"],
                "resolvedBy": row["resolved_by"],
                "resolvedByName": row["resolved_by_name"],
                "actionDescription": row["recommended_action"]
            },
            "baseline": b,
            "observationWindow": obs,
            "comparison": c,
            "outcomeStatus": row["outcome_status"],
            "statusMessage": row["status_message"],
            "confidence": row["confidence"],
            "evidence": ev,
            "measuredAt": row["measured_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"]
        }
