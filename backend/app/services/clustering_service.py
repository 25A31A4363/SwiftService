import re
import uuid
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set

from backend.app.core.errors import NotFoundError
from backend.app.services.audit_service import AuditService

STOP_WORDS = {
    "the", "is", "at", "which", "on", "a", "an", "and", "or", "in", "to", "for", "of",
    "with", "as", "by", "from", "it", "this", "that", "there", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "not", "but", "very",
    "our", "my", "we", "they", "i", "you", "he", "she", "me", "him", "her", "us"
}

def tokenize(text: Any) -> Set[str]:
    """Tokenize and remove stop words."""
    if isinstance(text, dict):
        text = text.get("text", "") or text.get("value", "") or ""
    elif not isinstance(text, str):
        text = str(text) if text is not None else ""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    words = cleaned.split()
    return {w for w in words if len(w) > 2 and w not in STOP_WORDS}

def calculate_jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union if union > 0 else 0.0

def calculate_time_proximity(t1_iso: str, t2_iso: str, max_hours: float = 72.0) -> float:
    try:
        dt1 = datetime.fromisoformat(t1_iso.replace("Z", "+00:00"))
        dt2 = datetime.fromisoformat(t2_iso.replace("Z", "+00:00"))
        hours_diff = abs((dt1 - dt2).total_seconds()) / 3600.0
        if hours_diff > max_hours:
            return 0.0
        return max(0.0, 1.0 - (hours_diff / max_hours))
    except Exception:
        return 0.5

class ClusteringService:
    @staticmethod
    def extract_semantic_features(feedback_row: sqlite3.Row) -> Dict[str, Any]:
        """Extract domain taxonomy and tokens for similarity matching."""
        raw_text = feedback_row["raw_text"] or ""
        tokens = tokenize(raw_text)

        interp = {}
        if feedback_row["ai_interpretation"]:
            try:
                interp = json.loads(feedback_row["ai_interpretation"])
            except Exception:
                pass

        # Multilingual & Normalized Token Inclusion:
        # Include tokens from normalized_text or normalizedInterpretation so English,
        # Hindi, Tamil, Hinglish, etc. share canonical tokens (e.g. dairy, cooler, leak, water)
        normalized_str = ""
        try:
            if "normalized_text" in feedback_row.keys() and feedback_row["normalized_text"]:
                normalized_str = feedback_row["normalized_text"]
        except Exception:
            pass

        if not normalized_str and interp.get("normalizedInterpretation"):
            normalized_str = interp.get("normalizedInterpretation", "")

        if normalized_str:
            tokens.update(tokenize(normalized_str))

        category = interp.get("issueCategory", {}).get("value", "unknown")
        if category == "unknown" and interp.get("extractedIssue", {}).get("category"):
            category = interp["extractedIssue"]["category"]

        issue_type = interp.get("issueType", {}).get("value", "unknown")
        if issue_type == "unknown" and interp.get("extractedIssue", {}).get("issueType"):
            issue_type = interp["extractedIssue"]["issueType"]

        entity = interp.get("affectedEntity", {}).get("value", "unknown")
        if entity == "unknown" and interp.get("extractedIssue", {}).get("affectedEntity"):
            entity = interp["extractedIssue"]["affectedEntity"]

        location = interp.get("location", {}).get("value", "unknown")
        if location == "unknown" and interp.get("extractedIssue", {}).get("location"):
            location = interp["extractedIssue"]["location"]

        symptoms = interp.get("symptoms", [])

        # Add symptom words to tokens
        for s in symptoms:
            tokens.update(tokenize(s))

        return {
            "id": feedback_row["id"],
            "storeId": feedback_row["store_id"],
            "channelType": feedback_row["channel_type"],
            "submitterType": feedback_row["submitter_type"],
            "submittedAt": feedback_row["submitted_at"] or feedback_row["created_at"],
            "rawText": raw_text,
            "category": category,
            "issueType": issue_type,
            "entity": entity,
            "location": location,
            "tokens": tokens,
            "confidence": interp.get("overallConfidence", interp.get("confidence", 0.7))
        }

    @staticmethod
    def calculate_pairwise_similarity(feat_a: Dict[str, Any], feat_b: Dict[str, Any]) -> tuple[float, str]:
        """
        Calculate multi-factor similarity between two feedback records:
        - Category & issue type match (weight 0.35)
        - Token/symptom Jaccard overlap (weight 0.35)
        - Location / store alignment (weight 0.15)
        - Temporal proximity (weight 0.15)
        Returns: (similarity_score, correlation_type)
        """
        # If both categories are known and distinct, strongly dampen similarity
        cat_match = 0.0
        if feat_a["category"] != "unknown" and feat_b["category"] != "unknown":
            if feat_a["category"] == feat_b["category"]:
                cat_match = 0.7
                if feat_a["issueType"] != "unknown" and feat_a["issueType"] == feat_b["issueType"]:
                    cat_match = 1.0
            else:
                cat_match = 0.0
        else:
            cat_match = 0.5

        token_sim = calculate_jaccard_similarity(feat_a["tokens"], feat_b["tokens"])

        # Location alignment
        loc_score = 0.0
        if feat_a["storeId"] == feat_b["storeId"]:
            loc_score = 0.7
            if (feat_a["location"] != "unknown" and feat_b["location"] != "unknown" and
                    feat_a["location"].lower() == feat_b["location"].lower()):
                loc_score = 1.0
        else:
            loc_score = 0.1  # Different store

        # Temporal proximity (within 72 hours)
        time_score = calculate_time_proximity(feat_a["submittedAt"], feat_b["submittedAt"], max_hours=72.0)

        # Composite score
        total_score = (0.35 * cat_match) + (0.35 * token_sim) + (0.15 * loc_score) + (0.15 * time_score)
        total_score = round(min(1.0, max(0.0, total_score)), 3)

        if total_score >= 0.65:
            corr_type = "SAME_ISSUE"
        elif total_score >= 0.40:
            corr_type = "RELATED_ISSUE"
        else:
            corr_type = "UNRELATED"

        return total_score, corr_type

    @staticmethod
    def generate_grounded_cluster_summary(
        items: List[Dict[str, Any]],
        category: str,
        store_id: Optional[str]
    ) -> tuple[str, str]:
        """
        Generate grounded title and summary based strictly on member evidence.
        ZERO LLM invention of facts.
        """
        if not items:
            return "Unassigned Incident", "No member observations recorded."

        # Find most frequent entity and location
        entities = [i["entity"] for i in items if i["entity"] != "unknown"]
        locations = [i["location"] for i in items if i["location"] != "unknown"]

        top_entity = max(set(entities), key=entities.count) if entities else None
        top_location = max(set(locations), key=locations.count) if locations else None

        channels = list({i["channelType"] for i in items})
        _submitters = list({i["submitterType"] for i in items})
        count = len(items)

        # Grounded Title
        category_clean = category.replace("_", " ").title()
        if top_entity and top_location:
            title = f"{category_clean}: {top_entity} in {top_location}"
        elif top_entity:
            title = f"{category_clean}: {top_entity}"
        elif top_location:
            title = f"{category_clean} reported at {top_location}"
        else:
            title = f"Operational {category_clean} Cluster"

        # Grounded Empirical Summary
        quotes = [f'"{i["rawText"].strip()}" ({i["channelType"]})' for i in items[:3]]
        quotes_str = "; ".join(quotes)
        if len(items) > 3:
            quotes_str += f"; and {len(items) - 3} additional report(s)"

        summary = (
            f"Cluster synthesizes {count} empirical report(s) from {len(channels)} distinct source channel(s) "
            f"({', '.join(channels)}). "
            f"Reported evidence: {quotes_str}. "
            f"Operational context: entity '{top_entity or 'unspecified'}', location '{top_location or 'unspecified'}'."
        )

        return title, summary

    @staticmethod
    def discover_and_cluster_feedback(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        time_window_hours: int = 72,
        similarity_threshold: float = 0.65,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Run cross-source semantic clustering on unclustered or active feedback items.
        Groups feedback into grounded clusters without forcing unrelated items together.
        """
        cur = conn.cursor()
        query = """
            SELECT fi.* FROM feedback_items fi
            WHERE fi.organization_id = ?
        """
        params: List[Any] = [organization_id]
        if store_id:
            query += " AND fi.store_id = ?"
            params.append(store_id)

        # Rolling time window filter
        since_time = (datetime.now(timezone.utc) - timedelta(hours=time_window_hours)).isoformat()
        query += " AND fi.submitted_at >= ? ORDER BY fi.submitted_at DESC LIMIT 150;"
        params.append(since_time)

        cur.execute(query, params)
        rows = cur.fetchall()
        if not rows:
            return []

        # Extract features for all feedback
        features = [ClusteringService.extract_semantic_features(r) for r in rows]

        # Greedy / agglomerative threshold clustering
        clusters: List[List[Dict[str, Any]]] = []
        assigned_ids: Set[str] = set()

        for i, feat_a in enumerate(features):
            if feat_a["id"] in assigned_ids:
                continue

            current_cluster = [feat_a]
            assigned_ids.add(feat_a["id"])

            for j, feat_b in enumerate(features):
                if feat_b["id"] in assigned_ids:
                    continue

                sim_score, corr_type = ClusteringService.calculate_pairwise_similarity(feat_a, feat_b)
                if sim_score >= similarity_threshold and corr_type == "SAME_ISSUE":
                    current_cluster.append(feat_b)
                    assigned_ids.add(feat_b["id"])

            # Only form multi-item clusters or keep high-severity singletons
            clusters.append(current_cluster)

        now = datetime.now(timezone.utc).isoformat()
        saved_cluster_ids = []

        for group in clusters:
            # Determine dominant category
            categories = [item["category"] for item in group if item["category"] != "unknown"]
            dominant_category = max(set(categories), key=categories.count) if categories else "EQUIPMENT_FAILURE"

            cluster_store_id = group[0]["storeId"] if all(item["storeId"] == group[0]["storeId"] for item in group) else None

            title, summary = ClusteringService.generate_grounded_cluster_summary(
                group, dominant_category, cluster_store_id
            )

            # Calculate quality and confidence
            avg_conf = sum(item["confidence"] for item in group) / len(group)
            source_diversity = len({item["channelType"] for item in group})
            # Quality score boosts with source diversity and sample size
            quality_score = min(1.0, round((0.6 * avg_conf) + (0.2 * min(1.0, len(group) / 4.0)) + (0.2 * min(1.0, source_diversity / 2.0)), 2))

            timestamps = [item["submittedAt"] for item in group]
            earliest_t = min(timestamps)
            latest_t = max(timestamps)

            top_entities = [i["entity"] for i in group if i["entity"] != "unknown"]
            top_locations = [i["location"] for i in group if i["location"] != "unknown"]

            cluster_id = f"cl-{uuid.uuid4().hex[:10]}"

            cur.execute("""
                INSERT INTO issue_clusters (
                    id, organization_id, store_id, title, category, summary,
                    status, confidence_score, quality_score, primary_entity,
                    primary_location, earliest_feedback_at, latest_feedback_at,
                    feedback_count, source_diversity_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                cluster_id, organization_id, cluster_store_id, title, dominant_category, summary,
                round(avg_conf, 2), quality_score,
                top_entities[0] if top_entities else None,
                top_locations[0] if top_locations else None,
                earliest_t, latest_t, len(group), source_diversity, now, now
            ))

            # Insert cluster feedback links
            for item in group:
                sim, corr = (1.0, "SAME_ISSUE") if item["id"] == group[0]["id"] else ClusteringService.calculate_pairwise_similarity(group[0], item)
                cur.execute("""
                    INSERT OR REPLACE INTO cluster_feedback_links (
                        cluster_id, feedback_item_id, similarity_score, correlation_type, added_by, created_at
                    ) VALUES (?, ?, ?, ?, 'SYSTEM_AI', ?);
                """, (cluster_id, item["id"], sim, corr, now))

            saved_cluster_ids.append(cluster_id)

        AuditService.record_audit(
            conn=conn,
            organization_id=organization_id,
            user_id=user_id,
            entity_type="ISSUE_CLUSTER",
            entity_id="BATCH_DISCOVERY",
            action="CLUSTERING_RUN_COMPLETED",
            new_state={"clustersGenerated": len(saved_cluster_ids), "feedbackProcessed": len(rows)}
        )

        return [ClusteringService.get_cluster_details(conn, cid) for cid in saved_cluster_ids]

    @staticmethod
    def get_cluster_details(conn: sqlite3.Connection, cluster_id: str) -> Dict[str, Any]:
        """Fetch full cluster data, quality score, and linked member evidence."""
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, s.name as store_name
            FROM issue_clusters c
            LEFT JOIN stores s ON c.store_id = s.id
            WHERE c.id = ?;
        """, (cluster_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError("IssueCluster", cluster_id)

        # Fetch members
        cur.execute("""
            SELECT l.similarity_score, l.correlation_type, fi.*
            FROM cluster_feedback_links l
            JOIN feedback_items fi ON l.feedback_item_id = fi.id
            WHERE l.cluster_id = ?
            ORDER BY l.similarity_score DESC;
        """, (cluster_id,))
        member_rows = cur.fetchall()

        members = []
        sources = set()
        for m in member_rows:
            sources.add(m["channel_type"])
            members.append({
                "feedbackItemId": m["id"],
                "similarityScore": m["similarity_score"],
                "correlationType": m["correlation_type"],
                "rawText": m["raw_text"],
                "channelType": m["channel_type"],
                "submitterType": m["submitter_type"],
                "submittedAt": m["submitted_at"] or m["created_at"],
                "evidenceExcerpt": m["raw_text"][:120]
            })

        return {
            "id": row["id"],
            "organizationId": row["organization_id"],
            "storeId": row["store_id"],
            "storeName": row["store_name"],
            "title": row["title"],
            "category": row["category"],
            "summary": row["summary"],
            "status": row["status"],
            "confidenceScore": row["confidence_score"],
            "qualityScore": row["quality_score"],
            "primaryEntity": row["primary_entity"],
            "primaryLocation": row["primary_location"],
            "feedbackCount": row["feedback_count"],
            "sourceDiversityCount": row["source_diversity_count"],
            "sources": list(sources),
            "earliestFeedbackAt": row["earliest_feedback_at"],
            "latestFeedbackAt": row["latest_feedback_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "members": members
        }

    @staticmethod
    def merge_clusters(
        conn: sqlite3.Connection,
        primary_cluster_id: str,
        secondary_cluster_id: str,
        merged_title: Optional[str] = None,
        justification: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Human operator merges two related clusters into one primary cluster."""
        cur = conn.cursor()
        c1 = ClusteringService.get_cluster_details(conn, primary_cluster_id)
        c2 = ClusteringService.get_cluster_details(conn, secondary_cluster_id)

        now = datetime.now(timezone.utc).isoformat()

        # Reassign all member links from secondary to primary
        cur.execute("""
            INSERT OR REPLACE INTO cluster_feedback_links (cluster_id, feedback_item_id, similarity_score, correlation_type, added_by, created_at)
            SELECT ?, feedback_item_id, similarity_score, correlation_type, 'HUMAN_OPERATOR', ?
            FROM cluster_feedback_links WHERE cluster_id = ?;
        """, (primary_cluster_id, now, secondary_cluster_id))

        cur.execute("DELETE FROM cluster_feedback_links WHERE cluster_id = ?;", (secondary_cluster_id,))

        # Mark secondary cluster as MERGED
        cur.execute("""
            UPDATE issue_clusters
            SET status = 'MERGED', merged_into_cluster_id = ?, updated_at = ?
            WHERE id = ?;
        """, (primary_cluster_id, now, secondary_cluster_id))

        # Recompute primary cluster summary & count
        cur.execute("SELECT COUNT(*) as cnt FROM cluster_feedback_links WHERE cluster_id = ?;", (primary_cluster_id,))
        total_cnt = cur.fetchone()["cnt"]

        final_title = merged_title or f"{c1['title']} + {c2['title']}"

        cur.execute("""
            UPDATE issue_clusters
            SET title = ?, feedback_count = ?, updated_at = ?
            WHERE id = ?;
        """, (final_title, total_cnt, now, primary_cluster_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=c1["organizationId"],
            user_id=user_id,
            entity_type="ISSUE_CLUSTER",
            entity_id=primary_cluster_id,
            action="CLUSTERS_MERGED",
            new_state={"mergedSecondaryId": secondary_cluster_id, "newCount": total_cnt},
            justification=justification
        )

        return ClusteringService.get_cluster_details(conn, primary_cluster_id)

    @staticmethod
    def split_cluster(
        conn: sqlite3.Connection,
        cluster_id: str,
        feedback_ids_to_eject: List[str],
        new_cluster_title: Optional[str] = None,
        justification: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Human operator splits a cluster by ejecting specified feedback items into a new or unclustered set."""
        cur = conn.cursor()
        orig = ClusteringService.get_cluster_details(conn, cluster_id)

        now = datetime.now(timezone.utc).isoformat()
        new_cluster_id = f"cl-{uuid.uuid4().hex[:10]}"
        new_title = new_cluster_title or f"Split: {orig['title']} (Segregated)"

        # Create new cluster for ejected items
        cur.execute("""
            INSERT INTO issue_clusters (
                id, organization_id, store_id, title, category, summary,
                status, confidence_score, quality_score, feedback_count,
                source_diversity_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'Human-split cluster segregated from original group.', 'ACTIVE', 0.85, 0.80, ?, 1, ?, ?);
        """, (new_cluster_id, orig["organizationId"], orig["storeId"], new_title, orig["category"], len(feedback_ids_to_eject), now, now))

        for fid in feedback_ids_to_eject:
            cur.execute("""
                UPDATE cluster_feedback_links
                SET cluster_id = ?, added_by = 'HUMAN_SPLIT', created_at = ?
                WHERE cluster_id = ? AND feedback_item_id = ?;
            """, (new_cluster_id, now, cluster_id, fid))

        # Recompute remaining count on original cluster
        cur.execute("SELECT COUNT(*) as cnt FROM cluster_feedback_links WHERE cluster_id = ?;", (cluster_id,))
        rem_cnt = cur.fetchone()["cnt"]
        cur.execute("UPDATE issue_clusters SET feedback_count = ?, updated_at = ? WHERE id = ?;", (rem_cnt, now, cluster_id))

        AuditService.record_audit(
            conn=conn,
            organization_id=orig["organizationId"],
            user_id=user_id,
            entity_type="ISSUE_CLUSTER",
            entity_id=cluster_id,
            action="CLUSTER_SPLIT",
            new_state={"ejectedIds": feedback_ids_to_eject, "newClusterId": new_cluster_id, "remainingCount": rem_cnt},
            justification=justification
        )

        return ClusteringService.get_cluster_details(conn, new_cluster_id)

    @staticmethod
    def update_cluster(
        conn: sqlite3.Connection,
        cluster_id: str,
        title: Optional[str] = None,
        category: Optional[str] = None,
        primary_location: Optional[str] = None,
        primary_entity: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Human operator corrects cluster metadata."""
        cur = conn.cursor()
        orig = ClusteringService.get_cluster_details(conn, cluster_id)

        updates = []
        params = []
        if title:
            updates.append("title = ?")
            params.append(title)
        if category:
            updates.append("category = ?")
            params.append(category)
        if primary_location:
            updates.append("primary_location = ?")
            params.append(primary_location)
        if primary_entity:
            updates.append("primary_entity = ?")
            params.append(primary_entity)

        if not updates:
            return orig

        now = datetime.now(timezone.utc).isoformat()
        updates.append("updated_at = ?")
        params.append(now)
        params.append(cluster_id)

        sql = f"UPDATE issue_clusters SET {', '.join(updates)} WHERE id = ?;"
        cur.execute(sql, params)

        AuditService.record_audit(
            conn=conn,
            organization_id=orig["organizationId"],
            user_id=user_id,
            entity_type="ISSUE_CLUSTER",
            entity_id=cluster_id,
            action="CLUSTER_UPDATED",
            new_state={"title": title, "category": category}
        )

        return ClusteringService.get_cluster_details(conn, cluster_id)

    @staticmethod
    def list_clusters(
        conn: sqlite3.Connection,
        organization_id: str,
        store_id: Optional[str] = None,
        status: Optional[str] = "ACTIVE",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List active clusters for an organization/store."""
        cur = conn.cursor()
        query = "SELECT id FROM issue_clusters WHERE organization_id = ?"
        params: List[Any] = [organization_id]
        if store_id:
            query += " AND (store_id = ? OR store_id IS NULL)"
            params.append(store_id)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY quality_score DESC, updated_at DESC LIMIT ?;"
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        return [ClusteringService.get_cluster_details(conn, r["id"]) for r in rows]
