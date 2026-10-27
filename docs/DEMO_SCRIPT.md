# GhostRange — 3-Minute Hackathon Demo Script & Presentation Guide

> **Track:** Best Apps and Agents  
> **Key Sponsor Integrations:** Nebius Token Factory (Platform), NVIDIA Nemotron (Model: `nvidia/nemotron-4-340b-instruct`), Tavily (Threat Intel Enrichment)  
> **Target Video Duration:** 3:00 (180 seconds)

---

## Quick Reference / Demo Flow Summary

| Time | Scene | On-Screen Action | Core Message |
|---|---|---|---|
| **0:00 – 0:35** | The Problem & Safety Premise | Attack Graph (50% baseline) | Safe simulation, zero invasive scanning, deterministic evaluation |
| **0:35 – 1:15** | Discovering the Blind Spot | Stage S2 drawer & Telemetry | Mismatch detected: `UpdateMfaPreference` bypassed starter rule |
| **1:15 – 1:55** | NVIDIA Nemotron via Nebius | Ask Nemotron for Fix | Grounded diagnosis & Sigma rule proposal citing real evidence IDs |
| **1:55 – 2:30** | Proving the Coverage Leap | Workspace Validation & Stacking | Local engine proves 50% → 60% → 75% coverage leap |
| **2:30 – 3:00** | Audit Report & Threat Intel | Incident Report & Tavily Tab | Executive AI summary & live Scattered Spider ATT&CK TTPs |

---

## Detailed Minute-by-Minute Script

### Scene 1: The Problem & Safety Premise (0:00 – 0:35)

**Visual:**
- Start on the **Attack Graph** view (`http://localhost:5173`).
- Show the 7-stage attack graph for **Cloud Identity Compromise** (`cloud-identity-compromise-v1`).
- Top banner shows: `Overall Coverage: 50.0%`, formula `coverage-v1`, simulation seed `1337`.

**Spoken Narration (Speaker):**
> *"Security teams spend millions on detection rules, but they usually only find out if their rules work when a real breach happens. Live penetration testing and offensive scanners are too slow, dangerous, and expensive to run on production cloud environments.*
>
> *This is GhostRange: a defensive security-control validation platform. GhostRange safely simulates complex cloud attacks—in this case, an identity compromise sequence—and generates 100% synthetic security telemetry. Every single event is marked `synthetic: true`. GhostRange never touches live infrastructure, yet evaluates detection rules with mathematical determinism."*

---

### Scene 2: The MFA Blind Spot (0:35 – 1:15)

**Visual:**
- Click on **Stage S2 (MFA manipulation)** on the Attack Graph.
- The stage detail drawer opens on the right.
- Point to the stage status: **MISSED (Score: 0%)**.
- Click to inspect the **Telemetry Event** (`evt_s2_03`) vs the **Loaded Rule** (`rule_s2_mfa_device_deletion`).

**Spoken Narration (Speaker):**
> *"In our baseline run, our loaded Sigma rules achieved only 50% detection coverage. Look at Stage 2: MFA Manipulation. It was completely missed.*
>
> *Why? Our starter rule was watching for `DeleteVirtualMfaDevice`. But the simulated adversary didn't delete the MFA device—they quietly called `UpdateMfaPreference` to bypass challenges. Our detection completely failed to alert, allowing the attacker to persist."*

---

### Scene 3: Evidence-Grounded NVIDIA Nemotron via Nebius (1:15 – 1:55)

**Visual:**
- Switch to the **Rule Improvement & Diff** tab (`RuleImprovementWorkspace`).
- Show the side-by-side mismatch view: Original starter rule on the left, rule editor on the right.
- Click the button: **"✨ Ask Nemotron for Fix"**.
- Watch the editor populate with Nemotron's structured Sigma YAML detection rule and technical rationale.
- Point out the provenance badge: `NVIDIA Nemotron (4-340B)` + `Evidence Grounded (Citations: event:evt_s2_03, rule:rule_s2_mfa_device_deletion)`.

**Spoken Narration (Speaker):**
> *"Here is where our AI integration shines. Hosted on Nebius Token Factory, we prompt NVIDIA Nemotron-4-340B to analyze this exact mismatch.*
>
> *Nemotron isn't hallucinating or making up IPs—it operates under strict evidence-grounding constraints, citing only verified telemetry IDs from the simulation. Nemotron instantly diagnoses the blind spot and authors a production-ready Sigma detection rule targeting `UpdateMfaPreference`."*

---

### Scene 4: Deterministic Validation & Compound Posture Leap (1:55 – 2:30)

**Visual:**
- In the workspace, point to the checkbox: **"Stack with prior improvements"** (checked).
- Click **"Validate Draft (Local Engine)"**.
- The evaluation spinner runs, and the result card updates in green:
  - **`50.0% → 60.0% (+10.0% coverage gain)`**.
- Select the next blind spot (Stage S6 — Storage Access). Click **"✨ Ask Nemotron for Fix"** and click **"Validate Draft"**.
- Watch coverage jump cumulatively:
  - **`60.0% → 75.0% (+15.0% cumulative coverage gain)`**.

**Spoken Narration (Speaker):**
> *"Crucially, in GhostRange, the AI model NEVER decides the score. The local deterministic evaluator is the sole source of truth.*
>
> *We validate the proposed rule against the simulation telemetry. Immediately, our coverage jumps from 50% to 60%! And with cumulative validation, fixing the second blind spot in Stage 6 compounds our defensive posture to 75%. Defenders can tangibly prove their security gains before pushing rules to production SIEMs."*

---

### Scene 5: Incident Audit Report & Tavily Threat Intel (2:30 – 3:00)

**Visual:**
- Switch to the **Incident Audit Report** tab.
- Click **"✨ AI Executive Briefing"**.
- Show the synthesized **AI Executive Assessment**:
  - Executive takeaway.
  - Simulated Attack Narrative.
  - Quantified Posture Leap (**50% → 75%**).
  - Strategic SOC recommendations.
- Switch to the **Threat Intel** tab.
- Show the stage technique cards and point out the **Tavily Live Search** badge, active adversary campaigns (e.g. *Scattered Spider*, *UNC3944*), and external reference sources.

**Spoken Narration (Speaker):**
> *"Finally, Nemotron compiles an executive incident-readiness audit report, translating technical rule diffs into a CISO-ready briefing with clear post-incident action items.*
>
> *Enriched with live adversary threat intelligence from Tavily, security leaders see exactly how real-world threat actors like Scattered Spider execute these TTPs.*
>
> *GhostRange transforms detection engineering from reactive firefighting into proactive, validated defense. Thank you!"*

---

## Rehearsal & Setup Checklist

1. **Pre-seed Demo Run:**
   ```bash
   ./scripts/seed.sh
   ```
2. **Start Backend (Port 8000):**
   ```bash
   cd apps/api && uv run uvicorn app.main:app --port 8000
   ```
3. **Start Frontend (Port 5173):**
   ```bash
   cd apps/web && npm run dev
   ```
4. **Browser Tab Checklist:**
   - Tab 1: `http://localhost:5173` (GhostRange Web UI).
   - Screen resolution: 1080p (1920x1080), browser zoomed to 110% for readable code diffs.
