"""GhostRange API entry point.

Responsibilities live in dedicated modules:
- domain/: deterministic simulator, rule engine, coverage (source of truth)
- ai/: Nebius client, prompts, schemas, grounding (never authoritative)
- persistence/: runs, events, rules, matches, proposals, reports
- api/: validation and orchestration

The frontend never calculates authoritative coverage and never calls Nebius.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import explanations, proposals, reports, runs, scenarios, threat_intel
from app.config import settings
from app.shared.errors import ApiError, ErrorCode

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

app.include_router(scenarios.router)
app.include_router(runs.router)
app.include_router(proposals.router)
app.include_router(reports.router)
app.include_router(explanations.router)
app.include_router(threat_intel.router)


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    status = {ErrorCode.NOT_FOUND: 404, ErrorCode.RUN_NOT_FOUND: 404,
              ErrorCode.SCENARIO_NOT_FOUND: 404, ErrorCode.INVALID_RUN_STATE: 409,
              ErrorCode.INTERNAL_ERROR: 500}.get(exc.code, 400)
    return JSONResponse(status_code=status, content=exc.to_payload())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Safe details only: location and message, never raw input values.
    details = [{"loc": err.get("loc"), "msg": err.get("msg")} for err in exc.errors()]
    return JSONResponse(
        status_code=400,
        content={"code": ErrorCode.VALIDATION_ERROR.value,
                 "message": "request validation failed", "details": details},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # Never leak stack traces or internals to clients.
    return JSONResponse(
        status_code=500,
        content={"code": ErrorCode.INTERNAL_ERROR.value,
                 "message": "internal error; check server logs"},
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