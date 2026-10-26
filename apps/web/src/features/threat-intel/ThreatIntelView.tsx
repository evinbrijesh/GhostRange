import React from "react";
import { BookOpen, Globe, Info } from "lucide-react";

interface TechniqueReference {
  techniqueId: string;
  name: string;
  stageId: string;
  stageName: string;
  description: string;
}

// Static reference content from the MITRE ATT&CK framework, mapped to the
// scenario's stages. This is not retrieved intelligence and is never evidence.
const TECHNIQUE_REFERENCES: TechniqueReference[] = [
  {
    techniqueId: "T1078.004",
    name: "Valid Accounts: Cloud Accounts",
    stageId: "S1",
    stageName: "Initial access",
    description:
      "Adversaries may obtain and abuse credentials of existing cloud accounts to gain initial access, persistence, privilege escalation, or defense evasion.",
  },
  {
    techniqueId: "T1556",
    name: "Modify Authentication Process",
    stageId: "S2",
    stageName: "MFA manipulation",
    description:
      "Adversaries may modify authentication mechanisms and processes to access user credentials or enable otherwise unwarranted access to accounts.",
  },
  {
    techniqueId: "T1087.004",
    name: "Account Discovery: Cloud Account",
    stageId: "S3",
    stageName: "Discovery",
    description:
      "Adversaries may attempt to enumerate cloud accounts, roles, and related directory objects to understand the environment before acting.",
  },
  {
    techniqueId: "T1098",
    name: "Account Manipulation",
    stageId: "S4",
    stageName: "Privilege escalation",
    description:
      "Adversaries may manipulate accounts, roles, or policies to maintain or elevate access to victim systems.",
  },
  {
    techniqueId: "T1098.001",
    name: "Additional Cloud Credentials",
    stageId: "S5",
    stageName: "Persistence",
    description:
      "Adversaries may add credentials such as access keys to cloud accounts to maintain persistent access across credential resets.",
  },
  {
    techniqueId: "T1530",
    name: "Data from Cloud Storage",
    stageId: "S6",
    stageName: "Sensitive access",
    description:
      "Adversaries may access data from cloud storage infrastructure, including buckets, blobs, and managed database snapshots.",
  },
  {
    techniqueId: "T1074.002",
    name: "Data Staged: Remote Data Staging",
    stageId: "S7",
    stageName: "Data staging",
    description:
      "Adversaries may stage collected data in a central location or directory prior to exfiltration, including another cloud storage location.",
  },
];

export const ThreatIntelView: React.FC = () => {
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
          background: "linear-gradient(135deg, rgba(6, 182, 212, 0.08), rgba(17, 24, 39, 0.8))",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
            <span className="badge" style={{ background: "rgba(6, 182, 212, 0.12)", color: "var(--cyan-500)" }}>
              <Globe size={12} /> Threat Context (Sample)
            </span>
            <span className="badge" style={{ background: "rgba(255, 255, 255, 0.05)", color: "var(--text-muted)" }}>
              Static Reference • No Live Retrieval
            </span>
            <span className="badge" style={{ background: "rgba(255, 255, 255, 0.05)", color: "var(--text-muted)" }}>
              Context Only • Never Simulated Evidence
            </span>
          </div>
          <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginTop: "0.4rem" }}>
            ATT&amp;CK Context for This Scenario
          </h2>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.2rem", maxWidth: "900px" }}>
            Static MITRE ATT&amp;CK technique references mapped to the seven scenario stages. This page performs no
            Tavily search and makes no claim about current adversary campaigns.
          </p>
        </div>
      </div>

      {/* Honest integration status */}
      <div
        className="glass-panel"
        style={{
          padding: "1rem 1.25rem",
          display: "flex",
          alignItems: "flex-start",
          gap: "0.65rem",
          background: "rgba(245, 158, 11, 0.06)",
          border: "1px solid rgba(245, 158, 11, 0.25)",
          fontSize: "0.8rem",
          color: "var(--text-muted)",
        }}
      >
        <Info size={17} style={{ color: "var(--status-partial)", flexShrink: 0, marginTop: "0.1rem" }} />
        <div>
          <strong style={{ color: "var(--text-main)" }}>Tavily is optional and not configured in this build.</strong>{" "}
          If enabled later, retrieved threat reports must be shown as external context with their source URLs and
          retrieval time, kept separate from run telemetry, and never used as proof that a detection fired.
        </div>
      </div>

      {/* Static Reference Cards */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.75rem" }}>
          <BookOpen size={16} style={{ color: "var(--cyan-500)" }} />
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-main)" }}>
            Framework References
          </h3>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem" }}>
          {TECHNIQUE_REFERENCES.map((ref) => (
            <div
              key={`${ref.stageId}-${ref.techniqueId}`}
              className="glass-panel"
              style={{
                padding: "0.9rem 1.25rem",
                display: "flex",
                alignItems: "flex-start",
                gap: "1rem",
              }}
            >
              <div
                style={{
                  minWidth: "110px",
                  padding: "0.35rem 0.6rem",
                  borderRadius: "var(--radius-sm)",
                  background: "rgba(56, 189, 248, 0.08)",
                  border: "1px solid rgba(56, 189, 248, 0.22)",
                  textAlign: "center",
                }}
              >
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem", fontWeight: 700, color: "#38bdf8" }}>
                  {ref.techniqueId}
                </div>
                <div style={{ fontSize: "0.65rem", color: "var(--text-dim)", textTransform: "uppercase" }}>
                  {ref.stageId} • {ref.stageName}
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text-main)" }}>{ref.name}</h4>
                <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.5, marginTop: "0.2rem" }}>
                  {ref.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <p style={{ fontSize: "0.72rem", color: "var(--text-dim)", lineHeight: 1.5 }}>
        Technique names and descriptions are paraphrased from the public MITRE ATT&amp;CK knowledge base. They explain
        terminology only; they do not describe the fictional Northwind Analytics environment and are not part of the
        detection coverage score.
      </p>
    </div>
  );
};
