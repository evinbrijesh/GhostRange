"""Threat Intelligence endpoints powered by Tavily (with curated MITRE ATT&CK fallback)."""

from fastapi import APIRouter, Query

from app.ai.tavily import search_threat_intel

router = APIRouter(prefix="/api/threat-intel", tags=["threat-intel"])


@router.get("/stages/{stage_id}")
def get_stage_threat_intel(stage_id: str):
    return search_threat_intel(stage_id=stage_id)


@router.get("/search")
def search_threat_intel_endpoint(
    query: str = Query(..., min_length=2),
    stage_id: str | None = None,
):
    return search_threat_intel(stage_id=stage_id, query=query)
