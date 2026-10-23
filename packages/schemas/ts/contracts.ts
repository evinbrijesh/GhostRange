/**
 * GhostRange shared contracts — TypeScript mirror of packages/schemas/json.
 *
 * These types are the single source of truth for the frontend. The JSON
 * Schemas in ../json are canonical; keep this file in sync when a contract
 * changes and record the change per TEAM_PLAN.md §3 (old shape, new shape,
 * reason, affected screens).
 */

// --- Vocabularies (must match common.schema.json) ---

export const RUN_STATUSES = ["queued", "running", "completed", "failed"] as const;
export type RunStatus = (typeof RUN_STATUSES)[number];

export const STAGE_STATUSES = ["detected", "partial", "missed", "error"] as const;
export type StageStatus = (typeof STAGE_STATUSES)[number];

export const STAGE_IDS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"] as const;
export type StageId = (typeof STAGE_IDS)[number];

export const EVENT_SOURCES = ["auth", "iam", "api", "storage", "network"] as const;
export type EventSource = (typeof EVENT_SOURCES)[number];

export const RULE_LEVELS = ["low", "medium", "high", "critical"] as const;
export type RuleLevel = (typeof RULE_LEVELS)[number];

export const PARSER_STATUSES = ["valid", "invalid"] as const;
export type ParserStatus = (typeof PARSER_STATUSES)[number];

export const AI_TASK_TYPES = ["explanation", "rule_proposal", "report_summary"] as const;
export type AiTaskType = (typeof AI_TASK_TYPES)[number];

export const AI_STATUSES = ["succeeded", "failed", "unavailable"] as const;
export type AiStatus = (typeof AI_STATUSES)[number];

export const PROPOSAL_STATUSES = ["proposed", "validated", "rejected", "accepted"] as const;
export type ProposalStatus = (typeof PROPOSAL_STATUSES)[number];

export const ERROR_CODES = [
  "VALIDATION_ERROR",
  "NOT_FOUND",
  "RUN_NOT_FOUND",
  "SCENARIO_NOT_FOUND",
  "INVALID_RUN_STATE",
  "RULE_PARSE_ERROR",
  "AI_UNAVAILABLE",
  "AI_OUTPUT_INVALID",
  "INTERNAL_ERROR",
] as const;
export type ErrorCode = (typeof ERROR_CODES)[number];

/** `event:{id}` | `rule:{id}` | `match:{id}` | `stage:{id}` */
export type EvidenceRef = string;

export type Iso8601Utc = string;

// --- Contracts ---

export interface ScenarioStage {
  id: StageId;
  name: string;
  description: string;
  /** Relative weight used by the coverage formula. */
  weight: number;
}

export interface Scenario {
  id: "cloud-identity-compromise-v1";
  name: string;
  description: string;
  version: string;
  seed: number;
  syntheticOnly: true;
  stages: ScenarioStage[];
}

export interface Run {
  id: string;
  scenarioId: string;
  scenarioVersion: string;
  seed: number;
  status: RunStatus;
  createdAt: Iso8601Utc;
  startedAt: Iso8601Utc | null;
  completedAt: Iso8601Utc | null;
  /** Set only when status is "failed". Safe message, no stack traces. */
  error: string | null;
}

export interface TelemetryEvent {
  id: string;
  runId: string;
  stageId: StageId;
  /** True for events the stage's coverage check requires; false for background noise. */
  expected: boolean;
  timestamp: Iso8601Utc;
  source: EventSource;
  identity: { id: string; type: string };
  action: string;
  resource: { id: string; type: string };
  /** Reserved documentation IP range only. */
  srcIp: string;
  attributes: Record<string, unknown>;
  synthetic: true;
}

export interface DetectionRule {
  id: string;
  version: string;
  title: string;
  stageId: StageId;
  logsource: { product: string; service: string };
  /** Raw YAML in the supported Sigma-like subset. */
  source: string;
  parserStatus: ParserStatus;
  /** Non-empty when parserStatus is "invalid". A parser error is not a security miss. */
  parserErrors: string[];
  level: RuleLevel | null;
  enabled: boolean;
}

export interface RuleMatch {
  id: string;
  runId: string;
  eventId: string;
  ruleId: string;
  stageId: StageId;
  matchedAt: Iso8601Utc;
  /** Which selection fields matched and how (exact/contains). */
  details: Record<string, unknown>;
}

export interface FailedExpression {
  field: string;
  operator: "exact" | "contains";
  /** What the rule wanted. */
  expected: string;
  /** What the event had; null when the field was absent on the event. */
  actual: string | null;
}

/** Why a specific rule did not match a specific expected event. */
export interface RuleMismatch {
  ruleId: string;
  eventId: string;
  failedExpressions: FailedExpression[];
}

export interface StageResult {
  stageId: StageId;
  status: StageStatus;
  expectedEventIds: string[];
  matchedEventIds: string[];
  matchedRuleIds: string[];
  /** First expected event -> first matching event; null when nothing matched. */
  detectionLatencyMs: number | null;
  evidenceIds: EvidenceRef[];
  /** Parser/evaluator errors for this stage; non-empty when status is "error". */
  errors: string[];
  /**
   * Why each valid stage rule did not match each unmatched expected event.
   * Capped at 50 per stage. Background events are never included.
   */
  mismatches: RuleMismatch[];
}

export interface CoverageResult {
  runId: string;
  /** 0–100, computed from stage weights. Never hard-coded in the frontend. */
  score: number;
  stageCounts: { detected: number; partial: number; missed: number; error: number };
  stages: StageResult[];
  formulaVersion: string;
  /** All parser/evaluation failures for the run, separate from security misses. */
  evaluatorErrors: string[];
}

export interface AiArtifact {
  id: string;
  runId: string;
  taskType: AiTaskType;
  /** The only IDs the model may cite in its output. */
  inputEvidenceIds: EvidenceRef[];
  /** Task-specific, schema-validated JSON. */
  output: Record<string, unknown>;
  model: string | null;
  status: AiStatus;
  validationErrors: string[];
  createdAt: Iso8601Utc;
}

export interface RuleProposal {
  id: string;
  runId: string;
  originalRuleId: string;
  /** Proposed YAML. Never auto-applied to the stored original rule. */
  proposedSource: string;
  rationale: string;
  status: ProposalStatus;
  validation: {
    parserStatus: ParserStatus;
    parserErrors: string[];
    /** Null until validated by the deterministic evaluator. */
    improvesCoverage: boolean | null;
    coverageBefore: number | null;
    coverageAfter: number | null;
  };
  createdAt: Iso8601Utc;
}

export interface ApiError {
  code: ErrorCode;
  message: string;
  details?: Record<string, unknown>;
}

// --- Report (GET /api/runs/{run_id}/report) ---

export interface ReportImprovement {
  proposalId: string;
  originalRuleId: string;
  improvesCoverage: boolean;
  coverageBefore: number;
  coverageAfter: number;
}

export interface RunReport {
  runId: string;
  scenario: { id: string; name: string; version: string };
  seed: number;
  generatedAt: Iso8601Utc;
  coverage: CoverageResult;
  /** Validated proposals only. Never-validated proposals are not improvements. */
  improvements: ReportImprovement[];
  /** Scenario assumptions the report's conclusions rest on. */
  assumptions: string[];
  /** Honest limitations. Reports must never overclaim production security. */
  limitations: string[];
  /** Nemotron executive summary (days 7-8). Null = unavailable; report stays valid. */
  aiSummary: AiArtifact | null;
}
