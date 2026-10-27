import React, { useState } from "react";
import { FileText, Download, Sparkles } from "lucide-react";
import type { RunReport } from "../../../../../packages/schemas/ts/contracts";
import { generateReportSummary } from "../../lib/api";

interface ReportViewProps {
  report: RunReport | null;
  onReportUpdated?: (updated: RunReport) => void;
}

export const ReportView: React.FC<ReportViewProps> = ({ report, onReportUpdated }) => {
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  if (!report) {
    return (
      <div className="glass-panel" style={{ padding: "3rem", textAlign: "center", color: "var(--text-dim)" }}>
        No report generated yet. Run a simulation to compile incident readiness findings.
      </div>
    );
  }

  const handleGenerateAiSummary = async () => {
    setIsGeneratingAi(true);
    setSummaryError(null);
    try {
      const updated = await generateReportSummary(report.runId);
      if (onReportUpdated) onReportUpdated(updated);
    } catch (err: unknown) {
      setSummaryError(err instanceof Error ? err.message : "Failed to generate AI executive summary");
    } finally {
      setIsGeneratingAi(false);
    }
  };

  const handleDownloadJson = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(report, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `GhostRange-Audit-${report.runId}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const totalStages = report.coverage.stages.length;

  const handleDownloadMarkdown = () => {
    const md = `# GhostRange Incident-Readiness Audit Report

**Run ID:** ${report.runId}  
**Scenario:** ${report.scenario.name} (${report.scenario.version})  
**Simulation Seed:** ${report.seed}  
**Generated At:** ${new Date(report.generatedAt).toUTCString()}  

---

## 1. Executive Summary

GhostRange executed a deterministic attack simulation of **${report.scenario.name}** against the organization's loaded Sigma-compatible detection rules. 

- **Overall Detection Coverage:** ${report.coverage.score}% (formula ${report.coverage.formulaVersion})
- **Stages Detected:** ${report.coverage.stageCounts.detected} / ${totalStages}
- **Partial Detections:** ${report.coverage.stageCounts.partial} / ${totalStages}
- **Critical Blind Spots (Missed):** ${report.coverage.stageCounts.missed} / ${totalStages}

---

## 2. Validated Remediation Improvements

${
  report.improvements.length > 0
    ? report.improvements
        .map(
          (imp) =>
            `- **Original Rule:** \`${imp.originalRuleId}\`\n  - Coverage Leap: **${imp.coverageBefore}% ➔ ${imp.coverageAfter}%**\n  - Status: Validated by Deterministic Evaluator`
        )
        .join("\n")
    : "No rule proposals evaluated yet during this run."
}

---

## 3. Assumptions & Safety Disclaimers

${report.assumptions.map((a) => `- ${a}`).join("\n")}

### Safety Disclaimers
${report.limitations.map((l) => `- ${l}`).join("\n")}
`;

    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `GhostRange-Audit-${report.runId}.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const aiOutput = report.aiSummary?.output as Record<string, unknown> | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", maxWidth: "1000px", margin: "0 auto" }}>
      {/* Top Action Bar */}
      <div
        className="glass-panel"
        style={{
          padding: "1rem 1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <FileText size={18} style={{ color: "var(--cyan-500)" }} />
          <div>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700 }}>
              Incident-Readiness Audit Report
            </h3>
            <p style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
              Run ID: <code>{report.runId}</code> • Seed {report.seed}
            </p>
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button
            id="generate-ai-summary-btn"
            className="btn btn-secondary"
            onClick={handleGenerateAiSummary}
            disabled={isGeneratingAi}
            style={{
              fontSize: "0.78rem",
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              background: "rgba(139, 92, 246, 0.15)",
              borderColor: "rgba(139, 92, 246, 0.4)",
              color: "#d8b4fe",
            }}
          >
            <Sparkles size={14} style={{ color: "var(--cyan-400)" }} />
            {isGeneratingAi ? "Synthesizing Briefing..." : "✨ AI Executive Briefing"}
          </button>
          <button className="btn btn-secondary" onClick={handleDownloadJson} style={{ fontSize: "0.78rem" }}>
            <Download size={14} /> Download JSON
          </button>
          <button className="btn btn-primary" onClick={handleDownloadMarkdown} style={{ fontSize: "0.78rem" }}>
            <Download size={14} /> Export Markdown
          </button>
        </div>
      </div>

      {summaryError && (
        <div
          style={{
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "var(--radius-sm)",
            padding: "0.65rem 1rem",
            fontSize: "0.8rem",
            color: "#fca5a5",
          }}
        >
          {summaryError}
        </div>
      )}

      {/* Printable Report Document Card */}
      <div
        className="glass-panel"
        style={{
          padding: "2.5rem",
          background: "rgba(15, 23, 42, 0.8)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          display: "flex",
          flexDirection: "column",
          gap: "1.75rem",
          lineHeight: 1.6,
        }}
      >
        {/* Document Header */}
        <div style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <span className="badge badge-synthetic" style={{ marginBottom: "0.5rem" }}>
                SYNTHETIC CONTROL VALIDATION AUDIT
              </span>
              <h1 style={{ fontSize: "1.6rem", fontWeight: 800, letterSpacing: "-0.02em" }}>
                Detection Coverage & Security Gap Report
              </h1>
              <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.35rem" }}>
                Target Scenario: <strong>{report.scenario.name}</strong> (v{report.scenario.version})
              </p>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>Generated Date (UTC)</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", fontWeight: 600 }}>
                {new Date(report.generatedAt).toISOString().replace("T", " ").substring(0, 19)} UTC
              </div>
            </div>
          </div>
        </div>

        {/* Section 1: Executive Findings */}
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-main)", marginBottom: "0.6rem" }}>
            1. Executive Findings
          </h2>
          <p style={{ fontSize: "0.88rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
            During automated testing, GhostRange simulated a {totalStages}-stage compromised cloud identity sequence
            and evaluated the scenario&apos;s detection logic against synthetic telemetry. Coverage uses formula{" "}
            <code>{report.coverage.formulaVersion}</code>.
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: "1rem",
              background: "rgba(0, 0, 0, 0.3)",
              padding: "1.25rem",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", textTransform: "uppercase" }}>Overall Coverage</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--status-partial)" }}>
                {report.coverage.score}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", textTransform: "uppercase" }}>Stages Detected</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--status-detected)" }}>
                {report.coverage.stageCounts.detected} / {totalStages}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", textTransform: "uppercase" }}>Partial Detections</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--status-partial)" }}>
                {report.coverage.stageCounts.partial} / {totalStages}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", textTransform: "uppercase" }}>Critical Blind Spots</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--status-missed)" }}>
                {report.coverage.stageCounts.missed} / {totalStages}
              </div>
            </div>
          </div>
        </div>

        {/* Section 2: Validated Remediations */}
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-main)", marginBottom: "0.6rem" }}>
            2. Validated Remediation Improvements
          </h2>
          {report.improvements.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {report.improvements.map((imp) => (
                <div
                  key={imp.proposalId}
                  style={{
                    background: "rgba(16, 185, 129, 0.08)",
                    border: "1px solid rgba(16, 185, 129, 0.25)",
                    borderRadius: "var(--radius-md)",
                    padding: "0.85rem 1.25rem",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, color: "var(--text-main)" }}>
                      Rule Remediation: <code>{imp.originalRuleId}</code>
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      Proposal ID: {imp.proposalId} • Tested against identical simulation telemetry
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: "1.15rem", fontWeight: 800, color: "var(--status-detected)" }}>
                      {imp.coverageBefore}% ➔ {imp.coverageAfter}%
                    </div>
                    <span className="badge badge-detected" style={{ fontSize: "0.65rem" }}>
                      VALIDATED ON THIS RUN
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>
              No rule improvements have been validated yet in this session. Visit the &quot;Rule Improvement & Diff&quot; tab to test proposed fixes.
            </p>
          )}
        </div>

        {/* Section 3: AI Executive Assessment (NVIDIA Nemotron) */}
        {report.aiSummary && aiOutput && (
          <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Sparkles size={17} style={{ color: "var(--cyan-400)" }} />
                <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-main)", margin: 0 }}>
                  3. AI Executive Assessment
                </h2>
              </div>
              <span
                className="badge"
                style={{
                  background: report.aiSummary.status === "succeeded" ? "rgba(16, 185, 129, 0.12)" : "rgba(245, 158, 11, 0.12)",
                  color: report.aiSummary.status === "succeeded" ? "var(--status-detected)" : "var(--status-partial)",
                  fontSize: "0.7rem",
                }}
              >
                {report.aiSummary.model ? `Model: ${report.aiSummary.model}` : "Deterministic Fallback (No Key)"}
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem", background: "rgba(0, 0, 0, 0.3)", padding: "1.25rem", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
              {Boolean(aiOutput.executiveSummary) && (
                <p style={{ fontSize: "0.9rem", color: "var(--text-main)", fontWeight: 500, lineHeight: 1.6, margin: 0 }}>
                  {String(aiOutput.executiveSummary)}
                </p>
              )}
              {Boolean(aiOutput.attackNarrative) && (
                <div>
                  <div style={{ fontSize: "0.74rem", textTransform: "uppercase", color: "var(--text-dim)", fontWeight: 700, marginBottom: "0.25rem" }}>
                    Simulated Attack Narrative
                  </div>
                  <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                    {String(aiOutput.attackNarrative)}
                  </div>
                </div>
              )}
              {Boolean(aiOutput.detectionGaps) && (
                <div>
                  <div style={{ fontSize: "0.74rem", textTransform: "uppercase", color: "var(--text-dim)", fontWeight: 700, marginBottom: "0.25rem" }}>
                    Identified Detection Gaps
                  </div>
                  <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                    {String(aiOutput.detectionGaps)}
                  </div>
                </div>
              )}
              {Boolean(aiOutput.remediationImpact) && (
                <div>
                  <div style={{ fontSize: "0.74rem", textTransform: "uppercase", color: "var(--text-dim)", fontWeight: 700, marginBottom: "0.25rem" }}>
                    Remediation Impact
                  </div>
                  <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                    {String(aiOutput.remediationImpact)}
                  </div>
                </div>
              )}
              {Array.isArray(aiOutput.recommendations) && (
                <div>
                  <div style={{ fontSize: "0.74rem", textTransform: "uppercase", color: "var(--text-dim)", fontWeight: 700, marginBottom: "0.35rem" }}>
                    Strategic Defensive Recommendations
                  </div>
                  <ul style={{ paddingLeft: "1.2rem", margin: 0, fontSize: "0.82rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                    {(aiOutput.recommendations as string[]).map((rec, idx) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Section 4: Assumptions & Disclaimers */}
        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "1.25rem", fontSize: "0.78rem" }}>
          <h3 style={{ fontSize: "0.88rem", fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", marginBottom: "0.5rem" }}>
            Safety Disclaimers & Assumptions
          </h3>
          <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            {report.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
            {report.limitations.map((l, i) => (
              <li key={`lim-${i}`}>{l}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};
