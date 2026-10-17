import json
import sqlite3
from typing import List, Dict, Any

from backend.app.core.errors import NotFoundError

class EvidenceLineageService:
    @staticmethod
    def classify_statement(text: str, is_empirically_verified: bool = False) -> str:
        """
        Classifies an assertion into FACT, HYPOTHESIS, RECOMMENDATION, or UNKNOWN.
        Enforces strict epistemological grounding.
        """
        lower = text.lower()
        if any(w in lower for w in ["recommend", "should", "dispatch", "inspect", "replace", "action plan", "suggest"]):
            return "RECOMMENDATION"
        if any(w in lower for w in ["unknown", "unspecified", "uncertain", "missing", "unclear", "not provided"]):
            return "UNKNOWN"
        if any(w in lower for w in ["hypothesis", "possible", "suspected", "potential", "likely", "pending verification"]):
            return "HYPOTHESIS"
        if is_empirically_verified or any(w in lower for w in ["verified", "measured", "timestamp", "recorded quote"]):
            return "FACT"

        # By default, root-cause statements without technician verification are HYPOTHESIS
        return "HYPOTHESIS"

    @staticmethod
    def build_issue_lineage_graph(conn: sqlite3.Connection, issue_id: str) -> Dict[str, Any]:
        """
        Constructs the complete traceable operational lineage DAG:
        Feedback -> Extraction -> Investigation Q&A -> Issue / Cluster -> Alert -> Priority -> Action -> Resolution
        """
        cur = conn.cursor()
        cur.execute("SELECT * FROM issues WHERE id = ?;", (issue_id,))
        issue = cur.fetchone()
        if not issue:
            raise NotFoundError("Issue", issue_id)

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # 1. Issue Node
        issue_node_id = f"node-issue-{issue['id']}"
        nodes.append({
            "id": issue_node_id,
            "type": "ISSUE",
            "label": f"Incident: {issue['title']}",
            "claimType": "FACT",
            "confidence": issue["confidence_score"],
            "details": {
                "priorityScore": issue["priority_score"],
                "priorityTier": issue["priority_tier"],
                "status": issue["status"],
                "storeId": issue["store_id"],
                "feedbackCount": issue["feedback_count"]
            }
        })

        # 1b. Root Cause Hypothesis Node (Explicitly labeled HYPOTHESIS unless closed/verified)
        hypothesis_text = issue["root_cause_hypothesis"] or "Preliminary triage hypothesis pending technician diagnosis."
        hyp_claim_type = "FACT" if issue["status"] == "CLOSED" else "HYPOTHESIS"
        hyp_node_id = f"node-hyp-{issue['id']}"
        nodes.append({
            "id": hyp_node_id,
            "type": "DIAGNOSTIC_HYPOTHESIS",
            "label": f"Diagnostic: {hypothesis_text}",
            "claimType": hyp_claim_type,
            "confidence": issue["confidence_score"] * 0.9,
            "details": {
                "verifiable": True,
                "requiresFieldVerification": issue["status"] != "CLOSED",
                "hypothesis": hypothesis_text
            }
        })
        edges.append({
            "source": hyp_node_id,
            "target": issue_node_id,
            "relation": "DIAGNOSES"
        })

        # 2. Priority Breakdown Node
        factor_breakdown = {}
        if issue["factor_breakdown"]:
            try:
                factor_breakdown = json.loads(issue["factor_breakdown"])
            except Exception:
                pass

        priority_node_id = f"node-priority-{issue['id']}"
        nodes.append({
            "id": priority_node_id,
            "type": "PRIORITY_EVALUATION",
            "label": f"Score {issue['priority_score']} ({issue['priority_tier']})",
            "claimType": "FACT",  # Deterministic mathematical calculation
            "confidence": 1.0,
            "details": {
                "explanation": issue["prioritization_explanation"] or "Deterministic mathematical formula evaluation",
                "factors": factor_breakdown
            }
        })
        edges.append({
            "source": priority_node_id,
            "target": issue_node_id,
            "relation": "PRIORITIZES"
        })

        # 3. Cluster Node (if linked)
        if issue["cluster_id"]:
            cur.execute("SELECT * FROM issue_clusters WHERE id = ?;", (issue["cluster_id"],))
            cluster = cur.fetchone()
            if cluster:
                cluster_node_id = f"node-cluster-{cluster['id']}"
                nodes.append({
                    "id": cluster_node_id,
                    "type": "CLUSTER",
                    "label": f"Cluster: {cluster['title']}",
                    "claimType": "FACT",
                    "confidence": cluster["confidence_score"],
                    "details": {
                        "category": cluster["category"],
                        "summary": cluster["summary"],
                        "qualityScore": cluster["quality_score"],
                        "feedbackCount": cluster["feedback_count"]
                    }
                })
                edges.append({
                    "source": cluster_node_id,
                    "target": issue_node_id,
                    "relation": "AGGREGATES_INTO"
                })

        # 4. Member Feedback Items & Extraction Nodes
        cur.execute("""
            SELECT fi.* FROM issue_feedback_links ifl
            JOIN feedback_items fi ON ifl.feedback_item_id = fi.id
            WHERE ifl.issue_id = ?;
        """, (issue_id,))
        fb_rows = cur.fetchall()

        for fb in fb_rows:
            fb_node_id = f"node-fb-{fb['id']}"
            nodes.append({
                "id": fb_node_id,
                "type": "FEEDBACK",
                "label": f"Feedback ({fb['channel_type']}): \"{fb['raw_text'][:50]}...\"",
                "claimType": "FACT",  # Immutable verbatim evidence
                "confidence": 1.0,
                "details": {
                    "rawText": fb["raw_text"],
                    "channel": fb["channel_type"],
                    "submitter": fb["submitter_type"],
                    "submittedAt": fb["submitted_at"] or fb["created_at"]
                }
            })

            # Extraction Node
            interp = {}
            if fb["ai_interpretation"]:
                try:
                    interp = json.loads(fb["ai_interpretation"])
                except Exception:
                    pass

            ext_node_id = f"node-ext-{fb['id']}"
            nodes.append({
                "id": ext_node_id,
                "type": "EXTRACTION",
                "label": f"AI Facts: {interp.get('issueCategory', {}).get('value', 'unknown')}",
                "claimType": "FACT",
                "confidence": interp.get("overallConfidence", 0.8),
                "details": {
                    "category": interp.get("issueCategory", {}).get("value"),
                    "severity": interp.get("severity", {}).get("value"),
                    "location": interp.get("location", {}).get("value"),
                    "entity": interp.get("affectedEntity", {}).get("value")
                }
            })
            edges.append({
                "source": fb_node_id,
                "target": ext_node_id,
                "relation": "EXTRACTED_FROM"
            })
            edges.append({
                "source": ext_node_id,
                "target": issue_node_id,
                "relation": "SUPPORTS_INCIDENT"
            })

            # Investigation Q&A Nodes (Phase 5)
            cur.execute("""
                SELECT * FROM investigation_questions
                WHERE feedback_item_id = ? AND status = 'ANSWERED';
            """, (fb["id"],))
            q_rows = cur.fetchall()
            for q in q_rows:
                q_node_id = f"node-inv-{q['id']}"
                nodes.append({
                    "id": q_node_id,
                    "type": "INVESTIGATION",
                    "label": f"Clarification: {q['question_text']} -> {q['answer']}",
                    "claimType": "FACT",
                    "confidence": 1.0,
                    "details": {
                        "question": q["question_text"],
                        "answer": q["answer"],
                        "answeredAt": q["answered_at"]
                    }
                })
                edges.append({
                    "source": q_node_id,
                    "target": ext_node_id,
                    "relation": "ENRICHES"
                })

        # 5. Alert Nodes
        cur.execute("SELECT * FROM alerts WHERE issue_id = ?;", (issue_id,))
        alert_rows = cur.fetchall()
        for a in alert_rows:
            alert_node_id = f"node-alert-{a['id']}"
            nodes.append({
                "id": alert_node_id,
                "type": "ALERT",
                "label": f"Alert: {a['alert_type']} ({a['severity']})",
                "claimType": "FACT",
                "confidence": a["confidence"] or 0.85,
                "details": {
                    "message": a["message"],
                    "zscore": a["velocity_zscore"],
                    "baselineStatus": a["baseline_status"],
                    "whyGenerated": a["why_generated"]
                }
            })
            edges.append({
                "source": issue_node_id,
                "target": alert_node_id,
                "relation": "TRIGGERS_ALERT"
            })

        # 6. Action Plan & Recommendation Nodes
        cur.execute("SELECT * FROM action_plans WHERE issue_id = ?;", (issue_id,))
        action_rows = cur.fetchall()
        for act in action_rows:
            act_node_id = f"node-action-{act['id']}"
            nodes.append({
                "id": act_node_id,
                "type": "ACTION",
                "label": f"Action Plan: {act['recommended_action']}",
                "claimType": "RECOMMENDATION",
                "confidence": 0.90,
                "details": {
                    "action": act["recommended_action"],
                    "approvalStatus": act["approval_status"],
                    "slaDeadline": act["sla_deadline"]
                }
            })
            edges.append({
                "source": issue_node_id,
                "target": act_node_id,
                "relation": "RECOMMENDS_WORK_ORDER"
            })

            # 7. Resolution Node
            cur.execute("SELECT * FROM resolutions WHERE action_plan_id = ?;", (act["id"],))
            res_rows = cur.fetchall()
            for r in res_rows:
                res_node_id = f"node-res-{r['id']}"
                nodes.append({
                    "id": res_node_id,
                    "type": "RESOLUTION",
                    "label": f"Fix Verified: {r['verification_status']}",
                    "claimType": "FACT",
                    "confidence": 1.0,
                    "details": {
                        "notes": r["technician_notes"],
                        "resolvedAt": r["resolved_at"],
                        "verification": r["verification_status"]
                    }
                })
                edges.append({
                    "source": act_node_id,
                    "target": res_node_id,
                    "relation": "RESOLVED_BY"
                })

        # Counts
        facts_cnt = sum(1 for n in nodes if n["claimType"] == "FACT")
        hyp_cnt = sum(1 for n in nodes if n["claimType"] == "HYPOTHESIS")
        rec_cnt = sum(1 for n in nodes if n["claimType"] == "RECOMMENDATION")
        unk_cnt = sum(1 for n in nodes if n["claimType"] == "UNKNOWN")

        return {
            "rootId": issue_id,
            "rootType": "ISSUE",
            "nodes": nodes,
            "edges": edges,
            "factsCount": facts_cnt,
            "hypothesesCount": hyp_cnt,
            "recommendationsCount": rec_cnt,
            "unknownsCount": unk_cnt
        }

    @staticmethod
    def get_alert_evidence(conn: sqlite3.Connection, alert_id: str) -> Dict[str, Any]:
        """Provides full supporting evidence and explainability details for an alert."""
        cur = conn.cursor()
        cur.execute("SELECT * FROM alerts WHERE id = ?;", (alert_id,))
        alert = cur.fetchone()
        if not alert:
            raise NotFoundError("Alert", alert_id)

        issue_id = alert["issue_id"]
        lineage = EvidenceLineageService.build_issue_lineage_graph(conn, issue_id)

        sources = []
        if alert["sources_summary"]:
            try:
                sources = json.loads(alert["sources_summary"])
            except Exception:
                sources = [alert["sources_summary"]]

        uncertainties = []
        if alert["uncertainties"]:
            try:
                uncertainties = json.loads(alert["uncertainties"])
            except Exception:
                uncertainties = [alert["uncertainties"]]

        return {
            "alertId": alert_id,
            "issueId": issue_id,
            "what": alert["what"] or alert["message"],
            "whenOccurred": alert["created_at"],
            "whereZone": alert["where_zone"] or f"Store {alert['store_id']}",
            "observationCount": alert["observation_count"] or 1,
            "sources": sources,
            "baselineDiff": alert["baseline_diff"] or 0.0,
            "velocityZscore": alert["velocity_zscore"] or 0.0,
            "growthRate": alert["growth_rate"] or 0.0,
            "baselineStatus": alert["baseline_status"] or "NORMAL",
            "severity": alert["severity"],
            "urgency": alert["urgency"] or "MEDIUM",
            "confidence": alert["confidence"] or 0.85,
            "whyGenerated": alert["why_generated"] or alert["message"],
            "uncertainties": uncertainties,
            "lineageGraph": lineage
        }
