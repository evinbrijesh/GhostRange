import React, { useState, useMemo } from "react";
import {
  Search,
  Copy,
  Check,
  Code2,
  ShieldCheck,
  X,
} from "lucide-react";
import type { TelemetryEvent } from "../../../../../packages/schemas/ts/contracts";

interface TelemetryExplorerProps {
  events: TelemetryEvent[];
}

export const TelemetryExplorer: React.FC<TelemetryExplorerProps> = ({ events }) => {
  const [selectedStage, setSelectedStage] = useState<string>("all");
  const [selectedSource, setSelectedSource] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activeEvent, setActiveEvent] = useState<TelemetryEvent | null>(events[0] || null);
  const [copied, setCopied] = useState<boolean>(false);

  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      if (selectedStage !== "all" && e.stageId !== selectedStage) return false;
      if (selectedSource !== "all" && e.source !== selectedSource) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesAction = e.action.toLowerCase().includes(q);
        const matchesIdentity = e.identity.id.toLowerCase().includes(q);
        const matchesResource = e.resource.id.toLowerCase().includes(q);
        const matchesIp = e.srcIp.includes(q);
        const matchesId = e.id.toLowerCase().includes(q);
        if (!matchesAction && !matchesIdentity && !matchesResource && !matchesIp && !matchesId) {
          return false;
        }
      }
      return true;
    });
  }, [events, selectedStage, selectedSource, searchQuery]);

  const handleCopyJson = () => {
    if (!activeEvent) return;
    navigator.clipboard.writeText(JSON.stringify(activeEvent, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Filter and Search Bar */}
      <div
        className="glass-panel"
        style={{
          padding: "1rem 1.25rem",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flex: 1, minWidth: "300px" }}>
          {/* Search Box */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              background: "rgba(0, 0, 0, 0.35)",
              border: "1px solid var(--border-medium)",
              borderRadius: "var(--radius-md)",
              padding: "0.45rem 0.75rem",
              flex: 1,
              maxWidth: "400px",
            }}
          >
            <Search size={15} style={{ color: "var(--text-dim)" }} />
            <input
              type="text"
              placeholder="Filter by action, actor, resource, or IP..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                background: "transparent",
                border: "none",
                outline: "none",
                color: "var(--text-main)",
                fontSize: "0.82rem",
                width: "100%",
                fontFamily: "var(--font-sans)",
              }}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                style={{ background: "none", border: "none", color: "var(--text-dim)", cursor: "pointer" }}
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Stage Dropdown */}
          <select
            value={selectedStage}
            onChange={(e) => setSelectedStage(e.target.value)}
            style={{
              background: "rgba(17, 24, 39, 0.8)",
              border: "1px solid var(--border-medium)",
              color: "var(--text-main)",
              borderRadius: "var(--radius-sm)",
              padding: "0.45rem 0.75rem",
              fontSize: "0.82rem",
              cursor: "pointer",
            }}
          >
            <option value="all">All Stages (S1–S7)</option>
            <option value="S1">S1 Initial Access</option>
            <option value="S2">S2 MFA Manipulation</option>
            <option value="S3">S3 Discovery</option>
            <option value="S4">S4 Privilege Escalation</option>
            <option value="S5">S5 Persistence</option>
            <option value="S6">S6 Sensitive Access</option>
            <option value="S7">S7 Data Staging</option>
          </select>

          {/* Source Dropdown */}
          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            style={{
              background: "rgba(17, 24, 39, 0.8)",
              border: "1px solid var(--border-medium)",
              color: "var(--text-main)",
              borderRadius: "var(--radius-sm)",
              padding: "0.45rem 0.75rem",
              fontSize: "0.82rem",
              cursor: "pointer",
            }}
          >
            <option value="all">All Sources</option>
            <option value="auth">auth</option>
            <option value="iam">iam</option>
            <option value="api">api</option>
            <option value="storage">storage</option>
            <option value="network">network</option>
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", fontSize: "0.78rem" }}>
          <span style={{ color: "var(--text-muted)" }}>
            Showing <strong>{filteredEvents.length}</strong> of <strong>{events.length}</strong> events
          </span>
          <span className="badge badge-synthetic">
            <ShieldCheck size={11} /> 100% Synthetic Telemetry
          </span>
        </div>
      </div>

      {/* Main Grid: Telemetry List + JSON Inspection Drawer */}
      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: "1.25rem", minHeight: "550px" }}>
        {/* Events Table Container */}
        <div
          className="glass-panel"
          style={{
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              padding: "0.75rem 1rem",
              borderBottom: "1px solid var(--border-subtle)",
              background: "rgba(0, 0, 0, 0.2)",
              display: "grid",
              gridTemplateColumns: "80px 70px 70px 1.4fr 1.2fr 100px",
              gap: "0.5rem",
              fontSize: "0.72rem",
              fontWeight: 700,
              color: "var(--text-dim)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>Event ID</span>
            <span>Stage</span>
            <span>Source</span>
            <span>Action</span>
            <span>Identity</span>
            <span>Source IP</span>
          </div>

          <div style={{ overflowY: "auto", maxHeight: "560px", flex: 1 }}>
            {filteredEvents.map((evt) => {
              const isSelected = activeEvent?.id === evt.id;
              return (
                <div
                  key={evt.id}
                  onClick={() => setActiveEvent(evt)}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "80px 70px 70px 1.4fr 1.2fr 100px",
                    gap: "0.5rem",
                    padding: "0.65rem 1rem",
                    fontSize: "0.78rem",
                    alignItems: "center",
                    cursor: "pointer",
                    borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                    background: isSelected ? "var(--bg-elevated)" : "transparent",
                    transition: "background 0.15s ease",
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) e.currentTarget.style.background = "rgba(255, 255, 255, 0.03)";
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) e.currentTarget.style.background = "transparent";
                  }}
                >
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--cyan-500)", fontWeight: 600 }}>
                    {evt.id}
                  </span>
                  <span>
                    <span className="badge" style={{ fontSize: "0.65rem", padding: "1px 6px" }}>
                      {evt.stageId}
                    </span>
                  </span>
                  <span style={{ color: "#a5b4fc", textTransform: "uppercase", fontSize: "0.7rem", fontWeight: 600 }}>
                    {evt.source}
                  </span>
                  <span
                    style={{
                      fontWeight: 600,
                      color: "var(--text-main)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {evt.action}
                  </span>
                  <span
                    style={{
                      color: "var(--text-muted)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {evt.identity.id}
                  </span>
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-dim)", fontSize: "0.72rem" }}>
                    {evt.srcIp}
                  </span>
                </div>
              );
            })}

            {filteredEvents.length === 0 && (
              <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-dim)" }}>
                No synthetic telemetry events matched your search filters.
              </div>
            )}
          </div>
        </div>

        {/* JSON Inspector Card */}
        <div
          className="glass-panel"
          style={{
            padding: "1.25rem",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {activeEvent ? (
            <>
              {/* Top Details & Copy */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "0.85rem",
                  borderBottom: "1px solid var(--border-subtle)",
                  paddingBottom: "0.75rem",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <Code2 size={16} style={{ color: "var(--cyan-500)" }} />
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: "0.95rem" }}>
                      event:{activeEvent.id}
                    </span>
                    <span className="badge badge-synthetic">SYNTHETIC</span>
                  </div>
                  <p style={{ fontSize: "0.72rem", color: "var(--text-dim)", marginTop: "0.2rem" }}>
                    Stage {activeEvent.stageId} • {new Date(activeEvent.timestamp).toISOString()}
                  </p>
                </div>

                <button
                  className="btn btn-secondary"
                  onClick={handleCopyJson}
                  style={{ fontSize: "0.75rem", padding: "0.35rem 0.75rem" }}
                >
                  {copied ? (
                    <>
                      <Check size={13} style={{ color: "var(--status-detected)" }} /> Copied
                    </>
                  ) : (
                    <>
                      <Copy size={13} /> Copy JSON
                    </>
                  )}
                </button>
              </div>

              {/* Formatted Code Block */}
              <pre
                style={{
                  background: "rgba(0, 0, 0, 0.45)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  borderRadius: "var(--radius-md)",
                  padding: "1rem",
                  fontSize: "0.75rem",
                  lineHeight: 1.5,
                  overflowY: "auto",
                  color: "#e2e8f0",
                  flex: 1,
                  fontFamily: "var(--font-mono)",
                }}
              >
                <code>{JSON.stringify(activeEvent, null, 2)}</code>
              </pre>

              {/* Key Attributes Pills */}
              <div
                style={{
                  marginTop: "0.85rem",
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "0.5rem",
                  fontSize: "0.72rem",
                }}
              >
                <span style={{ color: "var(--text-dim)" }}>Attributes:</span>
                {Object.entries(activeEvent.attributes || {}).map(([k, v]) => (
                  <span
                    key={k}
                    style={{
                      background: "rgba(255, 255, 255, 0.05)",
                      padding: "2px 6px",
                      borderRadius: "4px",
                      border: "1px solid var(--border-subtle)",
                    }}
                  >
                    <strong>{k}</strong>: {String(v)}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                color: "var(--text-dim)",
              }}
            >
              Select an event to view full JSON payload
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
