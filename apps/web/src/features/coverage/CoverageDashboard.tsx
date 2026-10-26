import React from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Clock,
  Calculator,
  Layers,
} from "lucide-react";
import type { CoverageResult, Scenario } from "../../../../../packages/schemas/ts/contracts";

interface CoverageDashboardProps {
  coverage: CoverageResult | null;
  scenario: Scenario | null;
  onNavigateToStage?: (stageId: string) => void;
}

export const CoverageDashboard: React.FC<CoverageDashboardProps> = ({
  coverage,
  scenario,
  onNavigateToStage,
}) => {
  if (!coverage) {
    return (
      <div className="glass-panel" style={{ padding: "3rem", textAlign: "center", color: "var(--text-dim)" }}>
        No simulation coverage data available. Please click &quot;Run Simulation&quot;.
      </div>
    );
  }

  const score = Number(coverage.score.toFixed(1));
  const counts = coverage.stageCounts;
  const totalStages = coverage.stages.length;
  const scenarioStages = new Map((scenario?.stages ?? []).map((stage) => [stage.id, stage]));

  let scoreColor = "var(--status-missed)";
  if (score >= 80) scoreColor = "var(--status-detected)";
  else if (score >= 45) scoreColor = "var(--status-partial)";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Top Metric Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr 1fr 1fr", gap: "1rem" }}>
        {/* Overall Score Card */}
        <div
          className="glass-panel"
          style={{
            padding: "1.25rem",
            display: "flex",
            alignItems: "center",
            gap: "1.25rem",
            background: "linear-gradient(135deg, rgba(17, 24, 39, 0.8), rgba(15, 23, 42, 0.9))",
            border: `1.5px solid ${scoreColor}`,
            boxShadow: `0 0 20px rgba(0, 0, 0, 0.4)`,
          }}
        >
          {/* Radial Gauge SVG */}
          <div style={{ position: "relative", width: "72px", height: "72px", flexShrink: 0 }}>
            <svg width="72" height="72" viewBox="0 0 36 36">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="rgba(255, 255, 255, 0.08)"
                strokeWidth="3.5"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke={scoreColor}
                strokeWidth="3.5"
                strokeDasharray={`${score}, 100`}
                strokeLinecap="round"
              />
            </svg>
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 800,
                fontSize: "1.1rem",
                color: scoreColor,
                fontFamily: "var(--font-mono)",
              }}
            >
              {score}%
            </div>
          </div>

          <div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
              Overall Coverage
            </span>
            <h3 style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-main)" }}>
              {score >= 80 ? "Resilient" : score >= 50 ? "Moderate Gaps" : "Critical Risk"}
            </h3>
            <span style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>
              Weighted score from the backend
            </span>
          </div>
        </div>

        {/* Detected Card */}
        <div className="glass-panel" style={{ padding: "1.1rem 1.25rem", borderLeft: "3px solid var(--status-detected)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>
              Detected
            </span>
            <CheckCircle2 size={16} style={{ color: "var(--status-detected)" }} />
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--status-detected)", margin: "0.2rem 0" }}>
            {counts.detected}
            <span style={{ fontSize: "0.9rem", color: "var(--text-dim)", fontWeight: 500 }}> / {totalStages}</span>
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>Stages fully covered</div>
        </div>

        {/* Partial Card */}
        <div className="glass-panel" style={{ padding: "1.1rem 1.25rem", borderLeft: "3px solid var(--status-partial)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>
              Partial
            </span>
            <AlertTriangle size={16} style={{ color: "var(--status-partial)" }} />
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--status-partial)", margin: "0.2rem 0" }}>
            {counts.partial}
            <span style={{ fontSize: "0.9rem", color: "var(--text-dim)", fontWeight: 500 }}> / {totalStages}</span>
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>Stages with incomplete coverage</div>
        </div>

        {/* Missed Card */}
        <div className="glass-panel" style={{ padding: "1.1rem 1.25rem", borderLeft: "3px solid var(--status-missed)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>
              Missed Blind Spots
            </span>
            <XCircle size={16} style={{ color: "var(--status-missed)" }} />
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--status-missed)", margin: "0.2rem 0" }}>
            {counts.missed}
            <span style={{ fontSize: "0.9rem", color: "var(--text-dim)", fontWeight: 500 }}> / {totalStages}</span>
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>Stages with no detection</div>
        </div>

        {/* Evaluator Errors Card */}
        <div className="glass-panel" style={{ padding: "1.1rem 1.25rem", borderLeft: "3px solid var(--text-dim)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>
              Not Evaluated
            </span>
            <HelpCircle size={16} style={{ color: "var(--text-dim)" }} />
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--text-main)", margin: "0.2rem 0" }}>
            {counts.error}
            <span style={{ fontSize: "0.9rem", color: "var(--text-dim)", fontWeight: 500 }}> / {totalStages}</span>
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>Stages blocked by parser errors</div>
        </div>
      </div>

      {/* Stage-by-Stage Breakdown Table */}
      <div className="glass-panel" style={{ padding: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", gap: "1rem", flexWrap: "wrap" }}>
          <div>
            <h3 style={{ fontSize: "1.05rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Layers size={18} style={{ color: "var(--cyan-500)" }} />
              Stage-by-Stage Validation Results
            </h3>
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
              Calculated using formula version <code>{coverage.formulaVersion}</code>.
            </p>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              background: "rgba(0, 0, 0, 0.3)",
              padding: "0.35rem 0.75rem",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-subtle)",
              fontSize: "0.72rem",
              color: "var(--text-muted)",
              maxWidth: "520px",
            }}
          >
            <Calculator size={14} style={{ color: "var(--cyan-500)", flexShrink: 0 }} />
            <span>
              <code>score = 100 × Σ(stage weight × points)</code> • detected 1.0, partial 0.5, missed/error 0.0
            </span>
          </div>
        </div>

        {/* Stages List */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem" }}>
          {coverage.stages.map((stage) => {
            const meta = scenarioStages.get(stage.stageId);
            let statusBadge = <span className="badge badge-missed">Missed</span>;
            let barColor = "var(--status-missed)";
            let progressPct = 0;

            if (stage.status === "detected") {
              statusBadge = <span className="badge badge-detected">Detected</span>;
              barColor = "var(--status-detected)";
              progressPct = 100;
            } else if (stage.status === "partial") {
              statusBadge = <span className="badge badge-partial">Partial</span>;
              barColor = "var(--status-partial)";
              progressPct = 50;
            } else if (stage.status === "error") {
              statusBadge = (
                <span className="badge" style={{ background: "rgba(148, 163, 184, 0.15)", color: "#cbd5e1" }}>
                  Evaluator error
                </span>
              );
              barColor = "var(--text-dim)";
            }

            return (
              <div
                key={stage.stageId}
                onClick={() => onNavigateToStage?.(stage.stageId)}
                style={{
                  background: "rgba(0, 0, 0, 0.25)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  padding: "0.85rem 1.25rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "1.5rem",
                  cursor: onNavigateToStage ? "pointer" : "default",
                }}
              >
                {/* Left: Stage Title & ID */}
                <div style={{ width: "280px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--cyan-500)", fontSize: "0.85rem" }}>
                      {stage.stageId}
                    </span>
                    <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-main)" }}>
                      {meta?.name ?? "Stage name unavailable"}
                    </span>
                    {meta && (
                      <span
                        className="badge"
                        style={{
                          fontSize: "0.65rem",
                          background: "rgba(255, 255, 255, 0.05)",
                          color: "var(--text-dim)",
                        }}
                        title="Relative weight in the coverage formula"
                      >
                        weight {Math.round(meta.weight * 100)}%
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", marginTop: "0.2rem" }}>
                    {stage.expectedEventIds.length} expected events • {stage.matchedEventIds.length} matched •{" "}
                    {stage.matchedRuleIds.length} rules fired
                  </div>
                </div>

                {/* Center: Visual Progress Bar */}
                <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <div
                    style={{
                      flex: 1,
                      height: "8px",
                      background: "rgba(255, 255, 255, 0.06)",
                      borderRadius: "4px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${progressPct}%`,
                        height: "100%",
                        background: barColor,
                        borderRadius: "4px",
                        transition: "width 0.4s ease",
                      }}
                    />
                  </div>
                  <span style={{ width: "40px", fontSize: "0.75rem", fontFamily: "var(--font-mono)", color: barColor, textAlign: "right" }}>
                    {progressPct}%
                  </span>
                </div>

                {/* Right: Latency & Status */}
                <div style={{ display: "flex", alignItems: "center", gap: "1rem", minWidth: "190px", justifyContent: "flex-end" }}>
                  {stage.detectionLatencyMs !== null ? (
                    <span style={{ fontSize: "0.75rem", color: "var(--status-detected)", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                      <Clock size={12} /> +{stage.detectionLatencyMs}ms
                    </span>
                  ) : (
                    <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>No detection latency</span>
                  )}
                  {statusBadge}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
