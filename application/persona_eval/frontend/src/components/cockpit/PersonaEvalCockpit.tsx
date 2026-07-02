/**
 * PersonaEvalCockpit: the PersonaEval chatbot surface (ports the PersonaEval
 * `app-redesign-v3.html` cockpit + liverun screens).
 *
 * Two flows off one shared state:
 *   - IDLE  (`data-view="cockpit"`) shows a centered "Configure a simulation" setup
 *     form: header + app-type switch, a compact Pipeline strip, then a 12-col
 *     grid (LEFT 8: application cards · run-configuration knobs · target persona;
 *     RIGHT 4: the read-only runtime panel · the glowing Run-eval CTA · a hint).
 *   - RUNNING/DONE (`data-view="liverun"`) shows the live-run layout: the stateful
 *     Pipeline strip, the Trajectory thread (persona/app bubbles with items +
 *     tool-plan fold), the right Inspector tabs (Evaluation / Persona / Prompts),
 *     and a bottom status bar.
 *
 * It owns all cross-component state (selected persona, run knobs, the run via
 * `usePersonaEval`, inspector tab, open tool-plan folds, focused turn) and the
 * keyboard shortcuts (R run · J/K move turns · 1/2/3 inspector tab · E expand
 * folds). Data is honest: real personas / goal-contexts / config / run shape
 * (real per-turn latency; no tokens or cost, which aren't tracked).
 */
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import { RunHeader } from "./RunHeader";
import { Trajectory } from "./Trajectory";
import { InspectorTabs, type InspectorTab } from "./InspectorTabs";
import { Scorecard } from "./Scorecard";
import { InstructionPanel } from "./InstructionPanel";
import { PersonaDrawer } from "./PersonaDrawer";
import { SurveyEvalCockpit } from "./SurveyEvalCockpit";
import { WebEvalCockpit } from "./WebEvalCockpit";
import { CuaEvalCockpit } from "./CuaEvalCockpit";
import { type PersonaEvalTaskType } from "./TaskTypeSwitch";
import { fmtDomain } from "../runsShared";
import { CockpitSetupShell } from "./setup/CockpitSetupShell";
import { PersonaSamplingRail } from "./setup/PersonaSamplingRail";
import { CockpitPipelineDiagram } from "./setup/CockpitPipelineDiagram";
import { TaskSelectionRail } from "./setup/TaskSelectionRail";
import { BatchTrialGrid } from "./setup/BatchTrialGrid";
import { CockpitLiveStage } from "./setup/CockpitLiveStage";
import { RunLaunchBar } from "./setup/RunLaunchBar";
import {
  batchProgressPct as computeBatchProgressPct,
  resolveRunLaunchPhase,
  useCockpitBatchJob,
} from "./setup/useCockpitBatchJob";
import {
  emptyPersonaDimensionFilters,
  type PersonaSamplingMode,
} from "./setup/personaSamplingTypes";
import { api, listGoalContexts, ApiError } from "@/lib/api";
import { useHarborCockpitRun, type HarborCockpitPhase } from "@/lib/useHarborCockpitRun";
import { useCockpitInstruction } from "@/lib/useCockpitInstruction";
import { mapChatbotDebriefToJobView, mapChatbotLiveToJobView, isRewardOnlyTrialFailure } from "@/lib/harborCockpitMappers";
import { type PersonaEvalRunPhase } from "@/lib/usePersonaEval";
import type {
  ApplicationId,
  ConfigOptionsResponse,
  ConfigOptionValue,
  Domain,
  GoalContext,
  GoalContextsResponse,
  PersonaEvalJobView,
  PersonaEvalPersona,
  ChatbotSidecarStatus,
} from "@/lib/types";
import { HARBOR_CHAT_TASKS, HARBOR_TASK_PATHS } from "@/lib/types";

/** Per-app display name + icon (presentational; the data layer is app-agnostic). */
const APP_NAME: Record<string, string> = {
  recai: "RecAI",
  finance_openbb: "OpenBB",
  medical_assistant: "Medical Assistant",
};

/** Map the job's coarse phase into a single "what's happening now" line. */
function liveStatusLine(
  job: PersonaEvalJobView | null,
  phase: HarborCockpitPhase,
  isRunning: boolean,
  harborPhase?: string | null,
): string | null {
  if (phase === "launching") return "Launching Harbor job…";
  if (!isRunning) return null;
  const raw = (harborPhase ?? job?.phase ?? "").toLowerCase();
  if (raw.includes("harbor")) return "Harbor is running the trial…";
  if (raw.includes("trial")) return "Waiting for trial artifacts…";
  if (raw.includes("persona") || raw.includes("user") || raw.includes("simulat")) return "The simulated user is typing…";
  if (raw.includes("chatbot") || raw.includes("application") || raw.includes("agent") || raw.includes("recai") || raw.includes("turn"))
    return "The app is thinking…";
  if (raw.includes("eval")) return "Scoring how it went…";
  if (job?.phase) return `${job.phase}…`;
  return "Running the PersonaEval…";
}

/** True when focus is in a text input / textarea / select / contenteditable. */
function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
}

/**
 * A frozen copy of the persona + run controls captured the moment a run reaches
 * `done`. The export is built from this (never the live controls), so changing
 * a knob after a run finishes cannot mislabel the completed transcript.
 */
interface ExportSnapshot {
  persona: { id: string; name: string; source: string } | null;
  config: {
    applicationId: ApplicationId;
    applicationContext: string;
    domain?: Domain;
    engine: string;
    personaModel: string;
    goalContextId: string | null;
    maxTurns: number;
  };
}

export interface PersonaEvalCockpitProps {
  /** Config metadata (knobs + defaults + environment) from the app. */
  options: ConfigOptionsResponse | null;
  /** Navigate to the Runs surface. */
  onOpenRuns: () => void;
  /** Open a Harbor batch job detail in the Runs sub-view. */
  onOpenHarborJob?: (jobName: string) => void;
  /** Open a Harbor trial debrief in the Runs sub-view. */
  onOpenHarborTrial?: (jobName: string, trialName: string) => void;
  /** Report the active run domain up (so the shared catalog drawer can match it). */
  onDomainChange?: (domain: Domain) => void;
  /** Report the honest footer context up (task type + active app/instrument/site). */
  onFooterContextChange?: (context: string) => void;
}

/** Keep inactive cockpits mounted (hidden) so setup + run state survives type switches. */
function CockpitPanel({ active, children }: { active: boolean; children: ReactNode }) {
  return (
    <div
      className={active ? "flex min-h-0 flex-1 flex-col overflow-hidden" : "hidden"}
      aria-hidden={!active}
    >
      {children}
    </div>
  );
}

export function PersonaEvalCockpit({
  options,
  onOpenRuns,
  onOpenHarborJob,
  onOpenHarborTrial,
  onDomainChange,
  onFooterContextChange,
}: PersonaEvalCockpitProps) {
  const [taskType, setTaskType] = useState<PersonaEvalTaskType>("chatbot");

    return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <CockpitPanel active={taskType === "chatbot"}>
        <ChatbotEvalCockpit
          options={options}
          onOpenRuns={onOpenRuns}
          onOpenHarborJob={onOpenHarborJob}
          onOpenHarborTrial={onOpenHarborTrial}
          onDomainChange={onDomainChange}
          onFooterContextChange={onFooterContextChange}
          taskType={taskType}
          onTaskTypeChange={setTaskType}
          isActive={taskType === "chatbot"}
        />
      </CockpitPanel>
      <CockpitPanel active={taskType === "survey"}>
      <SurveyEvalCockpit
        options={options}
        taskType={taskType}
        onTaskTypeChange={setTaskType}
        onFooterContextChange={onFooterContextChange}
        onOpenHarborJob={onOpenHarborJob}
        onOpenHarborTrial={onOpenHarborTrial}
          isActive={taskType === "survey"}
        />
      </CockpitPanel>
      <CockpitPanel active={taskType === "web"}>
      <WebEvalCockpit
        options={options}
        taskType={taskType}
        onTaskTypeChange={setTaskType}
        onFooterContextChange={onFooterContextChange}
        onOpenHarborJob={onOpenHarborJob}
        onOpenHarborTrial={onOpenHarborTrial}
          isActive={taskType === "web"}
        />
      </CockpitPanel>
      <CockpitPanel active={taskType === "cua"}>
        <CuaEvalCockpit
        options={options}
        taskType={taskType}
        onTaskTypeChange={setTaskType}
        onFooterContextChange={onFooterContextChange}
      onOpenHarborJob={onOpenHarborJob}
      onOpenHarborTrial={onOpenHarborTrial}
          isActive={taskType === "cua"}
    />
      </CockpitPanel>
    </div>
  );
}

interface ChatbotEvalCockpitProps extends PersonaEvalCockpitProps {
  taskType: PersonaEvalTaskType;
  onTaskTypeChange: (value: PersonaEvalTaskType) => void;
  isActive: boolean;
}

function ChatbotEvalCockpit({
  options,
  onOpenHarborJob,
  onDomainChange,
  onFooterContextChange,
  taskType,
  onTaskTypeChange,
  isActive,
}: ChatbotEvalCockpitProps) {
  const { run, job, phase, isRunning, error, timedOut, retry, reset, harborPhase, harborJobName, harborTrialName } =
    useHarborCockpitRun<PersonaEvalJobView>();

  // --- Selection + run knobs ---------------------------------------------
  const [persona, setPersona] = useState<PersonaEvalPersona | null>(null);
  const [applicationId, setApplicationId] = useState<ApplicationId>(
    (options?.defaults.applicationId as ApplicationId | undefined) ?? "recai",
  );
  const [domain, setDomain] = useState<Domain>((options?.defaults.domain as Domain) ?? "movie");
  const [engine, setEngine] = useState<string>(options?.defaults.engine ?? "gpt-4o-mini");
  const [personaModel, setPersonaModel] = useState<string>(
    options?.environment.personaModel ?? "anthropic/claude-haiku-4-5",
  );
  const [goalContextId, setGoalContextId] = useState<string | null>(null);
  const [maxTurns, setMaxTurns] = useState<number>(8);
  const [sidecarStartingId, setSidecarStartingId] = useState<string | null>(null);
  const [sidecarActionError, setSidecarActionError] = useState<string | null>(null);
  const [samplingMode, setSamplingMode] = useState<PersonaSamplingMode>("single");
  const [selectedPersonaIds, setSelectedPersonaIds] = useState<string[]>([]);
  const [groupFilters, setGroupFilters] = useState(emptyPersonaDimensionFilters());
  const [stratifyFields, setStratifyFields] = useState<string[]>(["age_bracket", "region"]);
  const [sampleSize, setSampleSize] = useState(4);
  const [seed] = useState(42);
  const [parallelTrials, setParallelTrials] = useState(2);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const {
    batchJobName,
    setBatchJobName,
    batchLive,
    clearBatch,
    isBatchActive,
    batchComplete,
    batchGridCells,
    expectedTrialCount,
  } = useCockpitBatchJob(selectedPersonaIds, parallelTrials);
  const [exportSnapshot, setExportSnapshot] = useState<ExportSnapshot | null>(null);

  useEffect(() => {
    const id = selectedPersonaIds[0];
    if (!id) {
      setPersona(null);
      return;
    }
    setPersona({
      id,
      name: `persona-${id}`,
      source: "bench-dev-sample",
    });
  }, [selectedPersonaIds]);

  // Adopt the canonical defaults once config metadata arrives.
  const adoptedDefaults = useRef(false);
  useEffect(() => {
    if (adoptedDefaults.current || !options) return;
    adoptedDefaults.current = true;
    setApplicationId((options.defaults.applicationId as ApplicationId | undefined) ?? "recai");
    setDomain((options.defaults.domain as Domain) ?? "movie");
    setEngine(options.defaults.engine ?? "gpt-4o-mini");
    setPersonaModel(options.environment.personaModel ?? "anthropic/claude-haiku-4-5");
  }, [options]);

  // Mirror the run domain up so the shared (⌘K) catalog drawer matches it.
  useEffect(() => {
    onDomainChange?.(domain);
  }, [domain, onDomainChange]);

  const applicationContext = contextForApplication(applicationId, domain);
  const requestDomain = applicationId === "recai" ? domain : undefined;

  // --- Goal contexts (the "Conversation style" knob) ----------------------
  const goalContextsQuery = useQuery<GoalContextsResponse>({
    queryKey: ["persona-eval-goal-contexts"],
    queryFn: listGoalContexts,
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  const goalContexts: GoalContext[] = useMemo(
    () => goalContextsQuery.data?.goalContexts ?? [],
    [goalContextsQuery.data],
  );
  const activeGoalContext =
    goalContexts.find((g) => g.id === (goalContextId ?? goalContexts[0]?.id)) ?? null;

  useEffect(() => {
    if (!goalContextId && goalContexts[0]?.id) {
      setGoalContextId(goalContexts[0].id);
    }
  }, [goalContextId, goalContexts]);

  const sidecarsQuery = useQuery({
    queryKey: ["chatbot-sidecars"],
    queryFn: api.getChatbotSidecars,
    refetchInterval: sidecarStartingId ? 3_000 : 15_000,
  });
  const sidecarsByApp = useMemo(() => {
    const map: Record<string, ChatbotSidecarStatus> = {};
    for (const sidecar of sidecarsQuery.data?.sidecars ?? []) {
      map[sidecar.applicationId] = sidecar;
    }
    return map;
  }, [sidecarsQuery.data]);

  const handleStartSidecar = useCallback(
    async (appId: string) => {
      setSidecarActionError(null);
      setSidecarStartingId(appId);
      try {
        await api.startChatbotSidecar(appId);
        await sidecarsQuery.refetch();
      } catch (e) {
        setSidecarActionError(e instanceof Error ? e.message : "Failed to start sidecar");
      } finally {
        setSidecarStartingId(null);
      }
    },
    [sidecarsQuery],
  );

  // Live persona + controls, mirrored to a ref so the "run finished" effect can
  // freeze them without re-running when a control changes.
  const liveControls = useMemo<ExportSnapshot>(
    () => ({
      persona: persona ? { id: persona.id, name: persona.name, source: persona.source } : null,
      config: {
        applicationId,
        applicationContext,
        domain: requestDomain,
        engine,
        personaModel,
        goalContextId: goalContextId ?? activeGoalContext?.id ?? null,
        maxTurns,
      },
    }),
    [persona, applicationId, applicationContext, requestDomain, engine, personaModel, goalContextId, activeGoalContext, maxTurns],
  );
  const liveControlsRef = useRef(liveControls);
  liveControlsRef.current = liveControls;

  useEffect(() => {
    if (phase === "done") {
      setExportSnapshot((prev) => prev ?? liveControlsRef.current);
    }
  }, [phase]);

  // --- Inspector + folds + focus -----------------------------------------
  const [tab, setTab] = useState<InspectorTab>("evaluation");
  const [expandedTurns, setExpandedTurns] = useState<Set<number>>(new Set());
  const [focusedTurnIndex, setFocusedTurnIndex] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const turnRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // --- Elapsed clock (live status bar) -----------------------------------
  const runStartedAtRef = useRef<number | null>(null);
  const [, setNowTick] = useState(0);
  useEffect(() => {
    if (!isRunning) return;
    const id = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [isRunning]);

  const turns = useMemo(() => job?.turns ?? [], [job]);
  const draftTurn = job?.draftTurn ?? null;
  const sutDescription = job?.sutDescription ?? null;
  const status = liveStatusLine(job, phase, isRunning, harborPhase);
  const questionnaire = job?.questionnaire ?? null;
  const metrics = job?.metricScores ?? null;
  const applicationOptions: ConfigOptionValue[] = useMemo(() => {
    const knob = (options?.knobs ?? []).find((k) => k.key === "applicationId");
    return knob?.options ?? [];
  }, [options]);
  const appName = APP_NAME[applicationId] ?? applicationOptions.find((o) => o.value === applicationId)?.label ?? "The app";
  const runContext = `${appName}${applicationId === "recai" ? ` · ${fmtDomain(domain)}` : ""}`;

  // Report the honest footer context up (task type + app + domain for RecAI).
  useEffect(() => {
    if (!isActive) return;
    onFooterContextChange?.(`chatbot · ${runContext}`);
  }, [isActive, runContext, onFooterContextChange]);

  // --- Actions ------------------------------------------------------------
  const handleRun = useCallback(() => {
    if (!persona || isRunning) return;
    setExpandedTurns(new Set());
    setFocusedTurnIndex(null);
    setExportSnapshot(null);
    setLaunchError(null);
    runStartedAtRef.current = Date.now();
    const taskPath = HARBOR_CHAT_TASKS[applicationId] ?? HARBOR_TASK_PATHS.chatbot;
    void run({
      taskPath,
      personaId: persona.id,
      personaModel,
      mode: "auto",
      chatDomain: requestDomain,
      chatApplicationId: applicationId,
      chatApplicationContext: requestDomain,
      chatGoalContextId: goalContextId ?? "scenario_default",
      chatMaxTurns: maxTurns,
      mapDebrief: (debrief, ctx) =>
        mapChatbotDebriefToJobView(debrief, ctx, {
          personaId: persona.id,
          personaName: persona.name,
          domain: requestDomain,
          applicationId,
        }),
      mapLive: (live, ctx) =>
        mapChatbotLiveToJobView(live, ctx, {
          personaId: persona.id,
          personaName: persona.name,
          domain: requestDomain,
          applicationId,
          goalContextId: goalContextId ?? "scenario_default",
        }),
    });
  }, [persona, isRunning, run, applicationId, personaModel, requestDomain, goalContextId, maxTurns]);

  const isBatchRun = samplingMode !== "single" || selectedPersonaIds.length > 1;

  const handleLaunch = useCallback(async () => {
    if (selectedPersonaIds.length === 0 || isRunning) return;
    if (isBatchRun) {
      setLaunchError(null);
      try {
        const taskPath = HARBOR_CHAT_TASKS[applicationId] ?? HARBOR_TASK_PATHS.chatbot;
        const launched = await api.launchHarborJob({
          taskPath,
          sampleSize: selectedPersonaIds.length,
          seed,
          personaModel,
          personaIds: selectedPersonaIds,
          nConcurrentTrials: Math.min(parallelTrials, selectedPersonaIds.length),
          mode: "auto",
          chatDomain: requestDomain,
          chatApplicationId: applicationId,
          chatApplicationContext: requestDomain,
          chatGoalContextId: goalContextId ?? "scenario_default",
          chatMaxTurns: maxTurns,
        });
        setBatchJobName(launched.jobName);
      } catch (exc) {
        const message = exc instanceof ApiError ? exc.message : exc instanceof Error ? exc.message : String(exc);
        setLaunchError(message);
      }
      return;
    }
    handleRun();
  }, [
    selectedPersonaIds,
    isRunning,
    isBatchRun,
    applicationId,
    seed,
    personaModel,
    parallelTrials,
    requestDomain,
    goalContextId,
    maxTurns,
    onOpenHarborJob,
    handleRun,
  ]);

  const handleRetry = useCallback(() => {
    if (timedOut || phase === "error") retry();
    else handleRun();
  }, [timedOut, phase, retry, handleRun]);

  const handleNewRun = useCallback(() => {
    reset();
    clearBatch();
    setLaunchError(null);
    setFocusedTurnIndex(null);
    setExpandedTurns(new Set());
  }, [reset, clearBatch]);

  const registerTurnRef = useCallback((index: number, el: HTMLDivElement | null) => {
    if (el) turnRefs.current.set(index, el);
    else turnRefs.current.delete(index);
  }, []);

  const toggleTurnFold = useCallback((index: number) => {
    setExpandedTurns((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }, []);

  const toggleExpandAll = useCallback(() => {
    setExpandedTurns((prev) => (prev.size >= turns.length && turns.length > 0 ? new Set() : new Set(turns.map((_, i) => i))));
  }, [turns]);

  const moveFocus = useCallback(
    (delta: number) => {
      if (turns.length === 0) return;
      setFocusedTurnIndex((prev) => {
        const start = prev ?? (delta > 0 ? -1 : turns.length);
        const next = Math.max(0, Math.min(turns.length - 1, start + delta));
        const el = turnRefs.current.get(next);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
        return next;
      });
    },
    [turns.length],
  );

  // --- Export (client-side JSON of the completed run) ---------------------
  const handleExport = useCallback(() => {
    if (!exportSnapshot || turns.length === 0) return;
    const payload = {
      persona: exportSnapshot.persona,
      config: exportSnapshot.config,
      transcript: turns,
      questionnaire,
      metricScores: metrics,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `persona-eval-${exportSnapshot.persona?.id ?? "run"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [exportSnapshot, turns, questionnaire, metrics]);

  const canExport = exportSnapshot !== null && turns.length > 0;

  // --- Keyboard shortcuts -------------------------------------------------
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (isTypingTarget(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
      switch (e.key) {
        case "r":
        case "R":
          e.preventDefault();
          void handleLaunch();
          break;
        case "j":
        case "J":
          e.preventDefault();
          moveFocus(1);
          break;
        case "k":
        case "K":
          e.preventDefault();
          moveFocus(-1);
          break;
        case "1":
          e.preventDefault();
          setTab("evaluation");
          break;
        case "2":
          e.preventDefault();
          setTab("instruction");
          break;
        case "e":
        case "E":
          e.preventDefault();
          toggleExpandAll();
          break;
        default:
          break;
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [handleLaunch, moveFocus, toggleExpandAll]);

  const knobs = options?.knobs ?? [];
  const personaModelKnob = knobs.find((k) => k.key === "personaModel");
  const personaModelOptions =
    personaModelKnob?.options.map((o) => ({ value: o.value, label: o.label })) ?? [
      { value: personaModel, label: personaModel },
    ];
  const engineKnob = knobs.find((k) => k.key === "engine");
  const engineOptions = engineKnob?.options ?? [];
  const domainKnob = knobs.find((k) => k.key === "domain");
  const domainOptions =
    applicationId === "recai"
      ? (domainKnob?.options ?? []).map((o) => ({ ...o, label: fmtDomain(o.label) }))
      : [];
  const chatTransport =
    applicationId === "finance_openbb" ? "mcp" : applicationId === "medical_assistant" ? "api" : "sidecar";
  const verifierOnlyFailure = isRewardOnlyTrialFailure(error ?? job?.error ?? null, {
    transcript: turns,
    questionnaire: questionnaire ?? undefined,
  });
  const pipelinePhase = (
    !verifierOnlyFailure && (job?.status === "error" || phase === "error")
      ? "error"
      : phase === "launching"
        ? "building"
        : phase
  ) as PersonaEvalRunPhase;
  const elapsedSeconds =
    isRunning && runStartedAtRef.current ? Math.max(0, Math.floor((Date.now() - runStartedAtRef.current) / 1000)) : 0;
  const showLiveCenter = phase !== "idle" || Boolean(batchJobName);
  const showInspector = phase !== "idle" && !batchJobName;
  const runBusy = isRunning || isBatchActive;
  const chatTaskPath = HARBOR_CHAT_TASKS[applicationId] ?? HARBOR_TASK_PATHS.chatbot;
  const instructionView = useCockpitInstruction({
    taskPath: chatTaskPath,
    fallbackTitle: appName,
    harborJobName,
    harborTrialName,
    enabled: phase !== "idle",
  });

  const runLaunchPhase = resolveRunLaunchPhase(
    batchJobName,
    batchComplete,
    batchLive.error,
    phase,
  );

  const runProgressPct = batchJobName
    ? computeBatchProgressPct(
        batchJobName,
        batchLive.live?.completedTrials,
        expectedTrialCount,
      )
    : pipelinePhase === "done"
      ? 100
      : pipelinePhase === "building"
        ? 12
        : pipelinePhase === "running"
          ? Math.min(100, Math.round((turns.length / Math.max(1, maxTurns)) * 100))
          : 0;

  const runProgressLabel = batchJobName
    ? `Harbor job · ${batchLive.live?.completedTrials ?? 0}/${expectedTrialCount} trials`
    : pipelinePhase === "building"
      ? "Starting the app…"
      : pipelinePhase === "running"
        ? `Turn ${turns.length} of ${maxTurns} · ${elapsedSeconds}s`
        : pipelinePhase === "done"
          ? `Run complete · ${turns.length} turn${turns.length === 1 ? "" : "s"}`
          : pipelinePhase === "error" || pipelinePhase === "timeout"
            ? error ?? "The run stopped before completing."
            : undefined;

  const cockpitView = (
    <CockpitSetupShell
      header={<RunHeader taskType={taskType} onTaskTypeChange={onTaskTypeChange} />}
      left={
        <PersonaSamplingRail
                personaModel={personaModel}
          onPersonaModelChange={setPersonaModel}
          personaModelOptions={personaModelOptions}
          mode={samplingMode}
          onModeChange={setSamplingMode}
          selectedPersonaIds={selectedPersonaIds}
          onSelectedPersonaIdsChange={setSelectedPersonaIds}
          sampleSize={sampleSize}
          onSampleSizeChange={setSampleSize}
          seed={seed}
          filters={groupFilters}
          onFiltersChange={setGroupFilters}
          stratifyFields={stratifyFields}
          onStratifyFieldsChange={setStratifyFields}
          disabled={runBusy}
        />
      }
      center={
        <div className="flex h-full min-h-0 w-full flex-col gap-2">
          {showLiveCenter ? (
            <CockpitLiveStage className="min-h-0 flex-1">
              {batchJobName ? (
                <BatchTrialGrid trials={batchGridCells} jobLabel={batchJobName} />
              ) : (
        <Trajectory
          turns={turns}
                  draftTurn={draftTurn}
                  livePhase={job?.phase ?? harborPhase}
          domain={domain}
          appName={appName}
          sutDescription={sutDescription}
          goalContext={activeGoalContext}
          phase={pipelinePhase}
          liveStatus={status}
          error={verifierOnlyFailure ? null : error}
          expandedTurns={expandedTurns}
          onToggleTurn={toggleTurnFold}
          focusedTurnIndex={focusedTurnIndex}
          registerTurnRef={registerTurnRef}
          onRetry={handleRetry}
        />
              )}
            </CockpitLiveStage>
          ) : (
            <div className="flex min-h-0 flex-1 flex-col">
              <CockpitPipelineDiagram
                className="h-full"
                taskType={taskType}
                chatTransport={chatTransport}
                hasPersona={selectedPersonaIds.length > 0}
                hasTask={Boolean(applicationId)}
              />
            </div>
          )}
          <RunLaunchBar
            canRun={selectedPersonaIds.length > 0 && !runBusy}
            isBatch={isBatchRun}
            personaCount={selectedPersonaIds.length}
            parallelTrials={parallelTrials}
            onParallelTrialsChange={setParallelTrials}
            isRunning={runBusy}
            onRun={() => void handleLaunch()}
            error={launchError ?? (verifierOnlyFailure ? null : error) ?? batchLive.error}
            runPhase={runLaunchPhase}
            progressPct={runProgressPct}
            progressLabel={runProgressLabel}
            progressSublabel={
              batchJobName && batchComplete
                ? "All trials finished — open Runs for debrief."
                : undefined
            }
            onNewRun={showLiveCenter ? handleNewRun : undefined}
            onViewJob={
              batchJobName && batchComplete && onOpenHarborJob
                ? () => onOpenHarborJob(batchJobName)
                : undefined
            }
            onDownload={!batchJobName ? handleExport : undefined}
            canDownload={canExport}
          />
        </div>
      }
      right={
        showInspector ? (
        <InspectorTabs
          active={tab}
          onChange={setTab}
          evaluation={<Scorecard questionnaire={questionnaire} metrics={metrics} phase={pipelinePhase} />}
          instruction={
            <InstructionPanel
              title={instructionView.title}
              markdown={instructionView.markdown}
              loading={instructionView.loading}
              error={instructionView.error}
            />
          }
        />
        ) : (
          <TaskSelectionRail
            taskType={taskType}
            chatOptions={applicationOptions}
            selectedChatAppId={applicationId}
            onChatAppChange={(v) => setApplicationId(v as ApplicationId)}
            sidecarsByApp={sidecarsByApp}
            sidecarsLoading={sidecarsQuery.isLoading}
            surveyTasks={[]}
            webTasks={[]}
            cuaTasks={[]}
            selectedTaskId={applicationId}
            onSelectTask={() => undefined}
            engine={engine}
            onEngineChange={setEngine}
            engineOptions={engineOptions}
            domain={domain}
            onDomainChange={(v) => setDomain(v as Domain)}
            domainOptions={domainOptions}
        maxTurns={maxTurns}
            onMaxTurnsChange={setMaxTurns}
            onStartSidecar={handleStartSidecar}
            sidecarStartingId={sidecarStartingId}
            sidecarActionError={sidecarActionError}
            disabled={runBusy}
          />
        )
      }
    />
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {cockpitView}
      <PersonaDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} persona={persona} context={null} />
    </div>
  );
}
function contextForApplication(applicationId: ApplicationId, domain: Domain): string {
  if (applicationId === "finance_openbb") return "financial_research";
  if (applicationId === "medical_assistant") return "medical_consultation";
  return domain;
}

export default PersonaEvalCockpit;
