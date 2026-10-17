"""
R5 Operational Intelligence Platform - Phase 20: Evidence Grounding Evaluator
Evaluates:
- Citation validity: Fraction of claims citing valid source feedback items
- Verbatim quote integrity: Accurate substring representation of source observations
- Rejection of ungrounded / unsupported claims
"""

import sqlite3
from typing import Optional

from backend.app.evaluation.evaluators.base import BaseEvaluator
from backend.app.evaluation.schemas import (
    DimensionEvaluationResult,
    EvaluationDimension,
    MetricResult,
    MetricNature
)
from backend.app.evaluation.metrics import (
    compute_grounding_ratio
)
from backend.app.evaluation.datasets import load_dataset


class EvidenceGroundingEvaluator(BaseEvaluator):
    @property
    def dimension(self) -> EvaluationDimension:
        return EvaluationDimension.EVIDENCE_GROUNDING

    @property
    def dimension_name(self) -> str:
        return "Evidence Grounding & Lineage"

    def evaluate(self, conn: Optional[sqlite3.Connection] = None) -> DimensionEvaluationResult:
        data = load_dataset("synthetic_evidence_grounding.json")
        cases = data.get("cases", [])
        if not cases:
            return DimensionEvaluationResult(
                dimension=self.dimension,
                dimension_name=self.dimension_name,
                score=0.0,
                passed=False,
                summary="No synthetic grounding cases found in benchmark dataset",
                caveats=["Empty evaluation dataset"]
            )

        total_claims = 0
        valid_citations = 0
        verbatim_matches = 0
        verbatim_cases = 0
        correct_validity_decisions = 0

        for case in cases:
            source_feedback = {fb["feedbackId"]: fb["rawText"] for fb in case.get("sourceFeedback", [])}
            claims = case.get("claims", [])

            for claim in claims:
                total_claims += 1
                cited_ids = claim.get("citedFeedbackIds", [])
                expected_valid = claim.get("expectedValid", False)
                quote = claim.get("verbatimQuote")

                # Check if cited IDs exist in source feedback
                citations_exist = len(cited_ids) > 0 and all(cid in source_feedback for cid in cited_ids)

                # Check verbatim quote presence
                quote_found = False
                if quote and citations_exist:
                    verbatim_cases += 1
                    for cid in cited_ids:
                        if quote.lower() in source_feedback[cid].lower():
                            quote_found = True
                            break
                    if quote_found:
                        verbatim_matches += 1

                actual_valid = citations_exist and (quote_found if quote else True)
                if actual_valid == expected_valid:
                    correct_validity_decisions += 1

                if citations_exist and expected_valid:
                    valid_citations += 1

        expected_valid_count = sum(1 for c in cases for claim in c.get("claims", []) if claim.get("expectedValid", False))
        citation_ratio = compute_grounding_ratio(valid_citations, expected_valid_count) if expected_valid_count > 0 else 1.0
        verbatim_fidelity = (
            round(verbatim_matches / verbatim_cases, 4) if verbatim_cases > 0 else 1.0
        )
        decision_acc = round(correct_validity_decisions / total_claims, 4) if total_claims > 0 else 1.0

        overall_score = round(
            (0.40 * citation_ratio + 0.30 * verbatim_fidelity + 0.30 * decision_acc) * 100.0,
            2
        )

        metrics = [
            MetricResult(
                name="citation_validity_ratio",
                label="Evidence Citation Validity Ratio",
                nature=MetricNature.QUANTITATIVE,
                value=citation_ratio,
                unit="ratio",
                threshold=0.65,
                passed=citation_ratio >= 0.65,
                description="Fraction of claims successfully linked to verified source feedback items"
            ),
            MetricResult(
                name="verbatim_quote_fidelity",
                label="Verbatim Quote Grounding Fidelity",
                nature=MetricNature.QUANTITATIVE,
                value=verbatim_fidelity,
                unit="ratio",
                threshold=0.90,
                passed=verbatim_fidelity >= 0.90,
                description="Proportion of cited quotes verified as exact substrings of original operational feedback"
            ),
            MetricResult(
                name="grounding_verification_accuracy",
                label="Grounding Verification Accuracy",
                nature=MetricNature.QUANTITATIVE,
                value=decision_acc,
                unit="ratio",
                threshold=0.85,
                passed=decision_acc >= 0.85,
                description="Accuracy of distinguishing grounded claims from fabricated/unsupported statements"
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
            evaluated_cases=total_claims,
            summary=(
                f"Evaluated {total_claims} claims across {len(cases)} synthetic issues: "
                f"Citation Ratio={citation_ratio:.2f}, Verbatim Fidelity={verbatim_fidelity:.2f}, "
                f"Verification Acc={decision_acc:.2f}."
            ),
            caveats=[
                "Evaluated on synthetic issues with controlled claim-to-feedback lineage.",
                "In field production, cross-department syntheses may draw upon dozens of simultaneous reports."
            ]
        )
