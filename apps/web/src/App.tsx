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
import { DetectionOpsView } from "./features/detection-ops/DetectionOpsView";

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
  fetchScenario,
  fetchScenarios,
  fetchProposals,
  type RunGraphStage,
} from "./lib/api";

const DEMO_RUN_ID = "run_demo_seed_0001";
const DEFAULT_SEED = 1337;

export default function App() {
  const [activeTab, setActiveTab] = useState<NavTab>("graph");
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [runId, setRunId] = useState<string | null>(null);
  const [seed, setSeed] = useState<number>(DEFAULT_SEED);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const [aiConfigured, setAiConfigured] = useState<boolean>(false);
  const [focusStageId, setFocusStageId] = useState<string | null>(null);

  // All run data starts empty. It is only populated from the API.
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [stages, setStages] = useState<RunGraphStage[]>([]);
  const [stageResults, setStageResults] = useState<StageResult[]>([]);
  const [coverage, setCoverage] = useState<CoverageResult | null>(null);
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [rules, setRules] = useState<DetectionRule[]>([]);
  const [proposals, setProposals] = useState<RuleProposal[]>([]);
  const [report, setReport] = useState<RunReport | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const clearRunData = useCallback(() => {
    setRunId(null);
    setStages([]);
    setStageResults([]);
    setCoverage(null);
    setEvents([]);
    setRules([]);
    setProposals([]);
    setReport(null);
  }, []);

  // All-or-nothing load so a partial API failure cannot leave hybrid state.
  const loadRunData = useCallback(async (currentRunId: string) => {
    const [graphRes, covRes, teleRes, rulesRes, propsRes, repRes] = await Promise.all([
      fetchRunGraph(currentRunId),
      fetchRunCoverage(currentRunId),
      fetchRunTelemetry(currentRunId),
      fetchRunRules(currentRunId),
      fetchProposals(currentRunId),
      fetchRunReport(currentRunId),
    ]);

    setStages(graphRes.stages);
    setCoverage(covRes);
    setStageResults(covRes.stages);
    setEvents(teleRes.events);
    setRules(rulesRes.rules);
    setProposals(propsRes.proposals);
    setReport(repRes);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      setIsLoading(true);
      try {
        const health = await fetchHealth();
        if (cancelled) return;
        setIsBackendConnected(health.status === "ok");
        setAiConfigured(health.ai_configured);
      } catch {
        if (cancelled) return;
        setIsBackendConnected(false);
        setErrorMsg("Backend unreachable. Start the API on port 8000, then reload.");
        setIsLoading(false);
        return;
      }

      try {
        const summaries = await fetchScenarios();
        if (!cancelled && summaries.length > 0) {
          const fullScenario = await fetchScenario(summaries[0].id);
          if (!cancelled) setScenario(fullScenario);
        }
      } catch {
        if (!cancelled) setErrorMsg("Could not load scenario metadata from the API.");
      }

      try {
        await loadRunData(DEMO_RUN_ID);
        if (!cancelled) {
          setRunId(DEMO_RUN_ID);
          setNotice(null);
        }
      } catch {
        if (!cancelled) {
          clearRunData();
          setNotice(
            "No seeded demo run loaded. Click Run Scenario Simulation to generate real telemetry."
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void init();
    return () => {
      cancelled = true;
    };
  }, [clearRunData, loadRunData]);

  const handleRunSimulation = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setErrorMsg(null);
    setNotice(null);
    try {
      const newRun = await createRun(
        scenario?.id ?? "cloud-identity-compromise-v1",
        seed
      );
      await loadRunData(newRun.id);
      setRunId(newRun.id);
      setActiveTab("graph");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Run execution failed";
      setErrorMsg(msg);
    } finally {
      setIsRunning(false);
    }
  };

  const handleReset = async () => {
    setSeed(DEFAULT_SEED);
    setErrorMsg(null);
    try {
      await loadRunData(DEMO_RUN_ID);
      setRunId(DEMO_RUN_ID);
      setNotice(null);
    } catch {
      clearRunData();
      setNotice(
        "No seeded demo run available. Click Run Scenario Simulation to generate real telemetry."
      );
    }
  };

  const handleSelectStageForImprovement = (stageId: string) => {
    setFocusStageId(stageId);
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

    if (runId) {
      fetchRunReport(runId)
        .then((nextReport) => setReport(nextReport))
        .catch(() =>
          setErrorMsg(
            "The proposal was validated, but the report could not be refreshed. Re-run the report fetch."
          )
        );
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <DisclaimerBanner />

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
        scenarioName={scenario?.name ?? null}
      />

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
            gap: "1rem",
          }}
        >
          <span>{errorMsg}</span>
          <button
            onClick={() => setErrorMsg(null)}
            style={{ background: "none", border: "none", color: "#fca5a5", cursor: "pointer" }}
          >
            Dismiss
          </button>
        </div>
      )}

      {notice && !errorMsg && (
        <div
          style={{
            background: "rgba(245, 158, 11, 0.12)",
            borderBottom: "1px solid rgba(245, 158, 11, 0.25)",
            color: "var(--status-partial)",
            padding: "0.5rem 1.75rem",
            fontSize: "0.8rem",
            display: "flex",
            justifyContent: "space-between",
            gap: "1rem",
          }}
        >
          <span>{notice}</span>
          <button
            onClick={() => setNotice(null)}
            style={{ background: "none", border: "none", color: "var(--status-partial)", cursor: "pointer" }}
          >
            Dismiss
          </button>
        </div>
      )}

      <main style={{ flex: 1, padding: "1.75rem", maxWidth: "1600px", margin: "0 auto", width: "100%" }}>
        {isLoading && (
          <div
            className="glass-panel"
            style={{ padding: "0.85rem 1.25rem", marginBottom: "1.5rem", fontSize: "0.82rem", color: "var(--text-muted)" }}
          >
            Loading scenario and seeded demo run from the API...
          </div>
        )}

        {activeTab === "graph" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
            <ScenarioHub scenario={scenario} onRunSimulation={handleRunSimulation} isRunning={isRunning} />
            <AttackGraph
              stages={stages}
              stageResults={stageResults}
              events={events}
              runId={runId}
              aiConfigured={aiConfigured}
              onSelectStageForImprovement={handleSelectStageForImprovement}
            />
          </div>
        )}

        {activeTab === "telemetry" && <TelemetryExplorer events={events} />}

        {activeTab === "coverage" && (
          <CoverageDashboard
            coverage={coverage}
            scenario={scenario}
            onNavigateToStage={() => setActiveTab("graph")}
          />
        )}

        {activeTab === "rules" && (
          <RuleImprovementWorkspace
            runId={runId}
            rules={rules}
            stageResults={stageResults}
            events={events}
            proposals={proposals}
            focusStageId={focusStageId}
            aiConfigured={aiConfigured}
            onProposalValidated={handleProposalValidated}
          />
        )}

        {activeTab === "ops" && <DetectionOpsView runId={runId} />}

        {activeTab === "report" && (
          <ReportView report={report} onReportUpdated={setReport} aiConfigured={aiConfigured} />
        )}

        {activeTab === "intel" && <ThreatIntelView />}
      </main>

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
          GhostRange • Security Control Validation Platform •{" "}
          {aiConfigured
            ? "AI analysis enabled via NVIDIA Nemotron on Nebius Token Factory"
            : "Deterministic mode — AI analysis unavailable"}
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
