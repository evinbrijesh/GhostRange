"""Coverage calculator: explainable score from stage weights."""

from app.domain.coverage.calculator import FORMULA_VERSION, calculate_coverage
from app.domain.detections.models import StageResult
from app.shared.vocab import StageStatus


def _result(stage_id: str, status: StageStatus) -> StageResult:
    return StageResult(
        stage_id=stage_id, status=status, expected_event_ids=[], matched_event_ids=[],
        matched_rule_ids=[], detection_latency_ms=None, evidence_ids=[], errors=[],
    )


WEIGHTS = {"S1": 0.15, "S2": 0.10, "S3": 0.10, "S4": 0.20, "S5": 0.15, "S6": 0.15, "S7": 0.15}


def test_all_detected_scores_100() -> None:
    results = [_result(sid, StageStatus.DETECTED) for sid in WEIGHTS]
    coverage = calculate_coverage("run_x", results, WEIGHTS, [])
    assert coverage.score == 100.0
    assert coverage.stage_counts == {"detected": 7, "partial": 0, "missed": 0, "error": 0}


def test_partial_counts_half() -> None:
    results = [_result(sid, StageStatus.DETECTED) for sid in WEIGHTS]
    results[0] = _result("S1", StageStatus.PARTIAL)
    coverage = calculate_coverage("run_x", results, WEIGHTS, [])
    assert coverage.score == round(100.0 * (1.0 - 0.15 * 0.5), 1)


def test_error_stage_contributes_zero_and_is_visible() -> None:
    results = [_result(sid, StageStatus.DETECTED) for sid in WEIGHTS]
    results[3] = _result("S4", StageStatus.ERROR)
    coverage = calculate_coverage("run_x", results, WEIGHTS, ["rule parse failure"])
    assert coverage.score == round(100.0 * (1.0 - 0.20), 1)
    assert coverage.stage_counts["error"] == 1
    assert coverage.evaluator_errors == ["rule parse failure"]


def test_formula_version_is_stored() -> None:
    coverage = calculate_coverage("run_x", [], WEIGHTS, [])
    assert coverage.formula_version == FORMULA_VERSION
    assert coverage.score == 0.0