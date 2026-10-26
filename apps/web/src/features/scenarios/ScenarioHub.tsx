import React from "react";
import type { Scenario } from "../../../../../packages/schemas/ts/contracts";

interface ScenarioHubProps {
  scenario: Scenario | null;
  onRunSimulation: () => void;
  isRunning: boolean;
}

const ROADMAP_SCENARIOS = [
  {
    id: "ransomware-cloud-stage",
    title: "Ransomware Preparation & Storage Encryption",
    category: "Endpoint & Cloud",
    description: "Adversary stages batch encryption payloads and purges snapshot restore points across multi-region backups.",
    tactics: ["Inhibit System Recovery", "Data Encrypted for Impact"],
  },
  {
    id: "insider-data-theft",
    title: "Insider Data Theft via Exfiltration Channel",
    category: "Insider Threat",
    description: "Disgruntled authorized identity creates anomalous bulk download requests during off-peak hours.",
    tactics: ["Data Staged", "Exfiltration Over Web Service"],
  },
  {
    id: "oauth-token-abuse",
    title: "OAuth Token Abuse & App Impersonation",
    category: "Identity & SaaS",
    description: "Illicit consent grant grants high-privilege offline tokens to an unverified third-party app.",
    tactics: ["Steal Application Access Token", "Account Manipulation"],
  },
  {
    id: "supply-chain-pipeline",
    title: "CI/CD Supply-Chain Infiltration",
    category: "DevSecOps",
    description: "Compromised build-runner token injects unauthorized binary packages into production registry.",
    tactics: ["Supply Chain Compromise", "Abuse Elevation Mechanism"],
  },
];

export const ScenarioHub: React.FC<ScenarioHubProps> = ({ scenario, onRunSimulation, isRunning }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Active MVP Scenario Hero */}
      <div
        className="glass-panel"
        style={{
          padding: "1.75rem",
          background: "linear-gradient(135deg, rgba(6, 182, 212, 0.12), rgba(17, 24, 39, 0.85))",
          border: "1.5px solid var(--border-accent)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1.5rem" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem", flexWrap: "wrap" }}>
              <span className="badge badge-detected">
                {scenario ? "ACTIVE MVP SCENARIO" : "SCENARIO NOT LOADED"}
              </span>
              <span className="badge badge-synthetic">SYNTHETIC ONLY • RFC 5737 SANDBOX</span>
            </div>
            <h2 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.02em" }}>
              {scenario ? scenario.name : "Waiting for scenario metadata from the API"}
            </h2>
            <p style={{ fontSize: "0.88rem", color: "var(--text-muted)", marginTop: "0.4rem", maxWidth: "780px", lineHeight: 1.6 }}>
              {scenario
                ? scenario.description
                : "Start the FastAPI backend on port 8000. The scenario definition, environment, and stage weights are served by the API and are never hard-coded in the frontend."}
            </p>

            {/* Scenario Environment from the API */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: "1rem",
                marginTop: "1.25rem",
                padding: "1rem",
                background: "rgba(0, 0, 0, 0.3)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
                fontSize: "0.78rem",
              }}
            >
              <div>
                <span style={{ color: "var(--text-dim)", textTransform: "uppercase" }}>Organization</span>
                <div style={{ fontWeight: 600, color: "var(--text-main)" }}>
                  {scenario?.environment.organization ?? "Loading..."}
                </div>
              </div>
              <div>
                <span style={{ color: "var(--text-dim)", textTransform: "uppercase" }}>Compromised Identity</span>
                <div style={{ fontWeight: 600, color: "#a5b4fc", fontFamily: "var(--font-mono)" }}>
                  {scenario?.environment.compromisedIdentity ?? "Loading..."}
                </div>
              </div>
              <div>
                <span style={{ color: "var(--text-dim)", textTransform: "uppercase" }}>Scenario Version</span>
                <div style={{ fontWeight: 600, color: "var(--text-main)", fontFamily: "var(--font-mono)" }}>
                  {scenario ? `v${scenario.version} • ${scenario.stages.length} stages • seed ${scenario.seed}` : "Loading..."}
                </div>
              </div>
              <div style={{ gridColumn: "1 / -1", borderTop: "1px solid var(--border-subtle)", paddingTop: "0.65rem" }}>
                <span style={{ color: "var(--text-dim)", textTransform: "uppercase" }}>Environment Note</span>
                <div style={{ color: "var(--text-muted)", lineHeight: 1.5 }}>
                  {scenario?.environment.note ?? "Loading..."}
                </div>
              </div>
            </div>
          </div>

          <div style={{ textAlign: "right", flexShrink: 0 }}>
            <button
              className="btn btn-primary"
              onClick={onRunSimulation}
              disabled={isRunning || !scenario}
              style={{ padding: "0.75rem 1.75rem", fontSize: "0.95rem" }}
            >
              {isRunning ? "Simulating Attack Chain..." : "Run Scenario Simulation"}
            </button>
            {!scenario && (
              <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: "0.5rem" }}>
                Requires the API and a loaded scenario.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Roadmap Future Scenarios */}
      <div>
        <div style={{ marginBottom: "0.75rem" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-main)" }}>
            Roadmap Validation Scenarios
          </h3>
          <p style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
            Illustrative future scenarios. They are not selectable or executable in this build.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem" }}>
          {ROADMAP_SCENARIOS.map((sc) => (
            <div
              key={sc.id}
              className="glass-panel"
              style={{
                padding: "1.25rem",
                opacity: 0.65,
                border: "1px dashed var(--border-medium)",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
                  <span style={{ fontSize: "0.72rem", color: "var(--text-dim)", textTransform: "uppercase", fontWeight: 600 }}>
                    {sc.category}
                  </span>
                  <span className="badge" style={{ background: "rgba(255, 255, 255, 0.05)", color: "var(--text-dim)" }}>
                    NOT IMPLEMENTED
                  </span>
                </div>
                <h4 style={{ fontSize: "0.92rem", fontWeight: 700, color: "var(--text-main)", marginBottom: "0.35rem" }}>
                  {sc.title}
                </h4>
                <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                  {sc.description}
                </p>
              </div>

              <div style={{ display: "flex", gap: "0.4rem", marginTop: "1rem", flexWrap: "wrap" }}>
                {sc.tactics.map((t) => (
                  <span
                    key={t}
                    style={{
                      fontSize: "0.68rem",
                      padding: "2px 6px",
                      borderRadius: "4px",
                      background: "rgba(255, 255, 255, 0.04)",
                      color: "var(--text-dim)",
                    }}
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
