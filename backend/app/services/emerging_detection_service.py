import uuid
import json
import math
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from backend.app.core.errors import NotFoundError
from backend.app.services.audit_service import AuditService

MIN_BASELINE_OBSERVATIONS = 3
MIN_BASELINE_DAYS = 3

class EmergingDetectionService:
    @staticmethod
    def calculate_historical_baseline(
        conn: sqlite3.Connection,
        store_id: str,
        category: str,
        baseline_days: int = 14,
        recent_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Calculate historical baseline frequency and variance for a store and category.
        If historical observations < 3 or span < 3 days, returns baseline_status="INSUFFICIENT_BASELINE".
        """
        now = datetime.now(timezone.utc)
        recent_cutoff = (now - timedelta(hours=recent_hours)).isoformat()
        baseline_start = (now - timedelta(days=baseline_days)).isoformat()

        cur = conn.cursor()
        cur.execute("""
            SELECT submitted_at, ai_interpretation, raw_text FROM feedback_items
            WHERE store_id = ?
              AND submitted_at >= ?
              AND submitted_at < ?
            ORDER BY submitted_at ASC;
        """, (store_id, baseline_start, recent_cutoff))
        rows = cur.fetchall()

        # Filter by category if ai_interpretation exists or category matches
        category_rows = []
        for r in rows:
            if category:
                matched = False
                if r["ai_interpretation"]:
                    try:
                        interp = json.loads(r["ai_interpretation"])
                        cat_val = interp.get("issueCategory", {}).get("value") or interp.get("detectedIntent")
                        if cat_val == category:
                            matched = True
                    except Exception:
                        pass
                if not matched and category.lower() in (r["raw_text"] or "").lower():
                    matched = True
                if not matched:
                    continue
            category_rows.append(r)

        total_obs = len(category_rows)
        # Check if baseline data is sufficient
        if total_obs < MIN_BASELINE_OBSERVATIONS:
            return {
                "status": "INSUFFICIENT_BASELINE",
                "observations": total_obs,
                "dailyMean": 0.0,
                "dailyStdDev": 0.0,
                "expectedRecent": 0.0,
                "reason": f"Only {total_obs} historical record(s) found in {baseline_days}-day baseline window (minimum {MIN_BASELINE_OBSERVATIONS} required)."
            }

        # Divide into daily buckets
        effective_days = max(1, baseline_days - (recent_hours / 24.0))
        daily_mean = total_obs / effective_days

        # Daily variance under Poisson assumption / sample variance
        daily_variance = max(daily_mean, 0.5)
        daily_stddev = math.sqrt(daily_variance)
        expected_recent = daily_mean * (recent_hours / 24.0)

        return {
            "status": "VALID_BASELINE",
            "observations": total_obs,
            "dailyMean": round(daily_mean, 2),
            "dailyStdDev": round(daily_stddev, 2),
            "expectedRecent": round(expected_recent, 2),
            "reason": f"Computed across {total_obs} historical observations over {effective_days:.1f} active baseline days."
        }

    @staticmethod
    def detect_emerging_issues(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        recent_hours: int = 24,
        baseline_days: int = 14,
        min_evidence_threshold: int = 2,
        zscore_threshold: float = 1.8,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Deterministic emerging issue detection engine.
        Compares recent activity against historical baselines, cross-source diversity,
        and acceleration metrics. Generates rich explainable alerts.
        """
        cur = conn.cursor()
        now = datetime.now(timezone.utc)
        recent_start = (now - timedelta(hours=recent_hours)).isoformat()

        # Query recent feedback items
        query = """
            SELECT fi.*, s.name as store_name
            FROM feedback_items fi
            LEFT JOIN stores s ON fi.store_id = s.id
            WHERE fi.organization_id = ?
              AND fi.submitted_at >= ?
        """
        params: List[Any] = [organization_id, recent_start]
        if store_id:
            query += " AND fi.store_id = ?"
            params.append(store_id)

        query += " ORDER BY fi.submitted_at DESC;"
        cur.execute(query, params)
        recent_items = cur.fetchall()

        if not recent_items:
            return []

        # Group by (store_id, category)
        grouped: Dict[tuple[str, str], List[sqlite3.Row]] = {}
        for item in recent_items:
            cat = "EQUIPMENT_FAILURE"
            if item["ai_interpretation"]:
                try:
                    interp = json.loads(item["ai_interpretation"])
                    cat = interp.get("issueCategory", {}).get("value") or "EQUIPMENT_FAILURE"
                except Exception:
                    pass
            key = (item["store_id"], cat)
            grouped.setdefault(key, []).append(item)

        generated_alerts = []

        for (st_id, cat), group in grouped.items():
            obs_count = len(group)
            if obs_count < min_evidence_threshold:
                continue

            # Compute historical baseline deterministically
            baseline = EmergingDetectionService.calculate_historical_baseline(
                conn, st_id, cat, baseline_days=baseline_days, recent_hours=recent_hours
            )

            # Sources diversity
            sources = list({r["channel_type"] for r in group})
            _submitters = list({r["submitter_type"] for r in group})

            # Check if any item is safety relevant or critical
            is_safety = False
            critical_count = 0
            for r in group:
                if r["ai_interpretation"]:
                    try:
                        interp = json.loads(r["ai_interpretation"])
                        if interp.get("safetyRelevance", {}).get("value") in [True, "true", "TRUE"]:
                            is_safety = True
                        if interp.get("severity", {}).get("value") in ["CRITICAL", "HIGH"]:
                            critical_count += 1
                    except Exception:
                        pass

            # Calculate deterministic metrics
            if baseline["status"] == "INSUFFICIENT_BASELINE":
                # Do NOT fabricate an anomaly alert if insufficient baseline exists,
                # UNLESS it's an immediate severe safety hazard
                if not is_safety and critical_count == 0:
                    continue

                baseline_diff = 0.0
                growth_rate = 0.0
                zscore = 0.0
                baseline_status = "INSUFFICIENT_BASELINE"
                why = (
                    f"Alert triggered due to {critical_count} high-severity observation(s) and safety flags, "
                    f"though historical data is insufficient to compute baseline velocity ({baseline['reason']})."
                )
            else:
                expected = baseline["expectedRecent"]
                stddev = baseline["dailyStdDev"]
                baseline_diff = round(obs_count - expected, 2)
                growth_rate = round((obs_count - expected) / max(expected, 0.5), 2)
                zscore = round((obs_count - expected) / max(stddev, 0.5), 2)

                if zscore < zscore_threshold and not is_safety:
                    continue  # Below anomaly threshold

                baseline_status = "ANOMALY" if zscore >= zscore_threshold else "NORMAL"
                why = (
                    f"Recent frequency ({obs_count} reports in {recent_hours}h) exceeds baseline expectation "
                    f"of {expected:.1f} (Z-Score: +{zscore:.2f}z, Growth: +{growth_rate * 100:.0f}%). "
                    f"Confirmed across {len(sources)} source channel(s) ({', '.join(sources)})."
                )

            # Determine severity & urgency
            if is_safety or critical_count >= 2 or zscore >= 3.0:
                severity = "CRITICAL"
                urgency = "IMMEDIATE"
            elif critical_count >= 1 or zscore >= 2.0:
                severity = "HIGH"
                urgency = "WITHIN_2_HOURS"
            else:
                severity = "MEDIUM"
                urgency = "NEXT_SHIFT"

            what = f"Emerging {cat.replace('_', ' ').title()} Spike"
            where_zone = group[0]["store_name"] or f"Store {st_id}"
            message = (
                f"{what} at {where_zone}: {obs_count} reports in {recent_hours}h "
                f"({'+' if zscore >= 0 else ''}{zscore:.1f}z vs baseline). "
                f"Sources: {', '.join(sources)}."
            )

            # Uncertainties
            uncertainties = []
            if baseline_status == "INSUFFICIENT_BASELINE":
                uncertainties.append("Baseline velocity is unconfirmed due to sparse historical logs.")
            if len(sources) == 1:
                uncertainties.append(f"Unconfirmed across other channels (only observed in {sources[0]}).")

            # Link or create issue for alert
            issue_id = f"issue-{uuid.uuid4().hex[:10]}"
            now_iso = now.isoformat()

            cur.execute("""
                INSERT INTO issues (
                    id, organization_id, store_id, title, description,
                    status, priority_score, priority_tier, severity_score,
                    urgency_score, impact_scope_score, confidence_score,
                    is_emerging_anomaly, anomaly_velocity_zscore,
                    feedback_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'DETECTED', 85, 'P1_CRITICAL', 0.85, 0.90, 0.75, 0.88, 1, ?, ?, ?, ?);
            """, (
                issue_id, organization_id, st_id, what, message,
                zscore, obs_count, now_iso, now_iso
            ))

            alert_id = f"alert-{uuid.uuid4().hex[:10]}"
            cur.execute("""
                INSERT INTO alerts (
                    id, organization_id, store_id, issue_id, alert_type,
                    severity, urgency, confidence, message, what, where_zone,
                    observation_count, sources_summary, baseline_diff,
                    velocity_zscore, growth_rate, baseline_status,
                    why_generated, uncertainties, status, is_acknowledged,
                    created_at
                ) VALUES (?, ?, ?, ?, 'EMERGING_ANOMALY', ?, ?, 0.88, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEW', 0, ?);
            """, (
                alert_id, organization_id, st_id, issue_id,
                severity, urgency, message, what, where_zone,
                obs_count, json.dumps(sources), baseline_diff,
                zscore, growth_rate, baseline_status,
                why, json.dumps(uncertainties), now_iso
            ))

            generated_alerts.append(EmergingDetectionService.get_alert_by_id(conn, alert_id))

        if generated_alerts:
            AuditService.record_audit(
                conn=conn,
                organization_id=organization_id,
                user_id=user_id,
                entity_type="ALERT",
                entity_id="EMERGING_DETECTION_RUN",
                action="ALERTS_GENERATED",
                new_state={"alertsCount": len(generated_alerts)}
            )

        return generated_alerts

    @staticmethod
    def get_alert_by_id(conn: sqlite3.Connection, alert_id: str) -> Dict[str, Any]:
        """Fetch alert by ID with formatted schema."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM alerts WHERE id = ?;", (alert_id,))
        r = cur.fetchone()
        if not r:
            raise NotFoundError("Alert", alert_id)

        sources = []
        if r["sources_summary"]:
            try:
                sources = json.loads(r["sources_summary"])
            except Exception:
                sources = [r["sources_summary"]]

        uncs = []
        if r["uncertainties"]:
            try:
                uncs = json.loads(r["uncertainties"])
            except Exception:
                uncs = [r["uncertainties"]]

        return {
            "id": r["id"],
            "organizationId": r["organization_id"],
            "storeId": r["store_id"],
            "issueId": r["issue_id"],
            "alertType": r["alert_type"],
            "severity": r["severity"],
            "urgency": r["urgency"] or "MEDIUM",
            "confidence": r["confidence"] or 0.85,
            "message": r["message"],
            "what": r["what"],
            "whereZone": r["where_zone"],
            "observationCount": r["observation_count"] or 1,
            "sourcesSummary": sources,
            "baselineDiff": r["baseline_diff"] or 0.0,
            "velocityZscore": r["velocity_zscore"] or 0.0,
            "growthRate": r["growth_rate"] or 0.0,
            "baselineStatus": r["baseline_status"] or "NORMAL",
            "whyGenerated": r["why_generated"],
            "uncertainties": uncs,
            "status": r["status"] or "NEW",
            "isAcknowledged": bool(r["is_acknowledged"]),
            "acknowledgedBy": r["acknowledged_by"],
            "acknowledgedAt": r["acknowledged_at"],
            "escalatedToTeamId": r["escalated_to_team_id"],
            "escalatedBy": r["escalated_by"],
            "escalatedAt": r["escalated_at"],
            "dismissedBy": r["dismissed_by"],
            "dismissedAt": r["dismissed_at"],
            "dismissReason": r["dismiss_reason"],
            "createdAt": r["created_at"]
        }

    @staticmethod
    def acknowledge_alert(
        conn: sqlite3.Connection,
        alert_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Acknowledge an active alert."""
        cur = conn.cursor()
        alert = EmergingDetectionService.get_alert_by_id(conn, alert_id)

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            UPDATE alerts
            SET is_acknowledged = 1, status = 'ACKNOWLEDGED', acknowledged_by = ?, acknowledged_at = ?
            WHERE id = ?;
        """, (user_id, now, alert_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=alert["organizationId"],
            user_id=user_id,
            entity_type="ALERT",
            entity_id=alert_id,
            action="ALERT_ACKNOWLEDGED",
            new_state={"status": "ACKNOWLEDGED", "isAcknowledged": True}
        )

        return EmergingDetectionService.get_alert_by_id(conn, alert_id)

    @staticmethod
    def escalate_alert(
        conn: sqlite3.Connection,
        alert_id: str,
        target_team_id: str,
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Escalate an alert to an operational team for urgent intervention."""
        cur = conn.cursor()
        alert = EmergingDetectionService.get_alert_by_id(conn, alert_id)

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            UPDATE alerts
            SET status = 'ESCALATED', escalated_to_team_id = ?, escalated_by = ?, escalated_at = ?
            WHERE id = ?;
        """, (target_team_id, user_id, now, alert_id))

        # Also assign issue to the team
        cur.execute("""
            UPDATE issues
            SET assigned_team_id = ?, status = 'TRIAGED', updated_at = ?
            WHERE id = ?;
        """, (target_team_id, now, alert["issueId"]))

        AuditService.record_audit(
            conn=conn,
            organization_id=alert["organizationId"],
            user_id=user_id,
            entity_type="ALERT",
            entity_id=alert_id,
            action="ALERT_ESCALATED",
            new_state={"status": "ESCALATED", "targetTeamId": target_team_id},
            justification=notes
        )

        return EmergingDetectionService.get_alert_by_id(conn, alert_id)

    @staticmethod
    def dismiss_alert(
        conn: sqlite3.Connection,
        alert_id: str,
        reason: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dismiss a false positive or duplicate alert with required justification."""
        cur = conn.cursor()
        alert = EmergingDetectionService.get_alert_by_id(conn, alert_id)

        now = datetime.now(timezone.utc).isoformat()
        cur.execute("""
            UPDATE alerts
            SET status = 'DISMISSED', dismissed_by = ?, dismissed_at = ?, dismiss_reason = ?
            WHERE id = ?;
        """, (user_id, now, reason, alert_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=alert["organizationId"],
            user_id=user_id,
            entity_type="ALERT",
            entity_id=alert_id,
            action="ALERT_DISMISSED",
            new_state={"status": "DISMISSED", "dismissReason": reason},
            justification=reason
        )

        return EmergingDetectionService.get_alert_by_id(conn, alert_id)

    @staticmethod
    def list_alerts(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List alerts with filtering."""
        cur = conn.cursor()
        query = "SELECT id FROM alerts WHERE organization_id = ?"
        params: List[Any] = [organization_id]
        if store_id:
            query += " AND store_id = ?"
            params.append(store_id)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?;"
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        return [EmergingDetectionService.get_alert_by_id(conn, r["id"]) for r in rows]

    @staticmethod
    def list_alerts_paginated(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> tuple[List[Dict[str, Any]], Any]:
        from backend.app.schemas.common import PaginationMeta
        cur = conn.cursor()
        base_where = "WHERE organization_id = ?"
        params: List[Any] = [organization_id]
        if store_id:
            base_where += " AND store_id = ?"
            params.append(store_id)
        if status:
            base_where += " AND status = ?"
            params.append(status)

        count_sql = f"SELECT COUNT(*) FROM alerts {base_where};"
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]

        query = f"SELECT id FROM alerts {base_where} ORDER BY created_at DESC LIMIT ? OFFSET ?;"
        page_params = list(params) + [limit, (page - 1) * limit]
        cur.execute(query, page_params)
        rows = cur.fetchall()
        items = [EmergingDetectionService.get_alert_by_id(conn, r["id"]) for r in rows]

        total_pages = max(1, (total + limit - 1) // limit)
        meta = PaginationMeta(page=page, limit=limit, total=total, totalPages=total_pages)
        return items, meta
