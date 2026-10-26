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

export async function validateProposal(runId: string, proposalId: string): Promise<RuleProposal> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/rule-proposals/${proposalId}/validate`, {
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
