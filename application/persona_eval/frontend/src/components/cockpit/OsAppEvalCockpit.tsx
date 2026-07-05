/**
 * OsAppEvalCockpit: Harbor computer-use tasks (linux / macos / ios) from MatrAIx
 * example-computer-use-* — not AppWorld.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { listOsAppEvalTasks, api, ApiError } from "@/lib/api";
import { FALLBACK_OS_APP_TASKS } from "@/lib/fallbackTasks";
import { mergeTaskCatalog } from "@/lib/mergeTaskCatalog";
import {
  cuaPersonaModelSelectOptions,
  DEFAULT_CUA_AGENT_MODEL,
  personaModelPipelineLabel,
  suggestedCuaBackend,
} from "@/lib/personaAgentCatalog";
import type {
  ConfigOptionsResponse,
  OsAppEvalJobView,
  OsAppEvalTask,
  OsAppEvalTasksResponse,
  OsAppResult,
  WebTrace,
} from "@/lib/types";
import { useHarborCockpitRun, type HarborCockpitPhase } from "@/lib/useHarborCockpitRun";
import { useCockpitInstruction } from "@/lib/useCockpitInstruction";
import { mapOsAppDebriefToJobView, formatCockpitRunError, harborTrialRecordingUrl } from "@/lib/harborCockpitMappers";
import { RunHeader } from "./RunHeader";
import { HarborTraceReplay } from "./HarborTraceReplay";
import { PersonaDrawer } from "./PersonaDrawer";
import { InspectorTabs, type InspectorTab } from "./InspectorTabs";
import { InstructionPanel } from "./InstructionPanel";
import { OsAppEvalScorecard } from "./TaskEvalScorecard";
import { CockpitSetupShell } from "./setup/CockpitSetupShell";
import { PersonaSamplingRail } from "./setup/PersonaSamplingRail";
import { CockpitPipelineDiagram } from "./setup/CockpitPipelineDiagram";
import { TaskSelectionRail } from "./setup/TaskSelectionRail";
import { CockpitRunCenter } from "./setup/CockpitRunCenter";
import { useSetupPersonaSampling } from "./setup/useSetupPersonaSampling";
import {
  batchProgressPct as computeBatchProgressPct,
  BATCH_RUN_COMPLETE_HINT,
  formatBatchProgressLabel,
  resolveRunLaunchPhase,
  useCockpitBatchJob,
} from "./setup/useCockpitBatchJob";
import { useCockpitRunCancel } from "./setup/useCockpitRunCancel";
import { useCockpitSetupLock } from "./setup/useCockpitSetupLock";
import { osAppTaskCards } from "./setup/cockpitTaskCards";
import { FOCUS_RING, Sym } from "./cockpitShared";
import type { PersonaEvalTaskType } from "./TaskTypeSwitch";

const DEFAULT_AGENT_MODEL = DEFAULT_CUA_AGENT_MODEL;

function mergeOsAppTasks(apiTasks: OsAppEvalTask[] | undefined): OsAppEvalTask[] {
  return mergeTaskCatalog(FALLBACK_OS_APP_TASKS, apiTasks);
}

export interface OsAppEvalCockpitProps {
  options: ConfigOptionsResponse | null;
  taskType: PersonaEvalTaskType;
  onTaskTypeChange: (value: PersonaEvalTaskType) => void;
  onFooterContextChange?: (context: string) => void;
  onOpenHarborJob?: (jobName: string) => void;
  onOpenHarborTrial?: (jobName: string, trialName: string) => void;
  /** When false, the cockpit stays mounted but hidden — skip footer updates. */
  isActive?: boolean;
}


function cuaStatusLine(
  phase: HarborCockpitPhase,
  jobPhase: string | null | undefined,
  harborPhase?: string | null,
): string | null {
  if (phase === "launching") return "Launching trial…";
  if (phase !== "running") return null;
  const raw = (harborPhase ?? jobPhase ?? "").toLowerCase();
  if (raw.includes("harbor") || raw.includes("trial")) return "Running OS app trial…";
  if (raw.includes("collect")) return "Saving OS app artifacts and trajectory…";
  return "The persona agent is using the desktop…";
}

export function OsAppEvalCockpit({
  options,
  taskType,
  onTaskTypeChange,
  onFooterContextChange,
  onOpenHarborJob,
  onOpenHarborTrial,
  isActive = true,
}: OsAppEvalCockpitProps) {
  const { run, job, phase, isRunning, error, timedOut, retry, reset, harborPhase, harborJobName, harborTrialName, cancelRun, cancelBusy: harborCancelBusy } =
    useHarborCockpitRun<OsAppEvalJobView>({ taskKind: "os-app" });
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
  } = useSetupPersonaSampling(options, "os-app");
  const [taskId, setTaskId] = useState("");
  const [cuaRuntimeByTaskId, setCuaRuntimeByTaskId] = useState<Record<string, string>>({});
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [tab, setTab] = useState<InspectorTab>("evaluation");
  const [launchError, setLaunchError] = useState<string | null>(null);
  const {
    batchJobName,
    batchTaskId,
    batchPersonaIds,
    setBatchJobName,
    batchLive,
    clearBatch,
    cancelBatch,
    cancelBusy,
    isBatchActive,
    batchComplete,
    batchGridCells,
    expectedTrialCount,
  } = useCockpitBatchJob(selectedPersonaIds, parallelTrials, "os-app");
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

  const tasksQuery = useQuery<OsAppEvalTasksResponse>({
    queryKey: ["os-app-eval-tasks"],
    queryFn: listOsAppEvalTasks,
    staleTime: 10 * 60_000,
    retry: 1,
  });
  const tasks = useMemo(
    () => mergeOsAppTasks(tasksQuery.data?.tasks),
    [tasksQuery.data?.tasks],
  );
  const { setupLocked, visiblePersonaIds } = useCockpitSetupLock(
    phase,
    batchJobName,
    batchPersonaIds,
    selectedPersonaIds,
  );
  const activeTaskId = batchJobName && batchTaskId ? batchTaskId : taskId;
  const task = tasks.find((item) => item.id === activeTaskId) ?? tasks[0] ?? null;

  const cuaPersonaModelOptions = useMemo(
    () => cuaPersonaModelSelectOptions(task?.platform, personaModelOptions),
    [task?.platform, personaModelOptions],
  );

  const pipelinePersonaModelLabel = useMemo(
    () => personaModelPipelineLabel(personaModel, cuaPersonaModelOptions),
    [personaModel, cuaPersonaModelOptions],
  );

  useEffect(() => {
    if (cuaPersonaModelOptions.length === 0) return;
    if (!cuaPersonaModelOptions.some((opt) => opt.value === personaModel)) {
      setPersonaModel(cuaPersonaModelOptions[0]?.value ?? DEFAULT_AGENT_MODEL);
    }
  }, [cuaPersonaModelOptions, personaModel, setPersonaModel]);

  useEffect(() => {
    if (batchTaskId) {
      setTaskId(batchTaskId);
      return;
    }
    if (!taskId && tasks.length > 0) {
      setTaskId(tasks[0].id);
    }
  }, [batchTaskId, taskId, tasks]);

  const resolveCuaRuntime = useCallback(
    (id: string, platform?: string) => {
      const row = tasks.find((item) => item.id === id);
      const base = row?.osAppBackend ?? suggestedCuaBackend(platform ?? "linux");
      return cuaRuntimeByTaskId[id] ?? base;
    },
    [cuaRuntimeByTaskId, tasks],
  );
  const activeCuaRuntime = task ? resolveCuaRuntime(task.id, task.platform) : "docker";

  useEffect(() => {
    if (!isActive) return;
    onFooterContextChange?.(`os-app · ${task?.platform ?? "desktop"} · ${task?.title ?? "task"}`);
  }, [isActive, onFooterContextChange, task]);

  const osAppResult = job?.osAppResult ?? null;
  const verifier = job?.verifier ?? null;
  const trace = job?.trace ?? null;
  const instructionView = useCockpitInstruction({
    taskPath: task?.taskPath ?? null,
    fallbackTitle: task?.title ?? null,
    harborJobName,
    harborTrialName,
    enabled: phase !== "idle",
  });
  const failed = phase === "error" || phase === "timeout" || job?.status === "error";
  const displayError = formatCockpitRunError(error ?? job?.error ?? null);
  const status = cuaStatusLine(phase, job?.phase, harborPhase);

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

  const taskCards = useMemo(() => osAppTaskCards(tasks), [tasks]);

  const harborLaunchBody = useCallback(
    (targetTask: OsAppEvalTask) => ({
      taskPath: targetTask.taskPath,
      sampleSize: selectedPersonaIds.length,
      seed,
      personaModel,
      agentName: "persona-computer-1",
      osAppBackend: resolveCuaRuntime(targetTask.id, targetTask.platform),
      personaIds: selectedPersonaIds,
      nConcurrentTrials: Math.min(parallelTrials, selectedPersonaIds.length),
      mode: "auto" as const,
      osAppSubmissionProfile: targetTask.osAppSubmissionProfile ?? undefined,
    }),
    [selectedPersonaIds, seed, personaModel, resolveCuaRuntime, parallelTrials],
  );

  const handleRun = useCallback(() => {
    if (!persona || !task || isRunning) return;
    setExportSnapshot(null);
    void run({
      taskPath: task.taskPath,
      personaId: persona.id,
      personaModel,
      agentName: "persona-computer-1",
      osAppBackend: activeCuaRuntime,
      mode: "auto",
      osAppSubmissionProfile: task.osAppSubmissionProfile ?? undefined,
      mapDebrief: (debrief, ctx) =>
        mapOsAppDebriefToJobView(debrief, ctx, {
          personaId: persona.id,
          personaName: persona.name,
          taskId: task.id,
          taskTitle: task.title,
          platform: task.platform,
        }),
    });
  }, [persona, task, isRunning, run, personaModel, activeCuaRuntime]);

  const handleLaunch = useCallback(async () => {
    if (selectedPersonaIds.length === 0 || !task || isRunning) return;
    if (isBatchRun) {
      setLaunchError(null);
      try {
        const launched = await api.launchHarborJob(harborLaunchBody(task));
        setBatchJobName(launched.jobName, { taskId: task.id });
      } catch (exc) {
        const message = exc instanceof ApiError ? exc.message : exc instanceof Error ? exc.message : String(exc);
        setLaunchError(message);
      }
      return;
    }
    handleRun();
  }, [selectedPersonaIds, task, isRunning, isBatchRun, harborLaunchBody, handleRun]);

  const handleNewRun = useCallback(() => {
    reset();
    clearBatch();
    setLaunchError(null);
  }, [reset, clearBatch]);

  const { onCancelRun, cancelRunBusy } = useCockpitRunCancel({
    batchJobName,
    batchComplete,
    cancelBatch,
    batchCancelBusy: cancelBusy,
    harborJobName,
    isRunning,
    cancelRun,
    harborCancelBusy,
    setError: setLaunchError,
  });

  const handleRetry = useCallback(() => {
    if (timedOut || phase === "error") retry();
    else handleRun();
  }, [timedOut, phase, retry, handleRun]);

  const handleExport = useCallback(() => {
    if (!exportSnapshot || !osAppResult) return;
    const payload = {
      applicationType: "os-app",
      config: exportSnapshot,
      osAppResult,
      trace,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `os-app-eval-${exportSnapshot.persona?.id ?? "run"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [exportSnapshot, osAppResult, trace]);

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
          ? Math.min(95, stepCount * 12)
          : phase === "running"
            ? 20
            : 0;
  const runProgressLabel = batchJobName
    ? formatBatchProgressLabel(
        batchLive.live?.completedTrials ?? 0,
        expectedTrialCount,
      )
    : phase === "launching"
      ? "Launching OS app trial…"
      : phase === "running"
        ? stepCount > 0
          ? `Desktop agent · ${stepCount} step${stepCount === 1 ? "" : "s"}`
          : (status ?? "Persona agent is using the desktop…")
        : phase === "done"
          ? `OS app complete · ${stepCount} steps`
          : failed
            ? "OS app trial failed"
            : undefined;
  const canExport = exportSnapshot !== null && osAppResult !== null;

  const osAppLiveContent = (
    <>
      <OsAppResults
        task={task}
        osAppResult={osAppResult}
        trace={trace}
        phase={phase}
        status={status}
        error={displayError}
        onRetry={handleRetry}
        harborJobName={harborJobName}
        harborTrialName={harborTrialName}
      />
    </>
  );

  const cockpitView = (
    <CockpitSetupShell
      header={<RunHeader taskType={taskType} onTaskTypeChange={onTaskTypeChange} />}
      left={
        <PersonaSamplingRail
          taskType="os-app"
          personaModel={personaModel}
          onPersonaModelChange={setPersonaModel}
          personaModelOptions={cuaPersonaModelOptions}
          mode={samplingMode}
          onModeChange={setSamplingMode}
          selectedPersonaIds={visiblePersonaIds}
          onSelectedPersonaIdsChange={setSelectedPersonaIds}
          sampleSize={sampleSize}
          onSampleSizeChange={setSampleSize}
          seed={seed}
          filters={groupFilters}
          onFiltersChange={setGroupFilters}
          stratifyFields={stratifyFields}
          onStratifyFieldsChange={setStratifyFields}
          disabled={setupLocked}
        />
      }
      center={
        <CockpitRunCenter
          showLive={showLiveCenter}
          pipeline={
            <CockpitPipelineDiagram
              className="h-full"
              taskType="os-app"
              cuaPlatform={task?.platform}
              personaModelLabel={pipelinePersonaModelLabel}
              hasPersona={visiblePersonaIds.length > 0}
              hasTask={Boolean(task)}
            />
          }
          liveContent={osAppLiveContent}
          batchJobName={batchJobName}
          batchCells={batchGridCells}
          runLaunchPhase={runLaunchPhase}
          progressPct={runProgressPct}
          progressLabel={runProgressLabel}
          progressSublabel={
            batchJobName && batchComplete ? BATCH_RUN_COMPLETE_HINT : undefined
          }
          canRun={visiblePersonaIds.length > 0 && Boolean(task) && !runBusy}
          isBatch={isBatchRun}
          personaCount={visiblePersonaIds.length}
          parallelTrials={parallelTrials}
          onParallelTrialsChange={setParallelTrials}
          runBusy={runBusy}
          onRun={() => void handleLaunch()}
          error={
            launchError ??
            batchLive.error ??
            (failed && !batchJobName ? null : displayError)
          }
          onNewRun={showLiveCenter ? handleNewRun : undefined}
          onCancelRun={onCancelRun}
          cancelRunBusy={cancelRunBusy}
          onViewJob={
            batchJobName && batchComplete && onOpenHarborJob
              ? () => onOpenHarborJob(batchJobName)
              : !batchJobName && harborJobName && harborTrialName && onOpenHarborTrial
                ? () => onOpenHarborTrial(harborJobName, harborTrialName)
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
              <OsAppEvalScorecard
                osAppResult={osAppResult}
                verifier={verifier}
                traceStepCount={trace?.events?.length ?? 0}
                phase={phase}
              />
            }
            instruction={
              <InstructionPanel
                title={instructionView.title}
                markdown={instructionView.instructionMarkdown ?? instructionView.markdown}
                loading={instructionView.loading}
                error={instructionView.error}
              />
            }
            context={
              <InstructionPanel
                label="Task context"
                title={instructionView.title}
                markdown={instructionView.contextMarkdown}
                loading={instructionView.loading}
                error={instructionView.error}
                emptyMessage="No separate context document is available for this task."
                icon="menu_book"
              />
            }
          />
        ) : (
        <TaskSelectionRail
          taskType="os-app"
          chatTasks={[]}
          surveyTasks={[]}
          webTasks={[]}
          cuaTasks={taskCards}
          selectedTaskId={activeTaskId}
          onSelectTask={(card) => setTaskId(card.id)}
          engine=""
          onEngineChange={() => undefined}
          engineOptions={[]}
          domain=""
          onDomainChange={() => undefined}
          domainOptions={[]}
          maxTurns={8}
          onMaxTurnsChange={() => undefined}
          resolveCuaRuntime={resolveCuaRuntime}
          onCuaRuntimeChange={(id, runtime) =>
            setCuaRuntimeByTaskId((prev) => ({ ...prev, [id]: runtime }))
          }
          tasksLoading={tasksQuery.isLoading}
          tasksError={
            tasks.length === 0
              ? tasksQuery.isError
                ? "OS app task API unavailable — restart PersonaEval backend (uvicorn backend.api.app:app on :8765)."
                : "No OS app tasks available."
              : null
          }
          disabled={setupLocked}
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


function OsAppResults({
  task,
  osAppResult,
  trace,
  phase,
  status,
  error,
  onRetry,
  harborJobName,
  harborTrialName,
}: {
  task: OsAppEvalTask | null;
  osAppResult: OsAppResult | null;
  trace: WebTrace | null;
  phase: HarborCockpitPhase;
  status: string | null;
  error: string | null;
  onRetry: () => void;
  harborJobName: string | null;
  harborTrialName: string | null;
}) {
  const running = phase === "launching" || phase === "running";
  const failed = phase === "error" || phase === "timeout";
  const recordingUrl =
    harborJobName && harborTrialName
      ? harborTrialRecordingUrl(harborJobName, harborTrialName)
      : null;
  const [recordingAvailable, setRecordingAvailable] = useState(Boolean(recordingUrl));

  useEffect(() => {
    setRecordingAvailable(Boolean(recordingUrl));
  }, [recordingUrl]);

  if (running && !osAppResult) {
    return (
      <div className="rounded-md border border-outline bg-surface-lowest p-5">
        <p className="text-[12px] font-semibold text-text-main">{status ?? "Running computer-use trial…"}</p>
        {task && <p className="mt-2 text-[12px] text-text-variant">{task.description}</p>}
      </div>
    );
  }

  if (failed) {
    const useComputerHint =
      (task?.platform === "macos" || task?.platform === "ios") &&
      (error?.includes("exit code") || error?.includes("environment definition"))
        ? " macOS and iOS tasks run on use.computer — set USE_COMPUTER_API_KEY (and ANTHROPIC_API_KEY) on the backend."
        : "";
    return (
      <section className="rounded-md border border-danger/30 bg-danger/10 p-5">
        <div className="flex items-start gap-3">
          <Sym name="error" fill={1} size={20} className="mt-0.5 text-danger" />
          <div>
            <h2 className="font-semibold text-text-main">OS app trial failed</h2>
            <p className="mt-1 text-[13px] text-text-variant">
              {error ?? "The trial did not finish."}
              {useComputerHint}
            </p>
            <button
              type="button"
              onClick={onRetry}
              className={`mt-3 inline-flex items-center gap-1.5 rounded-md border border-danger/40 px-3 py-1.5 text-[12px] font-medium text-danger hover:bg-danger/10 ${FOCUS_RING}`}
            >
              <Sym name="refresh" size={15} />
              Try again
            </button>
          </div>
        </div>
      </section>
    );
  }

  if (!osAppResult) {
    return (
      <section className="rounded-md border border-outline bg-surface-lowest p-5">
        <p className="text-[13px] text-text-variant">Waiting for OS app artifacts…</p>
      </section>
    );
  }

  return (
    <div className="space-y-4">
      {recordingUrl && recordingAvailable && (
        <section className="rounded-md border border-outline bg-surface-lowest p-4">
          <div className="hud mb-2 flex items-center gap-2 text-[9px] text-primary">
            <Sym name="videocam" size={14} />
            Session recording
          </div>
          <video
            src={recordingUrl}
            controls
            playsInline
            preload="metadata"
            className="max-h-[360px] w-full rounded-md border border-outline bg-black object-contain"
            onError={() => setRecordingAvailable(false)}
          />
        </section>
      )}
      {osAppResult.artifact && (
        <section className="rounded-md border border-outline bg-surface-lowest p-4">
          <div className="hud mb-2 text-[9px] text-text-dim">
            Output · {osAppResult.artifactName ?? task?.outputArtifact ?? "artifact"}
          </div>
          <pre className="custom-scrollbar max-h-80 overflow-auto rounded-md bg-surface p-3 font-mono text-[11px] text-text-main">
            {JSON.stringify(osAppResult.artifact, null, 2)}
          </pre>
        </section>
      )}
      {trace && trace.events.length > 0 && (
        <section className="rounded-md border border-outline bg-surface-lowest p-4">
          <div className="hud mb-3 flex items-center gap-2 text-[10px] text-primary">
            <Sym name="route" size={14} />
            Desktop trace · {trace.events.length} step{trace.events.length === 1 ? "" : "s"}
          </div>
          <HarborTraceReplay
            trace={trace}
            autoFollowLatest={running}
            emptyMessage="This run finished without step screenshots."
          />
        </section>
      )}
    </div>
  );
}

export default OsAppEvalCockpit;
