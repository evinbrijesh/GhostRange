import React from "react";
import {
  ShieldAlert,
  Play,
  RotateCcw,
  Sparkles,
  Activity,
  Layers,
  FileCode,
  FileText,
  Search,
  CheckCircle2,
} from "lucide-react";

export type NavTab = "graph" | "telemetry" | "coverage" | "rules" | "report" | "intel";

interface HeaderProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  isRunning: boolean;
  onRunSimulation: () => void;
  onReset: () => void;
  runId: string | null;
  seed: number;
  onSeedChange: (seed: number) => void;
  isBackendConnected: boolean;
  aiConfigured: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  isRunning,
  onRunSimulation,
  onReset,
  runId,
  seed,
  onSeedChange,
  isBackendConnected,
  aiConfigured,
}) => {
  return (
    <header
      style={{
        background: "rgba(11, 15, 25, 0.85)",
        backdropFilter: "blur(16px)",
        borderBottom: "1px solid var(--border-subtle)",
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      {/* Top Navbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0.85rem 1.75rem",
          gap: "1rem",
        }}
      >
        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.85rem" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, #06b6d4, #8b5cf6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 15px rgba(6, 182, 212, 0.4)",
            }}
          >
            <ShieldAlert size={20} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span style={{ fontSize: "1.25rem", fontWeight: 800, letterSpacing: "-0.02em" }}>
                Ghost<span style={{ color: "var(--cyan-500)" }}>Range</span>
              </span>
              <span className="badge" style={{ background: "rgba(6, 182, 212, 0.12)", color: "#22d3ee", border: "1px solid rgba(6, 182, 212, 0.3)" }}>
                v0.1 MVP
              </span>
            </div>
            <p style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
              Defensive Security Control Validation Platform
            </p>
          </div>
        </div>

        {/* Center: Scenario Info, Seed & Run ID */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            background: "rgba(17, 24, 39, 0.6)",
            padding: "0.35rem 0.85rem",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            fontSize: "0.82rem",
          }}
        >
          <span style={{ color: "var(--text-muted)" }}>Scenario:</span>
          <span style={{ fontWeight: 600, color: "var(--text-main)" }}>
            Cloud Identity Compromise
          </span>
          {runId && (
            <>
              <span style={{ color: "var(--border-medium)" }}>|</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--cyan-500)" }}>
                {runId}
              </span>
            </>
          )}
          <span style={{ color: "var(--border-medium)" }}>|</span>
          <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", color: "var(--text-muted)" }}>
            Seed:
            <input
              type="number"
              value={seed}
              onChange={(e) => onSeedChange(Number(e.target.value))}
              style={{
                width: "60px",
                background: "rgba(0, 0, 0, 0.3)",
                border: "1px solid var(--border-medium)",
                color: "var(--cyan-500)",
                borderRadius: "4px",
                padding: "2px 6px",
                fontFamily: "var(--font-mono)",
                fontSize: "0.78rem",
              }}
            />
          </label>
        </div>

        {/* Right Action Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          {/* Status Indicators */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.75rem" }}>
            <span
              className="badge"
              style={{
                background: isBackendConnected ? "rgba(16, 185, 129, 0.1)" : "rgba(245, 158, 11, 0.1)",
                color: isBackendConnected ? "var(--status-detected)" : "var(--status-partial)",
                border: `1px solid ${isBackendConnected ? "rgba(16, 185, 129, 0.3)" : "rgba(245, 158, 11, 0.3)"}`,
              }}
              title={isBackendConnected ? "FastAPI backend running" : "Using local simulation fallback"}
            >
              <span
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  background: isBackendConnected ? "var(--status-detected)" : "var(--status-partial)",
                  display: "inline-block",
                }}
              />
              {isBackendConnected ? "API LIVE" : "DEMO CACHE"}
            </span>

            <span
              className="badge badge-ai"
              title={aiConfigured ? "Nebius Token Factory live" : "Using grounded Nemotron reasoning fallback"}
            >
              <Sparkles size={11} />
              {aiConfigured ? "NVIDIA NEMOTRON" : "AI GROUNDED"}
            </span>
          </div>

          {/* Reset button */}
          <button
            className="btn btn-secondary"
            onClick={onReset}
            disabled={isRunning}
            title="Reset simulation to initial seed state"
            style={{ padding: "0.45rem 0.75rem", fontSize: "0.8rem" }}
          >
            <RotateCcw size={14} />
          </button>

          {/* Run button */}
          <button
            id="run-simulation-button"
            className="btn btn-primary"
            onClick={onRunSimulation}
            disabled={isRunning}
            style={{ padding: "0.5rem 1.25rem", minWidth: "160px" }}
          >
            {isRunning ? (
              <>
                <span className="animate-spin" style={{ display: "inline-block" }}>
                  <RotateCcw size={16} />
                </span>
                Evaluating...
              </>
            ) : (
              <>
                <Play size={16} fill="currentColor" />
                Run Simulation
              </>
            )}
          </button>
        </div>
      </div>

      {/* Navigation Bar */}
      <nav
        style={{
          display: "flex",
          gap: "0.5rem",
          padding: "0 1.75rem",
          borderTop: "1px solid rgba(255, 255, 255, 0.05)",
          overflowX: "auto",
        }}
      >
        <button
          id="tab-attack-graph"
          onClick={() => onTabChange("graph")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.75rem 1rem",
            background: "none",
            border: "none",
            borderBottom: activeTab === "graph" ? "2px solid var(--cyan-500)" : "2px solid transparent",
            color: activeTab === "graph" ? "var(--cyan-500)" : "var(--text-muted)",
            fontWeight: activeTab === "graph" ? 600 : 500,
            fontSize: "0.85rem",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          <Activity size={16} />
          Attack Graph
        </button>

        <button
          id="tab-telemetry"
          onClick={() => onTabChange("telemetry")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.75rem 1rem",
            background: "none",
            border: "none",
            borderBottom: activeTab === "telemetry" ? "2px solid var(--cyan-500)" : "2px solid transparent",
            color: activeTab === "telemetry" ? "var(--cyan-500)" : "var(--text-muted)",
            fontWeight: activeTab === "telemetry" ? 600 : 500,
            fontSize: "0.85rem",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          <Layers size={16} />
          Telemetry Explorer
        </button>

        <button
          id="tab-coverage"
          onClick={() => onTabChange("coverage")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.75rem 1rem",
            background: "none",
            border: "none",
            borderBottom: activeTab === "coverage" ? "2px solid var(--cyan-500)" : "2px solid transparent",
            color: activeTab === "coverage" ? "var(--cyan-500)" : "var(--text-muted)",
            fontWeight: activeTab === "coverage" ? 600 : 500,
            fontSize: "0.85rem",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          <CheckCircle2 size={16} />
          Detection Coverage
        </button>

        <button
          id="tab-rules"
          onClick={() => onTabChange("rules")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.75rem 1rem",
            background: "none",
            border: "none",
            borderBottom: activeTab === "rules" ? "2px solid var(--purple-500)" : "2px solid transparent",
            color: activeTab === "rules" ? "#c084fc" : "var(--text-muted)",
            fontWeight: activeTab === "rules" ? 600 : 500,
            fontSize: "0.85rem",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          <FileCode size={16} />
          Rule Improvement & Diff
          <span className="badge badge-ai" style={{ fontSize: "0.65rem", padding: "1px 6px" }}>
            AI Remediate
          </span>
        </button>

        <button
          id="tab-report"
          onClick={() => onTabChange("report")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.75rem 1rem",
            background: "none",
            border: "none",
            borderBottom: activeTab === "report" ? "2px solid var(--cyan-500)" : "2px solid transparent",
            color: activeTab === "report" ? "var(--cyan-500)" : "var(--text-muted)",
            fontWeight: activeTab === "report" ? 600 : 500,
            fontSize: "0.85rem",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          <FileText size={16} />
          Readiness Report
        </button>

        <button
          id="tab-intel"
          onClick={() => onTabChange("intel")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.75rem 1rem",
            background: "none",
            border: "none",
            borderBottom: activeTab === "intel" ? "2px solid var(--cyan-500)" : "2px solid transparent",
            color: activeTab === "intel" ? "var(--cyan-500)" : "var(--text-muted)",
            fontWeight: activeTab === "intel" ? 600 : 500,
            fontSize: "0.85rem",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          <Search size={16} />
          Threat Intelligence (Tavily)
        </button>
      </nav>
    </header>
  );
};
