"""DetectionOps unified metrics, regression detection, and CI/CD reporting.

Per Master Prompt:
- Attack coverage: How many expected attack stages were detected.
- Variant resilience: How consistently the rule set detects variations of the attack.
- Benign suppression: How often rules avoid matching benign administrative activity.
- Regression status: Compare current rule set with previous run/baseline.
- GitHub Actions / CI/CD compatible report format.
"""

from typing import Literal

from app.domain.coverage.models import CoverageResult
from app.domain.detections.models import DetectionRule
from app.domain.scenarios.models import ContractModel, Scenario
from app.domain.simulation.benign import (
    BenignSuppressionResult,
    evaluate_benign_suppression,
)
from app.domain.simulation.variants import (
    VARIANTS,
    VariantSummary,
    calculate_variant_resilience,
    evaluate_variant,
)


class DetectionOpsMetrics(ContractModel):
    run_id: str
    attack_coverage: float
    variant_resilience: float
    benign_suppression: float
    noise_risk: str
    regression_status: str  # baseline | pass | regression_detected
    variants_count: int
    benign_events_count: int
    noise_hits_count: int
    variant_breakdown: list[VariantSummary]
    benign_details: BenignSuppressionResult


class RegressionAnalysisResult(ContractModel):
    baseline_run_id: str
    candidate_run_id: str
    baseline_coverage: float
    candidate_coverage: float
    coverage_diff: float
    status: Literal["pass", "regression_detected", "unchanged"]
    is_blocked: bool
    summary: str


def compute_detection_ops_metrics(
    run_id: str,
    rules: list[DetectionRule],
    scenario: Scenario,
    coverage: CoverageResult,
    baseline_coverage: float | None = None,
) -> DetectionOpsMetrics:
    """Compute the full 4-tier DetectionOps metric suite."""
    variant_summaries: list[VariantSummary] = []
    for var_id in VARIANTS:
        summary = evaluate_variant(var_id, rules, scenario, run_id)
        variant_summaries.append(summary)

    resilience = calculate_variant_resilience(coverage.score, variant_summaries)
    benign_result = evaluate_benign_suppression(rules)

    if baseline_coverage is None:
        regression_status = "baseline"
    elif coverage.score < baseline_coverage:
        regression_status = "regression_detected"
    else:
        regression_status = "pass"

    return DetectionOpsMetrics(
        run_id=run_id,
        attack_coverage=coverage.score,
        variant_resilience=resilience,
        benign_suppression=benign_result.suppression_rate,
        noise_risk=benign_result.noise_risk,
        regression_status=regression_status,
        variants_count=len(variant_summaries),
        benign_events_count=benign_result.total_benign_events,
        noise_hits_count=benign_result.noise_hit_count,
        variant_breakdown=variant_summaries,
        benign_details=benign_result,
    )


def analyze_regression(
    baseline_run_id: str,
    candidate_run_id: str,
    baseline_coverage: float,
    candidate_coverage: float,
) -> RegressionAnalysisResult:
    """Analyze regression between a baseline run and candidate run."""
    diff = round(candidate_coverage - baseline_coverage, 1)
    if diff < 0:
        status: Literal["pass", "regression_detected", "unchanged"] = "regression_detected"
        is_blocked = True
        summary = f"REGRESSION BLOCKED: Candidate coverage dropped by {abs(diff)}% ({baseline_coverage}% -> {candidate_coverage}%)."
    elif diff > 0:
        status = "pass"
        is_blocked = False
        summary = f"VALIDATION PASSED: Coverage improved by +{diff}% ({baseline_coverage}% -> {candidate_coverage}%)."
    else:
        status = "unchanged"
        is_blocked = False
        summary = f"VALIDATION PASSED: Coverage unchanged at {candidate_coverage}%."

    return RegressionAnalysisResult(
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        baseline_coverage=baseline_coverage,
        candidate_coverage=candidate_coverage,
        coverage_diff=diff,
        status=status,
        is_blocked=is_blocked,
        summary=summary,
    )


def generate_ci_report_markdown(
    scenario: Scenario,
    metrics: DetectionOpsMetrics,
    baseline_metrics: DetectionOpsMetrics | None = None,
) -> str:
    """Generate GitHub Actions / CI/CD pull request comment in Markdown."""
    diff_str = ""
    gate_status = "✅ PASS"
    if baseline_metrics:
        diff = round(metrics.attack_coverage - baseline_metrics.attack_coverage, 1)
        sign = "+" if diff > 0 else ""
        diff_str = f" ({sign}{diff}% vs baseline)"
        if diff < 0:
            gate_status = "❌ BLOCKED (REGRESSION DETECTED)"

    lines = [
        "## 🛡️ GhostRange DetectionOps CI/CD Report",
        "",
        f"**Scenario:** `{scenario.name}` (`{scenario.id}`)  ",
        f"**Pipeline Run:** `{metrics.run_id}`  ",
        f"**CI Gate Decision:** **{gate_status}**  ",
        "",
        "### 📊 Detection Engineering Metrics",
        "",
        "| Metric | Result | Benchmark | Status |",
        "| :--- | :--- | :--- | :--- |",
        f"| **Attack Coverage** | **{metrics.attack_coverage}%**{diff_str} | Threshold: ≥50% | {'✅' if metrics.attack_coverage >= 50 else '⚠️'} |",
        f"| **Variant Resilience** | **{metrics.variant_resilience}%** | 3 Behavioral Variants | {'✅' if metrics.variant_resilience >= 60 else '⚠️'} |",
        f"| **Benign Suppression** | **{metrics.benign_suppression}%** | Noise Risk: `{metrics.noise_risk.upper()}` | {'✅' if metrics.noise_risk == 'low' else '⚠️'} |",
        f"| **Regression Guard** | **{metrics.regression_status.upper()}** | Zero Degradation Allowed | {'✅' if metrics.regression_status != 'regression_detected' else '❌'} |",
        "",
        "### 🔬 Behavioral Variant Matrix",
        "",
        "| Variant | Description | Events | Coverage |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for v in metrics.variant_breakdown:
        lines.append(f"| `{v.variant_id}` | {v.name} | {v.event_count} | **{v.coverage_score}%** |")

    lines.extend([
        "",
        "### 🔇 Benign Noise Suppression (Offline Estimate)",
        "",
        f"- **Tested Benign Events:** {metrics.benign_events_count}",
        f"- **Suppressed Events:** {metrics.benign_details.suppressed_count}",
        f"- **Noise Alert Hits:** {metrics.noise_hits_count}",
        f"- **Offline Noise Risk:** `{metrics.noise_risk.upper()}`",
        "",
        "> **Notice:** This test was evaluated deterministically against synthetic cloud telemetry with `synthetic: true`. No real infrastructure was accessed.",
    ])

    return "\n".join(lines)
