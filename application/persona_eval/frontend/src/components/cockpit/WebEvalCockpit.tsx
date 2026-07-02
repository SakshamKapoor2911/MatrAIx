/**
 * WebEvalCockpit: the Website-task PersonaEval surface.
 *
 * Reproduces the approved redesign mockup's `data-view="cockpit"` setup shell
 * (the same centered form as the canonical chatbot cockpit: header +
 * application-type switch + pipeline strip + run-config card + target-persona
 * panel + Run-eval CTA) with the Web-specific body (a website-task picker + a
 * "Website task" card and a driver/artifacts note instead of an environment
 * panel.
 * environment). Once a run starts, the left column flips to the debrief view
 * modelled on the mockup's `data-view="runs"` web body: need-fit / ease /
 * overall-UX score tiles, the selected product, and a browser trace rendered as
 * screenshot tiles with per-step actions.
 *
 * The data layer is untouched: `useWebEval`, the `listWebEvalTasks` query, the
 * export logic, and every result/trace shape are wired exactly as before. Only
 * the structure and presentation are rebuilt.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { listWebEvalTasks, api, ApiError } from "@/lib/api";
import { FALLBACK_WEB_TASKS } from "@/lib/fallbackTasks";
import { mergeTaskCatalog } from "@/lib/mergeTaskCatalog";
import { suggestedWebPersonaAgent, webPersonaAgentLabel, WEB_PERSONA_AGENTS } from "@/lib/personaAgentCatalog";
import type {
  ConfigOptionsResponse,
  PersonaEvalPersona,
  WebEvalJobView,
  WebEvalTask,
  WebEvalTasksResponse,
  WebResult,
  WebTrace,
  WebTraceEvent,
} from "@/lib/types";
import { useHarborCockpitRun, type HarborCockpitPhase } from "@/lib/useHarborCockpitRun";
import { useCockpitInstruction } from "@/lib/useCockpitInstruction";
import { mapWebDebriefToJobView, attachHarborTraceScreenshotUrls } from "@/lib/harborCockpitMappers";
import { RunHeader } from "./RunHeader";
import { PersonaDrawer } from "./PersonaDrawer";
import { InspectorTabs, type InspectorTab } from "./InspectorTabs";
import { InstructionPanel } from "./InstructionPanel";
import { WebEvalScorecard } from "./TaskEvalScorecard";
import { CockpitSetupShell } from "./setup/CockpitSetupShell";
import { PersonaSamplingRail } from "./setup/PersonaSamplingRail";
import { CockpitPipelineDiagram } from "./setup/CockpitPipelineDiagram";
import { TaskSelectionRail } from "./setup/TaskSelectionRail";
import { CockpitRunCenter } from "./setup/CockpitRunCenter";
import { useSetupPersonaSampling } from "./setup/useSetupPersonaSampling";
import {
  batchProgressPct as computeBatchProgressPct,
  resolveRunLaunchPhase,
  useCockpitBatchJob,
} from "./setup/useCockpitBatchJob";
import { webEvalTaskCards } from "./setup/cockpitTaskCards";
import {
  FOCUS_RING,
  Sym,
  personaDescriptiveTitle,
} from "./cockpitShared";
import type { PersonaEvalTaskType } from "./TaskTypeSwitch";

const DEFAULT_AGENT_MODEL = "anthropic/claude-sonnet-4-6";

function mergeWebTasks(apiTasks: WebEvalTask[] | undefined): WebEvalTask[] {
  return mergeTaskCatalog(FALLBACK_WEB_TASKS, apiTasks, (row, api, base) => ({
    ...row,
    taskPath: api?.taskPath || base?.taskPath || row.taskPath || "",
  }));
}

export interface WebEvalCockpitProps {
  options: ConfigOptionsResponse | null;
  taskType: PersonaEvalTaskType;
  onTaskTypeChange: (value: PersonaEvalTaskType) => void;
  /** Report the honest footer context up (the active website). */
  onFooterContextChange?: (context: string) => void;
  onOpenHarborJob?: (jobName: string) => void;
  onOpenHarborTrial?: (jobName: string, trialName: string) => void;
  /** When false, the cockpit stays mounted but hidden — skip footer updates. */
  isActive?: boolean;
}



function webStatusLine(
  phase: HarborCockpitPhase,
  jobPhase: string | null | undefined,
  harborPhase?: string | null,
): string | null {
  if (phase === "launching") return "Launching Harbor job…";
  if (phase !== "running") return null;
  const raw = (harborPhase ?? jobPhase ?? "").toLowerCase();
  if (raw.includes("harbor") || raw.includes("trial")) return "Harbor is running the web trial…";
  if (raw.includes("collect")) return "Saving the results and step screenshots…";
  if (raw.includes("web")) return "The simulated visitor is using the site…";
  return "Running the website test…";
}

/**
 * A short, friendly summary of a step's first browser action (verb + target),
 * e.g. "clicked Add to cart" / "typed “a search”" / "went to /store". Reads the
 * existing `event.actions[0]`; presentation only, no data change.
 */
function summarizeAction(event: WebTraceEvent): string | null {
  const action = event.actions[0];
  if (!action || !action.name) return null;
  const name = action.name.toLowerCase();
  const args = action.arguments ?? {};
  let target: string | null = null;
  for (const value of Object.values(args)) {
    if (typeof value === "string" && value.trim()) {
      target = value.trim();
      break;
    }
  }
  const clip = (text: string) => (text.length > 28 ? text.slice(0, 27) + "…" : text);
  if (name.includes("click")) return target ? `clicked ${clip(target)}` : "clicked";
  if (name.includes("type") || name.includes("fill") || name.includes("input")) {
    return target ? `typed “${clip(target)}”` : "typed";
  }
  if (name.includes("nav") || name.includes("goto") || name.includes("visit") || name.includes("open")) {
    return target ? `went to ${clip(target)}` : "navigated";
  }
  if (name.includes("search")) return target ? `searched ${clip(target)}` : "searched";
  if (name.includes("select")) return "selected an option";
  if (name.includes("submit")) return "submitted the form";
  if (name.includes("scroll")) return "scrolled";
  if (name.includes("back")) return "went back";
  return name.replace(/_/g, " ");
}

/** A `name(arg)` mono signature for a step (mockup: `goto(/store)` / `add_to_cart()`). */
function actionSignature(event: WebTraceEvent): string {
  const action = event.actions[0];
  if (action?.name) {
    const args = action.arguments ?? {};
    let arg = "";
    for (const value of Object.values(args)) {
      if (typeof value === "string" && value.trim()) {
        arg = value.trim();
        break;
      }
    }
    if (arg.length > 22) arg = arg.slice(0, 21) + "…";
    return `${action.name}(${arg})`;
  }
  const message = (event.message ?? "").trim();
  return message.length > 28 ? message.slice(0, 27) + "…" : message;
}

function formatDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function WebEvalCockpit({
  options,
  taskType,
  onTaskTypeChange,
  onFooterContextChange,
  onOpenHarborJob,
  isActive = true,
}: WebEvalCockpitProps) {
  const { run, job, phase, isRunning, error, timedOut, retry, reset, harborPhase, harborJobName, harborTrialName } =
    useHarborCockpitRun<WebEvalJobView>();
  const [liveTrace, setLiveTrace] = useState<WebTrace | null>(null);
  const {
    persona,
    personaModel,
    setPersonaModel,
    personaModelOptions,
    samplingMode,
    setSamplingMode,
    selectedPersonaIds,
    setSelectedPersonaIds,
    groupFilters,
    setGroupFilters,
    stratifyFields,
    setStratifyFields,
    sampleSize,
    setSampleSize,
    seed,
    parallelTrials,
    setParallelTrials,
    isBatchRun,
  } = useSetupPersonaSampling(options);
  const [taskId, setTaskId] = useState<string>("");
  const [webAgentByTaskId, setWebAgentByTaskId] = useState<Record<string, string>>({});
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [tab, setTab] = useState<InspectorTab>("evaluation");
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
  const [exportSnapshot, setExportSnapshot] = useState<{
    persona: { id: string; name: string; source: string } | null;
    taskId: string;
    personaModel: string;
  } | null>(null);

  useEffect(() => {
    setPersonaModel((current) =>
      current === "anthropic/claude-haiku-4-5" ? DEFAULT_AGENT_MODEL : current,
    );
  }, [setPersonaModel]);

  const tasksQuery = useQuery<WebEvalTasksResponse>({
    queryKey: ["web-eval-tasks"],
    queryFn: listWebEvalTasks,
    staleTime: 10 * 60_000,
    refetchOnWindowFocus: false,
    retry: 1,
  });
  const tasks = useMemo(
    () => mergeWebTasks(tasksQuery.data?.tasks),
    [tasksQuery.data?.tasks],
  );
  const task = tasks.find((item) => item.id === taskId) ?? tasks[0] ?? null;

  useEffect(() => {
    if (!task && tasks.length > 0) setTaskId(tasks[0].id);
  }, [task, tasks]);

  const resolveWebAgent = useCallback(
    (id: string) => webAgentByTaskId[id] ?? suggestedWebPersonaAgent(id),
    [webAgentByTaskId],
  );
  const activeWebAgent = task ? resolveWebAgent(task.id) : WEB_PERSONA_AGENTS[0].value;

  // Report the honest footer context up (the active website).
  useEffect(() => {
    if (!isActive) return;
    onFooterContextChange?.(`web · ${task?.siteName ?? "Website"}`);
  }, [isActive, task, onFooterContextChange]);

  const webResult = job?.webResult ?? null;
  const verifier = job?.verifier ?? null;
  const trace = job?.trace ?? liveTrace;
  const instructionView = useCockpitInstruction({
    taskPath: task?.taskPath ?? null,
    fallbackTitle: task?.title ?? null,
    harborJobName,
    harborTrialName,
    enabled: phase !== "idle",
  });
  useEffect(() => {
    if (phase === "idle") {
      setLiveTrace(null);
      return;
    }
    if (!harborJobName || !harborTrialName || phase !== "running") return;

    let cancelled = false;
    const poll = async () => {
      try {
        const payload = await api.getHarborTrialTrace(harborJobName, harborTrialName);
        if (!cancelled && payload.trace?.events?.length) {
          setLiveTrace(
            attachHarborTraceScreenshotUrls(payload.trace, harborJobName, harborTrialName),
          );
        }
      } catch {
        // trajectory.json is written once near the end of a Cocoa run
      }
    };

    void poll();
    const id = window.setInterval(() => void poll(), 800);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [phase, harborJobName, harborTrialName]);

  const failed = phase === "error" || phase === "timeout" || job?.status === "error";
  const status = webStatusLine(phase, job?.phase, harborPhase);

  useEffect(() => {
    if (phase === "done") {
      setExportSnapshot(
        (prev) =>
          prev ?? {
            persona: persona ? { id: persona.id, name: persona.name, source: persona.source } : null,
            taskId,
            personaModel,
          },
      );
    }
  }, [phase, persona, taskId, personaModel]);

  const taskCards = useMemo(() => webEvalTaskCards(tasks), [tasks]);

  const handleRun = useCallback(() => {
    if (!persona || !task?.taskPath || isRunning) return;
    setExportSnapshot(null);
    void run({
      taskPath: task.taskPath,
      personaId: persona.id,
      personaModel,
      agentName: activeWebAgent,
      mode: "auto",
      mapDebrief: (debrief, ctx) =>
        mapWebDebriefToJobView(debrief, ctx, {
          personaId: persona.id,
          personaName: persona.name,
      taskId: task.id,
          taskTitle: task.title,
        }),
    });
  }, [persona, task, isRunning, run, personaModel, activeWebAgent]);
  const handleLaunch = useCallback(async () => {
    if (selectedPersonaIds.length === 0 || !task?.taskPath || isRunning) return;
    if (isBatchRun) {
      setLaunchError(null);
      try {
        const launched = await api.launchHarborJob({
          taskPath: task.taskPath,
          sampleSize: selectedPersonaIds.length,
          seed,
          personaModel,
          agentName: activeWebAgent,
          personaIds: selectedPersonaIds,
          nConcurrentTrials: Math.min(parallelTrials, selectedPersonaIds.length),
          mode: "auto",
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
    task,
    isRunning,
    isBatchRun,
    seed,
    personaModel,
    activeWebAgent,
    parallelTrials,
    handleRun,
  ]);

  const handleNewRun = useCallback(() => {
    reset();
    clearBatch();
    setLaunchError(null);
  }, [reset, clearBatch]);

  const handleRetry = useCallback(() => {
    if (timedOut || phase === "error") retry();
    else handleRun();
  }, [timedOut, phase, retry, handleRun]);

  const handleExport = useCallback(() => {
    if (!exportSnapshot || !webResult) return;
    const payload = {
      applicationType: "web",
      config: exportSnapshot,
      webResult,
      trace,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `web-eval-${exportSnapshot.persona?.id ?? "run"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [exportSnapshot, webResult, trace]);

  const runBusy = isRunning || isBatchActive;
  const showLiveCenter = phase !== "idle" || Boolean(batchJobName);
  const showInspector = phase !== "idle" && !batchJobName;

  useEffect(() => {
    if (!showInspector) return;
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.key === "1") {
        e.preventDefault();
        setTab("evaluation");
      } else if (e.key === "2") {
        e.preventDefault();
        setTab("instruction");
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [showInspector]);
  const stepCount = trace?.events.length ?? 0;
  const runLaunchPhase = resolveRunLaunchPhase(
    batchJobName,
    batchComplete,
    batchLive.error,
    phase,
  );
  const runProgressPct = batchJobName
    ? computeBatchProgressPct(batchJobName, batchLive.live?.completedTrials, expectedTrialCount)
    : phase === "done"
      ? 100
      : phase === "launching"
        ? 12
        : stepCount > 0
          ? Math.min(95, Math.round((stepCount / Math.max(stepCount + 1, 8)) * 100))
          : phase === "running"
            ? 20
            : 0;
  const runProgressLabel = batchJobName
    ? `Harbor job · ${batchLive.live?.completedTrials ?? 0}/${expectedTrialCount} trials`
    : phase === "launching"
      ? "Launching web trial…"
      : phase === "running"
        ? stepCount > 0
          ? `Browser trace · ${stepCount} step${stepCount === 1 ? "" : "s"}`
          : (status ?? "Simulated visitor is browsing…")
        : phase === "done"
          ? `Web run complete · ${stepCount} steps`
          : failed
            ? error ?? "The website test didn't finish."
            : undefined;
  const canExport = exportSnapshot !== null && webResult !== null;

  const webLiveContent = (
    <>
              <WebResults
                task={task}
                webResult={webResult}
                trace={trace}
                phase={phase}
                status={status}
                error={error}
                persona={persona}
                onRetry={handleRetry}
              />
    </>
  );

  const cockpitView = (
    <CockpitSetupShell
      header={<RunHeader taskType={taskType} onTaskTypeChange={onTaskTypeChange} />}
      left={
        <PersonaSamplingRail
          taskType="web"
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
        <CockpitRunCenter
          showLive={showLiveCenter}
          pipeline={
            <CockpitPipelineDiagram
              className="h-full"
              taskType="web"
              webPersonaAgentLabel={
                task ? webPersonaAgentLabel(resolveWebAgent(task.id)) : undefined
              }
              hasPersona={selectedPersonaIds.length > 0}
              hasTask={Boolean(task?.taskPath)}
            />
          }
          liveContent={webLiveContent}
          batchJobName={batchJobName}
          batchCells={batchGridCells}
          runLaunchPhase={runLaunchPhase}
          progressPct={runProgressPct}
          progressLabel={runProgressLabel}
          progressSublabel={
            batchJobName && batchComplete ? "All trials finished — open Runs for debrief." : undefined
          }
          canRun={selectedPersonaIds.length > 0 && Boolean(task?.taskPath) && !runBusy}
          isBatch={isBatchRun}
          personaCount={selectedPersonaIds.length}
          parallelTrials={parallelTrials}
          onParallelTrialsChange={setParallelTrials}
          runBusy={runBusy}
          onRun={() => void handleLaunch()}
          error={launchError ?? error ?? batchLive.error}
          onNewRun={showLiveCenter ? handleNewRun : undefined}
          onViewJob={
            batchJobName && batchComplete && onOpenHarborJob
              ? () => onOpenHarborJob(batchJobName)
              : undefined
          }
          onDownload={!batchJobName ? handleExport : undefined}
          canDownload={canExport}
        />
      }
      right={
        showInspector ? (
          <InspectorTabs
            active={tab}
            onChange={setTab}
            evaluation={
              <WebEvalScorecard webResult={webResult} verifier={verifier} phase={phase} />
            }
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
          taskType="web"
          chatOptions={[]}
          selectedChatAppId=""
          onChatAppChange={() => undefined}
          sidecarsByApp={{}}
          sidecarsLoading={false}
          surveyTasks={[]}
          webTasks={taskCards}
          cuaTasks={[]}
          selectedTaskId={taskId}
          onSelectTask={(card) => setTaskId(card.id)}
          engine=""
          onEngineChange={() => undefined}
          engineOptions={[]}
          domain=""
          onDomainChange={() => undefined}
          domainOptions={[]}
          maxTurns={8}
          onMaxTurnsChange={() => undefined}
          webPersonaAgentOptions={WEB_PERSONA_AGENTS}
          resolveWebPersonaAgent={resolveWebAgent}
          onWebPersonaAgentChange={(id, agent) =>
            setWebAgentByTaskId((prev) => ({ ...prev, [id]: agent }))
          }
          tasksLoading={tasksQuery.isLoading}
          tasksError={
            tasks.length === 0
              ? tasksQuery.isError
                ? "Web task API unavailable — restart PersonaEval backend on :8765."
                : "No web tasks available."
              : null
          }
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

/** Status-aware Persona → Website → Trace → Evaluation pipeline strip. */
function WebResults({
  task,
  webResult,
  trace,
  phase,
  status,
  error,
  persona,
  onRetry,
}: {
  task: WebEvalTask | null;
  webResult: WebResult | null;
  trace: WebTrace | null;
  phase: HarborCockpitPhase;
  status: string | null;
  error: string | null;
  persona: PersonaEvalPersona | null;
  onRetry: () => void;
}) {
  const running = phase === "launching" || phase === "running";
  const failed = phase === "error" || phase === "timeout";
  const personaTitle = persona ? personaDescriptiveTitle(null, persona.blurb, persona.source) : "Persona";
  const runDate = formatDate(webResult?.createdAt);
  const headerBits = [
    "Web",
    task?.title ?? "website task",
    personaTitle,
    ...(runDate ? [runDate] : []),
  ];

  return (
    <section className="space-y-5">
      {/* Run identity line */}
      <div className="hud flex items-start gap-2 text-[9px] text-text-variant">
        <Sym name="language" size={16} className="shrink-0 text-primary" />
        <span className="min-w-0 break-words">Run · {headerBits.join(" · ")}</span>
      </div>

      {/* Live "browsing" banner */}
      {running && !webResult && (
        <div className="rise-in rounded-md border border-outline bg-surface-lowest px-4 py-4">
          <div className="flex items-center gap-2">
            <Sym name="autorenew" size={16} className="animate-rb-spin text-primary" />
            <span className="hud text-[10px] text-primary">Running</span>
          </div>
          <p className="mt-2 text-[13px] text-text-main">Simulated visitor is browsing…</p>
          {status && <p className="mt-0.5 text-[12px] text-text-variant">{status}</p>}
          {trace && trace.events.length > 0 && (
            <p className="mt-2 font-mono text-[11px] text-text-variant">Recorded {trace.events.length} steps so far</p>
          )}
        </div>
      )}

      {/* Error */}
      {failed && (
        <ErrorCard
          title="The website test didn’t finish"
          body={error ?? "Something interrupted the test. Your setup is still here. Press Try again."}
          onRetry={onRetry}
          retryLabel="Try again"
        />
      )}

      {/* Browser trace — show as soon as partial trajectory exists */}
      {trace && trace.events.length > 0 && (
        <div className="space-y-3">
          <h3 className="hud flex items-center gap-2 text-[10px] text-primary">
            <Sym name="route" size={14} /> Browser trace · {trace.events.length} step
            {trace.events.length === 1 ? "" : "s"}
          </h3>
          <WebTraceGrid trace={trace} autoFollowLatest={running} />
        </div>
      )}

      {/* Loading skeleton before any result/trace lands */}
      {running && !webResult && !trace && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4" aria-hidden>
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 animate-rb-pulse rounded-md bg-surface-high" />
          ))}
        </div>
      )}
    </section>
  );
}

/** Screenshot-tile grid + scrubber replay + per-step detail panel. */
function WebTraceGrid({
  trace,
  autoFollowLatest = false,
}: {
  trace: WebTrace;
  autoFollowLatest?: boolean;
}) {
  const [selected, setSelected] = useState<number | null>(null);
  const [scrubIndex, setScrubIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const events = trace.events;

  useEffect(() => {
    if (!autoFollowLatest || isPlaying) return;
    setScrubIndex(Math.max(0, events.length - 1));
  }, [autoFollowLatest, events.length, isPlaying]);

  useEffect(() => {
    if (!isPlaying) return;
    if (scrubIndex >= events.length - 1) {
      setIsPlaying(false);
      return;
    }
    const id = window.setInterval(() => {
      setScrubIndex((prev) => {
        const next = Math.min(prev + 1, events.length - 1);
        const nextEvent = events[next];
        if (nextEvent) setSelected(nextEvent.step);
        if (next >= events.length - 1) setIsPlaying(false);
        return next;
      });
    }, 1200);
    return () => window.clearInterval(id);
  }, [isPlaying, scrubIndex, events]);

  useEffect(() => {
    setScrubIndex((prev) => Math.min(prev, Math.max(0, events.length - 1)));
  }, [events.length]);

  if (events.length === 0) {
    return (
      <div className="rise-in rounded-md border border-dashed border-outline bg-surface-low px-4 py-6 text-center text-[12px] text-text-variant">
        This run finished without recording any steps.
      </div>
    );
  }

  const activeStep = events[Math.min(scrubIndex, events.length - 1)]?.step ?? events[0].step;
  const selectedEvent = selected != null ? events.find((event) => event.step === selected) ?? null : null;
  const previewEvent = events[Math.min(scrubIndex, events.length - 1)];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 rounded-md border border-outline/50 bg-surface-low px-3 py-2">
        <button
          type="button"
          onClick={() => {
            if (isPlaying) {
              setIsPlaying(false);
              return;
            }
            if (scrubIndex >= events.length - 1) {
              setScrubIndex(0);
              setSelected(events[0]?.step ?? null);
            }
            setIsPlaying(true);
          }}
          aria-label={isPlaying ? "Pause trace replay" : "Play trace replay"}
          className={`grid h-8 w-8 place-items-center rounded-full border border-outline/60 text-primary transition hover:border-primary/50 active:scale-95 ${FOCUS_RING}`}
        >
          <Sym name={isPlaying ? "pause_circle" : "play_circle"} size={18} />
        </button>
        <input
          type="range"
          min={0}
          max={Math.max(0, events.length - 1)}
          value={scrubIndex}
          onChange={(e) => {
            setIsPlaying(false);
            const next = Number(e.target.value);
            setScrubIndex(next);
            setSelected(events[next]?.step ?? null);
          }}
          className="min-w-[120px] flex-1 accent-primary"
        />
        <span className="font-mono text-[10px] text-text-dim">
          Step {previewEvent.step} / {events.length}
        </span>
      </div>

      {previewEvent?.screenshotUrl && (
        <div className="overflow-hidden rounded-md border border-outline bg-surface-low">
          <img
            src={previewEvent.screenshotUrl}
            alt={`Step ${previewEvent.step}`}
            className="max-h-[280px] w-full object-contain bg-surface-lowest"
          />
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {events.map((event, index) => (
          <TraceTile
            key={event.step}
            index={index}
            event={event}
            active={event.step === activeStep}
            onClick={() => {
              setSelected((prev) => (prev === event.step ? null : event.step));
              setScrubIndex(index);
            }}
          />
        ))}
      </div>
      {selectedEvent && (
        <TraceDetail key={selectedEvent.step} event={selectedEvent} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function TraceTile({
  index,
  event,
  active,
  onClick,
}: {
  index: number;
  event: WebTraceEvent;
  active: boolean;
  onClick: () => void;
}) {
  const [imgError, setImgError] = useState(false);
  const hint = summarizeAction(event);
  const showImage = Boolean(event.screenshotUrl) && !imgError;

  return (
    <button
      type="button"
      onClick={onClick}
      style={{ animationDelay: `${Math.min(index, 6) * 30}ms` }}
      className={`rise-in overflow-hidden rounded-md border bg-surface text-left transition active:scale-[0.98] ${FOCUS_RING} ${
        active ? "border-primary" : "border-outline hover:border-primary/60 hover:bg-surface-low"
      }`}
    >
      <div className="grid aspect-video place-items-center border-b border-outline bg-surface-low text-text-dim">
        {showImage ? (
          <img
            src={event.screenshotUrl as string}
            alt={`Browser screenshot for step ${event.step}`}
            className="h-full w-full bg-surface-lowest object-cover"
            loading="lazy"
            onError={() => setImgError(true)}
          />
        ) : (
          <Sym name="image" size={24} />
        )}
      </div>
      <div className="p-2.5">
        <div className="hud truncate text-[8px] text-text-dim">
          Step {event.step} · {hint ?? event.source ?? "visitor"}
        </div>
        <div className="mt-0.5 truncate font-mono text-[10px] text-text-variant">{actionSignature(event)}</div>
      </div>
    </button>
  );
}

function TraceDetail({ event, onClose }: { event: WebTraceEvent; onClose: () => void }) {
  const [imgError, setImgError] = useState(false);
  const message = event.message.trim();
  return (
    <div className="rise-in rounded-md border border-outline bg-surface p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="hud text-[10px] text-primary">
          Step {event.step} · {summarizeAction(event) ?? event.source ?? "visitor"}
        </span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close step detail"
          className={`grid h-7 w-7 place-items-center rounded-md border border-outline text-text-variant transition hover:border-primary hover:text-text-main active:scale-95 ${FOCUS_RING}`}
        >
          <Sym name="close" size={16} />
        </button>
      </div>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1.2fr)_minmax(260px,0.8fr)]">
        {event.screenshotUrl && !imgError ? (
          <div className="overflow-hidden rounded-md border border-outline bg-surface-low">
            <img
              src={event.screenshotUrl}
              alt={`Browser screenshot for step ${event.step}`}
              className="aspect-video max-h-80 w-full bg-surface-lowest object-contain"
              loading="lazy"
              onError={() => setImgError(true)}
            />
            {event.screenshotFile && (
              <div className="border-t border-outline px-2 py-1 font-mono text-[11px] text-text-variant">
                {event.screenshotFile}
              </div>
            )}
          </div>
        ) : event.screenshotUrl && imgError ? (
          <div className="grid aspect-video max-h-80 w-full place-items-center rounded-md border border-outline bg-surface-low text-text-dim">
            <div className="text-center">
              <Sym name="image" size={24} className="text-text-dim" />
              <p className="mt-1 text-[12px] text-text-variant">Screenshot unavailable for this step.</p>
            </div>
          </div>
        ) : null}
        <div className="min-w-0 rounded-md border border-outline bg-surface-low p-2">
          {message && (
            <p className="whitespace-pre-wrap break-words text-[12px] leading-relaxed text-text-variant">{message}</p>
          )}
          {event.actions.length > 0 && (
            <pre
              className={`${message ? "mt-2" : ""} max-h-52 overflow-auto whitespace-pre-wrap break-words rounded bg-field p-2 font-mono text-[11px] text-text-variant`}
            >
              {JSON.stringify(event.actions, null, 2)}
            </pre>
          )}
          {!message && event.actions.length === 0 && (
            <p className="text-[12px] text-text-variant">No extra detail recorded for this step.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function ErrorCard({
  title,
  body,
  onRetry,
  retryLabel = "Try again",
}: {
  title: string;
  body: string;
  onRetry: () => void;
  retryLabel?: string;
}) {
  return (
    <section className="rounded-md border border-danger/30 bg-danger/10 p-5">
      <div className="flex items-start gap-3">
        <Sym name="error" fill={1} size={20} className="mt-0.5 text-danger" />
        <div>
          <h2 className="font-semibold text-text-main">{title}</h2>
          <p className="mt-1 text-[13px] text-text-variant">{body}</p>
          <button
            type="button"
            onClick={onRetry}
            className={`mt-3 inline-flex items-center gap-1.5 rounded-md border border-danger/40 px-3 py-1.5 text-[12px] font-medium text-danger hover:bg-danger/10 ${FOCUS_RING}`}
          >
            <Sym name="refresh" size={15} />
            {retryLabel}
          </button>
        </div>
      </div>
    </section>
  );
}

