"""Tavily search client for external threat intelligence enrichment.

Connects to Tavily API for live ATT&CK / adversary campaign intelligence when
TAVILY_API_KEY is configured. Falls back to curated static MITRE ATT&CK reference
intel when unconfigured or unreachable.
"""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

CURATED_STAGE_INTEL: dict[str, dict[str, Any]] = {
    "S1": {
        "technique_id": "T1078.004",
        "name": "Valid Accounts: Cloud Accounts",
        "tactics": ["Initial Access", "Defense Evasion", "Persistence"],
        "description": (
            "Adversaries obtain and abuse existing cloud credentials to gain initial "
            "foothold without exploiting infrastructure vulnerabilities directly."
        ),
        "mitre_url": "https://attack.mitre.org/techniques/T1078/004/",
        "sample_adversaries": ["Scattered Spider", "Lapsus$", "APT29"],
    },
    "S2": {
        "technique_id": "T1556",
        "name": "Modify Authentication Process: Multi-Factor Authentication",
        "tactics": ["Defense Evasion", "Persistence"],
        "description": (
            "Adversaries modify user authentication preferences, enroll secondary devices, "
            "or update MFA parameters to evade future challenge checks."
        ),
        "mitre_url": "https://attack.mitre.org/techniques/T1556/",
        "sample_adversaries": ["Scattered Spider", "UNC3944", "Midnight Blizzard"],
    },
    "S3": {
        "technique_id": "T1087.004",
        "name": "Account Discovery: Cloud Account",
        "tactics": ["Discovery"],
        "description": (
            "Adversaries enumerate cloud identities, permissions, groups, and role trust "
            "policies to map privilege boundaries."
        ),
        "mitre_url": "https://attack.mitre.org/techniques/T1087/004/",
        "sample_adversaries": ["TeamTNT", "Kinsing", "Scattered Spider"],
    },
    "S4": {
        "technique_id": "T1098",
        "name": "Account Manipulation: Policy & Role Attachment",
        "tactics": ["Persistence", "Privilege Escalation"],
        "description": (
            "Adversaries attach administrator or high-privilege managed policies to existing "
            "or newly created accounts to escalate privileges."
        ),
        "mitre_url": "https://attack.mitre.org/techniques/T1098/",
        "sample_adversaries": ["Scattered Spider", "Midnight Blizzard"],
    },
    "S5": {
        "technique_id": "T1098.001",
        "name": "Additional Cloud Credentials",
        "tactics": ["Persistence"],
        "description": (
            "Adversaries generate long-lived API keys or secret access keys on service "
            "identities to survive password resets."
        ),
        "mitre_url": "https://attack.mitre.org/techniques/T1098/001/",
        "sample_adversaries": ["TeamTNT", "UNC3944", "Scattered Spider"],
    },
    "S6": {
        "technique_id": "T1530",
        "name": "Data from Cloud Storage",
        "tactics": ["Collection"],
        "description": (
            "Adversaries access object storage buckets and download sensitive databases, "
            "configuration files, and backups."
        ),
        "mitre_url": "https://attack.mitre.org/techniques/T1530/",
        "sample_adversaries": ["Kinsing", "Lapsus$", "Scattered Spider"],
    },
    "S7": {
        "technique_id": "T1074.002",
        "name": "Data Staged: Remote Data Staging",
        "tactics": ["Collection", "Exfiltration"],
        "description": (
            "Adversaries aggregate and stage collected artifacts into secondary buckets "
            "or external repositories prior to exfiltration."
        ),
        "mitre_url": "https://attack.mitre.org/techniques/T1074/002/",
        "sample_adversaries": ["Scattered Spider", "Lapsus$"],
    },
}


def search_threat_intel(stage_id: str | None = None, query: str | None = None) -> dict[str, Any]:
    """Search threat intel using Tavily API if configured, with curated fallback."""
    stage_key = stage_id.upper() if stage_id else "S2"
    curated = CURATED_STAGE_INTEL.get(stage_key, CURATED_STAGE_INTEL["S2"])

    search_query = (
        query
        if query
        else f"MITRE ATT&CK {curated['technique_id']} {curated['name']} cloud detection"
    )

    if settings.tavily_api_key:
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "api_key": settings.tavily_api_key,
                "query": search_query,
                "search_depth": "basic",
                "include_answer": True,
                "max_results": 3,
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post("https://api.tavily.com/search", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()

            answer = data.get("answer") or ""
            results = data.get("results") or []
            sources = [
                {
                    "title": r.get("title", "Threat Intelligence Reference"),
                    "url": r.get("url", curated["mitre_url"]),
                    "snippet": r.get("content", ""),
                }
                for r in results
            ]
            if not sources:
                sources = [{"title": curated["name"], "url": curated["mitre_url"], "snippet": curated["description"]}]

            return {
                "stageId": stage_key,
                "techniqueId": curated["technique_id"],
                "techniqueName": curated["name"],
                "tactics": curated["tactics"],
                "liveSearch": True,
                "summary": answer if answer else curated["description"],
                "adversaries": curated["sample_adversaries"],
                "sources": sources,
            }
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            logger.warning("Tavily search failed (%s); using curated fallback", type(exc).__name__)

    # Deterministic curated fallback
    return {
        "stageId": stage_key,
        "techniqueId": curated["technique_id"],
        "techniqueName": curated["name"],
        "tactics": curated["tactics"],
        "liveSearch": False,
        "summary": curated["description"],
        "adversaries": curated["sample_adversaries"],
        "sources": [
            {
                "title": f"MITRE ATT&CK {curated['technique_id']}: {curated['name']}",
                "url": curated["mitre_url"],
                "snippet": curated["description"],
            }
        ],
    }
