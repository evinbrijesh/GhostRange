"""GhostRange API entry point.

Responsibilities live in dedicated modules:
- domain/: deterministic simulator, rule engine, coverage (source of truth)
- ai/: Nebius client, prompts, schemas, grounding (never authoritative)
- persistence/: runs, events, rules, matches, proposals, reports
- api/: validation and orchestration

The frontend never calculates authoritative coverage and never calls Nebius.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title="GhostRange API",
    version="0.1.0",
    description="Defensive security-control validation platform (synthetic, non-invasive).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    """Liveness probe. Reports whether AI features are configured (not whether they work)."""
    return {
        "status": "ok",
        "service": "ghostrange-api",
        "version": "0.1.0",
        "ai_configured": settings.nebius_api_key is not None,
    }