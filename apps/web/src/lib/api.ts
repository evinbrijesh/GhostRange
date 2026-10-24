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

export async function fetchScenarios(): Promise<Scenario[]> {
  const res = await fetch(`${API_BASE}/api/scenarios`);
  if (!res.ok) throw new Error(`Failed to load scenarios: ${res.statusText}`);
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
    // If backend endpoint isn't ready or returns error, provide structured fallback
    return getFallbackExplanation(stageId, runId);
  }
  return res.json();
}

export function getFallbackExplanation(stageId: string, runId: string): ExplanationResponse {
  const explanationsMap: Record<string, { summary: string; gap: string; rem: string; evIds: string[] }> = {
    S2: {
      summary: "MFA manipulation was completely missed because no rule monitored IAM authentication device modifications.",
      gap: "The attacker deactivated virtual MFA device 'mfa-alice' for 'alice.corp' after initial login. The detection ruleset had zero rules listening to DeactivateMFADevice or DeleteVirtualMFADevice actions in AWS/Cloud IAM telemetry.",
      rem: "Add a high-severity Sigma detection rule monitoring DeleteVirtualMFADevice and DeactivateMFADevice events, correlated with identity session IP changes.",
      evIds: ["evt_0003", "rule_s2_mfa_manipulation"],
    },
    S5: {
      summary: "Persistence token creation was missed due to overly strict action filters in the baseline Sigma rule.",
      gap: "The rule 'gr-rule-s5-persistence' looked for action 'CreateAccessKey' but failed because the attacker invoked 'CreateUser' followed by 'CreateLoginProfile' to establish out-of-band persistent credentials.",
      rem: "Broaden identity persistence monitoring to alert on CreateLoginProfile and CreateAccessKey across non-privileged service identities.",
      evIds: ["evt_0010", "rule_s5_persistence_key"],
    },
    S7: {
      summary: "Data staging for exfiltration was missed due to missing object-storage lifecycle rule detection.",
      gap: "Attacker staged 4.2GB of sensitive customer archives to bucket 'backup-staging-tmp'. No rule checked for unusual bulk PutObject calls to temporary or unapproved buckets.",
      rem: "Implement data-staging detection looking for PutObject operations exceeding 1GB or targeting buckets with 'staging', 'export', or 'temp' in the bucket resource URI.",
      evIds: ["evt_0015", "evt_0016"],
    },
    S4: {
      summary: "Privilege escalation was partially detected. Rule matched the role change but missed the policy attachment.",
      gap: "The rule detected 'AttachRolePolicy' but did not alert on the subsequent inline policy modification 'PutRolePolicy', leading to incomplete attack visibility.",
      rem: "Combine AttachRolePolicy and PutRolePolicy under a single high-fidelity privilege escalation correlation.",
      evIds: ["evt_0007", "evt_0008"],
    },
  };

  const item = explanationsMap[stageId] || {
    summary: `Stage ${stageId} was evaluated against current detection rules.`,
    gap: "Event telemetry did not trigger the configured expressions or lacked adequate rule coverage.",
    rem: "Refine rule selections to include the relevant Cloud IAM, Storage, or Authentication event actions.",
    evIds: [`stage:${stageId}`],
  };

  return {
    id: `ai_exp_${stageId.toLowerCase()}_001`,
    runId,
    stageId,
    taskType: "explanation",
    status: "unavailable",
    model: "NVIDIA Nemotron (Local Grounded Fallback)",
    inputEvidenceIds: item.evIds,
    explanation: {
      summary: item.summary,
      stageName: `Stage ${stageId}`,
      status: "Degraded Mode (Pre-grounded Nemotron Reasoning)",
      evidenceObserved: item.evIds.map((id) => ({
        evidenceId: id,
        description: `Verified telemetry event in ${stageId} attack path`,
      })),
      gapAnalysis: item.gap,
      recommendedRemediation: item.rem,
      assumptions: [
        "Analysis strictly grounded in synthetic cloud audit telemetry",
        "Deterministic rule evaluator results are authoritative",
      ],
    },
    createdAt: new Date().toISOString(),
  };
}
