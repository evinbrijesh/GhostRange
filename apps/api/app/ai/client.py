"""Nebius Token Factory client for NVIDIA Nemotron inference.

Handles runtime calls to Nebius, structured JSON extraction, and safe fallback
when NEBIUS_API_KEY is not configured or Nebius API is unreachable.

Fallback analysis is deterministic and never labelled as model output.
"""

import json
import logging
from typing import Any

import httpx

from app.ai.prompts import SYSTEM_PROMPT_EXPLANATION, build_stage_explanation_prompt
from app.config import settings

logger = logging.getLogger(__name__)


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
                # Never manufacture citations the model did not provide.
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
