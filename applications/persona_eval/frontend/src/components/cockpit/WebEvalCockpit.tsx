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
  if (phase === "building") return "Setting up the website test…";
  if (phase !== "running") return null;
  const raw = (jobPhase ?? "").toLowerCase();
  if (raw.includes("collect")) return "Saving the results and browser recording…";
  if (raw.includes("harbor")) return "The simulated visitor is using the site…";
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
    : "No persona chosen yet";
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

      <main className="relative z-0 flex min-h-[640px] min-w-0 flex-1 flex-col bg-surface-dim lg:min-h-0">
        <TaskTypeSwitch value={taskType} onChange={onTaskTypeChange} disabled={isRunning} />
        <div className="flex flex-shrink-0 items-center justify-between border-b border-outline-dim bg-surface-lowest px-lg py-sm">
          <div className="flex min-w-0 items-center gap-3">
            <h1 className="truncate font-display text-[26px] font-bold tracking-tight text-text-main">{title}</h1>
            {codename && (
              <span className="flex-shrink-0 rounded bg-surface-high px-2 py-1 font-mono text-[11px] text-text-variant">
                {codename}
              </span>
            )}
          </div>
          <div className="flex flex-shrink-0 items-center gap-3">
            <button
              type="button"
              onClick={handleExport}
              disabled={!exportSnapshot || !webResult}
              className={`flex items-center gap-2 rounded-md border border-outline px-4 py-2 text-xs font-medium text-text-variant transition-colors hover:bg-surface-low hover:text-text-main disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              <Sym name="download" size={18} />
              Download results
            </button>
            <button
              type="button"
              onClick={handleRun}
              disabled={!persona || !task || isRunning}
              className={`glow flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-xs font-medium text-on-primary transition-colors hover:bg-primary-dim disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              {isRunning ? (
                <Sym name="autorenew" size={18} className="animate-spin" />
              ) : (
                <Sym name="play_arrow" fill={1} size={18} />
              )}
              {isRunning ? "Working…" : hasRun ? "Run it again" : "Run website test"}
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
        {phase === "idle" && (
          <div className="flex shrink-0 items-start gap-2.5 border-b border-outline-dim bg-primary/10 px-lg py-2.5">
            <Sym name="lightbulb" fill={1} size={16} className="mt-0.5 flex-shrink-0 text-primary" />
            <p className="text-[12px] leading-snug text-text-variant">
              <span className="font-medium text-text-main">New here?</span> Pick a persona and a website task, then
              press Run. PersonaEval plays a simulated visitor who browses the site, and you&apos;ll see each step and
              how it rated the experience.
            </p>
          </div>
        )}
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
          tasksLoading={tasksQuery.isLoading}
          tasksError={tasksQuery.isError}
          onReloadTasks={() => {
            void tasksQuery.refetch();
          }}
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
    <div className="flex shrink-0 flex-wrap items-center gap-x-5 gap-y-2 border-b border-outline-dim bg-surface-lowest px-lg py-2.5">
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
          label="Simulated-user model"
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
      owner: "The simulated user",
      ownerTitle: undefined,
      detail: "Acts as a visitor, clicking and typing in a real browser",
      icon: "badge",
      status: !hasPersona ? "Select persona" : failed ? "Stopped" : phase === "done" ? "Complete" : running && rawPhase.includes("harbor") ? "Active" : "Ready",
      tone: !hasPersona ? "idle" : failed ? "error" : phase === "done" ? "done" : running ? "active" : "idle",
    },
    {
      key: "website",
      label: "Website",
      owner: task?.siteName ?? "Website host",
      ownerTitle: undefined,
      detail: task ? `${task.title} · ${task.siteUrl}` : "Pick a website task",
      icon: "language",
      status: failed ? "Needs a look" : phase === "done" ? "Complete" : running ? "In use" : "Ready",
      tone: failed ? "error" : phase === "done" ? "done" : running ? "active" : "idle",
    },
    {
      key: "trace",
      label: "Browser steps",
      owner: "Browser recording",
      ownerTitle: "Harbor browser trajectory",
      detail: "Every click, keystroke, and screenshot the visitor made",
      icon: "route",
      status: failed ? "Needs a look" : hasTrace ? "Available" : running ? "Recording steps" : "Waiting",
      tone: failed ? "error" : hasTrace ? "done" : running ? "active" : "idle",
    },
    {
      key: "feedback",
      label: "Evaluation",
      owner: "The visitor's own rating",
      ownerTitle: undefined,
      detail: "Whether the site met the need, how easy it was, and the overall experience",
      icon: "rate_review",
      status: failed ? "No rating yet" : hasResult ? "Available" : running ? "Waiting" : "Waiting",
      tone: failed ? "error" : hasResult ? "done" : "idle",
    },
  ] as const;

  return (
    <section aria-label="Web component pipeline" className="border-b border-outline-dim bg-surface-lowest px-lg py-2.5">
      <div className="grid grid-cols-1 gap-2 2xl:grid-cols-4">
        {nodes.map((node, index) => (
          <div key={node.key} className="flex min-w-0 items-center gap-2">
            <div className="flex min-w-0 flex-1 items-start gap-2 rounded-md border border-outline bg-surface-low px-3 py-2">
              <div className={`mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded border ${toneClass(node.tone)}`}>
                <Sym name={node.icon} size={16} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate hud text-[10px] text-text-main">{node.label}</p>
                  <span className={`shrink-0 rounded border px-1.5 py-0.5 hud text-[9px] ${toneClass(node.tone)}`}>
                    {node.status}
                  </span>
                </div>
                <p className="mt-0.5 truncate font-mono text-[11px] text-text-variant" title={node.ownerTitle}>{node.owner}</p>
                <p className="mt-1 line-clamp-2 text-[12px] leading-snug text-text-variant">{node.detail}</p>
                {node.key === "persona" && (
                  <p className="mt-0.5 truncate font-mono text-[10px] text-text-dim" title="Simulated-user model">{personaModel}</p>
                )}
              </div>
            </div>
            {index < nodes.length - 1 && (
              <Sym name="arrow_forward" size={17} className="hidden flex-shrink-0 text-text-dim 2xl:inline-flex" />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

type PipelineTone = "idle" | "active" | "done" | "error";

function toneClass(tone: PipelineTone): string {
  if (tone === "active") return "border-primary/40 bg-primary/10 text-primary";
  if (tone === "done") return "border-secondary/30 bg-secondary/10 text-secondary";
  if (tone === "error") return "border-danger/30 bg-danger/10 text-danger";
  return "border-outline-dim bg-surface-high text-text-dim";
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
  tasksLoading,
  tasksError,
  onReloadTasks,
}: {
  task: WebEvalTask | null;
  webResult: WebResult | null;
  trace: WebTrace | null;
  phase: WebEvalRunPhase;
  status: string | null;
  error: string | null;
  hasPersona: boolean;
  onRetry: () => void;
  tasksLoading: boolean;
  tasksError: boolean;
  onReloadTasks: () => void;
}) {
  const running = phase === "building" || phase === "running";
  const failed = phase === "error" || phase === "timeout" || (!running && !!error);

  if (!hasPersona && phase === "idle") {
    return (
      <div className="custom-scrollbar flex flex-1 items-center justify-center overflow-y-auto p-lg">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-md bg-primary/10">
            <Sym name="language" fill={1} size={26} className="text-primary" />
          </div>
          <h3 className="font-display text-lg font-semibold text-text-main">Choose a persona to start</h3>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-text-variant">
            Pick a persona and a website task, then press Run. A simulated visitor will browse the site; you&apos;ll see
            every step it took and how it rated the experience.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="custom-scrollbar flex flex-1 justify-center overflow-y-auto p-lg">
      <div className="flex w-full max-w-5xl flex-col gap-md">
        {tasksError ? (
          <div className="rounded-md border border-danger/30 bg-danger/10 p-4">
            <div className="flex items-start gap-3">
              <Sym name="error" fill={1} size={20} className="mt-0.5 text-danger" />
              <div className="min-w-0 flex-1">
                <h4 className="font-display text-[15px] font-semibold text-danger">Couldn&apos;t load website tasks</h4>
                <p className="mt-1 break-words text-[13px] leading-relaxed text-text-variant">
                  We couldn&apos;t load the website tasks. Check your connection and try again.
                </p>
                <button
                  type="button"
                  onClick={onReloadTasks}
                  className={`mt-3 inline-flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-3 py-1.5 text-xs font-medium text-danger transition-colors hover:bg-danger/20 ${FOCUS_RING}`}
                >
                  <Sym name="refresh" size={16} />
                  Try again
                </button>
              </div>
            </div>
          </div>
        ) : tasksLoading ? (
          <div className="space-y-2" aria-hidden>
            <p className="hud text-[10px] text-text-dim">Loading website tasks…</p>
            <div className="overflow-hidden rounded-md border border-outline bg-surface">
              <div className="h-14 animate-pulse border-b border-outline bg-surface-high" />
              <div className="grid grid-cols-1 gap-3 px-4 py-3 md:grid-cols-3">
                <div className="h-12 animate-pulse rounded bg-surface-high" />
                <div className="h-12 animate-pulse rounded bg-surface-high" />
                <div className="h-12 animate-pulse rounded bg-surface-high" />
              </div>
            </div>
          </div>
        ) : task ? (
          <WebsiteTaskCard task={task} />
        ) : null}
        {running && (
          <div className="rounded-md border border-outline bg-surface-lowest px-4 py-4">
            <div className="flex items-center gap-2">
              <Sym name="autorenew" size={16} className="animate-spin text-primary" />
              <span className="hud text-[10px] text-primary">Running</span>
            </div>
            <p className="mt-2 text-[13px] text-text-main">Simulated visitor is browsing…</p>
            {status && <p className="mt-0.5 text-[12px] text-text-dim">{status}</p>}
            {trace && trace.events.length > 0 && (
              <p className="mt-2 font-mono text-[11px] text-text-variant">Recorded {trace.events.length} steps so far</p>
            )}
          </div>
        )}
        {failed && (
          <div className="rounded-md border border-danger/30 bg-danger/10 p-4">
            <div className="flex items-start gap-3">
              <Sym name="error" fill={1} size={20} className="mt-0.5 text-danger" />
              <div className="min-w-0 flex-1">
                <h4 className="font-display text-[15px] font-semibold text-danger">The website test didn&apos;t finish</h4>
                <p className="mt-1 break-words text-[13px] leading-relaxed text-text-variant">
                  {error ?? "Something interrupted the test. Your setup is still here — press Try again."}
                </p>
                <button
                  type="button"
                  onClick={onRetry}
                  className={`mt-3 inline-flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-3 py-1.5 text-xs font-medium text-danger transition-colors hover:bg-danger/20 ${FOCUS_RING}`}
                >
                  <Sym name="refresh" size={16} />
                  Try again
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
    <section className="panel overflow-hidden rounded-md border border-outline bg-surface">
      <div className="border-b border-outline px-4 py-3">
        <p className="hud text-[10px] text-text-dim">Website task</p>
        <p className="mt-0.5 text-[11px] text-text-dim">This is the goal the simulated visitor will try to complete.</p>
        <div className="mt-2 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate font-display text-[15px] font-semibold text-text-main">{task.siteName}</h3>
            <p className="mt-1 text-[12px] leading-snug text-text-variant">{task.description}</p>
          </div>
          <span
            title="Task ID"
            className="flex-shrink-0 rounded border border-outline px-1.5 py-0.5 hud text-[8px] text-text-dim"
          >
            {task.id}
          </span>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 px-4 py-3 md:grid-cols-3">
        <InfoTile label="Website URL" value={task.siteUrl} />
        <InfoTile label="Results file" value={task.outputArtifact} />
        <InfoTile label="Recording" value="Browser recording" />
      </div>
    </section>
  );
}

function WebArtifact({ result }: { result: WebResult }) {
  return (
    <section className="panel overflow-hidden rounded-md border border-outline bg-surface">
      <div className="flex items-center justify-between border-b border-outline px-4 py-3">
        <div className="min-w-0">
          <p className="hud text-[10px] text-text-dim">Visit results</p>
          <p className="mt-1 text-[12px] text-text-variant">
            The visitor chose {result.selectedProductName}{" "}
            <span className="font-mono text-[11px] text-text-dim">({result.selectedProductId})</span>
          </p>
        </div>
        <span
          title="Complete means the run produced a full, usable result."
          className={`shrink-0 rounded border px-1.5 py-0.5 hud text-[8px] ${result.valid ? "text-secondary border-secondary/30 bg-secondary/10" : "text-danger border-danger/30 bg-danger/10"}`}
        >
          {result.valid ? "Complete" : "Incomplete"}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-3 px-4 py-3 md:grid-cols-3">
        <MetricTile
          value={`${result.needSatisfaction}`}
          unit="/10"
          caption="Need fit"
          lead
          hint="How well the chosen item met the persona's need (0–10)."
        />
        <MetricTile
          value={`${result.easeOfUse}`}
          unit="/10"
          caption="Ease of use"
          hint="How easy the site was to use (0–10)."
        />
        <MetricTile
          value={`${result.overallExperienceRating}`}
          unit="/10"
          caption="Overall UX"
          hint="The visitor's overall experience rating (0–10)."
        />
      </div>
      <p className="border-t border-outline px-4 py-3 text-[13px] leading-relaxed text-text-variant">
        {result.reason}
      </p>
    </section>
  );
}

function WebTracePanel({ trace }: { trace: WebTrace }) {
  return (
    <section className="panel overflow-hidden rounded-md border border-outline bg-surface">
      <div className="border-b border-outline px-4 py-3">
        <div className="flex items-center gap-2">
          <Sym name="route" size={15} className="text-primary" />
          <p className="hud text-[10px] text-primary">Browser recording</p>
        </div>
        <p className="mt-1 text-[12px] text-text-variant">
          {trace.events.length} steps the visitor took, with screenshots.
        </p>
      </div>
      {trace.events.length === 0 ? (
        <div className="px-4 py-6 text-center text-[12px] text-text-dim">
          This run finished without recording any browser steps.
        </div>
      ) : (
        <div className="max-h-96 divide-y divide-outline-dim overflow-auto">
          {trace.events.map((event) => (
            <TraceEventRow key={event.step} event={event} />
          ))}
        </div>
      )}
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
        <div className="h-20 animate-pulse rounded-md bg-surface-high" />
        <div className="h-20 animate-pulse rounded-md bg-surface-high" />
        <div className="h-20 animate-pulse rounded-md bg-surface-high" />
      </div>
    );
  }
  if (!result) {
    return (
      <div className="p-md">
        <div className="rounded-md border border-dashed border-outline bg-surface-low px-4 py-10 text-center">
          <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
            <Sym name="language" size={22} className="text-primary" />
          </div>
          <p className="text-[13px] leading-relaxed text-text-variant">
            Run a website test to see scores, the chosen item, and the browser recording here.
          </p>
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-3 p-md">
      <section className="panel rounded-md border border-outline bg-surface p-3">
        <div className="flex items-center justify-between">
          <h3 className="hud text-[10px] text-primary">Result summary</h3>
          <Sym name="verified" fill={1} size={18} className={result.valid ? "text-secondary" : "text-danger"} />
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2">
          <MetricTile
            value={`${result.needSatisfaction}`}
            unit="/10"
            caption="Need fit"
            hint="How well the chosen item met the persona's need (0–10)."
          />
          <MetricTile
            value={`${result.easeOfUse}`}
            unit="/10"
            caption="Ease"
            hint="How easy the site was to use (0–10)."
          />
          <MetricTile
            value={`${result.overallExperienceRating}`}
            unit="/10"
            caption="Overall"
            hint="The visitor's overall experience rating (0–10)."
          />
        </div>
      </section>
      <section className="panel overflow-hidden rounded-md border border-outline bg-surface">
        <div className="border-b border-outline px-3 py-2">
          <h3 className="hud text-[10px] text-text-dim">What the visitor chose</h3>
        </div>
        <div className="px-3 py-3">
          <p className="font-mono text-[10px] text-primary">{result.selectedProductId}</p>
          <p className="mt-1 text-[13px] text-text-main">{result.selectedProductName}</p>
          <p className="mt-2 text-[12px] leading-relaxed text-text-variant">{result.reason}</p>
        </div>
      </section>
      {trace && (
        <section className="panel overflow-hidden rounded-md border border-outline bg-surface">
          <div className="border-b border-outline px-3 py-2">
            <h3 className="hud text-[10px] text-text-dim">Browser recording</h3>
          </div>
          <div className="max-h-72 divide-y divide-outline-dim overflow-auto">
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
  const [imgError, setImgError] = useState(false);
  const message = event.message.trim();
  const hasScreenshot = Boolean(event.screenshotUrl);
  const hasDetails = hasScreenshot || message || event.actions.length > 0;
  const actionHint = summarizeAction(event);

  return (
    <div className={`transition-colors hover:bg-surface-high ${compact ? "px-3 py-2" : "px-4 py-3"}`}>
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        className={`flex w-full items-start gap-2 rounded-md text-left transition-colors hover:bg-surface-low ${FOCUS_RING} ${compact ? "p-1.5" : "p-2"}`}
        aria-expanded={expanded}
        disabled={!hasDetails}
      >
        <Sym
          name={expanded ? "expand_more" : "chevron_right"}
          size={18}
          className="mt-0.5 flex-shrink-0 text-text-dim"
        />
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center justify-between gap-2">
            <span className="truncate hud text-[9px] text-text-dim">
              Step {event.step} · {actionHint ?? (event.source || "visitor")}
            </span>
            <span className="flex-shrink-0 font-mono text-[11px] text-text-variant">
              {event.actions.length} action{event.actions.length === 1 ? "" : "s"}
            </span>
          </div>
          {message && !expanded && (
            <p className="mt-1 truncate text-[12px] text-text-variant">{message}</p>
          )}
          {hasScreenshot && !expanded && (
            <div className="mt-1 inline-flex items-center gap-1 rounded border border-outline bg-surface-high px-1.5 py-0.5 hud text-[10px] text-text-dim">
              <Sym name="image" size={13} />
              {event.screenshotFile ?? "screenshot"}
            </div>
          )}
        </div>
      </button>
      {expanded && (
        <div className={`mt-2 grid grid-cols-1 gap-3 ${compact ? "" : "lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]"}`}>
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
                <p className="mt-1 text-[12px] text-text-dim">Screenshot unavailable for this step.</p>
              </div>
            </div>
          ) : null}
          <div className="min-w-0 rounded-md border border-outline bg-surface-low p-2">
            {message && (
              <p className="whitespace-pre-wrap break-words text-[12px] leading-relaxed text-text-variant">
                {message}
              </p>
            )}
            {event.actions.length > 0 && (
              <pre className={`${message ? "mt-2" : ""} max-h-52 overflow-auto whitespace-pre-wrap break-words rounded bg-field p-2 font-mono text-[11px] text-text-variant`}>
                {JSON.stringify(event.actions, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricTile({
  value,
  caption,
  unit,
  lead,
  hint,
}: {
  value: string;
  caption: string;
  unit?: string;
  lead?: boolean;
  hint?: string;
}) {
  return (
    <div
      title={hint}
      className={`rounded-md border border-outline bg-surface p-4 text-center ${lead ? "border-l-4 border-l-secondary" : ""}`}
    >
      <div className="flex items-baseline justify-center gap-0.5">
        <span className="font-display text-[24px] font-bold tabular-nums text-text-main">{value}</span>
        {unit && <span className="font-sans text-[12px] text-text-dim">{unit}</span>}
      </div>
      <span className={`mt-1 block hud text-[9px] ${lead ? "text-secondary" : "text-text-dim"}`}>{caption}</span>
    </div>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded border border-outline bg-surface-low px-3 py-2.5">
      <p className="hud text-[8px] text-text-dim">{label}</p>
      <p className="mt-1 truncate font-mono text-[11px] text-text-main">{value}</p>
    </div>
  );
}

export default WebEvalCockpit;
