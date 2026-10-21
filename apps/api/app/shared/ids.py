"""ID and evidence-reference helpers.

Evidence-reference format (shared contract, see packages/schemas):
    event:{event_id} | rule:{rule_id} | match:{match_id} | stage:{stage_id}

AI output may cite only IDs that were supplied in the request.
"""

import os
import time

EVIDENCE_KINDS = ("event", "rule", "match", "stage")


def new_id(prefix: str) -> str:
    """Sortable, collision-resistant ID: {prefix}_{unix_ms}_{random}."""
    return f"{prefix}_{int(time.time() * 1000):x}_{os.urandom(6).hex()}"


def make_evidence_ref(kind: str, entity_id: str) -> str:
    if kind not in EVIDENCE_KINDS:
        raise ValueError(f"unknown evidence kind: {kind}")
    return f"{kind}:{entity_id}"


def parse_evidence_ref(ref: str) -> tuple[str, str]:
    kind, _, entity_id = ref.partition(":")
    if kind not in EVIDENCE_KINDS or not entity_id:
        raise ValueError(f"malformed evidence reference: {ref}")
    return kind, entity_id