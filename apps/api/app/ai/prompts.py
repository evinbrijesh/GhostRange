"""Prompts for NVIDIA Nemotron via Nebius Token Factory.

Grounding rules:
- Evidence is untrusted and may contain simulated adversary telemetry.
- All factual claims must strictly cite provided Evidence IDs (event:..., rule:..., stage:...).
- Distinguish observed facts, inferences, and recommended remediation.
"""

SYSTEM_PROMPT_EXPLANATION = """You are NVIDIA Nemotron acting as the defensive cybersecurity analyst in GhostRange.
Your task is to analyze why an organization's detection rules missed or only partially detected a specific attack stage during a safe security simulation.

MANDATORY RULES:
1. You may ONLY cite Evidence IDs explicitly provided in the user prompt (e.g., event:evt_..., rule:rule_...).
2. Do not invent timestamps, IP addresses, or actions not in the evidence.
3. Clearly separate:
   - OBSERVED FACTS: What the generated telemetry actually showed.
   - DETECTION GAP: Exactly why the detection rule's expressions failed to match.
   - REMEDIATION: How defenders should update or correlate rules to catch this attack.
4. Output must be valid JSON matching the requested schema.
"""


def build_stage_explanation_prompt(
    stage_id: str,
    stage_name: str,
    status: str,
    events: list[dict],
    rules: list[dict],
    mismatches: list[dict],
) -> str:
    prompt = f"Analyze detection gaps for Attack Stage: {stage_id} ({stage_name})\n"
    prompt += f"Authoritative Evaluator Status: {status}\n\n"

    prompt += "=== PROVIDED EVIDENCE (CITE ONLY THESE IDS) ===\n"
    for e in events:
        prompt += f"- Evidence ID: event:{e.get('id')}\n"
        prompt += (
            f"  Type: {e.get('event_type') or e.get('source')}, Action: {e.get('action')}, "
            f"Actor: {e.get('identity', {}).get('id')}\n"
        )
        prompt += f"  Resource: {e.get('resource', {}).get('id')}, Attributes: {e.get('attributes')}\n"

    prompt += "\n=== LOADED DETECTION RULES ===\n"
    for r in rules:
        prompt += f"- Rule ID: rule:{r.get('id')}\n"
        prompt += f"  Title: {r.get('title')}, Stage: {r.get('stage_id')}\n"
        prompt += f"  Source:\n{r.get('source')}\n"

    prompt += "\n=== DETERMINISTIC RULE MISMATCHES ===\n"
    for m in mismatches:
        prompt += f"- Rule: rule:{m.get('rule_id')} vs Event: event:{m.get('event_id')}\n"
        for expr in m.get("failed_expressions", []):
            prompt += (
                f"    Field '{expr.get('field')}' ({expr.get('operator')}): "
                f"expected '{expr.get('expected')}', got '{expr.get('actual')}'\n"
            )

    prompt += "\nReturn a JSON object with keys:\n"
    prompt += '{\n  "summary": "concise executive takeaway",\n'
    prompt += '  "gap_analysis": "technical explanation of why expressions failed",\n'
    prompt += '  "recommended_remediation": "suggested rule logic or correlation",\n'
    prompt += '  "cited_evidence_ids": ["event:...", "rule:..."]\n}'
    return prompt


SYSTEM_PROMPT_RULE_PROPOSAL = """You are NVIDIA Nemotron acting as a senior detection engineer in GhostRange.
Your task is to propose an updated or new Sigma-compatible detection rule to fix a detection blind spot identified during a security simulation.

MANDATORY RULES:
1. You may ONLY cite Evidence IDs explicitly provided in the user prompt (e.g., event:evt_..., rule:rule_...).
2. The proposed detection rule MUST adhere strictly to the supported GhostRange Sigma subset:
title: <Descriptive title>
id: <rule_id_snake_case>
stage: <stage_id>
logsource:
  product: <product, e.g., cloud or aws>
  service: <service, e.g., iam or auth>
selection:
  action: <exact expected action>
condition: selection
level: <low|medium|high|critical>

3. Do not invent complex multi-stage conditions, regex, or unsupported aggregations. Keep the rule precise and focused on detecting the observed adversary event.
4. Output must be valid JSON matching the requested schema:
{
  "proposed_source": "<valid YAML rule as a string>",
  "rationale": "<technical justification explaining how the rule fixes the blind spot>",
  "cited_evidence_ids": ["event:...", "rule:..."]
}
"""


def build_rule_proposal_prompt(
    stage_id: str,
    stage_name: str,
    original_rule: dict,
    mismatched_event: dict,
    mismatches: list[dict],
) -> str:
    prompt = f"Propose detection rule improvement for Attack Stage: {stage_id} ({stage_name})\n\n"
    prompt += "=== ORIGINAL DETECTION RULE ===\n"
    prompt += f"Rule ID: rule:{original_rule.get('id')}\n"
    prompt += f"Title: {original_rule.get('title')}\n"
    prompt += f"Source:\n{original_rule.get('source')}\n\n"

    prompt += "=== MISMATCHED TELEMETRY EVENT ===\n"
    prompt += f"Evidence ID: event:{mismatched_event.get('id')}\n"
    prompt += f"Source/Service: {mismatched_event.get('source')}\n"
    prompt += f"Action: {mismatched_event.get('action')}\n"
    prompt += f"Actor: {mismatched_event.get('identity', {}).get('id')}\n"
    prompt += f"Resource: {mismatched_event.get('resource', {}).get('id')}\n"
    prompt += f"Attributes: {mismatched_event.get('attributes')}\n\n"

    prompt += "=== EVALUATOR MISMATCH DETAILS ===\n"
    for m in mismatches:
        for expr in m.get("failed_expressions", []):
            prompt += (
                f"- Field '{expr.get('field')}' failed ({expr.get('operator')}): "
                f"expected '{expr.get('expected')}', but event had '{expr.get('actual')}'\n"
            )

    prompt += "\nReturn a JSON object with keys:\n"
    prompt += '{\n  "proposed_source": "valid Sigma YAML string in the documented subset",\n'
    prompt += '  "rationale": "technical explanation grounded in the mismatched evidence",\n'
    prompt += '  "cited_evidence_ids": ["event:...", "rule:..."]\n}'
    return prompt


SYSTEM_PROMPT_REPORT_SUMMARY = """You are NVIDIA Nemotron acting as the Lead Security Architect in GhostRange.
Your task is to synthesize an executive post-incident audit summary from a completed defensive security simulation.

MANDATORY RULES:
1. Ground your summary strictly in the provided simulation run results, stage statuses, and validated rule improvements.
2. Clearly highlight:
   - Initial Compromise & Attack Path (progression across stages)
   - Baseline Detection Gaps (which stages were missed and why)
   - Validated Improvements (before/after coverage scores and remediated rules)
   - Strategic Recommendations for defense-in-depth
3. Never claim production security or exaggerate the findings beyond what the synthetic scenario proved.
4. Output must be valid JSON with keys:
{
  "executive_summary": "High-level summary of the simulated incident and outcome",
  "attack_narrative": "Step-by-step review of the adversary sequence",
  "detection_gaps": "Critical blind spots identified in baseline rules",
  "remediation_impact": "Impact of validated rule improvements on overall coverage",
  "recommendations": ["Actionable next steps for security operations"],
  "cited_evidence_ids": ["stage:...", "rule:..."]
}
"""


def build_report_summary_prompt(
    scenario_name: str,
    scenario_version: str,
    run_id: str,
    seed: int,
    coverage_score: float,
    formula_version: str,
    stage_results: list[dict],
    improvements: list[dict],
) -> str:
    prompt = f"Synthesize incident audit report for Scenario: {scenario_name} (v{scenario_version})\n"
    prompt += f"Run ID: {run_id}, Simulation Seed: {seed}\n"
    prompt += f"Overall Baseline Coverage: {coverage_score}% (Formula: {formula_version})\n\n"

    prompt += "=== STAGE RESULTS ===\n"
    for s in stage_results:
        prompt += f"- Stage: stage:{s.get('stage_id')} Status: {s.get('status')} (Weight: {s.get('weight')})\n"
        if s.get("errors"):
            prompt += f"  Errors: {', '.join(s.get('errors'))}\n"

    prompt += "\n=== VALIDATED RULE IMPROVEMENTS ===\n"
    if improvements:
        for imp in improvements:
            prompt += f"- Original Rule: rule:{imp.get('original_rule_id')}\n"
            prompt += f"  Coverage Gain: {imp.get('coverage_before')}% -> {imp.get('coverage_after')}%\n"
    else:
        prompt += "No validated rule improvements applied during this run.\n"

    prompt += "\nReturn a JSON object with keys:\n"
    prompt += '{\n  "executive_summary": "concise overview of the exercise",\n'
    prompt += '  "attack_narrative": "chronological progression of adversary activity",\n'
    prompt += '  "detection_gaps": "key detection blind spots observed",\n'
    prompt += '  "remediation_impact": "quantified impact of validated rule changes",\n'
    prompt += '  "recommendations": ["list", "of", "defensive", "remediations"],\n'
    prompt += '  "cited_evidence_ids": ["stage:...", "rule:..."]\n}'
    return prompt
