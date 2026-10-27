"""Report assembly from deterministic results.

The report is built ONLY from stored, authoritative data: the run, the
scenario, the stored coverage, and validated proposals. The AI summary is an
optional artifact slot (days 7-8) — its absence never invalidates the report.

Limitations are part of the contract: every report states what the result
does NOT prove. Never overclaim production security.
"""

from app.domain.reports.models import ReportImprovement, ReportScenario, RunReport
from app.persistence.models import RuleProposal
from app.persistence.repository import RunRecord

# Honest, static limitations for the MVP. These state what a simulated result
# does not prove; they must never be removed to make a report look stronger.
MVP_LIMITATIONS = [
    ("All telemetry is synthetic and generated from a fictional scenario; "
     "results do not prove production security."),
    ("Detection rules use a small documented Sigma-like subset, not full Sigma; "
     "unsupported syntax fails validation rather than silently degrading."),
    ("Only the Cloud Identity Compromise scenario is implemented; other "
     "scenario types are roadmap items."),
    ("Coverage is measured against the scenario's expected events and stage "
     "weights; real-world detection coverage may differ."),
    ("AI-generated explanations and summaries are model output, clearly "
     "separated from deterministic results, and may be unavailable."),
]

# Assumptions the scenario's conclusions rest on (mirrors the fixture).
MVP_ASSUMPTIONS = [
    ("The simulated identity (user-alice-morgan) is the only compromised "
     "identity; all other identities are benign."),
    ("Attack-stage events occur in the documented order within the simulated "
     "incident window."),
    ("Stage weights reflect the scenario author's judgment of relative "
     "importance, not a universal standard."),
    "Reserved documentation IP ranges stand in for real network origins.",
]


def build_report(
    record: RunRecord,
    proposals: list[RuleProposal],
    ai_summary: dict | None = None,
) -> RunReport:
    """Assemble the report. `proposals` comes from the caller's storage lookup;
    only validated, improving proposals count as improvements."""
    assert record.coverage is not None
    improvements = [
        ReportImprovement(
            proposal_id=p.id,
            original_rule_id=p.original_rule_id,
            improves_coverage=bool(p.validation.improves_coverage),
            coverage_before=p.validation.coverage_before or 0.0,
            coverage_after=p.validation.coverage_after or 0.0,
        )
        for p in proposals
        if p.status == "validated" and p.validation.improves_coverage is True
    ]
    return RunReport(
        run_id=record.run.id,
        scenario=ReportScenario(
            id=record.scenario.id,
            name=record.scenario.name,
            version=record.scenario.version,
        ),
        seed=record.run.seed,
        generated_at=record.run.completed_at or record.run.created_at,
        coverage=record.coverage,
        improvements=improvements,
        assumptions=list(MVP_ASSUMPTIONS),
        limitations=list(MVP_LIMITATIONS),
        ai_summary=ai_summary,
    )