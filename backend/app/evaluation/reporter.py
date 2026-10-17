"""
R5 Operational Intelligence Platform - Phase 20: Evaluation Reporter
Generates comprehensive GitHub-Flavored Markdown and JSON reports from benchmark evaluation runs.
Adheres strictly to the requirement:
- Do not fabricate benchmark results
- Controlled synthetic datasets labeled
- State when ground truth is unavailable / qualitative
- Do not claim production accuracy
"""

from pathlib import Path
from typing import Dict

from backend.app.evaluation.schemas import EvaluationSuiteReport


class EvaluationReporter:
    """Renders structured reports from EvaluationSuiteReport instances."""

    @staticmethod
    def render_markdown(report: EvaluationSuiteReport) -> str:
        """Render evaluation report as rich GitHub-Flavored Markdown document."""
        lines = []

        lines.append("# R5 Operational Intelligence Platform — System Evaluation Report")
        lines.append(f"**Run Identifier**: `{report.run_id}`  ")
        lines.append(f"**Evaluation Timestamp**: `{report.timestamp}`  ")
        lines.append(f"**Framework Version**: `{report.framework_version}`  ")
        lines.append(f"**Execution Environment**: Python {report.environment_info.get('python_version')}, {report.environment_info.get('platform')}  ")
        lines.append("")

        # Prominent Mandatory Disclaimer & Caveat Block
        lines.append("> [!WARNING]")
        lines.append("> **EVALUATION BENCHMARK CAVEATS & SCOPE RESTRICTIONS**")
        lines.append("> 1. **No Benchmark Fabrication**: All metrics below were dynamically computed by executing active algorithmic pipelines against controlled test datasets.")
        lines.append("> 2. **Controlled Synthetic Datasets**: All test cases are synthetic benchmark vectors specifically designed to probe algorithmic boundaries, stress-test resilience, and prevent regressions. **These metrics DO NOT represent production field accuracy or commercial claims.**")
        lines.append("> 3. **Qualitative & Unmeasured Dimensions**: Where objective ground truth cannot be established deterministically, metrics are explicitly marked as qualitative or not yet measurable.")
        lines.append("")

        # Executive Summary Scorecard
        status_badge = "🟢 **PASS**" if report.summary_status == "PASS" else ("🟡 **DEGRADED**" if report.summary_status == "DEGRADED" else "🔴 **FAIL**")
        lines.append("## 1. Executive Evaluation Scorecard")
        lines.append(f"- **Overall Benchmark Score**: **`{report.overall_score:.2f} / 100`**")
        lines.append(f"- **Suite Execution Status**: {status_badge}")
        lines.append(f"- **Dimensions Evaluated**: **`{report.passed_dimensions} / {report.total_dimensions}`** dimensions passing baseline thresholds")
        lines.append("")

        lines.append("| # | Evaluation Dimension | Score (0-100) | Status | Test Cases | Summary Diagnostic |")
        lines.append("|:---:|:---|:---:|:---:|:---:|:---|")

        for idx, dim in enumerate(report.dimension_results, 1):
            dim_status = "✅ PASS" if dim.passed else "❌ FAIL"
            lines.append(f"| {idx} | **{dim.dimension_name}** | `{dim.score:.1f}` | {dim_status} | {dim.total_cases} | {dim.summary} |")

        lines.append("")

        # Detailed Dimension Breakdowns
        lines.append("## 2. In-Depth Dimension Metric Breakdown")
        for idx, dim in enumerate(report.dimension_results, 1):
            lines.append(f"### 2.{idx} {dim.dimension_name} (`{dim.dimension.value}`)")
            lines.append(f"**Dimension Score**: `{dim.score:.2f} / 100` — **Status**: {'✅ Passed' if dim.passed else '❌ Failed'}")
            lines.append("")
            lines.append(f"*{dim.summary}*")
            lines.append("")

            if dim.metrics:
                lines.append("| Metric Name | Nature | Measured Value | Threshold | Status | Description |")
                lines.append("|:---|:---:|:---:|:---:|:---:|:---|")
                for m in dim.metrics:
                    val_str = f"`{m.value:.4f}` {m.unit}" if m.value is not None else "*Qualitative / N/A*"
                    thresh_str = f"`{m.threshold}` {m.unit}" if m.threshold is not None else "N/A"
                    m_status = "✅ Met" if m.passed else "❌ Missed"
                    lines.append(f"| **{m.label}** | `{m.nature.value}` | {val_str} | {thresh_str} | {m_status} | {m.description} |")
                lines.append("")

            if dim.qualitative_notes:
                lines.append("> [!NOTE]")
                lines.append(f"> **Qualitative Assessment**: {dim.qualitative_notes}")
                lines.append("")

            if dim.caveats:
                lines.append("**Caveats & Scope Constraints**:")
                for c in dim.caveats:
                    lines.append(f"- {c}")
                lines.append("")

        # Dataset Manifest
        lines.append("## 3. Synthetic Benchmark Datasets Manifest")
        lines.append("All evaluation datasets are version-controlled, synthetic, and explicitly labeled:")
        lines.append("")
        lines.append("| Dataset File | Target Dimension | Sample Count | Data Classification |")
        lines.append("|:---|:---|:---:|:---|")
        for ds in report.dataset_manifest:
            lines.append(f"| `{ds.filename}` | `{ds.dimension.value}` | {ds.sample_count} | `{ds.label}` |")
        lines.append("")

        lines.append("---")
        lines.append(f"*Report compiled deterministically by R5 Evaluation Runner at {report.timestamp}.*")

        return "\n".join(lines)

    @classmethod
    def save_reports(
        cls,
        report: EvaluationSuiteReport,
        output_dir: str = "docs/evaluation"
    ) -> Dict[str, str]:
        """Save both Markdown and JSON evaluation reports to disk."""
        target_path = Path(output_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        md_content = cls.render_markdown(report)
        md_filename = f"evaluation_report_{report.run_id}.md"
        latest_md_filename = "latest_evaluation_report.md"
        json_filename = f"evaluation_report_{report.run_id}.json"
        latest_json_filename = "latest_evaluation_report.json"

        # Write run-specific and latest files
        with open(target_path / md_filename, "w", encoding="utf-8") as f:
            f.write(md_content)
        with open(target_path / latest_md_filename, "w", encoding="utf-8") as f:
            f.write(md_content)

        with open(target_path / json_filename, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
        with open(target_path / latest_json_filename, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        return {
            "markdownPath": str(target_path / latest_md_filename),
            "jsonPath": str(target_path / latest_json_filename)
        }
