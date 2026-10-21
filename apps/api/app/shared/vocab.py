"""Shared vocabularies. Must stay in sync with packages/schemas/json/common.schema.json."""

from enum import StrEnum


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StageStatus(StrEnum):
    DETECTED = "detected"
    PARTIAL = "partial"
    MISSED = "missed"
    ERROR = "error"


class EventSource(StrEnum):
    AUTH = "auth"
    IAM = "iam"
    API = "api"
    STORAGE = "storage"
    NETWORK = "network"


class RuleLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ParserStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"


STAGE_IDS: tuple[str, ...] = ("S1", "S2", "S3", "S4", "S5", "S6", "S7")

EVENT_SOURCES: tuple[str, ...] = tuple(source.value for source in EventSource)

# Reserved documentation IP ranges (RFC 5737). The simulator never uses
# anything outside these networks.
RESERVED_NETWORKS = ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")