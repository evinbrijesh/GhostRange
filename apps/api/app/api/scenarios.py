"""Scenario endpoints."""

from fastapi import APIRouter

from app.domain.scenarios.loader import SCENARIO_ID, load_default_scenario
from app.shared.errors import ApiError, ErrorCode

router = APIRouter(prefix="/api", tags=["scenarios"])


@router.get("/scenarios")
def list_scenarios() -> list[dict]:
    scenario = load_default_scenario()
    return [
        {
            "id": scenario.id,
            "name": scenario.name,
            "version": scenario.version,
            "stageCount": len(scenario.stages),
            "available": True,
        }
    ]


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str):
    if scenario_id != SCENARIO_ID:
        raise ApiError(
            ErrorCode.SCENARIO_NOT_FOUND,
            f"scenario '{scenario_id}' is not available in the MVP",
        )
    return load_default_scenario()