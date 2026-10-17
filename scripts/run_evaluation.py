#!/usr/bin/env python3
"""
R5 Operational Intelligence Platform - Phase 20: Standalone Evaluation Runner CLI
Executes the reproducible evaluation framework across all 12 R5 dimensions.
Generates empirical benchmark reports from controlled synthetic datasets.

Usage:
    python scripts/run_evaluation.py
    python scripts/run_evaluation.py --dimension FEEDBACK_EXTRACTION_QUALITY
    python scripts/run_evaluation.py --output-dir docs/evaluation --format both
"""

import sys
import argparse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.evaluation.runner import EvaluationRunner  # noqa: E402
from backend.app.evaluation.reporter import EvaluationReporter  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="R5 Operational Intelligence Platform - Phase 20 Benchmark Evaluation CLI"
    )
    parser.add_argument(
        "--dimension", "-d",
        type=str,
        default=None,
        help="Specific evaluation dimension to run (e.g., FEEDBACK_EXTRACTION_QUALITY, ROUTING_ACCURACY)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="docs/evaluation",
        help="Directory to save generated markdown and JSON benchmark reports (default: docs/evaluation)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "markdown", "both"],
        default="both",
        help="Output report formats to generate on disk (default: both)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print verbose evaluation details to stdout"
    )

    args = parser.parse_args()

    dimensions_filter = [args.dimension] if args.dimension else None

    print("=" * 80)
    print(" R5 OPERATIONAL INTELLIGENCE — PHASE 20 EVALUATION FRAMEWORK")
    print("=" * 80)
    print("Notice: Running controlled synthetic benchmark battery...")
    if dimensions_filter:
        print(f"Target dimension: {args.dimension}")
    print()

    # Execute Evaluation Suite
    report = EvaluationRunner.run_all(dimensions=dimensions_filter)

    # Print Summary Table
    print(f"Run ID:            {report.run_id}")
    print(f"Timestamp:         {report.timestamp}")
    print(f"Overall Score:     {report.overall_score:.2f} / 100")
    print(f"Summary Status:    {report.summary_status}")
    print(f"Dimensions Passed: {report.passed_dimensions} / {report.total_dimensions}")
    print()
    print("-" * 80)
    print(f"{'#':<3} | {'Dimension Name':<35} | {'Score':<8} | {'Status':<6} | {'Cases':<6}")
    print("-" * 80)

    for idx, dim in enumerate(report.dimension_results, 1):
        status_symbol = "PASS" if dim.passed else "FAIL"
        print(f"{idx:<3} | {dim.dimension_name:<35} | {dim.score:>6.1f} | {status_symbol:<6} | {dim.total_cases:<6}")
        if args.verbose and dim.metrics:
            for m in dim.metrics:
                m_stat = "OK" if m.passed else "FAIL"
                val_str = f"{m.value:.4f}" if m.value is not None else "N/A"
                print(f"     -> {m.label:<32}: {val_str} {m.unit} [{m_stat}]")

    print("-" * 80)

    # Save reports to disk
    paths = EvaluationReporter.save_reports(report, output_dir=args.output_dir)
    print()
    print(f"Markdown report generated: {paths['markdownPath']}")
    print(f"JSON report generated:     {paths['jsonPath']}")
    print()
    print("CAVEAT: Results reflect controlled synthetic benchmark datasets and do not claim")
    print("commercial field-measured production accuracy.")
    print("=" * 80)

    return 0 if report.passed_dimensions == report.total_dimensions else 1


if __name__ == "__main__":
    sys.exit(main())
