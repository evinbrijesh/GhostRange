import type {
  CoverageResult,
  DetectionRule,
  Iso8601Utc,
  RuleProposal,
  Run,
  RunReport,
  Scenario,
  StageResult,
  TelemetryEvent,
} from "../../../../packages/schemas/ts/contracts";

export interface StageDetail {
  runId: string;
  stageId: string;
  name: string;
  description: string;
  result: StageResult;
  events: TelemetryEvent[];
}

const API_BASE = "";

export interface ScenarioSummary {
  id: string;
  name: string;
  version: string;
  stageCount: number;
  available: boolean;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  ai_configured: boolean;
}

export interface RunGraphStage {
  stageId: string;
  name: string;
  status: "detected" | "partial" | "missed" | "error";
  detectionLatencyMs: number | null;
  matchedRuleIds: string[];
}

export interface RunGraphResponse {
  runId: string;
  scenarioId: string;
  stages: RunGraphStage[];
}

export interface TelemetryResponse {
  runId: string;
  total: number;
  events: TelemetryEvent[];
}

export interface RulesResponse {
  runId: string;
  rules: DetectionRule[];
}

export interface ProposalsResponse {
  runId: string;
  proposals: RuleProposal[];
}

export interface ExplanationResponse {
  id: string;
  runId: string;
  stageId: string;
  taskType: "explanation";
  status: "succeeded" | "failed" | "unavailable";
  model: string | null;
  inputEvidenceIds: string[];
  explanation: {
    summary: string;
    stageName: string;
    status: string;
    evidenceObserved: Array<{
      evidenceId: string;
      description: string;
    }>;
    gapAnalysis: string;
    recommendedRemediation: string;
    assumptions: string[];
  };
  createdAt: Iso8601Utc;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  const res = await fetch(`${API_BASE}/api/scenarios`);
  if (!res.ok) throw new Error(`Failed to load scenarios: ${res.statusText}`);
  return res.json();
}

export async function fetchScenario(scenarioId: string): Promise<Scenario> {
  const res = await fetch(`${API_BASE}/api/scenarios/${scenarioId}`);
  if (!res.ok) throw new Error(`Failed to load scenario ${scenarioId}: ${res.statusText}`);
  return res.json();
}

export async function createRun(scenarioId: string, seed?: number): Promise<Run> {
  const res = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenarioId, seed }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || "Failed to create simulation run");
  }
  return res.json();
}

export async function fetchRun(runId: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch run ${runId}`);
  return res.json();
}

export async function fetchRunGraph(runId: string): Promise<RunGraphResponse> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/graph`);
  if (!res.ok) throw new Error(`Failed to fetch run graph for ${runId}`);
  return res.json();
}

export async function fetchRunCoverage(runId: string): Promise<CoverageResult> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/coverage`);
  if (!res.ok) throw new Error(`Failed to fetch coverage for ${runId}`);
  return res.json();
}

export async function fetchRunTelemetry(
  runId: string,
  filters?: { stage?: string; source?: string; expected?: boolean }
): Promise<TelemetryResponse> {
  const params = new URLSearchParams();
  if (filters?.stage) params.set("stage", filters.stage);
  if (filters?.source) params.set("source", filters.source);
  if (filters?.expected !== undefined) params.set("expected", String(filters.expected));

  const qs = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/api/runs/${runId}/telemetry${qs}`);
  if (!res.ok) throw new Error(`Failed to fetch telemetry for ${runId}`);
  return res.json();
}

export async function fetchRunRules(runId: string): Promise<RulesResponse> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/rules`);
  if (!res.ok) throw new Error(`Failed to fetch rules for ${runId}`);
  return res.json();
}

export async function fetchRunStage(runId: string, stageId: string): Promise<StageDetail> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/stages/${stageId}`);
  if (!res.ok) throw new Error(`Failed to fetch stage ${stageId} for ${runId}`);
  return res.json();
}

export async function fetchProposals(runId: string): Promise<ProposalsResponse> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/rule-proposals`);
  if (!res.ok) throw new Error(`Failed to fetch rule proposals for ${runId}`);
  return res.json();
}

export async function createProposal(
  runId: string,
  payload: { originalRuleId: string; proposedSource: string; rationale: string }
): Promise<RuleProposal> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/rule-proposals`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || "Failed to submit rule proposal");
  }
  return res.json();
}

export async function validateProposal(
  runId: string,
  proposalId: string,
  cumulative = false
): Promise<RuleProposal> {
  const query = cumulative ? "?cumulative=true" : "";
  const res = await fetch(`${API_BASE}/api/runs/${runId}/rule-proposals/${proposalId}/validate${query}`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || "Failed to validate rule proposal");
  }
  return res.json();
}

export async function fetchRunReport(runId: string): Promise<RunReport> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/report`);
  if (!res.ok) throw new Error(`Failed to fetch report for ${runId}`);
  return res.json();
}

export async function requestExplanation(
  runId: string,
  stageId: string
): Promise<ExplanationResponse> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/explanations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stageId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || "Failed to request stage explanation");
  }
  return res.json();
}

export interface GeneratedProposalResponse extends RuleProposal {
  aiArtifact: import("../../../../packages/schemas/ts/contracts").AiArtifact;
}

export async function generateProposal(
  runId: string,
  payload: { originalRuleId: string; eventId?: string }
): Promise<GeneratedProposalResponse> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/rule-proposals/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || "Failed to generate rule proposal");
  }
  return res.json();
}

export async function generateReportSummary(runId: string): Promise<RunReport> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/report/summary`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || "Failed to generate report summary");
  }
  return res.json();
}

export interface ThreatIntelResponse {
  stageId: string;
  techniqueId: string;
  techniqueName: string;
  tactics: string[];
  liveSearch: boolean;
  summary: string;
  adversaries: string[];
  sources: Array<{ title: string; url: string; snippet: string }>;
}

export async function fetchStageThreatIntel(stageId: string): Promise<ThreatIntelResponse> {
  const res = await fetch(`${API_BASE}/api/threat-intel/stages/${stageId}`);
  if (!res.ok) throw new Error(`Failed to fetch threat intel for stage ${stageId}`);
  return res.json();
}

export interface VariantSummary {
  variantId: string;
  name: string;
  description: string;
  seed: number;
  eventCount: number;
  coverageScore: number;
  stageStatuses: Record<string, string>;
}

export interface DetectionOpsMetrics {
  runId: string;
  attackCoverage: number;
  variantResilience: number;
  benignSuppression: number;
  noiseRisk: "low" | "medium" | "high";
  regressionStatus: "baseline" | "pass" | "regression_detected";
  variantsCount: number;
  benignEventsCount: number;
  noiseHitsCount: number;
  variantBreakdown: VariantSummary[];
  benignDetails: {
    totalBenignEvents: number;
    suppressedCount: number;
    noiseHitCount: number;
    suppressionRate: number;
    noiseRisk: string;
    hits: Array<{
      ruleId: string;
      ruleTitle: string;
      eventId: string;
      action: string;
      identity: string;
      resource: string;
      matchedFields: Record<string, unknown>;
    }>;
  };
}

export interface MatchRecord {
  id: string;
  runId: string;
  eventId: string;
  ruleId: string;
  stageId: string;
  matchedAt: string;
  details: Record<string, unknown>;
}

export interface MatchesResponse {
  runId: string;
  total: number;
  matches: MatchRecord[];
}

export interface VariantsResponse {
  runId: string;
  variantResilience: number;
  variants: VariantSummary[];
}

export interface CiReportResponse {
  runId: string;
  scenarioId: string;
  decision: "PASS" | "BLOCKED";
  markdown: string;
}

export interface RuleValidationResponse {
  valid: boolean;
  ruleId?: string;
  title?: string;
  stageId?: string;
  level?: string;
  errors: string[];
}

export interface RuleEvaluationResponse {
  valid: boolean;
  ruleId: string;
  title: string;
  stageId: string;
  attackMatchesCount: number;
  attackMatches: Array<Record<string, unknown>>;
  noiseHitsCount: number;
  noiseHits: Array<Record<string, unknown>>;
  benignSuppressed: boolean;
  errors: string[];
}

export async function fetchDetectionOps(runId: string): Promise<DetectionOpsMetrics> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/detection-ops`);
  if (!res.ok) throw new Error(`Failed to fetch DetectionOps metrics for ${runId}`);
  return res.json();
}

export async function fetchVariants(runId: string): Promise<VariantsResponse> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/variants`);
  if (!res.ok) throw new Error(`Failed to fetch variants for ${runId}`);
  return res.json();
}

export async function fetchMatches(runId: string): Promise<MatchesResponse> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/matches`);
  if (!res.ok) throw new Error(`Failed to fetch matches for ${runId}`);
  return res.json();
}

export async function fetchCiReport(runId: string): Promise<CiReportResponse> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/ci-report`);
  if (!res.ok) throw new Error(`Failed to fetch CI report for ${runId}`);
  return res.json();
}

export async function validateCustomRule(yamlSource: string): Promise<RuleValidationResponse> {
  const res = await fetch(`${API_BASE}/api/rules/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yamlSource }),
  });
  if (!res.ok) throw new Error(`Failed to validate rule syntax`);
  return res.json();
}

export async function evaluateCustomRule(
  yamlSource: string,
  runId?: string
): Promise<RuleEvaluationResponse> {
  const res = await fetch(`${API_BASE}/api/rules/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yamlSource, runId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || `Failed to evaluate custom rule`);
  }
  return res.json();
}



