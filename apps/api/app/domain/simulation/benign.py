"""Benign event corpus and offline noise suppression estimation.

Per Master Prompt §BENIGN SUPPRESSION:
How often the rules avoid matching legitimate administrative activity in
the supplied benign corpus. Labeled strictly as an offline estimate.
"""

import random
from datetime import timedelta

from app.domain.detections.evaluator import _evaluate_selection, flatten_event
from app.domain.detections.models import DetectionRule
from app.domain.detections.parser import parse_rule
from app.domain.scenarios.models import ContractModel
from app.domain.simulation.engine import BASE_TIME, OFFICE_IPS
from app.domain.telemetry.models import EventActor, TelemetryEvent
from app.shared.vocab import EventSource


class NoiseHit(ContractModel):
    rule_id: str
    rule_title: str
    event_id: str
    action: str
    identity: str
    resource: str
    matched_fields: dict


class BenignSuppressionResult(ContractModel):
    total_benign_events: int
    suppressed_count: int
    noise_hit_count: int
    suppression_rate: float
    noise_risk: str  # low | medium | high
    hits: list[NoiseHit]


# 12 distinct legitimate business/DevOps events that represent everyday cloud operations.
# Rules should be specific enough to NOT trigger on these normal activities.
BENIGN_TEMPLATES = (
    ("AUTH", "user-alice-morgan", "ConsoleLogin", "console-northwind", "console",
     {"auth_method": "saml-sso", "user_agent": "chrome-windows"}, 5),
    ("AUTH", "user-bob-chen", "ConsoleLogin", "console-northwind", "console",
     {"auth_method": "saml-sso", "user_agent": "safari-macos"}, 15),
    ("IAM", "user-carol-diaz", "GetUser", "user-carol-diaz", "iam-user",
     {"info": "profile-check"}, 22),
    ("IAM", "role-billing-auditor", "GetAccountSummary", "account-northwind", "iam-account",
     {"scope": "financial-audit"}, 30),
    ("IAM", "role-ci-cd-deployer", "GetRole", "role-app-backend", "iam-role",
     {"query": "verification"}, 45),
    ("API", "user-alice-morgan", "DescribeInstances", "compute-northwind", "compute-service",
     {"region": "us-east-1", "filter": "prod"}, 60),
    ("API", "role-datadog-collector", "DescribeSecurityGroups", "network-northwind", "vpc",
     {"interval": "monitoring"}, 75),
    ("STORAGE", "user-bob-chen", "GetObject", "bucket-northwind-public-docs", "bucket",
     {"object": "company-policies/2026.pdf", "bytes": 450200}, 90),
    ("STORAGE", "service-backup-agent", "GetObject", "bucket-northwind-daily-snapshots", "bucket",
     {"object": "db-dump-nightly.tar.gz", "bytes": 209715200}, 110),
    ("STORAGE", "user-carol-diaz", "ListObjects", "bucket-northwind-marketing-assets", "bucket",
     {"prefix": "logos/", "count": 12}, 130),
    ("IAM", "user-alice-morgan", "ListAttachedUserPolicies", "user-alice-morgan", "iam-user",
     {"audit": "quarterly-review"}, 150),
    ("API", "user-david-wright", "DescribeSubnets", "network-northwind", "vpc",
     {"region": "us-east-1"}, 170),
)


def generate_benign_corpus(run_id: str = "benign-baseline", seed: int = 777) -> list[TelemetryEvent]:
    """Generate the standardized corpus of legitimate benign events."""
    rng = random.Random(seed)
    events: list[TelemetryEvent] = []

    for idx, (source_name, actor, action, res_id, res_type, attrs, offset) in enumerate(BENIGN_TEMPLATES, 1):
        source = EventSource(source_name.lower())
        timestamp = BASE_TIME + timedelta(minutes=offset, seconds=rng.randrange(60))
        events.append(
            TelemetryEvent(
                id=f"evt_benign_{idx:02d}",
                run_id=run_id,
                stage_id="BENIGN",
                expected=False,
                timestamp=timestamp,
                source=source,
                identity=EventActor(id=actor, type="person" if "user-" in actor else "service-role"),
                action=action,
                resource=EventActor(id=res_id, type=res_type),
                src_ip=rng.choice(OFFICE_IPS),
                attributes=attrs,
            )
        )
    return events


def evaluate_benign_suppression(
    rules: list[DetectionRule],
    benign_events: list[TelemetryEvent] | None = None,
) -> BenignSuppressionResult:
    """Evaluate detection rules against the benign corpus.
    
    Returns the suppression rate (higher is better, 100% means zero noise)
    and an offline noise risk estimate.
    """
    events = benign_events or generate_benign_corpus()
    total = len(events)
    if total == 0:
        return BenignSuppressionResult(
            total_benign_events=0,
            suppressed_count=0,
            noise_hit_count=0,
            suppression_rate=100.0,
            noise_risk="low",
            hits=[],
        )

    compiled_rules = []
    for r in rules:
        if r.enabled and r.parser_status == "valid":
            _parsed, selection = parse_rule(r.source)
            compiled_rules.append((r, selection))

    hits: list[NoiseHit] = []
    matched_event_ids: set[str] = set()

    for rule, selection in compiled_rules:
        for event in events:
            # Rule only matches if logsource matches event source
            if rule.logsource.service != event.source:
                continue
            flat = flatten_event(event)
            matched, matched_details, _failed = _evaluate_selection(selection, flat)
            if matched:
                matched_event_ids.add(event.id)
                hits.append(
                    NoiseHit(
                        rule_id=rule.id,
                        rule_title=rule.title,
                        event_id=event.id,
                        action=event.action,
                        identity=event.identity.id,
                        resource=event.resource.id,
                        matched_fields=matched_details,
                    )
                )

    suppressed = total - len(matched_event_ids)
    rate = round((suppressed / total) * 100.0, 1)

    if rate >= 90.0:
        risk = "low"
    elif rate >= 75.0:
        risk = "medium"
    else:
        risk = "high"

    return BenignSuppressionResult(
        total_benign_events=total,
        suppressed_count=suppressed,
        noise_hit_count=len(matched_event_ids),
        suppression_rate=rate,
        noise_risk=risk,
        hits=hits,
    )
