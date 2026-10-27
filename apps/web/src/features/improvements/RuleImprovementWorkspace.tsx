import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  FileCode2,
  History,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Terminal,
} from "lucide-react";
import type {
  DetectionRule,
  RuleProposal,
  StageResult,
  TelemetryEvent,
} from "../../../../../packages/schemas/ts/contracts";
import { createProposal, generateProposal, validateProposal } from "../../lib/api";

interface RuleImprovementWorkspaceProps {
  runId: string | null;
  rules: DetectionRule[];
  stageResults: StageResult[];
  events: TelemetryEvent[];
  proposals: RuleProposal[];
  focusStageId?: string | null;
  onProposalValidated?: (updatedProposal: RuleProposal) => void;
}

function actionToSnake(action: string): string {
  return action
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .toLowerCase();
}

function buildAnalystDraft(rule: DetectionRule, event: TelemetryEvent | undefined): string {
  if (!event) {
    return rule.source;
  }
  return `title: Detect ${event.action} (analyst draft)
id: rule_${rule.stageId.toLowerCase()}_${actionToSnake(event.action)}_analyst_draft
stage: ${rule.stageId}
logsource:
  product: ${rule.logsource.product}
  service: ${event.source}
selection:
  action: ${event.action}
condition: selection
level: ${rule.level ?? "high"}`;
}

function buildRationale(
  rule: DetectionRule,
  event: TelemetryEvent | undefined,
  stageResult: StageResult | undefined
): string {
  if (!event) {
    const errors = stageResult?.errors.length
      ? ` The stage also reported evaluator errors: ${stageResult.errors.join("; ")}`
      : "";
    return `No mismatch record was returned for ${rule.id}, so this draft starts from the original rule. Edit it to address the blind spot before validating.${errors}`;
  }
  const failedAction = stageResult?.mismatches
    .filter((m) => m.ruleId === rule.id && m.eventId === event.id)
    .flatMap((m) => m.failedExpressions)
    .find((expr) => expr.field === "action");
  const reason = failedAction
    ? `it expected action '${failedAction.expected}'`
    : "its selection did not match the observed event";
  return `Telemetry event ${event.id} contains action '${event.action}', but ${rule.id} did not match because ${reason}. This local draft targets the observed action for analyst review. It was generated in the browser, not by a model.`;
}

export const RuleImprovementWorkspace: React.FC<RuleImprovementWorkspaceProps> = ({
  runId,
  rules,
  stageResults,
  events,
  proposals,
  focusStageId,
  onProposalValidated,
}) => {
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [draftSource, setDraftSource] = useState<string>("");
  const [baselineDraft, setBaselineDraft] = useState<string>("");
  const [rationale, setRationale] = useState<string>("");
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [isGeneratingNemotron, setIsGeneratingNemotron] = useState<boolean>(false);
  const [cumulativeValidation, setCumulativeValidation] = useState<boolean>(true);
  const [proposalOrigin, setProposalOrigin] = useState<"analyst" | "nemotron" | "fallback">("analyst");
  const [nemotronModel, setNemotronModel] = useState<string | null>(null);
  const [citedEvidence, setCitedEvidence] = useState<string[]>([]);
  const [activeProposal, setActiveProposal] = useState<RuleProposal | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const lastFocusRef = useRef<string | null>(null);

  const stageResultById = useMemo(() => {
    const map = new Map<string, StageResult>();
    for (const result of stageResults) map.set(result.stageId, result);
    return map;
  }, [stageResults]);

  const blindSpotRules = useMemo(
    () =>
      rules.filter((rule) => {
        const result = stageResultById.get(rule.stageId);
        return result !== undefined && result.status !== "detected";
      }),
    [rules, stageResultById]
  );

  useEffect(() => {
    if (!focusStageId || lastFocusRef.current === focusStageId) return;
    lastFocusRef.current = focusStageId;
    const focusRule = blindSpotRules.find((rule) => rule.stageId === focusStageId);
    if (focusRule) setSelectedRuleId(focusRule.id);
  }, [focusStageId, blindSpotRules]);

  useEffect(() => {
    if (blindSpotRules.length === 0) {
      if (selectedRuleId !== null) setSelectedRuleId(null);
      return;
    }
    if (!selectedRuleId || !blindSpotRules.some((rule) => rule.id === selectedRuleId)) {
      setSelectedRuleId(blindSpotRules[0].id);
    }
  }, [blindSpotRules, selectedRuleId]);

  const selectedRule = rules.find((rule) => rule.id === selectedRuleId) ?? null;
  const selectedStageResult = selectedRule
    ? stageResultById.get(selectedRule.stageId)
    : undefined;

  const selectedMismatches = useMemo(
    () =>
      selectedRule && selectedStageResult
        ? selectedStageResult.mismatches.filter((m) => m.ruleId === selectedRule.id)
        : [],
    [selectedRule, selectedStageResult]
  );

  const mismatchEvent = useMemo(() => {
    const firstMismatch = selectedMismatches[0];
    if (!firstMismatch) return undefined;
    return events.find((event) => event.id === firstMismatch.eventId);
  }, [selectedMismatches, events]);

  useEffect(() => {
    if (!selectedRule) {
      setDraftSource("");
      setBaselineDraft("");
      setRationale("");
      setActiveProposal(null);
      setActionError(null);
      setProposalOrigin("analyst");
      setNemotronModel(null);
      setCitedEvidence([]);
      return;
    }
    const draft = buildAnalystDraft(selectedRule, mismatchEvent);
    setDraftSource(draft);
    setBaselineDraft(draft);
    setRationale(buildRationale(selectedRule, mismatchEvent, selectedStageResult));
    setActiveProposal(null);
    setActionError(null);
    setProposalOrigin("analyst");
    setNemotronModel(null);
    setCitedEvidence([]);
    // selectedRule id and mismatch event id identify the scenario evidence;
    // parent updates to proposals must not overwrite the analyst's edits.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRule?.id, mismatchEvent?.id]);

  const ruleProposals = selectedRule
    ? proposals.filter((proposal) => proposal.originalRuleId === selectedRule.id)
    : [];

  const handleGenerateNemotron = async () => {
    if (!runId || !selectedRule) return;
    setIsGeneratingNemotron(true);
    setActionError(null);
    try {
      const res = await generateProposal(runId, {
        originalRuleId: selectedRule.id,
        eventId: mismatchEvent?.id,
      });
      setDraftSource(res.proposedSource);
      setRationale(res.rationale);
      setActiveProposal(res);
      setProposalOrigin(res.aiArtifact.status === "succeeded" ? "nemotron" : "fallback");
      setNemotronModel(res.aiArtifact.model);
      const cited = res.aiArtifact.output?.citedEvidenceIds as string[] | undefined;
      setCitedEvidence(cited || []);
      if (onProposalValidated) onProposalValidated(res);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to generate AI proposal");
    } finally {
      setIsGeneratingNemotron(false);
    }
  };

  const handleValidate = async () => {
    if (!runId || !selectedRule || !draftSource.trim()) return;
    setIsValidating(true);
    setActionError(null);
    try {
      const created = await createProposal(runId, {
        originalRuleId: selectedRule.id,
        proposedSource: draftSource,
        rationale,
      });
      if (created.validation.parserStatus === "invalid") {
        setActiveProposal(created);
        if (onProposalValidated) onProposalValidated(created);
        return;
      }
      const validated = await validateProposal(runId, created.id, cumulativeValidation);
      setActiveProposal(validated);
      if (onProposalValidated) onProposalValidated(validated);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Proposal validation failed");
    } finally {
      setIsValidating(false);
    }
  };

  const handleDiscardResult = () => {
    setActiveProposal(null);
    setActionError(null);
  };

  const isDirty = selectedRule !== null && draftSource !== baselineDraft;

  const getStageStatusBadge = (status: string | undefined) => {
    switch (status) {
      case "detected":
        return <span className="badge badge-detected">Detected</span>;
      case "partial":
        return <span className="badge badge-partial">Partial</span>;
      case "missed":
        return <span className="badge badge-missed">Missed</span>;
      case "error":
        return (
          <span className="badge" style={{ background: "rgba(148, 163, 184, 0.15)", color: "#cbd5e1" }}>
            Evaluator error
          </span>
        );
      default:
        return null;
    }
  };

  if (!runId) {
    return (
      <div className="glass-panel" style={{ padding: "3rem", textAlign: "center", color: "var(--text-dim)" }}>
        No run loaded. Run the scenario or load the seeded demo run before reviewing rule improvements.
      </div>
    );
  }

  if (rules.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: "3rem", textAlign: "center", color: "var(--text-dim)" }}>
        No detection rules were returned for this run.
      </div>
    );
  }

  if (blindSpotRules.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: "3rem", textAlign: "center", color: "var(--text-dim)" }}>
        <ShieldCheck size={28} style={{ color: "var(--status-detected)", marginBottom: "0.5rem" }} />
        <div>Every evaluated stage is detected. There is no blind spot to remediate in this run.</div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Top Banner */}
      <div
        className="glass-panel"
        style={{
          padding: "1.25rem 1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "1.5rem",
          background: "linear-gradient(135deg, rgba(139, 92, 246, 0.08), rgba(17, 24, 39, 0.8))",
          border: "1px solid rgba(139, 92, 246, 0.2)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
            {proposalOrigin === "nemotron" ? (
              <>
                <span className="badge" style={{ background: "rgba(16, 185, 129, 0.15)", color: "var(--status-detected)" }}>
                  <Sparkles size={12} /> NVIDIA Nemotron ({nemotronModel || "4-340B"})
                </span>
                <span className="badge" style={{ background: "rgba(6, 182, 212, 0.12)", color: "#22d3ee" }}>
                  Evidence Grounded ({citedEvidence.length} citations)
                </span>
              </>
            ) : proposalOrigin === "fallback" ? (
              <>
                <span className="badge" style={{ background: "rgba(245, 158, 11, 0.12)", color: "var(--status-partial)" }}>
                  <Sparkles size={12} /> Nemotron (Deterministic Fallback)
                </span>
                <span className="badge" style={{ background: "rgba(255, 255, 255, 0.05)", color: "var(--text-muted)" }}>
                  Key Unconfigured
                </span>
              </>
            ) : (
              <>
                <span className="badge" style={{ background: "rgba(139, 92, 246, 0.12)", color: "#c084fc" }}>
                  <FileCode2 size={12} /> Analyst Draft
                </span>
                <span className="badge" style={{ background: "rgba(255, 255, 255, 0.05)", color: "var(--text-muted)" }}>
                  Local / No Model Invoked
                </span>
              </>
            )}
            <span className="badge" style={{ background: "rgba(16, 185, 129, 0.1)", color: "var(--status-detected)" }}>
              Deterministic Evaluator
            </span>
          </div>
          <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginTop: "0.4rem" }}>
            Rule Improvement Workspace
          </h2>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.2rem", maxWidth: "760px" }}>
            Start from a real mismatch in this run, edit the proposed rule, then validate it against the same
            telemetry with the local evaluator. Proposals are sandbox-only and never modify stored rules.
          </p>
        </div>

        {/* Validation Result Box */}
        {activeProposal && (
          <div
            style={{
              background:
                activeProposal.validation.parserStatus === "invalid"
                  ? "rgba(239, 68, 68, 0.12)"
                  : activeProposal.validation.improvesCoverage
                    ? "rgba(16, 185, 129, 0.15)"
                    : "rgba(245, 158, 11, 0.12)",
              border: `1.5px solid ${
                activeProposal.validation.parserStatus === "invalid"
                  ? "var(--status-missed)"
                  : activeProposal.validation.improvesCoverage
                    ? "var(--status-detected)"
                    : "var(--status-partial)"
              }`,
              borderRadius: "var(--radius-md)",
              padding: "0.75rem 1.25rem",
              textAlign: "right",
              flexShrink: 0,
            }}
          >
            <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", textTransform: "uppercase", fontWeight: 700 }}>
              {activeProposal.validation.parserStatus === "invalid"
                ? "Parser Rejected"
                : activeProposal.validation.improvesCoverage === null
                  ? "Not Validated"
                  : "Evaluator Result"}
            </div>
            {activeProposal.validation.parserStatus === "invalid" ? (
              <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "#fca5a5", marginTop: "0.2rem" }}>
                Fix the YAML and try again
              </div>
            ) : activeProposal.validation.coverageAfter !== null &&
              activeProposal.validation.coverageBefore !== null ? (
              <>
                <div style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--text-main)" }}>
                  {activeProposal.validation.coverageBefore}% → {activeProposal.validation.coverageAfter}%
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-main)" }}>
                  {activeProposal.validation.improvesCoverage
                    ? `+${(Number(activeProposal.validation.coverageAfter) - Number(activeProposal.validation.coverageBefore)).toFixed(1)}% coverage gain on this run`
                    : "No coverage gain on this run"}
                </div>
              </>
            ) : (
              <div style={{ fontSize: "0.82rem", color: "var(--text-main)" }}>Awaiting evaluator result</div>
            )}
          </div>
        )}
      </div>

      {actionError && (
        <div
          style={{
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "var(--radius-sm)",
            padding: "0.65rem 1rem",
            fontSize: "0.8rem",
            color: "#fca5a5",
            display: "flex",
            justifyContent: "space-between",
            gap: "1rem",
          }}
        >
          <span>{actionError}</span>
          <button
            onClick={() => setActionError(null)}
            style={{ background: "none", border: "none", color: "#fca5a5", cursor: "pointer" }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Workspace Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        {/* Left Column: Original Rule + Real Mismatch */}
        <div className="glass-panel" style={{ padding: "1.25rem", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", marginBottom: "0.75rem" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", flexWrap: "wrap" }}>
                <span className="badge badge-missed" style={{ fontSize: "0.7rem" }}>
                  Original Rule
                </span>
                {getStageStatusBadge(selectedStageResult?.status)}
              </div>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginTop: "0.3rem" }}>
                {selectedRule?.title}
              </h3>
              <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>
                {selectedRule?.id} • {selectedRule?.stageId}
              </div>
            </div>
            <select
              value={selectedRuleId ?? ""}
              onChange={(e) => setSelectedRuleId(e.target.value)}
              style={{
                background: "rgba(17, 24, 39, 0.8)",
                border: "1px solid var(--border-medium)",
                color: "var(--text-main)",
                borderRadius: "var(--radius-sm)",
                padding: "0.3rem 0.6rem",
                fontSize: "0.75rem",
                fontFamily: "var(--font-mono)",
                cursor: "pointer",
                maxWidth: "260px",
              }}
            >
              {blindSpotRules.map((rule) => (
                <option key={rule.id} value={rule.id}>
                  {rule.stageId} — {rule.id}
                </option>
              ))}
            </select>
          </div>

          <pre
            style={{
              background: "rgba(0, 0, 0, 0.5)",
              border: "1px solid rgba(239, 68, 68, 0.25)",
              borderRadius: "var(--radius-md)",
              padding: "1rem",
              fontSize: "0.78rem",
              color: "#fca5a5",
              lineHeight: 1.5,
              margin: 0,
              fontFamily: "var(--font-mono)",
              whiteSpace: "pre-wrap",
            }}
          >
            <code>{selectedRule?.source}</code>
          </pre>

          <div style={{ marginTop: "0.85rem" }}>
            <h4
              style={{
                fontSize: "0.75rem",
                fontWeight: 600,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: "0.4rem",
                display: "flex",
                alignItems: "center",
                gap: "0.35rem",
              }}
            >
              <Terminal size={13} /> Observed Mismatches
            </h4>

            {selectedStageResult && selectedStageResult.errors.length > 0 && (
              <div
                style={{
                  marginBottom: "0.5rem",
                  padding: "0.6rem 0.8rem",
                  background: "rgba(148, 163, 184, 0.08)",
                  border: "1px solid rgba(148, 163, 184, 0.25)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.75rem",
                  color: "#cbd5e1",
                }}
              >
                <strong>Evaluator errors:</strong> {selectedStageResult.errors.join("; ")}
              </div>
            )}

            {selectedMismatches.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", maxHeight: "220px", overflowY: "auto" }}>
                {selectedMismatches.map((mismatch) => {
                  const event = events.find((candidate) => candidate.id === mismatch.eventId);
                  return (
                    <div
                      key={`${mismatch.ruleId}-${mismatch.eventId}`}
                      style={{
                        background: "rgba(239, 68, 68, 0.06)",
                        border: "1px solid rgba(239, 68, 68, 0.2)",
                        borderRadius: "var(--radius-sm)",
                        padding: "0.6rem 0.8rem",
                        fontSize: "0.75rem",
                      }}
                    >
                      <div style={{ color: "#fca5a5", fontWeight: 600, marginBottom: "0.25rem" }}>
                        event:{mismatch.eventId}
                        {event && (
                          <span style={{ color: "var(--text-dim)", fontWeight: 400 }}>
                            {" "}
                            • {event.action} ({event.source})
                          </span>
                        )}
                      </div>
                      {mismatch.failedExpressions.map((expr, index) => (
                        <div key={index} style={{ color: "var(--text-muted)", marginLeft: "0.35rem" }}>
                          • <code style={{ color: "#fcd34d" }}>{expr.field}</code> ({expr.operator}) expected{" "}
                          <strong>{expr.expected}</strong>, got{" "}
                          <strong>{expr.actual ?? "null / missing"}</strong>
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                No mismatch record was returned for this rule. The stage may have no valid rule, no expected
                events, or only parser errors.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Analyst Draft */}
        <div className="glass-panel" style={{ padding: "1.25rem", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", marginBottom: "0.75rem" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", flexWrap: "wrap" }}>
                <span className="badge" style={{ background: "rgba(6, 182, 212, 0.12)", color: "#22d3ee", fontSize: "0.7rem" }}>
                  {proposalOrigin === "nemotron"
                    ? "✨ Nemotron Grounded Fix"
                    : proposalOrigin === "fallback"
                      ? "Deterministic Fallback Fix"
                      : "Local Draft from Observed Event"}
                </span>
                {isDirty && (
                  <span className="badge badge-partial" style={{ fontSize: "0.68rem" }}>
                    Edited
                  </span>
                )}
                {activeProposal && (
                  <span
                    className={`badge ${activeProposal.validation.parserStatus === "valid" ? "badge-detected" : "badge-missed"}`}
                    style={{ fontSize: "0.68rem" }}
                  >
                    Parser: {activeProposal.validation.parserStatus}
                  </span>
                )}
              </div>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginTop: "0.3rem" }}>
                Proposed detection logic
              </h3>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <button
                id="nemotron-generate-button"
                className="btn btn-secondary"
                onClick={handleGenerateNemotron}
                disabled={isGeneratingNemotron || isValidating || !selectedRule}
                style={{
                  fontSize: "0.75rem",
                  padding: "0.35rem 0.75rem",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.35rem",
                  background: "rgba(139, 92, 246, 0.15)",
                  borderColor: "rgba(139, 92, 246, 0.4)",
                  color: "#d8b4fe",
                }}
              >
                <Sparkles size={13} style={{ color: "var(--cyan-400)" }} />
                {isGeneratingNemotron ? "Generating..." : "✨ Ask Nemotron for Fix"}
              </button>
              {activeProposal && (
                <button
                  className="btn btn-secondary"
                  onClick={handleDiscardResult}
                  style={{ fontSize: "0.75rem", padding: "0.35rem 0.7rem" }}
                >
                  <RotateCcw size={13} /> Clear
                </button>
              )}
            </div>
          </div>

          <textarea
            value={draftSource}
            onChange={(e) => setDraftSource(e.target.value)}
            spellCheck={false}
            style={{
              background: "rgba(0, 0, 0, 0.5)",
              border: "1px solid rgba(6, 182, 212, 0.35)",
              borderRadius: "var(--radius-md)",
              padding: "1rem",
              fontSize: "0.78rem",
              color: "#a7f3d0",
              lineHeight: 1.5,
              flex: 1,
              fontFamily: "var(--font-mono)",
              outline: "none",
              resize: "vertical",
              minHeight: "240px",
            }}
          />

          <div
            style={{
              marginTop: "0.85rem",
              padding: "0.65rem 0.85rem",
              background: "rgba(6, 182, 212, 0.06)",
              border: "1px solid rgba(6, 182, 212, 0.18)",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
            }}
          >
            <label style={{ display: "block", fontWeight: 600, color: "#67e8f9", marginBottom: "0.25rem" }}>
              Analyst rationale
            </label>
            <textarea
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              rows={3}
              style={{
                width: "100%",
                background: "rgba(0, 0, 0, 0.3)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "6px 8px",
                color: "var(--text-main)",
                fontSize: "0.75rem",
                fontFamily: "var(--font-sans)",
                resize: "vertical",
              }}
            />
          </div>

          {activeProposal?.validation.parserStatus === "invalid" && (
            <div
              style={{
                marginTop: "0.5rem",
                padding: "0.6rem 0.8rem",
                background: "rgba(239, 68, 68, 0.08)",
                border: "1px solid rgba(239, 68, 68, 0.25)",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.75rem",
                color: "#fca5a5",
              }}
            >
              {activeProposal.validation.parserErrors.map((error, index) => (
                <div key={index}>• {error}</div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Validation History for this Rule */}
      {ruleProposals.length > 0 && (
        <div className="glass-panel" style={{ padding: "1rem 1.5rem" }}>
          <h3
            style={{
              fontSize: "0.85rem",
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
              marginBottom: "0.6rem",
            }}
          >
            <History size={16} style={{ color: "var(--cyan-500)" }} />
            Validation history for {selectedRule?.id}
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem" }}>
            {[...ruleProposals].reverse().map((proposal) => (
              <div
                key={proposal.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "1rem",
                  padding: "0.55rem 0.8rem",
                  background: "rgba(0, 0, 0, 0.25)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.75rem",
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                    {proposal.id} • {new Date(proposal.createdAt).toISOString().substring(11, 19)} UTC
                  </div>
                  <div style={{ color: "var(--text-dim)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {proposal.rationale}
                  </div>
                </div>
                <div style={{ textAlign: "right", flexShrink: 0 }}>
                  {proposal.validation.parserStatus === "invalid" ? (
                    <span className="badge badge-missed" style={{ fontSize: "0.68rem" }}>
                      Parser rejected
                    </span>
                  ) : proposal.validation.coverageBefore !== null && proposal.validation.coverageAfter !== null ? (
                    <span style={{ fontWeight: 700, color: "var(--text-main)" }}>
                      {proposal.validation.coverageBefore}% → {proposal.validation.coverageAfter}%
                    </span>
                  ) : (
                    <span style={{ color: "var(--text-dim)" }}>Not validated</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bottom Action Footer */}
      <div
        className="glass-panel"
        style={{
          padding: "1rem 1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.78rem", color: "var(--text-dim)" }}>
          <ShieldCheck size={16} style={{ color: "var(--status-detected)" }} />
          <span>
            Each validation creates a new sandbox proposal. Stored rules are untouched; results apply to this
            run&apos;s telemetry only.
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <label style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", fontSize: "0.74rem", color: "var(--text-muted)", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={cumulativeValidation}
              onChange={(e) => setCumulativeValidation(e.target.checked)}
              style={{ accentColor: "var(--cyan-500)", cursor: "pointer" }}
            />
            <span>Stack with prior improvements</span>
          </label>
          {!mismatchEvent && (
            <span style={{ fontSize: "0.72rem", color: "var(--status-partial)", display: "flex", alignItems: "center", gap: "0.3rem" }}>
              <AlertTriangle size={13} /> No event-derived draft; edit manually
            </span>
          )}
          <button
            id="validate-proposal-button"
            className="btn btn-primary"
            onClick={handleValidate}
            disabled={isValidating || !selectedRule || !draftSource.trim()}
            style={{ minWidth: "240px" }}
          >
            {isValidating ? (
              <>
                <span className="animate-spin">
                  <RotateCcw size={15} />
                </span>
                Evaluating Against Telemetry...
              </>
            ) : (
              <>
                <Play size={15} fill="currentColor" />
                Validate Draft (Local Engine)
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
