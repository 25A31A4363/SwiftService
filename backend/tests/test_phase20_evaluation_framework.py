"""
Unit and regression test suite for Phase 20: R5 Evaluation Framework.

Verifies:
1. Controlled synthetic benchmark dataset manifests & labeling disclaimers.
2. Statistical metric calculator functions in evaluation/metrics.py.
3. All 12 operational dimension evaluators individually.
4. EvaluationRunner end-to-end suite execution & filtering.
5. EvaluationReporter Markdown & JSON artifact generation.
6. Evaluation REST API endpoints (/api/v1/evaluation).
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.evaluation.schemas import (
    EvaluationDimension,
    MetricNature,
    MetricResult,
    DimensionEvaluationResult,
    EvaluationSuiteReport
)
from backend.app.evaluation.metrics import (
    compute_accuracy,
    compute_classification_metrics,
    compute_token_overlap_f1,
    compute_cluster_purity,
    compute_rand_index,
    compute_cross_cluster_leakage_rate,
    compute_detection_sensitivity,
    compute_false_alert_rate,
    compute_monotonicity_compliance,
    compute_grounding_ratio,
    compute_hallucination_rate
)
from backend.app.evaluation.datasets import load_dataset, list_available_datasets
from backend.app.evaluation.evaluators import ALL_EVALUATORS
from backend.app.evaluation.evaluators.extraction_evaluator import ExtractionQualityEvaluator
from backend.app.evaluation.evaluators.followup_evaluator import FollowUpRelevanceEvaluator
from backend.app.evaluation.evaluators.clustering_evaluator import ClusteringQualityEvaluator
from backend.app.evaluation.evaluators.emerging_evaluator import EmergingDetectionEvaluator
from backend.app.evaluation.evaluators.false_alert_evaluator import FalseAlertRateEvaluator
from backend.app.evaluation.evaluators.priority_evaluator import PriorityConsistencyEvaluator
from backend.app.evaluation.evaluators.routing_evaluator import RoutingAccuracyEvaluator
from backend.app.evaluation.evaluators.grounding_evaluator import EvidenceGroundingEvaluator
from backend.app.evaluation.evaluators.hallucination_evaluator import HallucinationResistanceEvaluator
from backend.app.evaluation.evaluators.outcome_evaluator import OutcomeMeasurementEvaluator
from backend.app.evaluation.evaluators.multilingual_evaluator import MultilingualBehaviorEvaluator
from backend.app.evaluation.evaluators.reliability_evaluator import SystemReliabilityEvaluator
from backend.app.evaluation.runner import EvaluationRunner
from backend.app.evaluation.reporter import EvaluationReporter


# =============================================================================
# 1. DATASET MANIFEST & LABELING VERIFICATION
# =============================================================================
class TestEvaluationDatasets:
    def test_all_datasets_are_strictly_labeled_as_synthetic(self):
        manifests = list_available_datasets()
        assert len(manifests) >= 10, f"Expected at least 10 benchmark datasets, found {len(manifests)}"

        for m in manifests:
            assert m["synthetic"] is True, f"Dataset {m['filename']} is not marked synthetic"
            assert "SYNTHETIC" in m["label"], f"Dataset {m['filename']} label must declare synthetic nature"
            assert len(m["disclaimer"]) > 20, f"Dataset {m['filename']} missing explicit caveat disclaimer"
            assert m["sampleCount"] > 0, f"Dataset {m['filename']} must contain test items"

    def test_load_dataset_helper_loads_valid_json(self):
        data = load_dataset("synthetic_feedback_extraction.json")
        assert "_metadata" in data
        assert "cases" in data
        assert len(data["cases"]) == 20


# =============================================================================
# 2. STATISTICAL METRIC CALCULATOR UNIT TESTS
# =============================================================================
class TestMetricCalculators:
    def test_compute_accuracy(self):
        assert compute_accuracy(["A", "B", "C"], ["A", "B", "C"]) == 1.0
        assert compute_accuracy(["A", "B", "C"], ["A", "X", "C"]) == 0.6667
        assert compute_accuracy([], []) == 0.0

    def test_compute_classification_metrics(self):
        y_true = ["CAT_A", "CAT_A", "CAT_B", "CAT_B"]
        y_pred = ["CAT_A", "CAT_B", "CAT_B", "CAT_B"]
        res = compute_classification_metrics(y_true, y_pred)
        assert res["accuracy"] == 0.75
        assert 0.0 <= res["precision"] <= 1.0
        assert 0.0 <= res["recall"] <= 1.0
        assert 0.0 <= res["f1"] <= 1.0

    def test_compute_token_overlap_f1(self):
        f1 = compute_token_overlap_f1({"aisle", "cooler"}, {"cooler", "aisle"})
        assert f1 == 1.0
        f1_partial = compute_token_overlap_f1({"aisle", "cooler"}, {"cooler", "scanner"})
        assert 0.4 < f1_partial < 0.6
        assert compute_token_overlap_f1(set(), set()) == 1.0

    def test_clustering_metrics(self):
        # Perfect clustering
        predicted_clusters = {
            "cluster_1": ["i1", "i2"],
            "cluster_2": ["i3", "i4"],
            "cluster_3": ["i5", "i6"]
        }
        ground_truth = {
            "i1": "topic_a",
            "i2": "topic_a",
            "i3": "topic_b",
            "i4": "topic_b",
            "i5": "topic_c",
            "i6": "topic_c"
        }
        purity = compute_cluster_purity(predicted_clusters, ground_truth)
        rand_idx = compute_rand_index(predicted_clusters, ground_truth)
        leakage = compute_cross_cluster_leakage_rate(predicted_clusters, ground_truth)

        assert purity == 1.0
        assert rand_idx == 1.0
        assert leakage == 0.0

    def test_detection_sensitivity_and_false_alert_rate(self):
        # 8 True Positives, 2 False Negatives -> TPR = 8 / 10 = 0.8
        tpr = compute_detection_sensitivity(true_positives=8, false_negatives=2)
        assert tpr == 0.8

        # 1 False Positive, 9 True Negatives -> FPR = 1 / 10 = 0.1
        fpr = compute_false_alert_rate(false_positives=1, true_negatives=9)
        assert fpr == 0.1

    def test_monotonicity_compliance(self):
        scores = [(40.0, 30.0), (30.0, 20.0), (20.0, 10.0)]
        assert compute_monotonicity_compliance(scores) == 1.0
        non_mono = [(10.0, 40.0), (5.0, 20.0)]
        assert compute_monotonicity_compliance(non_mono) == 0.0

    def test_grounding_and_hallucination_rates(self):
        assert compute_grounding_ratio(8, 10) == 0.8
        assert compute_hallucination_rate(2, 10) == 0.2
        assert compute_hallucination_rate(0, 10) == 0.0


# =============================================================================
# 3. INDIVIDUAL DIMENSION EVALUATOR TESTS (ALL 12 DIMENSIONS)
# =============================================================================
class TestDimensionEvaluators:
    def test_feedback_extraction_evaluator(self):
        evaluator = ExtractionQualityEvaluator()
        assert evaluator.dimension == EvaluationDimension.FEEDBACK_EXTRACTION_QUALITY
        res = evaluator.evaluate()
        assert isinstance(res, DimensionEvaluationResult)
        assert res.score >= 80.0
        assert res.passed is True
        assert len(res.metrics) == 5
        assert len(res.caveats) > 0

    def test_followup_question_evaluator(self):
        evaluator = FollowUpRelevanceEvaluator()
        assert evaluator.dimension == EvaluationDimension.FOLLOWUP_QUESTION_RELEVANCE
        res = evaluator.evaluate()
        assert res.score >= 80.0
        assert res.passed is True
        assert len(res.metrics) == 3

    def test_semantic_clustering_evaluator(self):
        evaluator = ClusteringQualityEvaluator()
        assert evaluator.dimension == EvaluationDimension.SEMANTIC_CLUSTERING_QUALITY
        res = evaluator.evaluate()
        assert res.score >= 85.0
        assert res.passed is True
        assert len(res.metrics) == 3

    def test_emerging_detection_evaluator(self):
        evaluator = EmergingDetectionEvaluator()
        assert evaluator.dimension == EvaluationDimension.EMERGING_ISSUE_DETECTION
        res = evaluator.evaluate()
        assert res.score >= 85.0
        assert res.passed is True

    def test_false_alert_evaluator(self):
        evaluator = FalseAlertRateEvaluator()
        assert evaluator.dimension == EvaluationDimension.FALSE_ALERT_RATE
        res = evaluator.evaluate()
        assert res.score == 100.0
        assert res.passed is True

    def test_priority_consistency_evaluator(self):
        evaluator = PriorityConsistencyEvaluator()
        assert evaluator.dimension == EvaluationDimension.PRIORITY_CONSISTENCY
        res = evaluator.evaluate()
        assert res.score >= 90.0
        assert res.passed is True

    def test_routing_accuracy_evaluator(self):
        evaluator = RoutingAccuracyEvaluator()
        assert evaluator.dimension == EvaluationDimension.ROUTING_ACCURACY
        res = evaluator.evaluate()
        assert res.score >= 85.0
        assert res.passed is True

    def test_evidence_grounding_evaluator(self):
        evaluator = EvidenceGroundingEvaluator()
        assert evaluator.dimension == EvaluationDimension.EVIDENCE_GROUNDING
        res = evaluator.evaluate()
        assert res.score >= 85.0
        assert res.passed is True

    def test_ai_hallucination_evaluator(self):
        evaluator = HallucinationResistanceEvaluator()
        assert evaluator.dimension == EvaluationDimension.AI_HALLUCINATION_RESISTANCE
        res = evaluator.evaluate()
        assert res.score == 100.0
        assert res.passed is True

    def test_outcome_measurement_evaluator(self):
        evaluator = OutcomeMeasurementEvaluator()
        assert evaluator.dimension == EvaluationDimension.OUTCOME_MEASUREMENT_CORRECTNESS
        res = evaluator.evaluate()
        assert res.score == 100.0
        assert res.passed is True

    def test_multilingual_behavior_evaluator(self):
        evaluator = MultilingualBehaviorEvaluator()
        assert evaluator.dimension == EvaluationDimension.MULTILINGUAL_BEHAVIOR
        res = evaluator.evaluate()
        assert res.score == 100.0
        assert res.passed is True

    def test_system_reliability_evaluator(self):
        evaluator = SystemReliabilityEvaluator()
        assert evaluator.dimension == EvaluationDimension.SYSTEM_RELIABILITY
        res = evaluator.evaluate()
        assert res.score == 100.0
        assert res.passed is True


# =============================================================================
# 4. EVALUATION RUNNER & REPORTER TESTS
# =============================================================================
class TestRunnerAndReporter:
    def test_runner_executes_all_evaluators_and_stores_report(self):
        report = EvaluationRunner.run_all()
        assert isinstance(report, EvaluationSuiteReport)
        assert report.overall_score >= 90.0
        assert report.total_dimensions == 12
        assert report.passed_dimensions == 12
        assert report.summary_status == "PASS"

        last = EvaluationRunner.get_last_report()
        assert last is not None
        assert last.run_id == report.run_id

    def test_runner_can_filter_specific_dimensions(self):
        filtered_report = EvaluationRunner.run_all(dimensions=[
            "ROUTING_ACCURACY",
            "FALSE_ALERT_RATE"
        ])
        assert filtered_report.total_dimensions == 2
        assert len(filtered_report.dimension_results) == 2

    def test_reporter_renders_markdown_with_caveats(self):
        report = EvaluationRunner.run_all()
        md = EvaluationReporter.render_markdown(report)
        assert "# R5 Operational Intelligence Platform — System Evaluation Report" in md
        assert "EVALUATION BENCHMARK CAVEATS & SCOPE RESTRICTIONS" in md
        assert "Controlled Synthetic Datasets" in md
        assert "Executive Evaluation Scorecard" in md
        assert "Feedback Extraction Quality" in md

    def test_reporter_saves_reports_to_disk(self, tmp_path):
        report = EvaluationRunner.run_all()
        saved = EvaluationReporter.save_reports(report, output_dir=str(tmp_path))
        assert os.path.exists(saved["markdownPath"])
        assert os.path.exists(saved["jsonPath"])

        with open(saved["jsonPath"], "r", encoding="utf-8") as f:
            saved_json = json.load(f)
            assert saved_json["run_id"] == report.run_id
            assert saved_json["overall_score"] == report.overall_score


# =============================================================================
# 5. REST API ROUTER ENDPOINT TESTS
# =============================================================================
class TestEvaluationRouterAPI:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        from backend.app.core.security import create_access_token
        token = create_access_token({
            "userId": "usr-admin",
            "email": "orgadmin@apex.com",
            "role": "ORGANIZATION_ADMIN",
            "organizationId": "org-apex-01"
        })
        return {"Authorization": f"Bearer {token}"}

    def test_api_datasets_endpoint(self, client, auth_headers):
        resp = client.get("/api/v1/evaluation/datasets", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        datasets = data["data"]
        assert len(datasets) >= 10
        assert datasets[0]["synthetic"] is True

    def test_api_run_evaluation_endpoint(self, client, auth_headers):
        payload = {"dimensions": ["FALSE_ALERT_RATE", "SYSTEM_RELIABILITY"]}
        resp = client.post("/api/v1/evaluation/run", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        report = data["data"]
        assert report["total_dimensions"] == 2
        assert report["overall_score"] == 100.0

    def test_api_summary_endpoint(self, client, auth_headers):
        # Trigger run first
        client.post("/api/v1/evaluation/run", json={}, headers=auth_headers)
        resp = client.get("/api/v1/evaluation/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        summary = data["data"]
        assert "overall_score" in summary
        assert "summary_status" in summary
        assert "dimension_results" in summary
        assert len(summary["dimension_results"]) == 12

    def test_api_markdown_report_endpoint(self, client, auth_headers):
        client.post("/api/v1/evaluation/run", json={}, headers=auth_headers)
        resp = client.get("/api/v1/evaluation/report/markdown", headers=auth_headers)
        assert resp.status_code == 200
        assert "# R5 Operational Intelligence Platform — System Evaluation Report" in resp.text
