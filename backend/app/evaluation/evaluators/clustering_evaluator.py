"""
R5 Operational Intelligence Platform - Phase 20: Semantic Clustering Quality Evaluator
Evaluates:
- Cluster Purity: Fraction of dominant true class items within predicted clusters
- Pairwise Rand Index: Agreement between ground truth groupings and algorithmic clusters
- Cross-Cluster Leakage Rate: Unrelated items mistakenly clustered together
"""

import sqlite3
from typing import Optional, List, Dict, Any, Set

from backend.app.evaluation.evaluators.base import BaseEvaluator
from backend.app.evaluation.schemas import (
    DimensionEvaluationResult,
    EvaluationDimension,
    MetricResult,
    MetricNature
)
from backend.app.evaluation.metrics import (
    compute_cluster_purity,
    compute_rand_index,
    compute_cross_cluster_leakage_rate
)
from backend.app.evaluation.datasets import load_dataset
from backend.app.services.ai_understanding_service import AIUnderstandingService
from backend.app.services.clustering_service import (
    ClusteringService,
    tokenize
)


class ClusteringQualityEvaluator(BaseEvaluator):
    @property
    def dimension(self) -> EvaluationDimension:
        return EvaluationDimension.SEMANTIC_CLUSTERING_QUALITY

    @property
    def dimension_name(self) -> str:
        return "Semantic Clustering Quality"

    def evaluate(self, conn: Optional[sqlite3.Connection] = None) -> DimensionEvaluationResult:
        data = load_dataset("synthetic_clustering.json")
        cases = data.get("cases", [])
        if not cases:
            return DimensionEvaluationResult(
                dimension=self.dimension,
                dimension_name=self.dimension_name,
                score=0.0,
                passed=False,
                summary="No synthetic clustering cases found in benchmark dataset",
                caveats=["Empty evaluation dataset"]
            )

        ground_truth: Dict[str, str] = {}
        features: Dict[str, Dict[str, Any]] = {}

        # 1. Extract semantic features for each test item
        for item in cases:
            item_id = item["id"]
            ground_truth[item_id] = item["groundTruthCluster"]
            raw_text = item["rawText"]
            extracted = AIUnderstandingService.extract_understanding(raw_text)

            cat = extracted["issueCategory"]["value"]
            itype = extracted["issueType"]["value"]
            loc = extracted["location"]["value"]
            ent = extracted["affectedEntity"]["value"]
            tokens = tokenize(raw_text)

            features[item_id] = {
                "id": item_id,
                "storeId": item.get("storeId", "store-104"),
                "channelType": "MANUAL_ENTRY",
                "submitterType": "CUSTOMER",
                "submittedAt": "2026-10-17T10:00:00+00:00",
                "rawText": raw_text,
                "category": cat,
                "issueType": itype,
                "entity": ent,
                "location": loc,
                "tokens": tokens,
                "confidence": extracted.get("overallConfidence", 0.85)
            }

        # 2. Compute pairwise similarity matrix and group into clusters via threshold (0.45)
        item_ids = list(features.keys())
        adj: Dict[str, Set[str]] = {i: set() for i in item_ids}

        for i in range(len(item_ids)):
            for j in range(i + 1, len(item_ids)):
                id_a = item_ids[i]
                id_b = item_ids[j]
                sim, corr = ClusteringService.calculate_pairwise_similarity(features[id_a], features[id_b])
                if sim >= 0.45:
                    adj[id_a].add(id_b)
                    adj[id_b].add(id_a)

        # 3. Find connected components to form predicted clusters
        visited = set()
        predicted_clusters: Dict[str, List[str]] = {}
        c_idx = 1

        for item_id in item_ids:
            if item_id not in visited:
                cluster_members = []
                queue = [item_id]
                visited.add(item_id)
                while queue:
                    curr = queue.pop(0)
                    cluster_members.append(curr)
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                predicted_clusters[f"cluster_{c_idx}"] = cluster_members
                c_idx += 1

        # 4. Compute clustering metrics
        purity = compute_cluster_purity(predicted_clusters, ground_truth)
        rand_idx = compute_rand_index(predicted_clusters, ground_truth)
        leakage_rate = compute_cross_cluster_leakage_rate(predicted_clusters, ground_truth)

        # Dimension score: combination of purity, rand index, and inverse leakage
        overall_score = round(
            (0.45 * purity + 0.45 * rand_idx + 0.10 * max(0.0, 1.0 - leakage_rate)) * 100.0,
            2
        )

        metrics = [
            MetricResult(
                name="cluster_purity",
                label="Cluster Purity",
                nature=MetricNature.QUANTITATIVE,
                value=purity,
                unit="ratio",
                threshold=0.80,
                passed=purity >= 0.80,
                description="Fraction of dominant true operational topics correctly aligned in predicted clusters"
            ),
            MetricResult(
                name="pairwise_rand_index",
                label="Pairwise Rand Index",
                nature=MetricNature.QUANTITATIVE,
                value=rand_idx,
                unit="ratio",
                threshold=0.80,
                passed=rand_idx >= 0.80,
                description="Pairwise clustering agreement between ground truth groupings and algorithmic clusters"
            ),
            MetricResult(
                name="cross_cluster_leakage_rate",
                label="Cross-Cluster Leakage Rate",
                nature=MetricNature.QUANTITATIVE,
                value=leakage_rate,
                unit="ratio",
                threshold=0.15,
                passed=leakage_rate <= 0.15,
                description="Proportion of unrelated operational issues mistakenly clustered together"
            )
        ]

        passed = all(m.passed for m in metrics)

        return DimensionEvaluationResult(
            dimension=self.dimension,
            dimension_name=self.dimension_name,
            score=overall_score,
            passed=passed,
            metrics=metrics,
            total_cases=len(cases),
            evaluated_cases=len(cases),
            summary=(
                f"Evaluated {len(cases)} items across {len(predicted_clusters)} clusters: "
                f"Purity={purity:.2f}, Rand Index={rand_idx:.2f}, Leakage Rate={leakage_rate:.2f}."
            ),
            caveats=[
                "Evaluated on synthetic distinct-department problem scenarios.",
                "Real retail clusters can have multi-problem overlaps (e.g., refrigeration failure causing slip hazard)."
            ]
        )
