import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { listWebEvalTasks } from "@/lib/api";
import type {
  ConfigOptionsResponse,
  PersonaEvalPersona,
  PersonaModel,
  WebEvalTask,
  WebEvalTasksResponse,
  WebResult,
  WebTrace,
  WebTraceEvent,
} from "@/lib/types";
import { useWebEval, type WebEvalRunPhase } from "@/lib/useWebEval";
import { PersonaCatalog } from "./PersonaCatalog";
import { PersonaDrawer } from "./PersonaDrawer";
import { PersonaPanel } from "./PersonaPanel";
import { PromptPanel } from "./PromptPanel";
import { InspectorTabs, type InspectorTab } from "./InspectorTabs";
import { KnobSelect, type KnobOption } from "./KnobSelect";
import { FOCUS_RING, Sym, personaCodename, personaDescriptiveTitle } from "./cockpitShared";
import { TaskTypeSwitch, type PersonaEvalTaskType } from "./TaskTypeSwitch";

export interface WebEvalCockpitProps {
  options: ConfigOptionsResponse | null;
  taskType: PersonaEvalTaskType;
  onTaskTypeChange: (value: PersonaEvalTaskType) => void;
}

function optionsFor(options: ConfigOptionsResponse | null, key: string): KnobOption[] {
  const knob = options?.knobs.find((item) => item.key === key);
  return knob
    ? knob.options.map((item) => ({
        value: item.value,
        label: item.label,
        description: item.description,
      }))
    : [];
}

function webStatusLine(phase: WebEvalRunPhase, jobPhase: string | null | undefined): string | null {
  if (phase === "building") return "Preparing the website test environment...";
  if (phase !== "running") return null;
  const raw = (jobPhase ?? "").toLowerCase();
  if (raw.includes("collect")) return "Collecting website artifact and browser trace...";
  if (raw.includes("harbor")) return "Persona agent is using the website...";
  return "Running the website test...";
}

export function WebEvalCockpit({ options, taskType, onTaskTypeChange }: WebEvalCockpitProps) {
  const { run, job, phase, isRunning, error, timedOut, retry } = useWebEval();
  const [persona, setPersona] = useState<PersonaEvalPersona | null>(null);
  const [personaModel, setPersonaModel] = useState<string>(
    options?.environment.personaModel ?? "anthropic/claude-haiku-4-5",
  );
  const [taskId, setTaskId] = useState<string>("web-ecommerce-platform_product-discovery");
  const [tab, setTab] = useState<InspectorTab>("evaluation");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [exportSnapshot, setExportSnapshot] = useState<{
    persona: { id: string; name: string; source: string } | null;
    taskId: string;
    personaModel: string;
  } | null>(null);

  const adoptedDefaults = useRef(false);
  useEffect(() => {
    if (adoptedDefaults.current || !options) return;
    adoptedDefaults.current = true;
    setPersonaModel(options.environment.personaModel ?? "anthropic/claude-haiku-4-5");
  }, [options]);

  const tasksQuery = useQuery<WebEvalTasksResponse>({
    queryKey: ["web-eval-tasks"],
    queryFn: listWebEvalTasks,
    staleTime: 10 * 60_000,
    refetchOnWindowFocus: false,
  });
  const tasks = tasksQuery.data?.tasks ?? [];
  const task = tasks.find((item) => item.id === taskId) ?? tasks[0] ?? null;

  useEffect(() => {
    if (!task && tasks.length > 0) setTaskId(tasks[0].id);
  }, [task, tasks]);

  const webResult = job?.webResult ?? null;
  const trace = job?.trace ?? null;
  const prompts = job?.prompts ?? null;
  const hasRun = phase === "done" || phase === "error" || phase === "timeout";
  const status = webStatusLine(phase, job?.phase);
  const title = persona
    ? personaDescriptiveTitle(null, persona.blurb, persona.source)
    : "No persona selected";
  const codename = persona ? personaCodename(persona.name, persona.id) : null;

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

  const taskOptions: KnobOption[] = tasks.map((item) => ({
    value: item.id,
    label: item.title,
    description: item.description,
  }));
  const personaModelOptions = optionsFor(options, "personaModel");

  const handleRun = useCallback(() => {
    if (!persona || !task || isRunning) return;
    setExportSnapshot(null);
    run({
      personaId: persona.id,
      taskId: task.id,
      personaModel: personaModel as PersonaModel,
    });
  }, [persona, task, isRunning, run, personaModel]);

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
      prompts,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `web-eval-${exportSnapshot.persona?.id ?? "run"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [exportSnapshot, webResult, trace, prompts]);

  return (
    <div className="flex flex-1 flex-col overflow-y-auto lg:flex-row lg:overflow-hidden">
      <PersonaCatalog selectedId={persona?.id ?? null} onSelect={setPersona} />

      <main className="relative z-0 flex min-h-[640px] min-w-0 flex-1 flex-col bg-background lg:min-h-0">
        <TaskTypeSwitch value={taskType} onChange={onTaskTypeChange} disabled={isRunning} />
        <div className="flex flex-shrink-0 items-center justify-between border-b border-border-soft bg-surface-container-lowest px-lg py-sm">
          <div className="flex min-w-0 items-center gap-3">
            <h1 className="truncate text-display font-display text-on-surface">{title}</h1>
            {codename && (
              <span className="flex-shrink-0 rounded bg-surface-container px-2 py-1 font-mono-sm text-mono-sm text-on-surface-variant">
                {codename}
              </span>
            )}
          </div>
          <div className="flex flex-shrink-0 items-center gap-3">
            <button
              type="button"
              onClick={handleExport}
              disabled={!exportSnapshot || !webResult}
              className={`flex items-center gap-2 rounded-md border border-outline-variant px-4 py-2 text-label-md font-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              <Sym name="download" size={18} />
              Export log
            </button>
            <button
              type="button"
              onClick={handleRun}
              disabled={!persona || !task || isRunning}
              className={`flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-label-md font-label-md text-on-primary shadow-sm transition-colors hover:bg-primary-container disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              {isRunning ? (
                <Sym name="autorenew" size={18} className="animate-rb-spin" />
              ) : (
                <Sym name="play_arrow" fill={1} size={18} />
              )}
              {isRunning ? "Running..." : hasRun ? "Re-run website test" : "Run website test"}
            </button>
          </div>
        </div>

        <WebConfigBar
          taskId={taskId}
          taskOptions={taskOptions}
          onTask={setTaskId}
          personaModel={personaModel}
          personaModelOptions={personaModelOptions}
          onPersonaModel={setPersonaModel}
          disabled={isRunning}
        />
        <WebPipeline
          phase={phase}
          jobPhase={job?.phase}
          hasPersona={persona !== null}
          hasResult={webResult !== null}
          hasTrace={trace !== null}
          personaModel={personaModel}
          task={task}
        />
        <WebWorkspace
          task={task}
          webResult={webResult}
          trace={trace}
          phase={phase}
          status={status}
          error={error}
          hasPersona={persona !== null}
          onRetry={handleRetry}
        />
      </main>

      <InspectorTabs
        active={tab}
        onChange={setTab}
        evaluation={<WebResults result={webResult} trace={trace} phase={phase} />}
        persona={<PersonaPanel persona={persona} context={null} onOpenRaw={() => setDrawerOpen(true)} />}
        prompts={<PromptPanel prompts={prompts} />}
      />

      <PersonaDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} persona={persona} context={null} />
    </div>
  );
}

function WebConfigBar({
  taskId,
  taskOptions,
  onTask,
  personaModel,
  personaModelOptions,
  onPersonaModel,
  disabled,
}: {
  taskId: string;
  taskOptions: KnobOption[];
  onTask: (value: string) => void;
  personaModel: string;
  personaModelOptions: KnobOption[];
  onPersonaModel: (value: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-x-5 gap-y-2 border-b border-border-soft bg-surface-container-lowest px-lg py-2.5 shadow-sm">
      {taskOptions.length > 0 && (
        <KnobSelect
          label="Website task"
          value={taskId}
          options={taskOptions}
          onChange={onTask}
          disabled={disabled}
          accent
        />
      )}
      {personaModelOptions.length > 0 && (
        <KnobSelect
          label="Persona model"
          value={personaModel}
          options={personaModelOptions}
          onChange={onPersonaModel}
          disabled={disabled}
        />
      )}
    </div>
  );
}

function WebPipeline({
  phase,
  jobPhase,
  hasPersona,
  hasResult,
  hasTrace,
  personaModel,
  task,
}: {
  phase: WebEvalRunPhase;
  jobPhase: string | null | undefined;
  hasPersona: boolean;
  hasResult: boolean;
  hasTrace: boolean;
  personaModel: string;
  task: WebEvalTask | null;
}) {
  const running = phase === "building" || phase === "running";
  const failed = phase === "error" || phase === "timeout";
  const rawPhase = (jobPhase ?? "").toLowerCase();
  const nodes = [
    {
      key: "persona",
      label: "Persona",
      owner: "Persona task runtime",
      detail: `${personaModel} | browser/computer-use persona`,
      icon: "badge",
      status: !hasPersona ? "Select persona" : failed ? "Interrupted" : phase === "done" ? "Complete" : running && rawPhase.includes("harbor") ? "Active" : "Ready",
      tone: !hasPersona ? "idle" : failed ? "error" : phase === "done" ? "done" : running ? "active" : "idle",
    },
    {
      key: "website",
      label: "Website",
      owner: task?.siteName ?? "Website host",
      detail: task ? `${task.title} | ${task.siteUrl}` : "Load website task",
      icon: "language",
      status: failed ? "Check run" : phase === "done" ? "Complete" : running ? "Being tested" : "Ready",
      tone: failed ? "error" : phase === "done" ? "done" : running ? "active" : "idle",
    },
    {
      key: "trace",
      label: "Trace",
      owner: "Harbor browser trajectory",
      detail: "actions + messages + raw browser trace",
      icon: "route",
      status: failed ? "Check trace" : hasTrace ? "Available" : running ? "Recording" : "Waiting",
      tone: failed ? "error" : hasTrace ? "done" : running ? "active" : "idle",
    },
    {
      key: "feedback",
      label: "Evaluation",
      owner: "Persona self-report",
      detail: "need satisfaction + ease of use + UX rating",
      icon: "rate_review",
      status: failed ? "Missing artifact" : hasResult ? "Available" : running ? "Waiting" : "Waiting",
      tone: failed ? "error" : hasResult ? "done" : "idle",
    },
  ] as const;

  return (
    <section aria-label="Web component pipeline" className="border-b border-border-soft bg-surface-container-lowest px-lg py-2.5">
      <div className="grid grid-cols-1 gap-2 2xl:grid-cols-4">
        {nodes.map((node, index) => (
          <div key={node.key} className="flex min-w-0 items-center gap-2">
            <div className="flex min-w-0 flex-1 items-start gap-2 rounded-md border border-border-soft bg-surface-container-low px-3 py-2">
              <div className={`mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded border ${toneClass(node.tone)}`}>
                <Sym name={node.icon} size={16} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate text-label-md font-label-md uppercase tracking-wider text-on-surface">{node.label}</p>
                  <span className={`shrink-0 rounded border px-1.5 py-0.5 text-[11px] font-medium ${toneClass(node.tone)}`}>
                    {node.status}
                  </span>
                </div>
                <p className="mt-0.5 truncate font-mono-sm text-mono-sm text-on-surface">{node.owner}</p>
                <p className="mt-1 text-body-sm leading-snug text-on-surface-variant">{node.detail}</p>
              </div>
            </div>
            {index < nodes.length - 1 && (
              <Sym name="arrow_forward" size={17} className="hidden flex-shrink-0 text-outline 2xl:inline-flex" />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

type PipelineTone = "idle" | "active" | "done" | "error";

function toneClass(tone: PipelineTone): string {
  if (tone === "active") return "border-primary/35 bg-primary-container/45 text-primary";
  if (tone === "done") return "border-success/30 bg-success-container/55 text-on-success-container";
  if (tone === "error") return "border-error/30 bg-error-container/55 text-on-error-container";
  return "border-border-soft bg-surface-container text-on-surface-variant";
}

function WebWorkspace({
  task,
  webResult,
  trace,
  phase,
  status,
  error,
  hasPersona,
  onRetry,
}: {
  task: WebEvalTask | null;
  webResult: WebResult | null;
  trace: WebTrace | null;
  phase: WebEvalRunPhase;
  status: string | null;
  error: string | null;
  hasPersona: boolean;
  onRetry: () => void;
}) {
  const running = phase === "building" || phase === "running";
  const failed = phase === "error" || phase === "timeout" || (!running && !!error);

  if (!hasPersona && phase === "idle") {
    return (
      <div className="custom-scrollbar flex flex-1 items-center justify-center overflow-y-auto p-lg">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
            <Sym name="language" fill={1} size={26} className="text-primary" />
          </div>
          <h3 className="text-headline-md font-headline-md text-on-surface">Pick a persona to begin</h3>
          <p className="mx-auto mt-2 max-w-sm text-body-md leading-relaxed text-on-surface-variant">
            Choose a persona and a website task, then run the browser test to collect the trace and experience rating.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="custom-scrollbar flex flex-1 justify-center overflow-y-auto p-lg">
      <div className="flex w-full max-w-5xl flex-col gap-md">
        {task && <WebsiteTaskCard task={task} />}
        {running && (
          <div className="flex items-center justify-center gap-2 rounded-lg border border-border-soft bg-surface-container-lowest px-4 py-4">
            <Sym name="autorenew" size={18} className="animate-rb-spin text-primary" />
            <span className="text-body-sm text-on-surface-variant">{status ?? "Running the website test..."}</span>
          </div>
        )}
        {failed && (
          <div className="rounded-lg border border-error/40 bg-error-container/40 p-4">
            <div className="flex items-start gap-3">
              <Sym name="error" fill={1} size={20} className="mt-0.5 text-error" />
              <div className="min-w-0 flex-1">
                <h4 className="text-body-md font-semibold text-on-surface">This website test did not finish</h4>
                <p className="mt-1 break-words text-body-sm leading-relaxed text-on-surface-variant">
                  {error ?? "The website test stopped unexpectedly. Your configuration is unchanged."}
                </p>
                <button
                  type="button"
                  onClick={onRetry}
                  className={`mt-3 inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-label-md font-label-md text-on-primary shadow-sm transition-colors hover:bg-primary-container ${FOCUS_RING}`}
                >
                  <Sym name="refresh" size={16} />
                  Retry
                </button>
              </div>
            </div>
          </div>
        )}
        {webResult && <WebArtifact result={webResult} />}
        {trace && <WebTracePanel trace={trace} />}
      </div>
    </div>
  );
}

function WebsiteTaskCard({ task }: { task: WebEvalTask }) {
  return (
    <section className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
      <div className="border-b border-border-soft bg-surface-container-low px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-headline-sm font-headline-sm text-on-surface">{task.siteName}</h3>
            <p className="mt-1 text-body-sm text-on-surface-variant">{task.description}</p>
          </div>
          <span className="flex-shrink-0 rounded border border-border-soft bg-surface-container px-2 py-1 font-mono-sm text-mono-sm text-on-surface-variant">
            {task.id}
          </span>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 px-4 py-3 md:grid-cols-3">
        <InfoTile label="Website URL" value={task.siteUrl} />
        <InfoTile label="Output artifact" value={task.outputArtifact} />
        <InfoTile label="Trace source" value="Harbor browser trajectory" />
      </div>
    </section>
  );
}

function WebArtifact({ result }: { result: WebResult }) {
  return (
    <section className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
      <div className="flex items-center justify-between border-b border-border-soft bg-surface-container-low px-4 py-3">
        <div>
          <h3 className="text-headline-sm font-headline-sm text-on-surface">Website evaluation artifact</h3>
          <p className="mt-1 text-body-sm text-on-surface-variant">
            Selected {result.selectedProductName} ({result.selectedProductId})
          </p>
        </div>
        <span className={`rounded border px-2 py-1 text-label-md font-label-md ${result.valid ? "border-success/40 bg-success-container text-on-success-container" : "border-error/40 bg-error-container text-on-error-container"}`}>
          {result.valid ? "Valid" : "Invalid"}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-3 px-4 py-3 md:grid-cols-3">
        <MetricTile value={`${result.needSatisfaction}/10`} caption="Need fit" />
        <MetricTile value={`${result.easeOfUse}/10`} caption="Ease of use" />
        <MetricTile value={`${result.overallExperienceRating}/10`} caption="Overall UX" />
      </div>
      <p className="border-t border-border-soft px-4 py-3 text-body-md leading-relaxed text-on-surface-variant">
        {result.reason}
      </p>
    </section>
  );
}

function WebTracePanel({ trace }: { trace: WebTrace }) {
  return (
    <section className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
      <div className="border-b border-border-soft bg-surface-container-low px-4 py-3">
        <h3 className="text-headline-sm font-headline-sm text-on-surface">Website trace</h3>
        <p className="mt-1 text-body-sm text-on-surface-variant">
          {trace.events.length} preserved browser-agent events.
        </p>
      </div>
      <div className="max-h-96 divide-y divide-border-soft overflow-auto">
        {trace.events.map((event) => (
          <TraceEventRow key={event.step} event={event} />
        ))}
      </div>
    </section>
  );
}

function WebResults({
  result,
  trace,
  phase,
}: {
  result: WebResult | null;
  trace: WebTrace | null;
  phase: WebEvalRunPhase;
}) {
  const running = phase === "building" || phase === "running";
  if (running && !result) {
    return (
      <div className="space-y-3 p-md" aria-hidden>
        <div className="h-20 animate-rb-pulse rounded-xl bg-surface-container" />
        <div className="h-20 animate-rb-pulse rounded-xl bg-surface-container" />
        <div className="h-20 animate-rb-pulse rounded-xl bg-surface-container" />
      </div>
    );
  }
  if (!result) {
    return (
      <div className="p-md">
        <div className="rounded-xl border border-dashed border-border-soft bg-surface-container-low px-4 py-10 text-center">
          <Sym name="language" size={28} className="text-outline" />
          <p className="mt-2 text-body-sm leading-relaxed text-on-surface-variant">
            Run a website test to see UX scores, selected item, and trace here.
          </p>
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-3 p-md">
      <section className="rounded-xl border border-border-soft bg-surface-container-lowest p-3 shadow-soft">
        <div className="flex items-center justify-between">
          <h3 className="text-headline-sm font-headline-sm uppercase tracking-wider text-on-surface">Website result</h3>
          <Sym name="verified" fill={1} size={18} className={result.valid ? "text-success" : "text-error"} />
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2">
          <MetricTile value={`${result.needSatisfaction}/10`} caption="Need fit" />
          <MetricTile value={`${result.easeOfUse}/10`} caption="Ease" />
          <MetricTile value={`${result.overallExperienceRating}/10`} caption="Overall" />
        </div>
      </section>
      <section className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
        <div className="border-b border-border-soft bg-surface-container-low px-3 py-2">
          <h3 className="text-headline-sm font-headline-sm text-on-surface">Selected item</h3>
        </div>
        <div className="px-3 py-3">
          <p className="font-mono-sm text-mono-sm text-primary">{result.selectedProductId}</p>
          <p className="mt-1 text-body-md text-on-surface">{result.selectedProductName}</p>
          <p className="mt-2 text-body-sm leading-relaxed text-on-surface-variant">{result.reason}</p>
        </div>
      </section>
      {trace && (
        <section className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
          <div className="border-b border-border-soft bg-surface-container-low px-3 py-2">
            <h3 className="text-headline-sm font-headline-sm text-on-surface">Trace</h3>
          </div>
          <div className="max-h-72 divide-y divide-border-soft overflow-auto">
            {trace.events.map((event) => (
              <TraceEventRow key={event.step} event={event} compact />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function TraceEventRow({ event, compact }: { event: WebTraceEvent; compact?: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const message = event.message.trim();
  const hasScreenshot = Boolean(event.screenshotUrl);
  const hasDetails = hasScreenshot || message || event.actions.length > 0;

  return (
    <div className={compact ? "px-3 py-2" : "px-4 py-3"}>
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        className={`flex w-full items-start gap-2 rounded-md text-left transition-colors hover:bg-surface-container-low ${FOCUS_RING} ${compact ? "p-1.5" : "p-2"}`}
        aria-expanded={expanded}
        disabled={!hasDetails}
      >
        <Sym
          name={expanded ? "expand_more" : "chevron_right"}
          size={18}
          className="mt-0.5 flex-shrink-0 text-on-surface-variant"
        />
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center justify-between gap-2">
            <span className="truncate text-body-sm font-medium text-on-surface">
              Step {event.step} | {event.source || "agent"}
            </span>
            <span className="flex-shrink-0 font-mono-sm text-mono-sm text-on-surface-variant">
              {event.actions.length} actions
            </span>
          </div>
          {message && !expanded && (
            <p className="mt-1 truncate text-body-sm text-on-surface-variant">{message}</p>
          )}
          {hasScreenshot && !expanded && (
            <div className="mt-1 inline-flex items-center gap-1 rounded border border-border-soft bg-surface-container px-1.5 py-0.5 font-mono-sm text-mono-sm text-on-surface-variant">
              <Sym name="image" size={13} />
              {event.screenshotFile ?? "screenshot"}
            </div>
          )}
        </div>
      </button>
      {expanded && (
        <div className={`mt-2 grid grid-cols-1 gap-3 ${compact ? "" : "lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]"}`}>
          {event.screenshotUrl && (
            <div className="overflow-hidden rounded-md border border-border-soft bg-surface-container-low">
              <img
                src={event.screenshotUrl}
                alt={`Browser screenshot for step ${event.step}`}
                className="aspect-video max-h-80 w-full bg-surface-container-lowest object-contain"
                loading="lazy"
              />
              {event.screenshotFile && (
                <div className="border-t border-border-soft px-2 py-1 font-mono-sm text-mono-sm text-on-surface-variant">
                  {event.screenshotFile}
                </div>
              )}
            </div>
          )}
          <div className="min-w-0 rounded-md border border-border-soft bg-surface-container-low p-2">
            {message && (
              <p className="whitespace-pre-wrap break-words text-body-sm leading-relaxed text-on-surface-variant">
                {message}
              </p>
            )}
            {event.actions.length > 0 && (
              <pre className={`${message ? "mt-2" : ""} max-h-52 overflow-auto whitespace-pre-wrap break-words rounded bg-surface-container-lowest p-2 font-mono-sm text-mono-sm text-on-surface-variant`}>
                {JSON.stringify(event.actions, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricTile({ value, caption }: { value: string; caption: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-border-soft bg-surface-container-low py-2.5">
      <span className="text-headline-md font-headline-md tabular-nums text-on-surface">{value}</span>
      <span className="mt-0.5 text-center text-[10px] uppercase leading-tight tracking-wider text-on-surface-variant">
        {caption}
      </span>
    </div>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-border-soft bg-surface-container-low px-3 py-2">
      <p className="text-[10px] uppercase tracking-wider text-on-surface-variant">{label}</p>
      <p className="mt-1 truncate font-mono-sm text-mono-sm text-on-surface">{value}</p>
    </div>
  );
}

export default WebEvalCockpit;
