import React from "react";
import { ShieldCheck, Info } from "lucide-react";

export const DisclaimerBanner: React.FC = () => {
  return (
    <aside aria-label="Simulation Safety Disclaimer" className="banner-disclaimer">
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <ShieldCheck size={14} style={{ color: "var(--status-detected)" }} />
        <span>
          <strong>GHOSTRANGE ENVIRONMENT:</strong> Digital twin simulation running inside a safe, synthetic sandbox. Zero real infrastructure or live credentials are ever contacted.
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <span className="badge badge-synthetic">SYNTHETIC TELEMETRY ONLY</span>
        <span style={{ display: "flex", alignItems: "center", gap: "0.25rem", color: "var(--text-dim)" }}>
          <Info size={12} /> RFC 5737 Reserved IPs
        </span>
      </div>
    </aside>
  );
};
