"""Nebius Token Factory client for NVIDIA Nemotron inference.

Handles runtime calls to Nebius, structured JSON extraction, and safe fallback
when NEBIUS_API_KEY is not configured or Nebius API is unreachable.

Fallback analysis is deterministic and never labelled as model output.
"""

import json
import logging
import re
from typing import Any

import httpx

from app.ai.prompts import (
    SYSTEM_PROMPT_EXPLANATION,
    SYSTEM_PROMPT_REPORT_SUMMARY,
    SYSTEM_PROMPT_RULE_PROPOSAL,
    build_report_summary_prompt,
    build_rule_proposal_prompt,
    build_stage_explanation_prompt,
)
from app.config import settings
from app.domain.detections.parser import parse_rule

logger = logging.getLogger(__name__)


def _action_to_snake(action: str) -> str:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", action)
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).lower().strip("_")


def _mismatch_details(mismatches: list[dict]) -> list[str]:
    details: list[str] = []
    for mismatch in mismatches:
        for expr in mismatch.get("failed_expressions", []):
            details.append(
                f"Field '{expr.get('field')}' failed check ({expr.get('operator')}): "
                f"expected '{expr.get('expected')}', but event had '{expr.get('actual')}'"
            )
    return details


def _deterministic_remediation(
    stage_id: str, events: list[dict], mismatches: list[dict]
) -> str:
    if mismatches:
        mismatch = mismatches[0]
        rule_id = mismatch.get("rule_id")
        failed = mismatch.get("failed_expressions") or []
        if failed:
            expr = failed[0]
            return (
                f"Update rule '{rule_id}' so its '{expr.get('field')}' check matches the "
                f"observed value '{expr.get('actual')}' (the baseline expects "
                f"'{expr.get('expected')}')."
            )
        return f"Review rule '{rule_id}' against the telemetry recorded for stage {stage_id}."

    actions = sorted(
        {
            event.get("action")
            for event in events
            if event.get("expected") and isinstance(event.get("action"), str)
        }
    )
    if actions:
        return (
            f"Add a stage-specific detection rule covering the expected actions observed "
            f"for {stage_id}: {', '.join(actions)}."
        )
    return f"Add a stage-specific detection rule for the expected activity in {stage_id}."


def _deterministic_fallback(
    stage_id: str,
    stage_name: str,
    status: str,
    events: list[dict],
    rules: list[dict],
    mismatches: list[dict],
    input_evidence_ids: list[str],
    ai_note: str | None,
) -> dict[str, Any]:
    valid_evidence = set(input_evidence_ids)
    cited: list[str] = []
    for mismatch in mismatches:
        for evidence_id in (
            f"rule:{mismatch.get('rule_id')}",
            f"event:{mismatch.get('event_id')}",
        ):
            if evidence_id in valid_evidence and evidence_id not in cited:
                cited.append(evidence_id)

    details = _mismatch_details(mismatches)
    if details:
        gap_analysis = "Deterministic evaluator rejected rule matching: " + "; ".join(details) + "."
    elif status == "missed":
        gap_analysis = (
            f"The evaluator recorded no rule mismatch for {stage_id}; no loaded rule "
            "currently targets this stage's expected events."
        )
    else:
        gap_analysis = f"The evaluator recorded no rule mismatch for stage {stage_id}."

    prefix = ""
    if ai_note:
        prefix = f"AI analysis unavailable ({ai_note}). "
    summary = (
        f"{prefix}Deterministic fallback analysis: attack stage {stage_id} "
        f"({stage_name}) was {status} in the simulated run."
    )

    return {
        "status": "failed" if ai_note else "unavailable",
        "model": None,
        "summary": summary,
        "gap_analysis": gap_analysis,
        "recommended_remediation": _deterministic_remediation(stage_id, events, mismatches),
        "input_evidence_ids": input_evidence_ids,
        "cited_evidence_ids": cited,
    }


def explain_stage_with_nemotron(
    stage_id: str,
    stage_name: str,
    status: str,
    events: list[dict],
    rules: list[dict],
    mismatches: list[dict],
) -> dict[str, Any]:
    """Generate an evidence-grounded explanation for a stage.

    With Nebius configured, a live model call is attempted. The returned
    ``cited_evidence_ids`` are always a subset of the evidence supplied in
    ``input_evidence_ids``; the client never invents or backfills citations.
    When the call is unavailable or its output is ungrounded, deterministic
    analysis is returned with ``model: null``.
    """
    input_evidence_ids = [f"event:{event.get('id')}" for event in events] + [
        f"rule:{rule.get('id')}" for rule in rules
    ]
    valid_evidence_ids = set(input_evidence_ids)

    ai_note: str | None = None
    if settings.nebius_api_key:
        try:
            model = settings.nebius_model or "nvidia/nemotron-4-340b-instruct"
            prompt = build_stage_explanation_prompt(
                stage_id, stage_name, status, events, rules, mismatches
            )
            headers = {
                "Authorization": f"Bearer {settings.nebius_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_EXPLANATION},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }
            with httpx.Client(timeout=25.0) as client:
                res = client.post(
                    f"{settings.nebius_base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                res.raise_for_status()
                content = res.json()["choices"][0]["message"]["content"]
                parsed = json.loads(content)

            summary = parsed.get("summary")
            gap_analysis = parsed.get("gap_analysis")
            remediation = parsed.get("recommended_remediation")
            cited_raw = parsed.get("cited_evidence_ids")
            if not all(isinstance(value, str) for value in (summary, gap_analysis, remediation)):
                raise ValueError("model response fields are not strings")
            if not isinstance(cited_raw, list) or not all(
                isinstance(cid, str) for cid in cited_raw
            ):
                raise ValueError("model citations are not a list of strings")

            cited = [cid for cid in cited_raw if cid in valid_evidence_ids]
            if not cited:
                ai_note = "the model output cited no valid evidence and was rejected"
            else:
                return {
                    "status": "succeeded",
                    "model": model,
                    "summary": summary,
                    "gap_analysis": gap_analysis,
                    "recommended_remediation": remediation,
                    "input_evidence_ids": input_evidence_ids,
                    "cited_evidence_ids": cited,
                }
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "Nebius Token Factory call failed (%s); using deterministic fallback",
                type(exc).__name__,
            )
            ai_note = "the model call failed"

    return _deterministic_fallback(
        stage_id=stage_id,
        stage_name=stage_name,
        status=status,
        events=events,
        rules=rules,
        mismatches=mismatches,
        input_evidence_ids=input_evidence_ids,
        ai_note=ai_note,
    )


# --- AI Rule Proposals ---


def _deterministic_proposal_fallback(
    stage_id: str,
    original_rule: dict,
    mismatched_event: dict,
    input_evidence_ids: list[str],
    ai_note: str | None = None,
) -> dict[str, Any]:
    action = mismatched_event.get("action", "ExpectedAction")
    service = mismatched_event.get("source", "iam")
    snake_act = _action_to_snake(action)
    product = original_rule.get("logsource", {}).get("product", "cloud")
    level = original_rule.get("level", "high")

    proposed_source = f"""title: Detect {action}
id: rule_{stage_id.lower()}_{snake_act}
stage: {stage_id}
logsource:
  product: {product}
  service: {service}
selection:
  action: {action}
condition: selection
level: {level}"""

    cited = [cid for cid in input_evidence_ids if cid.startswith(("event:", "rule:"))]
    prefix = f"AI proposal unavailable ({ai_note}). " if ai_note else ""
    event_id = mismatched_event.get("id", "event")
    rule_id = original_rule.get("id", "rule")
    rationale = (
        f"{prefix}Deterministic rule proposal: Telemetry event {event_id} contained "
        f"action '{action}', which bypassed starter rule '{rule_id}'. This proposal "
        f"updates selection to detect the observed action directly."
    )

    return {
        "status": "failed" if ai_note else "unavailable",
        "model": None,
        "proposed_source": proposed_source,
        "rationale": rationale,
        "input_evidence_ids": input_evidence_ids,
        "cited_evidence_ids": cited,
    }


def propose_rule_with_nemotron(
    stage_id: str,
    stage_name: str,
    original_rule: dict,
    mismatched_event: dict,
    mismatches: list[dict],
) -> dict[str, Any]:
    """Generate an improved Sigma detection rule using Nemotron or deterministic fallback."""
    input_evidence_ids = [
        f"event:{mismatched_event.get('id')}",
        f"rule:{original_rule.get('id')}",
    ]
    valid_evidence_ids = set(input_evidence_ids)

    ai_note: str | None = None
    if settings.nebius_api_key:
        try:
            model = settings.nebius_model or "nvidia/nemotron-4-340b-instruct"
            prompt = build_rule_proposal_prompt(
                stage_id, stage_name, original_rule, mismatched_event, mismatches
            )
            headers = {
                "Authorization": f"Bearer {settings.nebius_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_RULE_PROPOSAL},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }
            with httpx.Client(timeout=25.0) as client:
                res = client.post(
                    f"{settings.nebius_base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                res.raise_for_status()
                content = res.json()["choices"][0]["message"]["content"]
                parsed = json.loads(content)

            proposed_source = parsed.get("proposed_source")
            rationale = parsed.get("rationale")
            cited_raw = parsed.get("cited_evidence_ids")
            if not isinstance(proposed_source, str) or not isinstance(rationale, str):
                raise TypeError("model response fields are not strings")
            if not isinstance(cited_raw, list) or not all(
                isinstance(cid, str) for cid in cited_raw
            ):
                raise TypeError("model citations are not a list of strings")

            cited = [cid for cid in cited_raw if cid in valid_evidence_ids]
            if not cited:
                ai_note = "the model output cited no valid evidence and was rejected"
            else:
                # Verify proposed YAML is valid in the documented subset
                parsed_rule, _ = parse_rule(proposed_source)
                if parsed_rule.parser_status != "valid":
                    ai_note = (
                        f"the model proposed invalid rule syntax: "
                        f"{'; '.join(parsed_rule.parser_errors)}"
                    )
                else:
                    return {
                        "status": "succeeded",
                        "model": model,
                        "proposed_source": proposed_source,
                        "rationale": rationale,
                        "input_evidence_ids": input_evidence_ids,
                        "cited_evidence_ids": cited,
                    }
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "Nebius Token Factory call failed (%s); using deterministic proposal fallback",
                type(exc).__name__,
            )
            ai_note = "the model call failed"

    return _deterministic_proposal_fallback(
        stage_id=stage_id,
        original_rule=original_rule,
        mismatched_event=mismatched_event,
        input_evidence_ids=input_evidence_ids,
        ai_note=ai_note,
    )


# --- AI Report Summary ---


def _deterministic_report_summary_fallback(
    scenario_name: str,
    run_id: str,
    coverage_score: float,
    stage_results: list[dict],
    improvements: list[dict],
    input_evidence_ids: list[str],
    ai_note: str | None = None,
) -> dict[str, Any]:
    valid_evidence = set(input_evidence_ids)
    cited = [cid for cid in input_evidence_ids if cid in valid_evidence]

    prefix = f"AI summary unavailable ({ai_note}). " if ai_note else ""
    missed_stages = [s.get("stage_id") for s in stage_results if s.get("status") == "missed"]

    executive_summary = (
        f"{prefix}Deterministic executive audit: Simulation run '{run_id}' for '{scenario_name}' "
        f"evaluated detection posture across {len(stage_results)} stages with baseline coverage of {coverage_score}%."
    )
    attack_narrative = (
        "The adversary executed a multi-stage cloud identity compromise beginning with initial access "
        "via anomalous authentication, followed by persistence and defense evasion through MFA configuration manipulation."
    )
    gaps_str = ", ".join(missed_stages) if missed_stages else "none"
    detection_gaps = (
        f"Critical detection gaps were identified in stages: {gaps_str}. Specifically, baseline rules "
        "failed to match due to mismatches in expected actions and parameters."
    )
    if improvements:
        remediation_impact = (
            f"Validated detection rule improvements addressed {len(improvements)} blind spot(s), "
            f"raising coverage from {improvements[0].get('coverage_before')}% to {improvements[0].get('coverage_after')}%."
        )
    else:
        remediation_impact = "No validated rule improvements were evaluated during this run."

    recommendations = [
        "Deploy detection rules targeting UpdateMfaPreference and MFA modification events.",
        "Implement correlation between anomalous geographic logins and administrative IAM changes.",
        "Enforce strict multi-person review on privileged role assumption.",
    ]

    return {
        "status": "failed" if ai_note else "unavailable",
        "model": None,
        "executive_summary": executive_summary,
        "attack_narrative": attack_narrative,
        "detection_gaps": detection_gaps,
        "remediation_impact": remediation_impact,
        "recommendations": recommendations,
        "input_evidence_ids": input_evidence_ids,
        "cited_evidence_ids": cited,
    }


def summarize_report_with_nemotron(
    scenario_name: str,
    scenario_version: str,
    run_id: str,
    seed: int,
    coverage_score: float,
    formula_version: str,
    stage_results: list[dict],
    improvements: list[dict],
) -> dict[str, Any]:
    """Generate an executive incident report summary using Nemotron or deterministic fallback."""
    input_evidence_ids = (
        [f"stage:{s.get('stage_id')}" for s in stage_results]
        + [f"rule:{imp.get('original_rule_id')}" for imp in improvements]
    )
    valid_evidence_ids = set(input_evidence_ids)

    ai_note: str | None = None
    if settings.nebius_api_key:
        try:
            model = settings.nebius_model or "nvidia/nemotron-4-340b-instruct"
            prompt = build_report_summary_prompt(
                scenario_name=scenario_name,
                scenario_version=scenario_version,
                run_id=run_id,
                seed=seed,
                coverage_score=coverage_score,
                formula_version=formula_version,
                stage_results=stage_results,
                improvements=improvements,
            )
            headers = {
                "Authorization": f"Bearer {settings.nebius_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_REPORT_SUMMARY},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }
            with httpx.Client(timeout=25.0) as client:
                res = client.post(
                    f"{settings.nebius_base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                res.raise_for_status()
                content = res.json()["choices"][0]["message"]["content"]
                parsed = json.loads(content)

            exec_summary = parsed.get("executive_summary")
            narrative = parsed.get("attack_narrative")
            gaps = parsed.get("detection_gaps")
            impact = parsed.get("remediation_impact")
            recs = parsed.get("recommendations")
            cited_raw = parsed.get("cited_evidence_ids")

            if not all(isinstance(v, str) for v in (exec_summary, narrative, gaps, impact)):
                raise TypeError("model summary fields are not strings")
            if not isinstance(recs, list) or not all(isinstance(r, str) for r in recs):
                raise TypeError("model recommendations are not a list of strings")
            if not isinstance(cited_raw, list) or not all(
                isinstance(cid, str) for cid in cited_raw
            ):
                raise TypeError("model citations are not a list of strings")

            cited = [cid for cid in cited_raw if cid in valid_evidence_ids]
            if not cited:
                ai_note = "the model output cited no valid evidence and was rejected"
            else:
                return {
                    "status": "succeeded",
                    "model": model,
                    "executive_summary": exec_summary,
                    "attack_narrative": narrative,
                    "detection_gaps": gaps,
                    "remediation_impact": impact,
                    "recommendations": recs,
                    "input_evidence_ids": input_evidence_ids,
                    "cited_evidence_ids": cited,
                }
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "Nebius Token Factory call failed (%s); using deterministic report fallback",
                type(exc).__name__,
            )
            ai_note = "the model call failed"

    return _deterministic_report_summary_fallback(
        scenario_name=scenario_name,
        run_id=run_id,
        coverage_score=coverage_score,
        stage_results=stage_results,
        improvements=improvements,
        input_evidence_ids=input_evidence_ids,
        ai_note=ai_note,
    )
