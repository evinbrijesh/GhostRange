import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  GitBranch,
  Volume2,
  Terminal,
  Play,
  Copy,
  Check,
  CheckCircle2,
  XCircle,
  FileCode,
} from "lucide-react";
import {
  fetchDetectionOps,
  fetchCiReport,
  validateCustomRule,
  evaluateCustomRule,
  type DetectionOpsMetrics,
  type CiReportResponse,
  type RuleValidationResponse,
  type RuleEvaluationResponse,
} from "../../lib/api";

interface DetectionOpsViewProps {
  runId: string | null;
}

const SAMPLE_CUSTOM_RULE = `title: Detect MFA Preference Modification
id: rule_s2_custom_mfa_update
stage: S2
logsource:
  product: cloud
  service: iam
selection:
  action: UpdateMfaPreference
condition: selection
level: high`;

export const DetectionOpsView: React.FC<DetectionOpsViewProps> = ({ runId }) => {
  const [metrics, setMetrics] = useState<DetectionOpsMetrics | null>(null);
  const [ciReport, setCiReport] = useState<CiReportResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Playground state
  const [playgroundYaml, setPlaygroundYaml] = useState<string>(SAMPLE_CUSTOM_RULE);
  const [validationResult, setValidationResult] = useState<RuleValidationResponse | null>(null);
  const [evaluationResult, setEvaluationResult] = useState<RuleEvaluationResponse | null>(null);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [copiedCi, setCopiedCi] = useState<boolean>(false);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;

    async function loadData() {
      setIsLoading(true);
      setError(null);
      try {
        const [opsData, reportData] = await Promise.all([
          fetchDetectionOps(runId!),
          fetchCiReport(runId!),
        ]);
        if (!cancelled) {
          setMetrics(opsData);
          setCiReport(reportData);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load DetectionOps metrics");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadData();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  const handleValidateSyntax = async () => {
    try {
      const res = await validateCustomRule(playgroundYaml);
      setValidationResult(res);
    } catch (err: unknown) {
      setValidationResult({
        valid: false,
        errors: [err instanceof Error ? err.message : "Validation request failed"],
      });
    }
  };

  const handleEvaluatePlayground = async () => {
    setIsEvaluating(true);
    setEvaluationResult(null);
    try {
      const res = await evaluateCustomRule(playgroundYaml, runId || undefined);
      setEvaluationResult(res);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleCopyCiMarkdown = () => {
    if (!ciReport?.markdown) return;
    navigator.clipboard.writeText(ciReport.markdown);
    setCopiedCi(true);
    setTimeout(() => setCopiedCi(false), 2500);
  };

  const isGateBlocked = ciReport
    ? ciReport.gate.status === "blocked"
    : metrics?.regressionStatus === "regression_detected";
  const gateFailure = ciReport?.gate.failures[0] ?? "Coverage regression detected";
  const gateSummary = isGateBlocked
    ? gateFailure
    : "All gate checks meet the committed baseline";

  if (!runId) {
    return (
      <div className="glass-panel" style={{ padding: "3rem", textAlign: "center", color: "var(--text-dim)" }}>
        Please run a simulation to inspect DetectionOps metrics, behavioral variants, and noise suppression.
      </div>
    );
  }

  if (isLoading && !metrics) {
    return (
      <div className="glass-panel" style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
        Computing DetectionOps variant resilience and noise suppression...
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel" style={{ padding: "2rem", color: "var(--status-missed)", border: "1px solid rgba(239, 68, 68, 0.3)" }}>
        Failed to load DetectionOps metrics: {error}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* 4-Tier DetectionOps Metrics Header */}
      <div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
          <div>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Terminal size={20} color="var(--cyan-500)" />
              DetectionOps CI/CD Metrics
            </h2>
            <p style={{ fontSize: "0.85rem", color: "var(--text-dim)", marginTop: "0.2rem" }}>
              Automated testing across attack variants, offline noise suppression, and CI/CD regression gating.
            </p>
          </div>
          <button
            className="btn btn-secondary"
            onClick={handleCopyCiMarkdown}
            style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8rem", padding: "0.5rem 0.9rem" }}
          >
            {copiedCi ? <Check size={14} color="var(--status-detected)" /> : <Copy size={14} />}
            {copiedCi ? "Copied CI Report!" : "Export GitHub Actions Markdown"}
          </button>
        </div>

        {metrics && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
            {/* Metric 1: Attack Coverage */}
            <div className="glass-panel" style={{ padding: "1.25rem", borderLeft: "4px solid var(--cyan-500)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase" }}>
                <span>Attack Coverage</span>
                <ShieldCheck size={16} color="var(--cyan-500)" />
              </div>
              <div style={{ fontSize: "1.85rem", fontWeight: 800, color: "var(--text-main)", marginTop: "0.4rem" }}>
                {metrics.attackCoverage}%
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.25rem" }}>
                Base scenario expected stages
              </div>
            </div>

            {/* Metric 2: Variant Resilience */}
            <div className="glass-panel" style={{ padding: "1.25rem", borderLeft: "4px solid #8b5cf6" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase" }}>
                <span>Variant Resilience</span>
                <GitBranch size={16} color="#8b5cf6" />
              </div>
              <div style={{ fontSize: "1.85rem", fontWeight: 800, color: "#c084fc", marginTop: "0.4rem" }}>
                {metrics.variantResilience}%
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.25rem" }}>
                Mean across 3 attack variants
              </div>
            </div>

            {/* Metric 3: Benign Suppression */}
            <div className="glass-panel" style={{ padding: "1.25rem", borderLeft: "4px solid var(--status-detected)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase" }}>
                <span>Benign Suppression</span>
                <Volume2 size={16} color="var(--status-detected)" />
              </div>
              <div style={{ fontSize: "1.85rem", fontWeight: 800, color: "var(--status-detected)", marginTop: "0.4rem" }}>
                {metrics.benignSuppression}%
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.25rem" }}>
                Noise Risk: <span style={{ textTransform: "uppercase", fontWeight: 700, color: metrics.noiseRisk === "low" ? "var(--status-detected)" : "#f59e0b" }}>{metrics.noiseRisk}</span> (Offline)
              </div>
            </div>

            {/* Metric 4: Regression Guard */}
            <div
              className="glass-panel"
              style={{
                padding: "1.25rem",
                borderLeft: `4px solid ${isGateBlocked ? "var(--status-missed)" : "var(--status-detected)"}`,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase" }}>
                <span>Regression Guard</span>
                {isGateBlocked ? (
                  <XCircle size={16} color="var(--status-missed)" />
                ) : (
                  <CheckCircle2 size={16} color="var(--status-detected)" />
                )}
              </div>
              <div
                style={{
                  fontSize: "1.3rem",
                  fontWeight: 800,
                  marginTop: "0.5rem",
                  color: isGateBlocked ? "var(--status-missed)" : "var(--status-detected)",
                  textTransform: "uppercase",
                }}
              >
                {isGateBlocked ? "BLOCKED" : "PASSED"}
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.25rem" }}>
                {gateSummary}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Behavioral Variant Matrix */}
      {metrics && metrics.variantBreakdown.length > 0 && (
        <div className="glass-panel" style={{ padding: "1.5rem" }}>
          <h3 style={{ fontSize: "1.05rem", fontWeight: 700, marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <GitBranch size={18} color="#8b5cf6" />
            Behavioral Variant Matrix (3 Deterministic Variations)
          </h3>
          <p style={{ fontSize: "0.8rem", color: "var(--text-dim)", marginBottom: "1.25rem" }}>
            The detection engine evaluates rules across distinct adversary behavioral mutations to prevent rule overfitting.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
            {metrics.variantBreakdown.map((variant) => (
              <div
                key={variant.variantId}
                style={{
                  background: "rgba(17, 24, 39, 0.6)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "8px",
                  padding: "1rem",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                    <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--text-main)" }}>
                      {variant.name}
                    </span>
                    <span className="badge" style={{ background: "rgba(139, 92, 246, 0.15)", color: "#c084fc", border: "1px solid rgba(139, 92, 246, 0.3)", fontSize: "0.7rem" }}>
                      Seed {variant.seed}
                    </span>
                  </div>
                  <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "0.85rem", lineHeight: "1.4" }}>
                    {variant.description}
                  </p>
                </div>

                <div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "0.75rem", borderTop: "1px solid rgba(255, 255, 255, 0.06)", fontSize: "0.8rem" }}>
                    <span style={{ color: "var(--text-dim)" }}>Events: {variant.eventCount}</span>
                    <span style={{ fontWeight: 700, color: variant.coverageScore >= 60 ? "var(--status-detected)" : "#f59e0b" }}>
                      Coverage: {variant.coverageScore}%
                    </span>
                  </div>

                  {/* Stage pills */}
                  <div style={{ display: "flex", gap: "4px", marginTop: "0.5rem" }}>
                    {Object.entries(variant.stageStatuses).map(([stId, status]) => {
                      let bg = "rgba(239, 68, 68, 0.2)";
                      let fg = "var(--status-missed)";
                      if (status === "detected") {
                        bg = "rgba(16, 185, 129, 0.2)";
                        fg = "var(--status-detected)";
                      } else if (status === "partial") {
                        bg = "rgba(245, 158, 11, 0.2)";
                        fg = "var(--status-partial)";
                      }
                      return (
                        <span
                          key={stId}
                          title={`${stId}: ${status}`}
                          style={{
                            fontSize: "0.65rem",
                            padding: "2px 5px",
                            borderRadius: "3px",
                            background: bg,
                            color: fg,
                            fontWeight: 600,
                          }}
                        >
                          {stId}
                        </span>
                      );
                    })}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bring Your Own Detection Rule Playground */}
      <div className="glass-panel" style={{ padding: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
          <div>
            <h3 style={{ fontSize: "1.05rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <FileCode size={18} color="var(--cyan-500)" />
              Bring Your Own Rule (Detection Engineering Playground)
            </h3>
            <p style={{ fontSize: "0.8rem", color: "var(--text-dim)", marginTop: "0.2rem" }}>
              Test custom Sigma YAML detection rules live against synthetic attack telemetry and the benign noise corpus.
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              className="btn btn-secondary"
              onClick={() => setPlaygroundYaml(SAMPLE_CUSTOM_RULE)}
              style={{ fontSize: "0.75rem", padding: "0.4rem 0.75rem" }}
            >
              Load S2 MFA Fix
            </button>
            <button
              className="btn btn-secondary"
              onClick={() =>
                setPlaygroundYaml(`title: Tor Exit Access To Prod Storage
id: rule_s6_tor_prod_storage
stage: S6
logsource:
  product: cloud
  service: storage
selection:
  action: GetObject
  resource.id: bucket-northwind-prod-backups
condition: selection
level: critical`)
              }
              style={{ fontSize: "0.75rem", padding: "0.4rem 0.75rem" }}
            >
              Load S6 Storage Rule
            </button>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: "1.25rem", marginTop: "1rem" }}>
          {/* YAML Editor Area */}
          <div>
            <textarea
              value={playgroundYaml}
              onChange={(e) => setPlaygroundYaml(e.target.value)}
              rows={12}
              style={{
                width: "100%",
                background: "rgba(10, 14, 23, 0.9)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "6px",
                padding: "0.85rem",
                fontFamily: "var(--font-mono)",
                fontSize: "0.85rem",
                color: "var(--text-main)",
                resize: "vertical",
                lineHeight: "1.45",
              }}
              placeholder="Paste or write custom Sigma YAML rule here..."
            />
            <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.75rem" }}>
              <button
                className="btn btn-secondary"
                onClick={handleValidateSyntax}
                style={{ fontSize: "0.8rem", padding: "0.45rem 1rem" }}
              >
                Validate Syntax
              </button>
              <button
                className="btn btn-primary"
                onClick={handleEvaluatePlayground}
                disabled={isEvaluating}
                style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", padding: "0.45rem 1.25rem" }}
              >
                <Play size={14} fill="currentColor" />
                {isEvaluating ? "Evaluating..." : "Test Against Telemetry & Noise"}
              </button>
            </div>
          </div>

          {/* Test Outcomes */}
          <div
            style={{
              background: "rgba(17, 24, 39, 0.5)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "6px",
              padding: "1rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem",
            }}
          >
            <h4 style={{ fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)" }}>
              Evaluation Feedback
            </h4>

            {validationResult && (
              <div
                style={{
                  padding: "0.75rem",
                  borderRadius: "6px",
                  background: validationResult.valid ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                  border: `1px solid ${validationResult.valid ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontWeight: 700, fontSize: "0.8rem", color: validationResult.valid ? "var(--status-detected)" : "var(--status-missed)" }}>
                  {validationResult.valid ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                  Syntax {validationResult.valid ? "Valid" : "Errors"}
                </div>
                {validationResult.valid ? (
                  <p style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.2rem" }}>
                    Rule ID: <code>{validationResult.ruleId}</code> ({validationResult.stageId})
                  </p>
                ) : (
                  <ul style={{ fontSize: "0.75rem", color: "var(--status-missed)", marginTop: "0.3rem", paddingLeft: "1.2rem" }}>
                    {validationResult.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {evaluationResult && (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div
                  style={{
                    padding: "0.75rem",
                    borderRadius: "6px",
                    background: evaluationResult.attackMatchesCount > 0 ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                    border: `1px solid ${evaluationResult.attackMatchesCount > 0 ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: "0.8rem", color: evaluationResult.attackMatchesCount > 0 ? "var(--status-detected)" : "var(--status-missed)" }}>
                    Attack Telemetry Matches: {evaluationResult.attackMatchesCount}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.2rem" }}>
                    {evaluationResult.attackMatchesCount > 0
                      ? `Rule triggered on targeted adversary activity in stage ${evaluationResult.stageId}.`
                      : "Rule did not match any attack events in the simulated timeline."}
                  </div>
                </div>

                <div
                  style={{
                    padding: "0.75rem",
                    borderRadius: "6px",
                    background: evaluationResult.noiseHitsCount === 0 ? "rgba(16, 185, 129, 0.1)" : "rgba(245, 158, 11, 0.1)",
                    border: `1px solid ${evaluationResult.noiseHitsCount === 0 ? "rgba(16, 185, 129, 0.3)" : "rgba(245, 158, 11, 0.3)"}`,
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: "0.8rem", color: evaluationResult.noiseHitsCount === 0 ? "var(--status-detected)" : "#f59e0b" }}>
                    Offline Benign Noise Hits: {evaluationResult.noiseHitsCount}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.2rem" }}>
                    {evaluationResult.noiseHitsCount === 0
                      ? "Zero false alerts against 12 benign administrative events."
                      : `Rule triggered ${evaluationResult.noiseHitsCount} false positive alert(s) on routine admin activity!`}
                  </div>
                </div>
              </div>
            )}

            {!validationResult && !evaluationResult && (
              <div style={{ color: "var(--text-dim)", fontSize: "0.8rem", fontStyle: "italic", textAlign: "center", padding: "2rem 0" }}>
                Click &quot;Validate Syntax&quot; or &quot;Test Against Telemetry &amp; Noise&quot; to inspect rule behavior.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* CI/CD & GitHub Actions Preview */}
      {ciReport && (
        <div className="glass-panel" style={{ padding: "1.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
            <h3 style={{ fontSize: "1.05rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Terminal size={18} color="#06b6d4" />
              GitHub Actions CI/CD Pull Request Summary Preview
            </h3>
            <span
              className="badge"
              style={{
                background: ciReport.decision === "PASS" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                color: ciReport.decision === "PASS" ? "var(--status-detected)" : "var(--status-missed)",
                border: `1px solid ${ciReport.decision === "PASS" ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
                fontWeight: 700,
              }}
            >
              GATE: {ciReport.decision}
            </span>
          </div>

          <pre
            style={{
              background: "rgba(10, 14, 23, 0.9)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "6px",
              padding: "1rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.8rem",
              color: "var(--text-main)",
              overflowX: "auto",
              maxHeight: "260px",
              lineHeight: "1.5",
            }}
          >
            {ciReport.markdown}
          </pre>
        </div>
      )}
    </div>
  );
};
