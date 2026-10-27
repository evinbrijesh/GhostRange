"""Deterministic scenario variants for Cloud Identity Compromise.

Per Master Prompt §SCENARIO VARIANTS:
1. Unusual source-location variation (var-location-shift)
2. Delayed MFA-change variation (var-delayed-mfa)
3. Benign administrative-noise variation (var-admin-noise)

The simulator generates variants through controlled, deterministic code,
never through arbitrary LLM-generated executable behavior.
"""

import random
from dataclasses import dataclass
from datetime import timedelta

from app.domain.detections.evaluator import evaluate_stage
from app.domain.detections.models import DetectionRule
from app.domain.detections.parser import parse_rule
from app.domain.scenarios.models import ContractModel, Scenario
from app.domain.simulation.engine import BASE_TIME, TEMPLATES, EventTemplate
from app.domain.telemetry.models import EventActor, TelemetryEvent
from app.shared.vocab import EventSource

# Additional documentation IPs for variants (RFC 5737)
TOR_EXIT_IPS = ("198.51.100.240", "198.51.100.241", "198.51.100.242")
VPN_RANGE_IPS = ("203.0.113.190", "203.0.113.195", "203.0.113.200")
REMOTE_OFFICE_IPS = ("192.0.2.100", "192.0.2.101")


class VariantSummary(ContractModel):
    variant_id: str
    name: str
    description: str
    seed: int
    event_count: int
    coverage_score: float
    stage_statuses: dict[str, str]


@dataclass(frozen=True)
class ScenarioVariant:
    variant_id: str
    name: str
    description: str
    seed: int
    templates: tuple[EventTemplate, ...]


def _create_location_shift_templates() -> tuple[EventTemplate, ...]:
    """Variant 1: Unusual source-location variation.
    
    Adversary operates from rotating documentation VPN and Tor exit nodes across
    different stages rather than consistent internal subnet IPs.
    """
    shifted = []
    for t in TEMPLATES:
        if t.expected:
            # Shift IPs to VPN or Tor exit ranges
            new_ips = TOR_EXIT_IPS if t.stage in ("S1", "S6", "S7") else VPN_RANGE_IPS
            shifted.append(EventTemplate(
                stage=t.stage,
                offset_min=t.offset_min,
                source=t.source,
                identity_id=t.identity_id,
                identity_type=t.identity_type,
                action=t.action,
                resource_id=t.resource_id,
                resource_type=t.resource_type,
                src_ips=new_ips,
                expected=t.expected,
                attributes=dict(t.attributes),
            ))
        else:
            shifted.append(t)
    return tuple(shifted)


def _create_delayed_mfa_templates() -> tuple[EventTemplate, ...]:
    """Variant 2: Delayed MFA-change variation.
    
    Adversary delays MFA tampering until after reconnaissance (S3),
    using an alternative Virtual MFA device deletion action.
    """
    modified = []
    for t in TEMPLATES:
        if t.stage == "S2" and t.expected:
            # Shift timing after S3 (offset 16 min) and use DeleteVirtualMfaDevice
            modified.append(EventTemplate(
                stage="S2",
                offset_min=16,
                source=t.source,
                identity_id=t.identity_id,
                identity_type=t.identity_type,
                action="DeleteVirtualMfaDevice",
                resource_id=t.resource_id,
                resource_type=t.resource_type,
                src_ips=t.src_ips,
                expected=True,
                attributes={"device": "mfa-totp-primary", "change": "deleted"},
            ))
        else:
            modified.append(t)
    return tuple(modified)


def _create_admin_noise_templates() -> tuple[EventTemplate, ...]:
    """Variant 3: Benign administrative-noise variation.
    
    Injects realistic DevOps background activity interleaved throughout
    the attack window to evaluate detection signal-to-noise resilience.
    """
    templates = list(TEMPLATES)
    # Interleave 5 additional background DevOps events
    noise = [
        EventTemplate("S1", 2, EventSource.AUTH, "user-david-wright", "person", "ConsoleLogin",
                      "console-northwind", "console", REMOTE_OFFICE_IPS, False,
                      {"auth_method": "sso", "user_agent": "safari-macos"}),
        EventTemplate("S3", 11, EventSource.API, "role-ci-cd-runner", "service-role", "DescribeInstances",
                      "compute-northwind", "compute-service", REMOTE_OFFICE_IPS, False,
                      {"count": 24}),
        EventTemplate("S4", 19, EventSource.IAM, "user-admin-sam", "person", "GetRolePolicy",
                      "role-reporting-etl", "iam-role", REMOTE_OFFICE_IPS, False,
                      {"policy": "ReadOnlyAccess"}),
        EventTemplate("S6", 38, EventSource.STORAGE, "service-backup-job", "service-role", "GetObject",
                      "bucket-northwind-prod-backups", "bucket", REMOTE_OFFICE_IPS, False,
                      {"object": "daily-snapshot.tar.gz", "bytes": 8388608}),
        EventTemplate("S7", 48, EventSource.STORAGE, "user-bob-chen", "person", "ListObjects",
                      "bucket-northwind-public-docs", "bucket", REMOTE_OFFICE_IPS, False,
                      {"prefix": "public/", "count": 14}),
    ]
    templates.extend(noise)
    templates.sort(key=lambda t: t.offset_min)
    return tuple(templates)


VARIANTS: dict[str, ScenarioVariant] = {
    "var-location-shift": ScenarioVariant(
        variant_id="var-location-shift",
        name="Unusual Location Shift",
        description="Adversary operates via rotating external documentation VPN and Tor exit ranges across stages.",
        seed=101,
        templates=_create_location_shift_templates(),
    ),
    "var-delayed-mfa": ScenarioVariant(
        variant_id="var-delayed-mfa",
        name="Delayed MFA Variation",
        description="Adversary performs MFA tampering out-of-order after discovery using DeleteVirtualMfaDevice.",
        seed=202,
        templates=_create_delayed_mfa_templates(),
    ),
    "var-admin-noise": ScenarioVariant(
        variant_id="var-admin-noise",
        name="Administrative Noise Variation",
        description="Heavy concurrent DevOps and administrative operations interleaved during attack execution.",
        seed=303,
        templates=_create_admin_noise_templates(),
    ),
}


def generate_variant_telemetry(
    variant_id: str,
    run_id: str,
) -> list[TelemetryEvent]:
    """Generate deterministic telemetry for a named scenario variant."""
    if variant_id not in VARIANTS:
        raise ValueError(f"Unknown variant ID '{variant_id}'")
    variant = VARIANTS[variant_id]
    rng = random.Random(variant.seed)
    events: list[TelemetryEvent] = []

    for index, template in enumerate(variant.templates, start=1):
        timestamp = BASE_TIME + timedelta(
            minutes=template.offset_min, seconds=rng.randrange(60)
        )
        events.append(
            TelemetryEvent(
                id=f"evt_{variant_id}_{template.stage.lower()}_{index:02d}",
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


def evaluate_variant(
    variant_id: str,
    rules: list[DetectionRule],
    scenario: Scenario,
    run_id: str,
) -> VariantSummary:
    """Evaluate a rule set against a specific scenario variant."""
    variant = VARIANTS[variant_id]
    events = generate_variant_telemetry(variant_id, run_id)
    compiled_rules = [(r, parse_rule(r.source)[1]) for r in rules]

    stage_weights = {s.id: s.weight for s in scenario.stages}
    statuses: dict[str, str] = {}
    stage_points: dict[str, float] = {
        "detected": 1.0,
        "partial": 0.5,
        "missed": 0.0,
        "error": 0.0,
    }

    total_score = 0.0
    for stage in scenario.stages:
        st_res, _matches, _errors = evaluate_stage(
            stage.id, events, compiled_rules, run_id
        )
        statuses[stage.id] = st_res.status.value
        total_score += 100.0 * stage_weights.get(stage.id, 0.0) * stage_points.get(st_res.status.value, 0.0)

    return VariantSummary(
        variant_id=variant.variant_id,
        name=variant.name,
        description=variant.description,
        seed=variant.seed,
        event_count=len(events),
        coverage_score=round(total_score, 1),
        stage_statuses=statuses,
    )


def calculate_variant_resilience(
    base_coverage: float,
    variant_summaries: list[VariantSummary],
) -> float:
    """Calculate Variant Resilience: mean coverage across base and all behavioral variants."""
    all_scores = [base_coverage] + [v.coverage_score for v in variant_summaries]
    return round(sum(all_scores) / len(all_scores), 1)
