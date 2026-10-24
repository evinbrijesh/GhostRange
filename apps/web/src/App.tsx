import { useState, useEffect, useCallback } from "react";
import { DisclaimerBanner } from "./components/DisclaimerBanner";
import { Header, type NavTab } from "./components/Header";
import { AttackGraph } from "./features/attack-graph/AttackGraph";
import { TelemetryExplorer } from "./features/telemetry/TelemetryExplorer";
import { CoverageDashboard } from "./features/coverage/CoverageDashboard";
import { RuleImprovementWorkspace } from "./features/improvements/RuleImprovementWorkspace";
import { ReportView } from "./features/reports/ReportView";
import { ThreatIntelView } from "./features/threat-intel/ThreatIntelView";
import { ScenarioHub } from "./features/scenarios/ScenarioHub";

import type {
  CoverageResult,
  DetectionRule,
  RuleProposal,
  RunReport,
  Scenario,
  StageResult,
  TelemetryEvent,
} from "../../../packages/schemas/ts/contracts";
import {
  createRun,
  fetchHealth,
  fetchRunCoverage,
  fetchRunGraph,
  fetchRunReport,
  fetchRunRules,
  fetchRunTelemetry,
  fetchScenarios,
  fetchProposals,
  type RunGraphStage,
} from "./lib/api";
import {
  DEFAULT_SCENARIO,
  DEFAULT_STAGES,
  DEFAULT_COVERAGE,
  DEFAULT_EVENTS,
  DEFAULT_RULES,
  DEFAULT_PROPOSALS,
  DEFAULT_REPORT,
} from "./lib/defaultData";

const DEMO_RUN_ID = "run_demo_seed_0001";
const DEFAULT_SEED = 1337;

export default function App() {
  const [activeTab, setActiveTab] = useState<NavTab>("graph");
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [runId, setRunId] = useState<string | null>(DEMO_RUN_ID);
  const [seed, setSeed] = useState<number>(DEFAULT_SEED);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const [aiConfigured, setAiConfigured] = useState<boolean>(false);

  // Core Data State - preloaded with valid baseline state
  const [scenario, setScenario] = useState<Scenario | null>(DEFAULT_SCENARIO);
  const [stages, setStages] = useState<RunGraphStage[]>(DEFAULT_STAGES);
  const [stageResults, setStageResults] = useState<StageResult[]>(DEFAULT_COVERAGE.stages);
  const [coverage, setCoverage] = useState<CoverageResult | null>(DEFAULT_COVERAGE);
  const [events, setEvents] = useState<TelemetryEvent[]>(DEFAULT_EVENTS);
  const [rules, setRules] = useState<DetectionRule[]>(DEFAULT_RULES);
  const [proposals, setProposals] = useState<RuleProposal[]>(DEFAULT_PROPOSALS);
  const [report, setReport] = useState<RunReport | null>(DEFAULT_REPORT);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load Run Data
  const loadRunData = useCallback(async (currentRunId: string) => {
    try {
      const [graphRes, covRes, teleRes, rulesRes, propsRes, repRes] = await Promise.all([
        fetchRunGraph(currentRunId).catch(() => null),
        fetchRunCoverage(currentRunId).catch(() => null),
        fetchRunTelemetry(currentRunId).catch(() => null),
        fetchRunRules(currentRunId).catch(() => null),
        fetchProposals(currentRunId).catch(() => null),
        fetchRunReport(currentRunId).catch(() => null),
      ]);

      if (graphRes) setStages(graphRes.stages);
      if (covRes) {
        setCoverage(covRes);
        setStageResults(covRes.stages);
      }
      if (teleRes) setEvents(teleRes.events);
      if (rulesRes) setRules(rulesRes.rules);
      if (propsRes) setProposals(propsRes.proposals);
      if (repRes) setReport(repRes);
      setErrorMsg(null);
    } catch (err: unknown) {
      console.warn("Could not load complete run data from API:", err);
    }
  }, []);

  // Initial Load & Health Check
  useEffect(() => {
    async function init() {
      try {
        const health = await fetchHealth();
        setIsBackendConnected(health.status === "ok");
        setAiConfigured(health.ai_configured);

        const scenarios = await fetchScenarios();
        if (scenarios.length > 0) {
          setScenario(scenarios[0]);
        }

        await loadRunData(DEMO_RUN_ID);
      } catch (err) {
        console.warn("Backend not running on :8000; falling back to demo state", err);
        setIsBackendConnected(false);
        // Load offline demo data
        await loadRunData(DEMO_RUN_ID);
      }
    }
    init();
  }, [loadRunData]);

  // Execute Simulation Run
  const handleRunSimulation = async () => {
    setIsRunning(true);
    setErrorMsg(null);
    try {
      const newRun = await createRun("cloud-identity-compromise-v1", seed);
      setRunId(newRun.id);
      await loadRunData(newRun.id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Run execution failed";
      console.error("Simulation error:", err);
      setErrorMsg(msg);
      // Fallback reload
      await loadRunData(DEMO_RUN_ID);
    } finally {
      setIsRunning(false);
    }
  };

  // Reset Run
  const handleReset = async () => {
    setSeed(DEFAULT_SEED);
    setRunId(DEMO_RUN_ID);
    await loadRunData(DEMO_RUN_ID);
  };

  const handleSelectStageForImprovement = (_stageId: string) => {
    setActiveTab("rules");
  };

  const handleProposalValidated = (updatedProposal: RuleProposal) => {
    setProposals((prev) => {
      const exists = prev.some((p) => p.id === updatedProposal.id);
      if (exists) {
        return prev.map((p) => (p.id === updatedProposal.id ? updatedProposal : p));
      }
      return [...prev, updatedProposal];
    });

    // Refresh report with new improvement
    if (runId) {
      fetchRunReport(runId)
        .then((r) => setReport(r))
        .catch(() => {});
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Top Safety Disclaimer */}
      <DisclaimerBanner />

      {/* Main App Navigation & Controls Header */}
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        isRunning={isRunning}
        onRunSimulation={handleRunSimulation}
        onReset={handleReset}
        runId={runId}
        seed={seed}
        onSeedChange={setSeed}
        isBackendConnected={isBackendConnected}
        aiConfigured={aiConfigured}
      />

      {/* Error alert if any */}
      {errorMsg && (
        <div
          style={{
            background: "rgba(239, 68, 68, 0.15)",
            borderBottom: "1px solid rgba(239, 68, 68, 0.3)",
            color: "#fca5a5",
            padding: "0.5rem 1.75rem",
            fontSize: "0.8rem",
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <span>Error: {errorMsg}</span>
          <button
            onClick={() => setErrorMsg(null)}
            style={{ background: "none", border: "none", color: "#fca5a5", cursor: "pointer" }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main View Area */}
      <main style={{ flex: 1, padding: "1.75rem", maxWidth: "1600px", margin: "0 auto", width: "100%" }}>
        {activeTab === "graph" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
            <ScenarioHub scenario={scenario} onRunSimulation={handleRunSimulation} isRunning={isRunning} />
            <AttackGraph
              stages={stages}
              stageResults={stageResults}
              events={events}
              runId={runId}
              onSelectStageForImprovement={handleSelectStageForImprovement}
            />
          </div>
        )}

        {activeTab === "telemetry" && <TelemetryExplorer events={events} />}

        {activeTab === "coverage" && (
          <CoverageDashboard coverage={coverage} onNavigateToStage={() => setActiveTab("graph")} />
        )}

        {activeTab === "rules" && (
          <RuleImprovementWorkspace
            runId={runId}
            rules={rules}
            proposals={proposals}
            onProposalValidated={handleProposalValidated}
          />
        )}

        {activeTab === "report" && <ReportView report={report} />}

        {activeTab === "intel" && <ThreatIntelView />}
      </main>

      {/* Footer */}
      <footer
        style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "1rem 1.75rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: "0.75rem",
          color: "var(--text-dim)",
          background: "rgba(11, 15, 25, 0.9)",
        }}
      >
        <div>
          GhostRange • Security Control Validation Platform • Powered by NVIDIA Nemotron via Nebius Token Factory
        </div>
        <div style={{ display: "flex", gap: "1rem" }}>
          <span>Deterministic Rule Evaluator</span>
          <span>•</span>
          <span>Open-Source Defense (MIT)</span>
          <span>•</span>
          <span>Synthetic RFC 5737 Sandbox</span>
        </div>
      </footer>
    </div>
  );
}
