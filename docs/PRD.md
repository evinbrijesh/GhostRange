# GhostRange Product Requirements Document

**Product:** GhostRange  
**Document status:** Approved product direction  
**Hackathon track:** Best Apps and Agents  
**Primary platform:** Nebius Token Factory / Nebius AI Cloud  
**Primary model:** NVIDIA Nemotron  
**Initial scenario:** Cloud Identity Compromise

## 1. Product summary

GhostRange is a defensive security-control validation platform. It safely simulates a realistic cloud identity compromise, generates synthetic security telemetry, evaluates detection rules against that telemetry, identifies blind spots, and helps security teams improve and re-test their controls.

GhostRange is not a chatbot, an offensive scanner, or a live red-team tool. Its purpose is to answer one practical question:

> If this attack happened tomorrow, would our existing security controls detect it?

### Product pitch

> GhostRange turns security-control assumptions into measurable evidence by safely simulating attacks, testing detections, and proving coverage improvements.

## 2. Background and problem

Organizations invest in SIEM rules, cloud-audit detections, IAM monitoring, endpoint rules, and threat-intelligence feeds, but they often do not know whether those controls would identify a complete attack chain. A rule can look correct and still miss the important event, detect it too late, or fail when several events must be correlated.

Traditional validation is manual, disruptive, expensive, and difficult to reproduce. Waiting for a real incident is unacceptable. GhostRange creates a controlled testing loop in which defenders can simulate an attack, inspect the resulting evidence, measure detection coverage, fix gaps, and run the same scenario again.

## 3. Goals

GhostRange must provide a credible, safe, and repeatable way to:

- Model a cloud identity compromise as a sequence of attack stages.
- Generate realistic but clearly synthetic telemetry.
- Evaluate defensive detection rules using deterministic logic.
- Show exactly which stages were detected, partially detected, or missed.
- Explain detection gaps using NVIDIA Nemotron through Nebius Token Factory.
- Suggest improvements without silently changing the original rules.
- Validate proposed improvements and show a before/after result.
- Produce an evidence-linked technical and executive report.
- Establish an extensible scenario framework for future attack types.

## 4. Non-goals

The product will not:

- Access or modify real cloud environments.
- Scan public systems or launch attacks.
- Execute malware, exploit payloads, or destructive actions.
- Handle live credentials, real customer logs, or production secrets in the demo.
- Claim that a simulated result proves production security.
- Support every SIEM or the complete Sigma specification in the first release.
- Automatically remediate live security controls.

## 5. Target users

### Primary persona: Security engineer / SOC analyst

This user needs to validate whether cloud identity detections work before an incident. They care about evidence, repeatability, coverage, false positives, and actionable rule improvements.

### Secondary personas

MSSPs can use GhostRange to validate client detection programs. Security educators can use it to teach attack detection safely. Cloud platform teams can use it to test identity monitoring. Security leaders can use reports to understand measurable detection readiness.

## 6. Product principles

**Evidence before confidence:** Every important conclusion must be traceable to a generated event, rule, match, or evaluation result.

**Deterministic truth, AI assistance:** The rule engine determines whether a detection matched. Nemotron explains, proposes, and summarizes; it does not invent scores.

**Safe by construction:** The product uses fictional environments, synthetic events, reserved IP ranges, and no live target access.

**Reproducible validation:** A fixed scenario version and seed must produce the same events and evaluation result.

**Professional uncertainty:** The system must distinguish observed facts, model inferences, recommendations, parser errors, and unresolved limitations.

## 7. Initial product experience

A user opens GhostRange and sees the Cloud Identity Compromise scenario. The product explains that it is a synthetic, non-invasive simulation. The user starts a run, watches the seven-stage attack path complete, and receives a coverage score.

The user can inspect each stage, see the generated telemetry, identify which rule matched or failed, request a Nemotron explanation, review a proposed rule change, validate the proposal, and compare the original result with the improved result.

The ideal result is a visible, reproducible improvement such as:

```text
Before remediation: 41% detection coverage
After validated rule improvements: 83% detection coverage
```

The score must be calculated from real simulator output and evaluator matches, never hard-coded for presentation.

## 8. Initial scenario: Cloud Identity Compromise

The scenario models a fictional identity progressing through these stages:

1. **Initial access:** valid credentials are used from an unusual location.
2. **MFA manipulation:** an MFA method or security setting is changed.
3. **Discovery:** roles, users, and storage resources are enumerated.
4. **Privilege escalation:** a low-privilege identity receives an admin-capable role.
5. **Persistence:** a long-lived token or service credential is created.
6. **Sensitive access:** protected object storage is accessed.
7. **Data staging:** data is listed, copied, or prepared for transfer.

The scenario is provider-neutral for the MVP. The environment, identities, resources, events, and IP addresses are fictional.

## 9. Functional requirements

### FR-1: Scenario catalog

The system must show Cloud Identity Compromise as available. Future scenarios may be displayed as clearly labeled Coming Soon cards, but they must not appear functional.

### FR-2: Simulation runs

A user must be able to start a run. Each run must have a stable run ID, scenario version, seed, status, timestamps, and error field. Supported states are `queued`, `running`, `completed`, and `failed`.

### FR-3: Synthetic telemetry

The simulator must generate normalized authentication, IAM, API, storage, and network events for the scenario. Every event must be marked synthetic and linked to a stage and run ID.

### FR-4: Detection rules

The system must load and evaluate a documented Sigma-like YAML subset. Unsupported syntax must result in a useful parser error. The product must not claim full Sigma compatibility.

### FR-5: Coverage calculation

The system must calculate stage status, overall coverage, detection latency, matched rules, and evaluator errors. A stage is detected only when the deterministic evaluator finds a valid match.

### FR-6: Evidence inspection

A user must be able to inspect the events, rules, matches, and assumptions associated with a stage result.

### FR-7: AI explanations

Nemotron must explain a selected missed or partial stage using supplied evidence. The output must reference existing evidence IDs and distinguish facts from inferences.

### FR-8: Rule proposals

Nemotron may propose a rule or modification in the supported syntax. The original rule must remain unchanged until the user explicitly validates and accepts the proposal for comparison.

### FR-9: Proposal validation

The application must run a proposed rule through the local parser and deterministic evaluator. It must show whether the proposal improves coverage and whether parser or evaluation errors occurred.

### FR-10: Reporting

The system must export a technical report and an executive summary containing the scenario, run ID, coverage, stage results, evidence references, improvements, assumptions, and limitations.

### FR-11: Optional threat intelligence

Tavily may enrich a scenario with public threat context. This is optional and must not be required for the core demo. External sources must be labeled separately from synthetic evidence.

## 10. User interface requirements

The primary screens are Overview, Scenarios, Simulation Run, Attack Graph, Telemetry, Detections, Improvements, Reports, and Roadmap.

The attack graph must show the seven stages with both color and text status labels. Selecting a stage must open its evidence, matched rules, mismatch explanation, latency, and AI explanation.

The telemetry explorer must support filtering by event type, identity, resource, stage, timestamp, and detection status. It must show the normalized event and its readable interpretation.

The improvement workspace must show a rule diff, assumptions, validation status, and before/after coverage. It must never imply that a model suggestion was verified before deterministic validation.

## 11. Quality requirements

The core flow should be understandable in a three-minute demo. The product must have professional loading, empty, error, and degraded-AI states. It must be responsive enough for a laptop browser and accessible without relying on color alone.

A fixed seed must produce stable telemetry and scores. The product must be safe to run repeatedly. A clean checkout must be installable using documented commands.

## 12. Technology requirements

The product must make a real runtime call to NVIDIA Nemotron through Nebius Token Factory. Nebius Serverless Jobs may be used for asynchronous or parallel simulation work. The core deterministic evaluator should remain independent from model availability.

The recommended implementation is a React/TypeScript frontend, a Python/FastAPI backend, a deterministic simulation and rule-engine domain layer, and SQLite for the MVP with a persistence boundary that can later support PostgreSQL.

## 13. Success metrics

The hackathon MVP is successful when:

- A complete run finishes from a clean demo state.
- All seven stages are represented and inspectable.
- Coverage is calculated from actual matches.
- At least one meaningful detection gap is found.
- At least one proposed rule improves validated coverage.
- The before/after result is reproducible.
- AI explanations cite existing evidence.
- No live infrastructure is contacted.
- The repository, demo, video, and documentation clearly explain Nebius and Nemotron usage.

## 14. Future roadmap

After the MVP, GhostRange can add Ransomware Precursor Activity, OAuth and SaaS Token Abuse, Insider Data Exfiltration, AI-Agent Tool Abuse, Cloud Privilege Escalation, Supply-Chain Compromise, Kubernetes and Container Escape, Business Email Compromise, and Web Application Intrusion.

These are product expansion paths, not part of the initial implementation.
