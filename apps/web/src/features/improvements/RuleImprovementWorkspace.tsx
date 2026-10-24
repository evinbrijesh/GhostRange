import React, { useState } from "react";
import {
  Sparkles,
  Play,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import type { DetectionRule, RuleProposal } from "../../../../../packages/schemas/ts/contracts";
import { createProposal, validateProposal } from "../../lib/api";

const DEFAULT_PROPOSED_YAML = `title: Detect MFA Device Deletion Following Unusual Login
id: gr-rule-s2-mfa-manipulation-improved
stage: S2
logsource:
  product: cloud
  service: iam
selection:
  action: DeleteVirtualMFADevice
condition: selection
level: critical`;

const ORIGINAL_YAML_S2 = `title: Detect Unusual Console Login
id: gr-rule-s2-mfa-manipulation
stage: S2
logsource:
  product: cloud
  service: auth
selection:
  action: ConsoleLogin
  mfa_used: false
condition: selection
level: medium`;

interface RuleImprovementWorkspaceProps {
  runId: string | null;
  rules: DetectionRule[];
  proposals: RuleProposal[];
  onProposalValidated?: (updatedProposal: RuleProposal) => void;
}

export const RuleImprovementWorkspace: React.FC<RuleImprovementWorkspaceProps> = ({
  runId,
  rules,
  proposals,
  onProposalValidated,
}) => {
  const [selectedRuleId, setSelectedRuleId] = useState<string>("gr-rule-s2-mfa-manipulation");
  const [proposedYaml, setProposedYaml] = useState<string>(DEFAULT_PROPOSED_YAML);
  const [rationale, setRationale] = useState<string>(
    "Original rule only checked if ConsoleLogin had mfa_used: false, but the adversary possessed valid credentials and logged in normally before modifying MFA settings. The improved rule monitors the actual high-risk DeleteVirtualMFADevice API call."
  );
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [activeProposal, setActiveProposal] = useState<RuleProposal | null>(
    proposals.find((p) => p.originalRuleId === selectedRuleId) || null
  );

  const selectedRule = rules.find((r) => r.id === selectedRuleId);

  const handleValidate = async () => {
    if (!runId) return;
    setIsValidating(true);
    try {
      // 1. Create proposal if none exists
      let proposal = activeProposal;
      if (!proposal) {
        proposal = await createProposal(runId, {
          originalRuleId: selectedRuleId,
          proposedSource: proposedYaml,
          rationale,
        });
        setActiveProposal(proposal);
      }

      // 2. Validate proposal through deterministic evaluator
      const validated = await validateProposal(runId, proposal.id);
      setActiveProposal(validated);
      if (onProposalValidated) {
        onProposalValidated(validated);
      }
    } catch (err) {
      console.error("Validation error:", err);
    } finally {
      setIsValidating(false);
    }
  };

  const handleResetProposal = () => {
    setActiveProposal(null);
  };

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
          background: "linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(17, 24, 39, 0.8))",
          border: "1px solid rgba(139, 92, 246, 0.25)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span className="badge badge-ai">
              <Sparkles size={12} /> Closed-Loop Remediation
            </span>
            <span className="badge" style={{ background: "rgba(16, 185, 129, 0.1)", color: "var(--status-detected)" }}>
              Deterministic Validation
            </span>
          </div>
          <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginTop: "0.4rem" }}>
            Rule Improvement Workspace
          </h2>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
            Review Nemotron-proposed Sigma detection rule updates, test them deterministically against simulated telemetry, and verify coverage gains.
          </p>
        </div>

        {/* Validation Result Box */}
        {activeProposal && activeProposal.validation && activeProposal.validation.improvesCoverage !== null && (
          <div
            style={{
              background: activeProposal.validation.improvesCoverage ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
              border: `1.5px solid ${activeProposal.validation.improvesCoverage ? "var(--status-detected)" : "var(--status-missed)"}`,
              borderRadius: "var(--radius-md)",
              padding: "0.75rem 1.25rem",
              textAlign: "right",
            }}
          >
            <div style={{ fontSize: "0.72rem", color: "var(--text-dim)", textTransform: "uppercase", fontWeight: 700 }}>
              Evaluator Verified
            </div>
            <div style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--status-detected)" }}>
              {activeProposal.validation.coverageBefore}% ➔ {activeProposal.validation.coverageAfter}%
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-main)" }}>
              +{(Number(activeProposal.validation.coverageAfter) - Number(activeProposal.validation.coverageBefore)).toFixed(1)}% Coverage Gain
            </div>
          </div>
        )}
      </div>

      {/* Workspace Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        {/* Left Column: Original Rule */}
        <div className="glass-panel" style={{ padding: "1.25rem", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <div>
              <span className="badge badge-missed" style={{ fontSize: "0.7rem" }}>
                Original Rule (Blind Spot)
              </span>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginTop: "0.25rem" }}>
                {selectedRule?.title || "Detect Unusual Console Login"}
              </h3>
            </div>
            <select
              value={selectedRuleId}
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
              }}
            >
              {rules.length > 0 ? (
                rules.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.id} ({r.stageId})
                  </option>
                ))
              ) : (
                <option value="gr-rule-s2-mfa-manipulation">gr-rule-s2-mfa-manipulation</option>
              )}
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
              flex: 1,
              fontFamily: "var(--font-mono)",
            }}
          >
            <code>{selectedRule?.source || ORIGINAL_YAML_S2}</code>
          </pre>

          <div
            style={{
              marginTop: "0.85rem",
              padding: "0.65rem 0.85rem",
              background: "rgba(239, 68, 68, 0.08)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
            }}
          >
            <strong>Evaluation Failure:</strong> Telemetry showed <code>DeleteVirtualMFADevice</code>, which was never captured because the rule only queried <code>ConsoleLogin</code> with <code>mfa_used: false</code>.
          </div>
        </div>

        {/* Right Column: Proposed Rule */}
        <div className="glass-panel" style={{ padding: "1.25rem", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <div>
              <span className="badge badge-ai" style={{ fontSize: "0.7rem" }}>
                <Sparkles size={11} /> Nemotron Proposed Rule
              </span>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginTop: "0.25rem" }}>
                Detect MFA Device Deletion Following Unusual Login
              </h3>
            </div>
            <span className="badge badge-detected" style={{ fontSize: "0.7rem" }}>
              Sigma Valid
            </span>
          </div>

          <textarea
            value={proposedYaml}
            onChange={(e) => setProposedYaml(e.target.value)}
            style={{
              background: "rgba(0, 0, 0, 0.5)",
              border: "1px solid rgba(139, 92, 246, 0.35)",
              borderRadius: "var(--radius-md)",
              padding: "1rem",
              fontSize: "0.78rem",
              color: "#a7f3d0",
              lineHeight: 1.5,
              flex: 1,
              fontFamily: "var(--font-mono)",
              outline: "none",
              resize: "none",
              minHeight: "220px",
            }}
          />

          <div
            style={{
              marginTop: "0.85rem",
              padding: "0.65rem 0.85rem",
              background: "rgba(139, 92, 246, 0.08)",
              border: "1px solid rgba(139, 92, 246, 0.2)",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
            }}
          >
            <label style={{ display: "block", fontWeight: 600, color: "#c084fc", marginBottom: "0.25rem" }}>
              Nemotron Rationale:
            </label>
            <input
              type="text"
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              style={{
                width: "100%",
                background: "rgba(0, 0, 0, 0.3)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                padding: "4px 8px",
                color: "var(--text-main)",
                fontSize: "0.75rem",
              }}
            />
          </div>
        </div>
      </div>

      {/* Bottom Action Footer */}
      <div
        className="glass-panel"
        style={{
          padding: "1rem 1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.78rem", color: "var(--text-dim)" }}>
          <ShieldCheck size={16} style={{ color: "var(--status-detected)" }} />
          <span>Original production rules remain untouched. Proposals run in sandbox evaluation only.</span>
        </div>

        <div style={{ display: "flex", gap: "0.75rem" }}>
          {activeProposal && (
            <button className="btn btn-secondary" onClick={handleResetProposal} style={{ fontSize: "0.82rem" }}>
              <RotateCcw size={14} /> Clear Proposal
            </button>
          )}

          <button
            id="validate-proposal-button"
            className="btn btn-primary"
            onClick={handleValidate}
            disabled={isValidating || !runId}
            style={{ minWidth: "220px" }}
          >
            {isValidating ? (
              <>
                <span className="animate-spin">
                  <RotateCcw size={15} />
                </span>
                Evaluating Against Scenario...
              </>
            ) : (
              <>
                <Play size={15} fill="currentColor" />
                Validate Improvement (Local Engine)
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
