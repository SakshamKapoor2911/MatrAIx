/**
 * CuaEvalCockpit: Harbor computer-use (persona-computer-1) tasks from MatrAIx
 * example-computer-use-* and example-web-cua_* — not AppWorld.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { listCuaEvalTasks, api, ApiError } from "@/lib/api";
import { FALLBACK_CUA_TASKS } from "@/lib/fallbackTasks";
import { mergeTaskCatalog } from "@/lib/mergeTaskCatalog";
import {
  cuaRuntimeLabel,
  cuaRuntimeOptionsForPlatform,
  suggestedCuaBackend,
} from "@/lib/personaAgentCatalog";
import type {
  ConfigOptionsResponse,
  CuaEvalJobView,
  CuaEvalTask,
  CuaEvalTasksResponse,
  CuaResult,
  WebTrace,
} from "@/lib/types";
import { useHarborCockpitRun, type HarborCockpitPhase } from "@/lib/useHarborCockpitRun";
import { useCockpitInstruction } from "@/lib/useCockpitInstruction";
import { mapCuaDebriefToJobView } from "@/lib/harborCockpitMappers";
import { RunHeader } from "./RunHeader";
import { PersonaDrawer } from "./PersonaDrawer";
import { InspectorTabs, type InspectorTab } from "./InspectorTabs";
import { InstructionPanel } from "./InstructionPanel";
import { CuaEvalScorecard } from "./TaskEvalScorecard";
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
import { cuaTaskCards } from "./setup/cockpitTaskCards";
import { FOCUS_RING, Sym } from "./cockpitShared";
import type { PersonaEvalTaskType } from "./TaskTypeSwitch";

const DEFAULT_AGENT_MODEL = "anthropic/claude-sonnet-4-6";

function mergeCuaTasks(apiTasks: CuaEvalTask[] | undefined): CuaEvalTask[] {
  return mergeTaskCatalog(FALLBACK_CUA_TASKS, apiTasks);
}

export interface CuaEvalCockpitProps {
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
  if (phase === "launching") return "Launching Harbor CUA trial…";
  if (phase !== "running") return null;
  const raw = (harborPhase ?? jobPhase ?? "").toLowerCase();
  if (raw.includes("harbor") || raw.includes("trial")) return "Harbor is running the computer-use trial…";
  if (raw.includes("collect")) return "Saving CUA artifacts and trajectory…";
  return "The persona agent is using the desktop…";
}

export function CuaEvalCockpit({
  options,
  taskType,
  onTaskTypeChange,
  onFooterContextChange,
  onOpenHarborJob,
  isActive = true,
}: CuaEvalCockpitProps) {
  const { run, job, phase, isRunning, error, timedOut, retry, reset, harborPhase, harborJobName, harborTrialName } =
    useHarborCockpitRun<CuaEvalJobView>();
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
  const [taskId, setTaskId] = useState("");
  const [cuaRuntimeByTaskId, setCuaRuntimeByTaskId] = useState<Record<string, string>>({});
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

  const tasksQuery = useQuery<CuaEvalTasksResponse>({
    queryKey: ["cua-eval-tasks"],
    queryFn: listCuaEvalTasks,
    staleTime: 10 * 60_000,
    retry: 1,
  });
  const tasks = useMemo(
    () => mergeCuaTasks(tasksQuery.data?.tasks),
    [tasksQuery.data?.tasks],
  );
  const task = tasks.find((item) => item.id === taskId) ?? tasks[0] ?? null;

  useEffect(() => {
    if (!task && tasks.length > 0) setTaskId(tasks[0].id);
  }, [task, tasks]);

  const resolveCuaRuntime = useCallback(
    (id: string, platform?: string) => {
      const row = tasks.find((item) => item.id === id);
      const base = row?.cuaBackend ?? suggestedCuaBackend(platform ?? "linux");
      return cuaRuntimeByTaskId[id] ?? base;
    },
    [cuaRuntimeByTaskId, tasks],
  );
  const activeCuaRuntime = task ? resolveCuaRuntime(task.id, task.platform) : "docker";

  useEffect(() => {
    if (!isActive) return;
    onFooterContextChange?.(`cua · ${task?.platform ?? "desktop"} · ${task?.title ?? "task"}`);
  }, [isActive, onFooterContextChange, task]);

  const cuaResult = job?.cuaResult ?? null;
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

  const taskCards = useMemo(() => cuaTaskCards(tasks), [tasks]);

  const harborLaunchBody = useCallback(
    (targetTask: CuaEvalTask) => ({
      taskPath: targetTask.taskPath,
      sampleSize: selectedPersonaIds.length,
      seed,
      personaModel,
      agentName: "persona-computer-1",
      cuaBackend: resolveCuaRuntime(targetTask.id, targetTask.platform),
      personaIds: selectedPersonaIds,
      nConcurrentTrials: Math.min(parallelTrials, selectedPersonaIds.length),
      mode: "auto" as const,
      cuaSubmissionProfile: targetTask.cuaSubmissionProfile ?? undefined,
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
      cuaBackend: activeCuaRuntime,
      mode: "auto",
      cuaSubmissionProfile: task.cuaSubmissionProfile ?? undefined,
      mapDebrief: (debrief, ctx) =>
        mapCuaDebriefToJobView(debrief, ctx, {
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
        setBatchJobName(launched.jobName);
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

  const handleRetry = useCallback(() => {
    if (timedOut || phase === "error") retry();
    else handleRun();
  }, [timedOut, phase, retry, handleRun]);

  const handleExport = useCallback(() => {
    if (!exportSnapshot || !cuaResult) return;
    const payload = {
      applicationType: "cua",
      config: exportSnapshot,
      cuaResult,
      trace,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cua-eval-${exportSnapshot.persona?.id ?? "run"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [exportSnapshot, cuaResult, trace]);

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
    ? `Harbor job · ${batchLive.live?.completedTrials ?? 0}/${expectedTrialCount} trials`
    : phase === "launching"
      ? "Launching CUA trial…"
      : phase === "running"
        ? stepCount > 0
          ? `Desktop agent · ${stepCount} step${stepCount === 1 ? "" : "s"}`
          : (status ?? "Persona agent is using the desktop…")
        : phase === "done"
          ? `CUA complete · ${stepCount} steps`
          : failed
            ? error ?? "The computer-use trial didn't finish."
            : undefined;
  const canExport = exportSnapshot !== null && cuaResult !== null;

  const cuaLiveContent = (
    <>
      <CuaResults
        task={task}
        cuaResult={cuaResult}
        trace={trace}
        phase={phase}
        status={status}
        error={error}
        onRetry={handleRetry}
      />
    </>
  );

  const cockpitView = (
    <CockpitSetupShell
      header={<RunHeader taskType={taskType} onTaskTypeChange={onTaskTypeChange} />}
      left={
        <PersonaSamplingRail
          taskType="cua"
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
              taskType="cua"
              cuaRuntimeLabel={cuaRuntimeLabel(activeCuaRuntime)}
              hasPersona={selectedPersonaIds.length > 0}
              hasTask={Boolean(task)}
            />
          }
          liveContent={cuaLiveContent}
          batchJobName={batchJobName}
          batchCells={batchGridCells}
          runLaunchPhase={runLaunchPhase}
          progressPct={runProgressPct}
          progressLabel={runProgressLabel}
          progressSublabel={
            batchJobName && batchComplete ? "All trials finished — open Runs for debrief." : undefined
          }
          canRun={selectedPersonaIds.length > 0 && Boolean(task) && !runBusy}
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
              <CuaEvalScorecard
                cuaResult={cuaResult}
                verifier={verifier}
                traceStepCount={trace?.events?.length ?? 0}
                phase={phase}
              />
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
          taskType="cua"
          chatOptions={[]}
          selectedChatAppId=""
          onChatAppChange={() => undefined}
          sidecarsByApp={{}}
          sidecarsLoading={false}
          surveyTasks={[]}
          webTasks={[]}
          cuaTasks={taskCards}
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
          resolveCuaRuntime={resolveCuaRuntime}
          onCuaRuntimeChange={(id, runtime) =>
            setCuaRuntimeByTaskId((prev) => ({ ...prev, [id]: runtime }))
          }
          cuaRuntimeOptionsForTask={(platform) => cuaRuntimeOptionsForPlatform(platform ?? "linux")}
          tasksLoading={tasksQuery.isLoading}
          tasksError={
            tasks.length === 0
              ? tasksQuery.isError
                ? "CUA task API unavailable — restart PersonaEval backend (uvicorn backend.api.app:app on :8765)."
                : "No CUA tasks available."
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


function CuaResults({
  task,
  cuaResult,
  trace,
  phase,
  status,
  error,
  onRetry,
}: {
  task: CuaEvalTask | null;
  cuaResult: CuaResult | null;
  trace: WebTrace | null;
  phase: HarborCockpitPhase;
  status: string | null;
  error: string | null;
  onRetry: () => void;
}) {
  const running = phase === "launching" || phase === "running";
  const failed = phase === "error" || phase === "timeout";

  if (running && !cuaResult) {
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
        ? " macOS/iOS CUA runs on use.computer — you need USE_COMPUTER_API_KEY (and ANTHROPIC_API_KEY) in the environment running the backend."
        : "";
    return (
      <section className="rounded-md border border-danger/30 bg-danger/10 p-5">
        <div className="flex items-start gap-3">
          <Sym name="error" fill={1} size={20} className="mt-0.5 text-danger" />
          <div>
            <h2 className="font-semibold text-text-main">CUA trial failed</h2>
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

  if (!cuaResult) {
    return (
      <section className="rounded-md border border-outline bg-surface-lowest p-5">
        <p className="text-[13px] text-text-variant">Waiting for CUA artifacts…</p>
      </section>
    );
  }

  return (
    <div className="space-y-4">
      {cuaResult.artifact && (
        <section className="rounded-md border border-outline bg-surface-lowest p-4">
          <div className="hud mb-2 text-[9px] text-text-dim">
            Output · {cuaResult.artifactName ?? task?.outputArtifact ?? "artifact"}
          </div>
          <pre className="custom-scrollbar max-h-80 overflow-auto rounded-md bg-surface p-3 font-mono text-[11px] text-text-main">
            {JSON.stringify(cuaResult.artifact, null, 2)}
          </pre>
        </section>
      )}
      {trace && trace.events.length > 0 && (
        <section className="rounded-md border border-outline bg-surface-lowest p-4">
          <div className="hud mb-2 text-[9px] text-primary">Trajectory</div>
          <ol className="space-y-2">
            {trace.events.slice(0, 12).map((event, index) => (
              <li key={`${event.step}-${index}`} className="rounded border border-outline bg-surface px-3 py-2 text-[12px] text-text-main">
                <span className="font-mono text-[10px] text-text-dim">Step {event.step}</span>
                <p className="mt-1">{event.message ?? "CUA step"}</p>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

export default CuaEvalCockpit;
