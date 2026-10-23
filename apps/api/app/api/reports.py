"""Report endpoint: assembles the structured run report."""

from fastapi import APIRouter

from app.domain.reports.builder import build_report
from app.persistence.instance import repository
from app.shared.errors import ApiError, ErrorCode

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/runs/{run_id}/report")
def get_run_report(run_id: str):
    record = repository.get_run(run_id)
    if record is None:
        raise ApiError(ErrorCode.RUN_NOT_FOUND, f"run '{run_id}' does not exist")
    return build_report(record, repository.list_proposals(run_id))