"""Seeded synthetic telemetry generation for the Cloud Identity Compromise scenario.

Determinism guarantees:
- The same scenario version + seed produces byte-identical telemetry.
- Timestamps derive from a fixed base time plus seeded offsets (never wall clock).
- All IPs come from reserved documentation ranges; every event is synthetic.
- Event IDs are deterministic (derived from stage + sequence), so two runs with
  the same seed produce identical event IDs.
"""

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.domain.scenarios.models import Scenario
from app.domain.telemetry.models import EventActor, TelemetryEvent
from app.shared.vocab import EventSource

# Fixed base time: the fictional incident window. Never derived from wall clock.
BASE_TIME = datetime(2026, 3, 2, 9, 0, 0, tzinfo=UTC)

# Reserved documentation ranges only (RFC 5737).
OFFICE_IPS = ("192.0.2.14", "192.0.2.31", "192.0.2.47")
INTERNAL_IPS = ("198.51.100.20", "198.51.100.21")
UNUSUAL_IPS = ("203.0.113.7", "203.0.113.77", "203.0.113.140")


@dataclass(frozen=True)
class EventTemplate:
    stage: str
    offset_min: int
    source: EventSource
    identity_id: str
    identity_type: str
    action: str
    resource_id: str
    resource_type: str
    src_ips: tuple[str, ...]
    expected: bool
    attributes: dict = field(default_factory=dict)


ALICE = "user-alice-morgan"
BOB = "user-bob-chen"
CAROL = "user-carol-diaz"

# The attack timeline. `expected` events are what each stage's coverage check
# requires; background events are benign noise that rules must NOT match.
TEMPLATES: tuple[EventTemplate, ...] = (
    EventTemplate("S1", 0, EventSource.AUTH, ALICE, "person", "ConsoleLogin",
                  "console-northwind", "console", UNUSUAL_IPS, True,
                  {"auth_method": "password+otp", "user_agent": "firefox-ubuntu"}),
    EventTemplate("S1", 1, EventSource.AUTH, BOB, "person", "ConsoleLogin",
                  "console-northwind", "console", OFFICE_IPS, False,
                  {"auth_method": "password+otp", "user_agent": "chrome-macos"}),
    EventTemplate("S2", 8, EventSource.IAM, ALICE, "person", "UpdateMfaPreference",
                  ALICE, "iam-user", INTERNAL_IPS, True,
                  {"mfa_method": "totp", "change": "disabled"}),
    EventTemplate("S2", 9, EventSource.IAM, BOB, "person", "GetUser",
                  BOB, "iam-user", OFFICE_IPS, False,
                  {"info": "self-lookup"}),
    EventTemplate("S3", 12, EventSource.API, ALICE, "person", "ListUsers",
                  "iam-northwind", "iam-directory", INTERNAL_IPS, True,
                  {"count": 42}),
    EventTemplate("S3", 13, EventSource.API, ALICE, "person", "ListRoles",
                  "iam-northwind", "iam-directory", INTERNAL_IPS, True,
                  {"count": 11}),
    EventTemplate("S3", 14, EventSource.API, ALICE, "person", "ListBuckets",
                  "storage-northwind", "storage-account", INTERNAL_IPS, True,
                  {"count": 7}),
    EventTemplate("S3", 15, EventSource.API, BOB, "person", "DescribeInstances",
                  "compute-northwind", "compute-service", OFFICE_IPS, False,
                  {"count": 5}),
    EventTemplate("S4", 20, EventSource.IAM, ALICE, "person", "AttachRolePolicy",
                  "role-reporting-etl", "iam-role", INTERNAL_IPS, True,
                  {"policy": "AdministratorAccess"}),
    EventTemplate("S4", 22, EventSource.IAM, ALICE, "person", "AssumeRole",
                  "role-reporting-etl", "iam-role", INTERNAL_IPS, True,
                  {"session": "etl-batch"}),
    EventTemplate("S4", 23, EventSource.IAM, CAROL, "person", "AttachRolePolicy",
                  "role-reporting-readonly", "iam-role", OFFICE_IPS, False,
                  {"policy": "ReadOnlyAccess"}),
    EventTemplate("S5", 30, EventSource.IAM, ALICE, "person", "CreateAccessKey",
                  ALICE, "iam-user", INTERNAL_IPS, True,
                  {"key_max_age_days": 365}),
    EventTemplate("S5", 31, EventSource.IAM, BOB, "person", "CreateAccessKey",
                  BOB, "iam-user", OFFICE_IPS, False,
                  {"key_max_age_days": 90}),
    EventTemplate("S6", 40, EventSource.STORAGE, ALICE, "person", "GetObject",
                  "bucket-northwind-prod-backups", "bucket", INTERNAL_IPS, True,
                  {"object": "finance/payroll-2026.csv", "bytes": 1048576}),
    EventTemplate("S6", 41, EventSource.STORAGE, BOB, "person", "GetObject",
                  "bucket-northwind-public-docs", "bucket", OFFICE_IPS, False,
                  {"object": "handbook.pdf", "bytes": 20480}),
    EventTemplate("S7", 50, EventSource.STORAGE, ALICE, "person", "ListObjects",
                  "bucket-northwind-prod-backups", "bucket", INTERNAL_IPS, True,
                  {"prefix": "finance/", "count": 128}),
    EventTemplate("S7", 52, EventSource.STORAGE, ALICE, "person", "CopyObject",
                  "bucket-northwind-prod-backups", "bucket", INTERNAL_IPS, True,
                  {"object": "finance/*", "destination": "bucket-northwind-dev-scratch",
                   "bytes": 4294967296}),
)


def generate_telemetry(scenario: Scenario, run_id: str, seed: int) -> list[TelemetryEvent]:
    """Generate the full event timeline for a run. Deterministic per (scenario, seed)."""
    rng = random.Random(seed)
    events: list[TelemetryEvent] = []

    for index, template in enumerate(TEMPLATES, start=1):
        timestamp = BASE_TIME + timedelta(
            minutes=template.offset_min, seconds=rng.randrange(60)
        )
        events.append(
            TelemetryEvent(
                id=f"evt_{template.stage.lower()}_{index:02d}",
                run_id=run_id,
                stage_id=template.stage,
                expected=template.expected,
                timestamp=timestamp,
                source=template.source,
                identity=EventActor(id=template.identity_id, type=template.identity_type),
                action=template.action,
                resource=EventActor(id=template.resource_id, type=template.resource_type),
                src_ip=rng.choice(template.src_ips),
                attributes=dict(template.attributes),
            )
        )
    return events