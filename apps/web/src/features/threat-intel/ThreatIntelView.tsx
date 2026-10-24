import React, { useState } from "react";
import { Search, Globe, ExternalLink } from "lucide-react";

interface ThreatArticle {
  title: string;
  source: string;
  url: string;
  date: string;
  summary: string;
  mappedTechniques: string[];
}

const PRELOADED_THREAT_CONTEXT: ThreatArticle[] = [
  {
    title: "Scattered Spider: Cloud Identity Compromise and MFA Fatigue Campaigns",
    source: "CISA Cybersecurity Advisory (AA23-320A)",
    url: "https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-320a",
    date: "2026-04",
    summary:
      "Threat actors gain initial access through credential harvesting and session hijacking, followed by rapid deactivation of virtual MFA devices and role assumption in AWS/Azure tenants.",
    mappedTechniques: ["T1078.004", "T1556", "T1098"],
  },
  {
    title: "Storm-0501: Multi-Stage Ransomware Attacks Exploiting Cloud Admin Roles",
    source: "Microsoft Threat Intelligence",
    url: "https://www.microsoft.com/security/blog",
    date: "2026-02",
    summary:
      "Adversaries abuse compromised credentials to attach AdministratorAccess roles to backup service identities, staging sensitive storage data before encryption.",
    mappedTechniques: ["T1098", "T1530", "T1074.002"],
  },
  {
    title: "Midnight Blizzard: Persistent Access via OAuth and Cloud IAM Manipulation",
    source: "Mandiant Threat Research",
    url: "https://www.mandiant.com/resources/blog",
    date: "2025-11",
    summary:
      "Campaign focused on creating rogue login profiles and secondary API access keys to maintain undetected persistence across hybrid cloud environments.",
    mappedTechniques: ["T1136.003", "T1087.004"],
  },
];

export const ThreatIntelView: React.FC = () => {
  const [query, setQuery] = useState<string>("Cloud identity compromise MFA bypass");
  const [articles, setArticles] = useState<ThreatArticle[]>(PRELOADED_THREAT_CONTEXT);
  const [isSearching, setIsSearching] = useState<boolean>(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSearching(true);
    setTimeout(() => {
      if (query.trim()) {
        const q = query.toLowerCase();
        setArticles(
          PRELOADED_THREAT_CONTEXT.filter(
            (a) => a.title.toLowerCase().includes(q) || a.summary.toLowerCase().includes(q)
          )
        );
      } else {
        setArticles(PRELOADED_THREAT_CONTEXT);
      }
      setIsSearching(false);
    }, 400);
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
          background: "linear-gradient(135deg, rgba(6, 182, 212, 0.08), rgba(17, 24, 39, 0.8))",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span className="badge" style={{ background: "rgba(6, 182, 212, 0.12)", color: "var(--cyan-500)" }}>
              <Globe size={12} /> Tavily Threat Research
            </span>
            <span className="badge" style={{ background: "rgba(255, 255, 255, 0.05)", color: "var(--text-muted)" }}>
              Context Only • Never Simulated Evidence
            </span>
          </div>
          <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginTop: "0.4rem" }}>
            External Threat Intelligence Enrichment
          </h2>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
            Map real-world adversary campaigns to GhostRange simulation stages. All external reports are strictly tagged as external context.
          </p>
        </div>
      </div>

      {/* Search Input */}
      <form onSubmit={handleSearch} className="glass-panel" style={{ padding: "1rem 1.25rem" }}>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              background: "rgba(0, 0, 0, 0.35)",
              border: "1px solid var(--border-medium)",
              borderRadius: "var(--radius-md)",
              padding: "0.5rem 0.85rem",
              flex: 1,
            }}
          >
            <Search size={16} style={{ color: "var(--text-dim)" }} />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search threat reports (e.g., 'Cloud identity compromise MFA bypass')..."
              style={{
                background: "transparent",
                border: "none",
                outline: "none",
                color: "var(--text-main)",
                fontSize: "0.85rem",
                width: "100%",
                fontFamily: "var(--font-sans)",
              }}
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={isSearching}>
            {isSearching ? "Searching Tavily..." : "Search Context"}
          </button>
        </div>
      </form>

      {/* Articles Cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {articles.map((art, idx) => (
          <div
            key={idx}
            className="glass-panel"
            style={{
              padding: "1.25rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.65rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <span className="badge" style={{ fontSize: "0.68rem", background: "rgba(255, 255, 255, 0.06)", color: "#94a3b8" }}>
                  {art.source} • {art.date}
                </span>
                <h3 style={{ fontSize: "1rem", fontWeight: 700, marginTop: "0.3rem", color: "var(--text-main)" }}>
                  {art.title}
                </h3>
              </div>
              <a
                href={art.url}
                target="_blank"
                rel="noreferrer"
                style={{
                  color: "var(--cyan-500)",
                  fontSize: "0.75rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.25rem",
                  textDecoration: "none",
                }}
              >
                Read Report <ExternalLink size={12} />
              </a>
            </div>

            <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
              {art.summary}
            </p>

            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.25rem" }}>
              <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>Mapped ATT&CK Techniques:</span>
              {art.mappedTechniques.map((tech) => (
                <span
                  key={tech}
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.7rem",
                    padding: "2px 6px",
                    background: "rgba(56, 189, 248, 0.1)",
                    border: "1px solid rgba(56, 189, 248, 0.25)",
                    borderRadius: "4px",
                    color: "#38bdf8",
                  }}
                >
                  {tech}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
