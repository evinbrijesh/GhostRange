# GhostRange Team Plan

**Team:** Evin and Athul  
**Project:** GhostRange  
**Hackathon track:** Best Apps and Agents  
**Primary scenario:** Cloud Identity Compromise  
**Document purpose:** Define ownership, repository handoff, collaboration procedure, and the ten-day engineering roadmap.

## 1. Team ownership

### Evin — Simulation, Detection Engine, and Backend

Evin owns the authoritative technical layer of GhostRange. This includes the scenario model, seven attack stages, seeded synthetic telemetry, normalized event schemas, the supported detection-rule syntax, the parser, the deterministic evaluator, stage-status calculation, coverage scoring, detection latency, persistence, backend APIs, backend tests, deployment configuration, and reproducibility.

Evin owns the answer to the question:

> Did the detection rule actually match the simulated evidence?

The backend must remain correct and useful even when the frontend or Nemotron integration is unavailable.

### Athul — Frontend, AI Workflow, and Product Experience

Athul owns the user-facing product and the AI-assisted workflow. This includes the dashboard, navigation, scenario view, run experience, attack graph, coverage visualization, telemetry explorer, detection-rule viewer, improvement workspace, rule diff, before/after comparison, report interface, loading and error states, visual design, Nebius Token Factory integration, Nemotron prompts, structured AI responses, and optional Tavily enrichment.

Athul owns the answer to the question:

> How do we make the validated result understandable, useful, and compelling?

The frontend must display backend results and must not independently calculate authoritative coverage.

## 2. Repository handoff: what Evin should complete first

Evin already has the repository created. Before sharing it with Athul, the repository should be a stable engineering foundation rather than an empty repository or an unfinished backend. The purpose of this handoff is to let both people start independently without repeatedly renegotiating file structure, API shapes, environment variables, or data contracts.

### Repository identity and documentation

The repository should contain the approved `PRD.md`, `MVP.md`, and `CLAUDE.md` files in the root or in the agreed documentation location. It should also contain a concise `README.md` that explains what GhostRange does, how the local system is structured, how to start the backend and frontend, how to run the seeded demo, and how the Nebius integration is configured.

The repository should include an open-source license, preferably MIT or Apache-2.0, because the hackathon requires a public repository with a visible open-source license. It should include `.gitignore`, `.env.example`, and a clear rule that real secrets must never be committed.

The README should distinguish deterministic demo mode from live Nemotron mode. Anyone should be able to launch the interface and inspect seeded synthetic results without a Nebius key, while AI explanation and proposal features should show a clear configuration message when the key is not present.

### Project scaffold

Evin should establish the agreed application boundaries before Athul begins feature work. The repository should have separate frontend and backend applications, shared schemas or types, scenario fixtures, documentation, and scripts. The exact tooling can be chosen by the team, but the responsibilities should remain separated:

```text
ghostrange/
├── apps/
│   ├── api/
│   └── web/
├── packages/
│   └── schemas/
├── scenarios/
│   └── cloud-identity-compromise/
├── docs/
│   ├── PRD.md
│   ├── MVP.md
│   └── TEAM_PLAN.md
├── scripts/
├── CLAUDE.md
├── README.md
├── LICENSE
├── .env.example
└── .gitignore
```

The backend should expose a health endpoint and a minimal scenario endpoint before handoff. The frontend should be able to start against a mock or seeded API response even if the complete simulation engine is still being implemented.

### Shared contracts

Before Athul builds the real interface, Evin should publish the first version of the shared contracts. These contracts are more important than the initial implementation details because they allow parallel work.

The required contracts are the scenario object, run lifecycle, telemetry event, detection rule, rule match, stage result, coverage result, AI artifact, and rule proposal. They should be represented using typed models and, where practical, JSON Schema or generated TypeScript types.

The run lifecycle must be:

```text
queued → running → completed
                   ↘ failed
```

The only authoritative stage statuses are:

```text
detected
partial
missed
error
```

The backend must distinguish a security miss from an evaluator error. Athul should never need to infer this distinction from an empty response or a missing field.

### Scenario and fixture foundation

Evin should define the fictional cloud environment and the seven stages of the Cloud Identity Compromise scenario. The fixture must use fictional identities and resources and documentation-reserved IP addresses. Every generated event must carry a run ID, stage ID, UTC timestamp, and `synthetic: true` marker.

The default seed should intentionally produce a mixed result: some detections should match, at least one stage should be partial, and at least one important stage should be missed. This gives Athul a meaningful dashboard to present and gives the team a real remediation story for the demo.

### Deterministic backend slice

Before handoff, Evin should make the simulator and evaluator callable from a simple command or endpoint. Given the same scenario version, rules, and seed, the system should generate the same events and coverage result.

The first backend slice does not need to be complete, but it should prove the central technical path:

```text
scenario + rules + seed
        ↓
synthetic telemetry
        ↓
rule evaluation
        ↓
stage results and coverage
```

This gives Athul a reliable contract to integrate against instead of building a UI around imagined behavior.

### Development and quality foundation

The repository should define the development commands for installing dependencies, starting the backend, starting the frontend, seeding demo data, resetting the demo state, running tests, and formatting or linting code. These commands should work from a clean checkout.

Evin should add initial tests for scenario validation, deterministic event generation, rule parsing, and at least one detected and one missed stage. The goal is not to finish all tests before sharing; it is to prove that the deterministic layer is testable and that future changes can be checked.

A lightweight CI workflow should run formatting, type checks, unit tests, and a basic build. CI does not need deployment automation on the first day, but it should prevent the shared branch from silently becoming unbuildable.

### Environment configuration

The repository should include `.env.example` with variable names and safe placeholders only. The expected categories are database configuration, API origin, Nebius configuration, optional Tavily configuration, and frontend public configuration.

Secrets should be kept in each developer's local environment or the deployment platform's secret manager. Athul must not need access to Evin's personal keys, and Evin must not commit a key merely to make the frontend work.

### Handoff communication

When Evin shares the repository, he should send Athul a short handoff message containing the current branch or commit, the commands to run, the local URLs, the API contract location, the seed/reset command, the current known limitations, and the first frontend endpoint that is safe to integrate.

The handoff should explicitly state whether the current backend uses real persistence or an in-memory/demo repository. This prevents Athul from depending on behavior that is about to change.

## 3. Collaboration procedure after handoff

The team should use a contract-first, vertical-slice workflow. Evin does not need to finish the entire backend before Athul starts, and Athul does not need to wait for the complete AI workflow before building the product experience.

Athul should begin with typed mock data that follows the agreed backend contracts. Evin should continue replacing mock behavior with real seeded results behind the same contracts. This allows the UI and backend to progress simultaneously without forcing either person to guess the other's implementation.

Shared contract changes should be discussed before implementation. A change to event fields, run states, stage statuses, coverage structure, or evidence references affects both workstreams and should be recorded in a small architecture-decision note or pull request description.

### Contract Change Log

1. **Scenario Environment Contract Addition (Day 5 / Builder B & A)**
   - **Old shape:** `Scenario` without `environment` property in `packages/schemas`.
   - **New shape:** `Scenario` includes `environment: { organization: string, compromisedIdentity: string, note: string }`.
   - **Reason:** Surface fictional cloud environment context from the scenario metadata cleanly in the frontend rather than hardcoding in UI cards.
   - **Affected schemas & screens:** `packages/schemas/json/scenario.schema.json`, `packages/schemas/ts/contracts.ts`, `ScenarioHub.tsx`, backend `ScenarioEnvironment` model. Reviewed and recorded.

2. **AIArtifact Persistence & Output Mapping (Day 6 / Builder A)**
   - **Old shape:** `POST /api/runs/{run_id}/explanations` returned non-persisted ephemeral explanation objects.
   - **New shape:** `AiArtifact` persistence added in SQLite & memory repositories (`ai_artifacts` table). Endpoint persists artifacts with schema-conforming `output` payload, `model: null` for fallbacks, and surfaces `GET /api/runs/{run_id}/explanations` and `GET /api/runs/{run_id}/ai-artifacts`.
   - **Reason:** Audit trail and incident readiness report summarization require persistent AI artifacts.

3. **AI Rule Proposals Generation Route (Day 6 / Builder A)**
   - **Endpoint:** `POST /api/runs/{run_id}/rule-proposals/generate` (aliased to `/ai-generate`).
   - **Request:** `{ originalRuleId: string, eventId?: string }`.
   - **Response:** `RuleProposal` object with embedded `aiArtifact: AiArtifact`.
   - **Behavior:** Prompts NVIDIA Nemotron via Nebius Token Factory with exact mismatch telemetry. Returns valid Sigma YAML in the documented subset, creates a persisted `RuleProposal`, and stores an `AIArtifact(task_type="rule_proposal")`. Operates in deterministic fallback when unconfigured.

4. **AI Executive Incident Report Summary Route (Day 6 / Builder A)**
   - **Endpoints:** `POST /api/runs/{run_id}/report/summary` and `GET /api/runs/{run_id}/report`.
   - **Behavior:** `POST /api/runs/{run_id}/report/summary` calls Nemotron to synthesize incident progression, detection blind spots, and validated remediation gains into `aiSummary: AiArtifact`. The artifact is persisted and returned directly in `RunReport.aiSummary` on subsequent `GET` requests.

5. **Cumulative Proposal Validation (Day 6 / Builder A)**
   - **Endpoint:** `POST /api/runs/{run_id}/rule-proposals/{proposal_id}/validate?cumulative=true`.
   - **Behavior:** When `cumulative=true`, applies all previously validated improving proposals on that run cumulatively. Demonstrates compound posture improvements (e.g., 50% → 60% → 75%). Defaults to `false` for independent validation against baseline.

6. **Tavily Live Threat Intelligence Search (Day 6 / Builder A)**
   - **Endpoints:** `GET /api/threat-intel/stages/{stage_id}` and `GET /api/threat-intel/search`.
   - **Behavior:** Queries Tavily API for emerging adversary TTPs, active campaigns, and detection guidance when `TAVILY_API_KEY` is present. Falls back to curated MITRE ATT&CK reference data when unconfigured. External reference only; never alters simulation evidence.

The ownership boundary is strict: Evin determines whether something was detected; Athul determines how that result is presented and explained. Nemotron can support the explanation layer, but neither the frontend nor the model may override Evin's deterministic result.

## 4. Branch and integration procedure

Use `main` as the always-runnable integration branch. Evin can work on backend branches such as `feat/simulation-engine`, `feat/rule-evaluator`, or `feat/api-runs`. Athul can work on branches such as `feat/dashboard`, `feat/attack-graph`, or `feat/ai-workflow`.

Keep commits narrow and descriptive. Prefer commits such as `feat: add seeded cloud identity scenario`, `feat: implement stage coverage`, `feat: add attack graph`, and `feat: integrate Nemotron explanations`.

Merge into `main` at least once per day after the relevant checks pass. Avoid a final-day merge of two large, independently evolved systems. Integration should happen in vertical slices: first run creation and graph data, then telemetry inspection, then rule improvement, then reports.

When a pull request changes a shared contract, the author should include the old shape, the new shape, the reason for the change, and the files or screens that need to be updated. This keeps the collaboration lightweight while preventing silent mismatches.

## 5. Ten-day engineering roadmap

### Phase 1: Foundation and contract alignment — Day 1

Evin establishes the scenario definition, shared schemas, initial deterministic simulator, repository commands, and backend health path. Athul establishes the frontend shell, navigation, visual direction, and typed mock data. Both confirm the run lifecycle, status vocabulary, evidence-reference format, and API naming.

The outcome of this phase is not a polished product. It is a shared foundation where both developers can work without blocking each other.

### Phase 2: Independent core systems — Days 2 and 3

Evin implements seeded telemetry generation, the supported rule syntax, parser validation, event matching, stage mapping, and initial coverage calculations. Athul builds the overview, scenario screen, run interface, attack graph, coverage cards, and telemetry explorer using the shared contracts.

By the end of this phase, Evin should be able to run the simulation outside the browser, while Athul should have a navigable product experience populated with representative results.

### Phase 3: First vertical integration — Day 4

Evin exposes scenario, run, graph, telemetry, and coverage endpoints. Athul replaces the relevant mock data with real API calls and adds run-status refresh or polling. The team should be able to click Run, receive a real backend result, and view the resulting attack graph and coverage breakdown.

This is the first important integration milestone. Any instability discovered here should be fixed before adding AI features.

### Phase 4: Remediation loop — Days 5 and 6

Evin finalizes rule mismatch details, proposal validation, before/after comparison, and persistence for run artifacts. Athul builds the detection workspace, improvement view, rule diff, and comparison experience.

The team should now have the core GhostRange story working without depending on external threat intelligence: simulate, detect, inspect a gap, validate a rule improvement, and compare results.

### Phase 5: Nemotron and report experience — Days 7 and 8

Athul integrates Nemotron through Nebius Token Factory for evidence-grounded explanations, supported rule proposals, and report summaries. Evin supplies structured evidence objects and validates all proposed rules using the deterministic parser and evaluator.

The report experience should present technical findings, executive language, evidence references, assumptions, and limitations. Tavily should be added only if the core AI flow is stable; it is an enhancement, not a dependency for the product narrative.

### Phase 6: Stabilization and delivery — Days 9 and 10

Evin focuses on reproducibility, error handling, clean-install behavior, backend deployment, and final tests. Athul focuses on visual polish, accessibility, responsive behavior, report presentation, demo copy, and video preparation.

Both developers perform a clean end-to-end run from the shared branch, verify the Nebius/Nemotron usage path, confirm that the repository is public-ready, and rehearse the three-minute demonstration. No new major feature should be introduced during this phase.

## 6. Definition of a successful collaboration

The collaboration is working when both developers can work independently for most of the day, shared contracts change deliberately, the integration branch remains runnable, and neither developer needs to duplicate the other's domain logic.

The final product should make the division of responsibility visible in the architecture: deterministic simulation and evaluation on one side, professional product experience and evidence-grounded AI assistance on the other.

GhostRange should be presented as a single coherent product, not as a backend demo with a separate dashboard. The strongest demo is the complete shared workflow:

```text
Run a safe simulation
        ↓
Measure detection coverage
        ↓
Inspect synthetic evidence
        ↓
Explain a blind spot with Nemotron
        ↓
Validate a proposed rule
        ↓
Prove the improvement
```
