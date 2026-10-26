import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Clock,
  Sparkles,
  Shield,
  FileCode,
  ArrowRight,
  Database,
  Terminal,
} from "lucide-react";
import type { StageResult, TelemetryEvent } from "../../../../../packages/schemas/ts/contracts";
import type { ExplanationResponse, RunGraphStage } from "../../lib/api";
import { requestExplanation } from "../../lib/api";

const MITRE_MAPPINGS: Record<string, { techId: string; techName: string; tactics: string }> = {
  S1: { techId: "T1078.004", techName: "Valid Cloud Accounts", tactics: "Initial Access" },
  S2: { techId: "T1556", techName: "Modify Authentication Process", tactics: "Defense Evasion" },
  S3: { techId: "T1087.004", techName: "Cloud Account Discovery", tactics: "Discovery" },
  S4: { techId: "T1098", techName: "Account Manipulation", tactics: "Privilege Escalation" },
  S5: { techId: "T1098.001", techName: "Additional Cloud Credentials", tactics: "Persistence" },
  S6: { techId: "T1530", techName: "Data from Cloud Storage", tactics: "Collection" },
  S7: { techId: "T1074.002", techName: "Remote Data Staging", tactics: "Exfiltration Prep" },
};

interface AttackGraphProps {
  stages: RunGraphStage[];
  stageResults: StageResult[];
  events: TelemetryEvent[];
  runId: string | null;
  aiConfigured: boolean;
  onSelectStageForImprovement?: (stageId: string) => void;
}

export const AttackGraph: React.FC<AttackGraphProps> = ({
  stages,
  stageResults,
  events,
  runId,
  aiConfigured,
  onSelectStageForImprovement,
}) => {
  const [selectedStageId, setSelectedStageId] = useState<string>("S2");
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [isExplaining, setIsExplaining] = useState<boolean>(false);
  const [explanationError, setExplanationError] = useState<string | null>(null);

  useEffect(() => {
    if (stages.length > 0 && !stages.some((stage) => stage.stageId === selectedStageId)) {
      setSelectedStageId(stages[0].stageId);
    }
  }, [stages, selectedStageId]);

  if (stages.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: "2.5rem", textAlign: "center" }}>
        <Shield size={30} style={{ color: "var(--text-dim)", marginBottom: "0.75rem" }} />
        <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-main)" }}>
          No simulation results loaded
        </h2>
        <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: "0.4rem" }}>
          {runId
            ? "This run returned no stage data."
            : "Run the Cloud Identity Compromise scenario to generate real synthetic telemetry and stage results."}
        </p>
      </div>
    );
  }

  const selectedStage = stages.find((s) => s.stageId === selectedStageId) ?? stages[0];
  const selectedResult = stageResults.find((r) => r.stageId === selectedStage.stageId);
  const selectedEvents = events.filter((e) => e.stageId === selectedStage.stageId);
  const mitre = MITRE_MAPPINGS[selectedStage.stageId] || {
    techId: "T1000",
    techName: "Attack Step",
    tactics: "Adversarial",
  };

  const detectedCount = stages.filter((stage) => stage.status === "detected").length;
  const partialCount = stages.filter((stage) => stage.status === "partial").length;
  const missedCount = stages.filter((stage) => stage.status === "missed").length;

  const handleSelectStage = (stageId: string) => {
    setSelectedStageId(stageId);
    setExplanation(null);
    setExplanationError(null);
  };

  const handleExplain = async () => {
    if (!runId) return;
    setIsExplaining(true);
    setExplanationError(null);
    try {
      const exp = await requestExplanation(runId, selectedStage.stageId);
      setExplanation(exp);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Explanation request failed";
      setExplanationError(message);
    } finally {
      setIsExplaining(false);
    }
  };

  const explanationIsDegraded = explanation !== null && explanation.status !== "succeeded";
  const explanationEvidence = explanation?.explanation.evidenceObserved ?? [];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "detected":
        return (
          <span className="badge badge-detected">
            <CheckCircle2 size={12} /> Detected
          </span>
        );
      case "partial":
        return (
          <span className="badge badge-partial">
            <AlertTriangle size={12} /> Partial
          </span>
        );
      case "missed":
        return (
          <span className="badge badge-missed">
            <XCircle size={12} /> Missed
          </span>
        );
      default:
        return (
          <span className="badge badge-error">
            <HelpCircle size={12} /> Error
          </span>
        );
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Top Banner Overview */}
      <div
        className="glass-panel"
        style={{
          padding: "1.25rem 1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(17, 24, 39, 0.7))",
        }}
      >
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Shield size={18} style={{ color: "var(--cyan-500)" }} />
            Attack Progression Graph (MITRE ATT&CK Matrix)
          </h2>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
            Sequential attack path of Cloud Identity Compromise. Green nodes indicate rules triggered; Red nodes expose blind spots.
          </p>
        </div>
        <div style={{ display: "flex", gap: "1rem", fontSize: "0.78rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--status-detected)" }} />
            <span>Detected ({detectedCount})</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--status-partial)" }} />
            <span>Partial ({partialCount})</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--status-missed)" }} />
            <span>Missed ({missedCount})</span>
          </div>
        </div>
      </div>

      {/* Horizontal Interactive Node Chain */}
      <div
        className="glass-panel"
        style={{
          padding: "1.5rem",
          overflowX: "auto",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            minWidth: "1000px",
            justifyContent: "space-between",
          }}
        >
          {stages.map((stage, idx) => {
            const isSelected = stage.stageId === selectedStageId;
            const stageMitre = MITRE_MAPPINGS[stage.stageId] || { techId: "T1000", tactics: "Attack" };
            let borderColor = "var(--border-subtle)";
            let glow = "none";
            if (stage.status === "detected") {
              borderColor = "var(--status-detected-border)";
              glow = isSelected ? "0 0 20px var(--status-detected-glow)" : "none";
            } else if (stage.status === "partial") {
              borderColor = "var(--status-partial-border)";
              glow = isSelected ? "0 0 20px var(--status-partial-glow)" : "none";
            } else if (stage.status === "missed") {
              borderColor = "var(--status-missed-border)";
              glow = isSelected ? "0 0 20px var(--status-missed-glow)" : "none";
            }

            return (
              <React.Fragment key={stage.stageId}>
                <div
                  onClick={() => handleSelectStage(stage.stageId)}
                  style={{
                    flex: 1,
                    background: isSelected ? "var(--bg-elevated)" : "rgba(17, 24, 39, 0.6)",
                    border: `1.5px solid ${borderColor}`,
                    boxShadow: glow,
                    borderRadius: "var(--radius-md)",
                    padding: "1rem 0.85rem",
                    cursor: "pointer",
                    transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
                    transform: isSelected ? "scale(1.03)" : "scale(1)",
                    position: "relative",
                  }}
                >
                  {/* Top: Stage ID & Status */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontWeight: 700,
                        fontSize: "0.78rem",
                        color: isSelected ? "var(--cyan-500)" : "var(--text-muted)",
                      }}
                    >
                      {stage.stageId}
                    </span>
                    {getStatusBadge(stage.status)}
                  </div>

                  {/* Stage Name */}
                  <h3
                    style={{
                      fontSize: "0.85rem",
                      fontWeight: 600,
                      color: "var(--text-main)",
                      marginBottom: "0.35rem",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {stage.name}
                  </h3>

                  {/* MITRE Technique */}
                  <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginBottom: "0.6rem" }}>
                    <span style={{ fontFamily: "var(--font-mono)", color: "#38bdf8" }}>{stageMitre.techId}</span>
                  </div>

                  {/* Latency & Match Metric */}
                  <div
                    style={{
                      borderTop: "1px solid rgba(255, 255, 255, 0.06)",
                      paddingTop: "0.45rem",
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: "0.7rem",
                      color: "var(--text-muted)",
                    }}
                  >
                    <span>
                      {stage.matchedRuleIds.length > 0
                        ? `${stage.matchedRuleIds.length} rule${stage.matchedRuleIds.length === 1 ? "" : "s"} fired`
                        : "No rule fired"}
                    </span>
                    {stage.detectionLatencyMs !== null ? (
                      <span style={{ color: "var(--status-detected)", display: "flex", alignItems: "center", gap: "2px" }}>
                        <Clock size={10} /> {stage.detectionLatencyMs}ms
                      </span>
                    ) : (
                      <span style={{ color: "var(--status-missed)" }}>unmatched</span>
                    )}
                  </div>
                </div>

                {idx < stages.length - 1 && (
                  <ArrowRight size={16} style={{ color: "var(--text-dim)", flexShrink: 0 }} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Stage Inspection Details & AI Reasoning Pane */}
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: "1.5rem" }}>
        {/* Left Column: Stage Telemetry & Mismatch Reason */}
        <div className="glass-panel" style={{ padding: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span className="badge badge-synthetic" style={{ fontSize: "0.75rem" }}>
                  {selectedStage.stageId}
                </span>
                <span className="badge" style={{ background: "rgba(56, 189, 248, 0.1)", color: "#38bdf8" }}>
                  {mitre.techId}: {mitre.techName}
                </span>
                {getStatusBadge(selectedStage.status)}
              </div>
              <h3 style={{ fontSize: "1.15rem", fontWeight: 700, marginTop: "0.5rem" }}>
                {selectedStage.name}
              </h3>
            </div>
            {selectedStage.status !== "detected" && onSelectStageForImprovement && (
              <button
                className="btn btn-secondary"
                onClick={() => onSelectStageForImprovement(selectedStage.stageId)}
                style={{ fontSize: "0.78rem", padding: "0.4rem 0.8rem" }}
              >
                <FileCode size={14} /> Remediate in Workspace
              </button>
            )}
          </div>

          {/* Section: Synthetic Events Generated in this stage */}
          <div style={{ marginBottom: "1.25rem" }}>
            <h4
              style={{
                fontSize: "0.82rem",
                fontWeight: 600,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: "0.5rem",
                display: "flex",
                alignItems: "center",
                gap: "0.4rem",
              }}
            >
              <Database size={14} /> Generated Telemetry Evidence ({selectedEvents.length} events)
            </h4>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {selectedEvents.map((evt) => (
                <div
                  key={evt.id}
                  style={{
                    background: "rgba(0, 0, 0, 0.25)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-sm)",
                    padding: "0.6rem 0.85rem",
                    fontSize: "0.8rem",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--cyan-500)", fontWeight: 600 }}>
                      event:{evt.id}
                    </span>
                    <span style={{ color: "var(--text-dim)", fontSize: "0.72rem" }}>
                      {new Date(evt.timestamp).toISOString().substring(11, 19)} UTC
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: "1rem", color: "var(--text-main)" }}>
                    <span>
                      Action: <strong>{evt.action}</strong>
                    </span>
                    <span style={{ color: "var(--text-muted)" }}>
                      Identity: <code style={{ color: "#a5b4fc" }}>{evt.identity.id}</code>
                    </span>
                    <span style={{ color: "var(--text-muted)" }}>
                      Resource: <code style={{ color: "#fbcfe8" }}>{evt.resource.id}</code>
                    </span>
                  </div>
                </div>
              ))}
              {selectedEvents.length === 0 && (
                <div
                  style={{
                    fontSize: "0.78rem",
                    color: "var(--text-dim)",
                    padding: "0.65rem 0.85rem",
                    border: "1px dashed var(--border-subtle)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  No telemetry events were generated for this stage in this run.
                </div>
              )}
            </div>
          </div>

          {/* Section: Deterministic Mismatches */}
          {selectedResult && selectedResult.mismatches && selectedResult.mismatches.length > 0 && (
            <div>
              <h4
                style={{
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  color: "var(--status-missed)",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  marginBottom: "0.5rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.4rem",
                }}
              >
                <Terminal size={14} /> Deterministic Rule Mismatches (Authoritative Engine)
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {selectedResult.mismatches.map((m, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: "rgba(239, 68, 68, 0.06)",
                      border: "1px solid rgba(239, 68, 68, 0.2)",
                      borderRadius: "var(--radius-sm)",
                      padding: "0.65rem 0.85rem",
                      fontSize: "0.78rem",
                    }}
                  >
                    <div style={{ color: "#fca5a5", fontWeight: 600, marginBottom: "0.3rem" }}>
                      Rule: <code style={{ color: "#ffffff" }}>rule:{m.ruleId}</code> vs Event:{" "}
                      <code style={{ color: "#ffffff" }}>event:{m.eventId}</code>
                    </div>
                    {m.failedExpressions.map((fe, feIdx) => (
                      <div key={feIdx} style={{ color: "var(--text-muted)", marginLeft: "0.5rem" }}>
                        • Field <code style={{ color: "#fcd34d" }}>{fe.field}</code> ({fe.operator}):
                        expected &quot;<strong>{fe.expected}</strong>&quot;, but event contained &quot;
                        <strong>{fe.actual || "null / missing"}</strong>&quot;
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Stage Gap Analysis */}
        <div
          className="glass-panel"
          style={{
            padding: "1.5rem",
            background: "linear-gradient(145deg, rgba(139, 92, 246, 0.05), rgba(17, 24, 39, 0.7))",
            border: "1px solid rgba(139, 92, 246, 0.2)",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "6px",
                  background: "linear-gradient(135deg, #8b5cf6, #6d28d9)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Sparkles size={16} color="#ffffff" />
              </div>
              <div>
                <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>
                  {explanation?.status === "succeeded"
                    ? "NVIDIA Nemotron Analysis"
                    : "Stage Gap Analysis"}
                </h3>
                <p style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>
                  {explanation?.status === "succeeded" && explanation.model
                    ? `Model: ${explanation.model}`
                    : explanation
                      ? "Deterministic fallback — no model output shown"
                      : aiConfigured
                        ? "Nebius Token Factory configured"
                        : "AI not configured — deterministic analysis only"}
                </p>
              </div>
            </div>

            <button
              id={`explain-${selectedStage.stageId}-button`}
              className="btn btn-ai"
              onClick={handleExplain}
              disabled={isExplaining || !runId}
              style={{ fontSize: "0.78rem", padding: "0.45rem 0.85rem" }}
            >
              {isExplaining ? (
                <>
                  <span className="animate-spin">
                    <Sparkles size={14} />
                  </span>
                  Analyzing Telemetry...
                </>
              ) : (
                <>
                  <Sparkles size={14} />
                  {aiConfigured ? "Explain Blind Spot" : "Run Deterministic Analysis"}
                </>
              )}
            </button>
          </div>

          {explanationError && (
            <div
              style={{
                background: "rgba(239, 68, 68, 0.08)",
                border: "1px solid rgba(239, 68, 68, 0.25)",
                borderRadius: "var(--radius-sm)",
                padding: "0.65rem 0.85rem",
                fontSize: "0.78rem",
                color: "#fca5a5",
                marginBottom: "0.9rem",
              }}
            >
              Explanation request failed: {explanationError}. The deterministic stage results
              above remain authoritative.
            </div>
          )}

          {/* AI Output Content */}
          {explanation ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.9rem", fontSize: "0.82rem" }}>
              {explanationIsDegraded && (
                <div
                  style={{
                    background: "rgba(245, 158, 11, 0.08)",
                    border: "1px solid rgba(245, 158, 11, 0.25)",
                    borderRadius: "var(--radius-sm)",
                    padding: "0.65rem 0.85rem",
                    fontSize: "0.75rem",
                    color: "var(--status-partial)",
                  }}
                >
                  <strong>
                    {explanation.status === "unavailable"
                      ? "AI unavailable."
                      : "AI analysis failed or was rejected."}
                  </strong>{" "}
                  Deterministic fallback shown. No model output is being presented as AI
                  analysis.
                </div>
              )}

              {explanation.status === "succeeded" && explanation.model && (
                <div
                  style={{
                    background: "rgba(139, 92, 246, 0.1)",
                    border: "1px solid rgba(139, 92, 246, 0.25)",
                    borderRadius: "var(--radius-sm)",
                    padding: "0.5rem 0.75rem",
                    fontSize: "0.72rem",
                    color: "#c084fc",
                  }}
                >
                  Evidence-grounded output from {explanation.model}
                </div>
              )}

              {/* Summary */}
              <div
                style={{
                  background: "rgba(139, 92, 246, 0.1)",
                  border: "1px solid rgba(139, 92, 246, 0.25)",
                  borderRadius: "var(--radius-sm)",
                  padding: "0.75rem",
                }}
              >
                <div style={{ fontWeight: 600, color: "#c084fc", marginBottom: "0.25rem" }}>
                  Summary
                </div>
                <p style={{ color: "var(--text-main)" }}>{explanation.explanation.summary}</p>
              </div>

              {/* Gap Analysis */}
              <div>
                <div style={{ fontWeight: 600, color: "var(--text-muted)", marginBottom: "0.25rem" }}>
                  Detection Gap Root Cause
                </div>
                <p style={{ color: "var(--text-main)", lineHeight: 1.5 }}>
                  {explanation.explanation.gapAnalysis}
                </p>
              </div>

              {/* Recommended Remediation */}
              <div>
                <div style={{ fontWeight: 600, color: "var(--status-detected)", marginBottom: "0.25rem" }}>
                  Recommended Rule Remediation
                </div>
                <p style={{ color: "var(--text-main)", lineHeight: 1.5 }}>
                  {explanation.explanation.recommendedRemediation}
                </p>
              </div>

              {/* Evidence Audit Trail */}
              <div
                style={{
                  borderTop: "1px solid rgba(255, 255, 255, 0.08)",
                  paddingTop: "0.75rem",
                  marginTop: "auto",
                }}
              >
                <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", marginBottom: "0.35rem" }}>
                  {explanation.status === "succeeded"
                    ? "Evidence cited by the model:"
                    : "Evidence used by the deterministic fallback:"}
                </div>
                {explanationEvidence.length === 0 ? (
                  <p style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                    No evidence IDs were cited.
                  </p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                    {explanationEvidence.map((item) => (
                      <div
                        key={item.evidenceId}
                        style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}
                      >
                        <code
                          style={{
                            fontFamily: "var(--font-mono)",
                            color: "var(--cyan-500)",
                            marginRight: "0.35rem",
                          }}
                        >
                          {item.evidenceId}
                        </code>
                        {item.description}
                      </div>
                    ))}
                  </div>
                )}

                <details style={{ marginTop: "0.5rem" }}>
                  <summary
                    style={{
                      fontSize: "0.7rem",
                      color: "var(--text-dim)",
                      cursor: "pointer",
                    }}
                  >
                    Evidence supplied to analysis ({explanation.inputEvidenceIds.length} IDs)
                  </summary>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", marginTop: "0.4rem" }}>
                    {explanation.inputEvidenceIds.map((cid) => (
                      <span
                        key={cid}
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "0.68rem",
                          padding: "2px 6px",
                          background: "rgba(0, 0, 0, 0.4)",
                          border: "1px solid var(--border-medium)",
                          borderRadius: "4px",
                          color: "var(--text-muted)",
                        }}
                      >
                        {cid}
                      </span>
                    ))}
                  </div>
                </details>
              </div>
            </div>
          ) : (
            <div
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                padding: "2rem",
                color: "var(--text-dim)",
              }}
            >
              <Sparkles size={36} style={{ color: "var(--purple-500)", opacity: 0.4, marginBottom: "0.75rem" }} />
              <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                {aiConfigured
                  ? 'Click "Explain Blind Spot" to request an evidence-grounded explanation from NVIDIA Nemotron.'
                  : "AI analysis is unavailable (Nebius is not configured). Run a deterministic gap analysis from the evaluator mismatches."}
              </p>
              <p style={{ fontSize: "0.72rem", marginTop: "0.35rem", maxWidth: "340px" }}>
                {aiConfigured
                  ? "The deterministic engine remains authoritative. Ungrounded model output is rejected rather than shown."
                  : "No model is called in this mode; only deterministic evidence is shown."}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
