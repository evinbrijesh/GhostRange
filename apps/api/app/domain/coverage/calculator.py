"""Coverage calculation (formula coverage-v1).

score = 100 * sum(stage_weight * stage_points)
stage_points: detected=1.0, partial=0.5, missed=0.0, error=0.0

An `error` stage contributes 0 points and is flagged in evaluator_errors so
tooling failures are visible rather than silently absorbed. The formula and
per-stage results are always stored so every score is explainable.
"""

from app.domain.coverage.models import CoverageResult
from app.domain.detections.models import StageResult
from app.shared.vocab import StageStatus

FORMULA_VERSION = "coverage-v1"

STAGE_POINTS: dict[StageStatus, float] = {
    StageStatus.DETECTED: 1.0,
    StageStatus.PARTIAL: 0.5,
    StageStatus.MISSED: 0.0,
    StageStatus.ERROR: 0.0,
}


def calculate_coverage(
    run_id: str,
    stage_results: list[StageResult],
    stage_weights: dict[str, float],
    evaluator_errors: list[str],
) -> CoverageResult:
    counts = {status.value: 0 for status in StageStatus}
    for result in stage_results:
        counts[result.status.value] += 1

    score = 100.0 * sum(
        stage_weights.get(result.stage_id, 0.0) * STAGE_POINTS[result.status]
        for result in stage_results
    )

    return CoverageResult(
        run_id=run_id,
        score=round(score, 1),
        stage_counts=counts,
        stages=stage_results,
        formula_version=FORMULA_VERSION,
        evaluator_errors=evaluator_errors,
    )