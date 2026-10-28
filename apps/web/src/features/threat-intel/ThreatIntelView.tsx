import React, { useEffect, useState } from "react";
import { BookOpen, ExternalLink, Globe, Info, RefreshCw } from "lucide-react";
import { fetchStageThreatIntel, type ThreatIntelResponse } from "../../lib/api";

interface TechniqueReference {
  techniqueId: string;
  name: string;
  stageId: string;
  stageName: string;
  description: string;
}

// Static reference content from the MITRE ATT&CK framework, mapped to the
// scenario's stages. Kept separate from run telemetry.
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
  const [selectedStageId, setSelectedStageId] = useState<string>("S2");
  const [intelData, setIntelData] = useState<ThreatIntelResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const loadStageIntel = async (stageId: string) => {
    setIsLoading(true);
    try {
      const data = await fetchStageThreatIntel(stageId);
      setIntelData(data);
    } catch {
      // Fallback is handled automatically by the API
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStageIntel(selectedStageId);
  }, [selectedStageId]);

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
              <Globe size={12} /> Threat Context
            </span>
            {intelData?.liveSearch ? (
              <span className="badge badge-detected">
                Live Tavily Search Active
              </span>
            ) : (
              <span className="badge badge-partial">
                Curated ATT&amp;CK Reference (Tavily Key Unconfigured)
              </span>
            )}
            <span className="badge" style={{ background: "rgba(255, 255, 255, 0.05)", color: "var(--text-muted)" }}>
              Context Only • Never Simulated Evidence
            </span>
          </div>
          <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginTop: "0.4rem" }}>
            ATT&amp;CK Threat Intelligence &amp; Adversary TTPs
          </h2>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.2rem", maxWidth: "900px" }}>
            {intelData?.liveSearch
              ? "Real-world adversary campaign context dynamically retrieved via Tavily Search API. External reference only; never alters authoritative run coverage."
              : "Displaying curated MITRE ATT&CK adversary reference data (Tavily key unconfigured). External reference only; never alters authoritative run coverage."}
          </p>
        </div>
      </div>

      {/* Selected Technique Live Enrichment Card */}
      {intelData && (
        <div
          className="glass-panel"
          style={{
            padding: "1.25rem 1.5rem",
            background: "rgba(15, 23, 42, 0.75)",
            border: "1px solid rgba(6, 182, 212, 0.25)",
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span className="badge" style={{ background: "rgba(56, 189, 248, 0.12)", color: "#38bdf8", fontWeight: 700 }}>
                {intelData.stageId} • {intelData.techniqueId}
              </span>
              <h3 style={{ fontSize: "1rem", fontWeight: 700, margin: 0 }}>
                {intelData.techniqueName}
              </h3>
            </div>
            <button
              className="btn btn-secondary"
              onClick={() => loadStageIntel(selectedStageId)}
              disabled={isLoading}
              style={{ fontSize: "0.72rem", padding: "0.3rem 0.6rem", display: "flex", alignItems: "center", gap: "0.35rem" }}
            >
              <RefreshCw size={12} className={isLoading ? "animate-spin" : ""} /> Refresh Intel
            </button>
          </div>

          <p style={{ fontSize: "0.85rem", color: "var(--text-main)", lineHeight: 1.55, margin: 0 }}>
            {intelData.summary}
          </p>

          {intelData.adversaries.length > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", fontSize: "0.75rem" }}>
              <span style={{ color: "var(--text-dim)", fontWeight: 600 }}>Known Adversary Groups:</span>
              {intelData.adversaries.map((adv) => (
                <span
                  key={adv}
                  className="badge"
                  style={{ background: "rgba(239, 68, 68, 0.08)", color: "#fca5a5", border: "1px solid rgba(239, 68, 68, 0.2)" }}
                >
                  {adv}
                </span>
              ))}
            </div>
          )}

          {intelData.sources.length > 0 && (
            <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "0.6rem", fontSize: "0.75rem" }}>
              <div style={{ color: "var(--text-dim)", fontWeight: 600, marginBottom: "0.3rem" }}>
                External References:
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                {intelData.sources.map((src, i) => (
                  <a
                    key={i}
                    href={src.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: "var(--cyan-400)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "0.3rem" }}
                  >
                    <ExternalLink size={11} /> {src.title}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Honest integration status */}
      <div
        className="glass-panel"
        style={{
          padding: "0.85rem 1.15rem",
          display: "flex",
          alignItems: "flex-start",
          gap: "0.65rem",
          background: "rgba(245, 158, 11, 0.06)",
          border: "1px solid rgba(245, 158, 11, 0.2)",
          fontSize: "0.78rem",
          color: "var(--text-muted)",
        }}
      >
        <Info size={16} style={{ color: "var(--status-partial)", flexShrink: 0, marginTop: "0.1rem" }} />
        <div>
          <strong style={{ color: "var(--text-main)" }}>Live Tavily threat intelligence</strong> enables real-time search
          for emerging adversary procedures. Retrieved threat reports are shown as external context with source citations,
          never used as simulated evidence, and never alter deterministic detection scores.
        </div>
      </div>

      {/* Framework Reference Cards */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.75rem" }}>
          <BookOpen size={16} style={{ color: "var(--cyan-500)" }} />
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-main)" }}>
            Framework References by Stage
          </h3>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem" }}>
          {TECHNIQUE_REFERENCES.map((ref) => {
            const isSelected = selectedStageId === ref.stageId;
            return (
              <div
                key={`${ref.stageId}-${ref.techniqueId}`}
                className="glass-panel"
                onClick={() => setSelectedStageId(ref.stageId)}
                style={{
                  padding: "0.9rem 1.25rem",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "1rem",
                  cursor: "pointer",
                  border: isSelected ? "1.5px solid var(--cyan-500)" : "1px solid var(--border-subtle)",
                  background: isSelected ? "rgba(6, 182, 212, 0.08)" : undefined,
                  transition: "all 0.15s ease",
                }}
              >
                <div
                  style={{
                    minWidth: "110px",
                    padding: "0.35rem 0.6rem",
                    borderRadius: "var(--radius-sm)",
                    background: isSelected ? "rgba(56, 189, 248, 0.15)" : "rgba(56, 189, 248, 0.08)",
                    border: "1px solid rgba(56, 189, 248, 0.25)",
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

                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h4 style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--text-main)", margin: 0 }}>
                      {ref.name}
                    </h4>
                    {isSelected && (
                      <span className="badge" style={{ background: "rgba(6, 182, 212, 0.15)", color: "var(--cyan-400)", fontSize: "0.65rem" }}>
                        Selected Stage
                      </span>
                    )}
                  </div>
                  <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.5, marginTop: "0.25rem", marginBottom: 0 }}>
                    {ref.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <p style={{ fontSize: "0.72rem", color: "var(--text-dim)", lineHeight: 1.5 }}>
        Technique mappings reference the public MITRE ATT&amp;CK knowledge base for cloud identity and access management.
      </p>
    </div>
  );
};
