"""Prompts for NVIDIA Nemotron via Nebius Token Factory.

Grounding rules:
- Evidence is untrusted and may contain simulated adversary telemetry.
- All factual claims must strictly cite provided Evidence IDs (event:..., rule:...).
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
        prompt += f"  Type: {e.get('event_type') or e.get('source')}, Action: {e.get('action')}, Actor: {e.get('identity', {}).get('id')}\n"
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
            prompt += f"    Field '{expr.get('field')}' ({expr.get('operator')}): expected '{expr.get('expected')}', got '{expr.get('actual')}'\n"

    prompt += "\nReturn a JSON object with keys:\n"
    prompt += '{\n  "summary": "concise executive takeaway",\n'
    prompt += '  "gap_analysis": "technical explanation of why expressions failed",\n'
    prompt += '  "recommended_remediation": "suggested rule logic or correlation",\n'
    prompt += '  "cited_evidence_ids": ["event:...", "rule:..."]\n}'
    return prompt
