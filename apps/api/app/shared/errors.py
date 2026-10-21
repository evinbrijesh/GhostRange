"""Stable, safe error codes returned by the API.

Rules (from CLAUDE.md):
- Never return stack traces, secret values, or internal credentials.
- A parser error is not a security miss; it is reported in evaluator_errors.
- A failed AI call must not mark a stage as missed.
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    SCENARIO_NOT_FOUND = "SCENARIO_NOT_FOUND"
    INVALID_RUN_STATE = "INVALID_RUN_STATE"
    RULE_PARSE_ERROR = "RULE_PARSE_ERROR"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    AI_OUTPUT_INVALID = "AI_OUTPUT_INVALID"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ApiError(Exception):
    """API-boundary error with a stable code and a safe, human-readable message."""

    def __init__(self, code: ErrorCode, message: str, details: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_payload(self) -> dict:
        return {"code": self.code.value, "message": self.message, "details": self.details}