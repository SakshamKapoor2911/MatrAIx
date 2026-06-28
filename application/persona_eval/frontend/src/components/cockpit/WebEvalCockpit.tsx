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
import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
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
import { usePersonaDetail } from "@/lib/usePersonaEval";
import { PersonaCatalog } from "./PersonaCatalog";
import { PersonaDrawer } from "./PersonaDrawer";
import { PromptPanel } from "./PromptPanel";
import {
  FOCUS_RING,
  Sym,
  parseDemographics,
  parseDemographicsFromBlurb,
  personaCodename,
  personaDescriptiveTitle,
} from "./cockpitShared";
import { fmtDomain } from "../runsShared";
import type { PersonaEvalTaskType } from "./TaskTypeSwitch";

export interface WebEvalCockpitProps {
  options: ConfigOptionsResponse | null;
  taskType: PersonaEvalTaskType;
  onTaskTypeChange: (value: PersonaEvalTaskType) => void;
  /** Report the honest footer context up (the active website). */
  onFooterContextChange?: (context: string) => void;
}

interface SelectOption {
  value: string;
  label: string;
}

type PipelineTone = "idle" | "active" | "done" | "error";

const SOURCE_TONE: Record<string, string> = {
  Nemotron: "text-secondary border-secondary/30 bg-secondary/10",
  OASIS: "text-primary border-primary/30 bg-primary/10",
  PersonaHub: "text-warn border-warn/30 bg-warn/10",
};
const NEUTRAL_SOURCE_TONE = "text-text-variant border-outline bg-surface-high";

function optionsFor(options: ConfigOptionsResponse | null, key: string): SelectOption[] {
  const knob = options?.knobs.find((item) => item.key === key);
  return knob ? knob.options.map((item) => ({ value: item.value, label: item.label })) : [];
}

function webStatusLine(phase: WebEvalRunPhase, jobPhase: string | null | undefined): string | null {
  if (phase === "building") return "Setting up the website test…";
  if (phase !== "running") return null;
  const raw = (jobPhase ?? "").toLowerCase();
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

function toneClass(tone: PipelineTone): string {
  if (tone === "active") return "border-primary/40 bg-primary/10 text-primary";
  if (tone === "done") return "border-secondary/30 bg-secondary/10 text-secondary";
  if (tone === "error") return "border-danger/30 bg-danger/10 text-danger";
  return "border-outline-dim bg-surface-high text-text-dim";
}

function iconToneText(tone: PipelineTone, idle: boolean): string {
  if (idle) return "text-primary";
  if (tone === "active") return "text-primary";
  if (tone === "done") return "text-secondary";
  if (tone === "error") return "text-danger";
  return "text-text-dim";
}

function pillForTone(tone: PipelineTone): string {
  if (tone === "active") return "running";
  if (tone === "done") return "done";
  if (tone === "error") return "stopped";
  return "waiting";
}

export function WebEvalCockpit({ options, taskType, onTaskTypeChange, onFooterContextChange }: WebEvalCockpitProps) {
  const { run, job, phase, isRunning, error, timedOut, retry } = useWebEval();
  const [persona, setPersona] = useState<PersonaEvalPersona | null>(null);
  const [personaModel, setPersonaModel] = useState<string>(
    options?.environment.personaModel ?? "anthropic/claude-haiku-4-5",
  );
  const [taskId, setTaskId] = useState<string>("web-ecommerce-platform_product-discovery");
  const [catalogOpen, setCatalogOpen] = useState(false);
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

  // Report the honest footer context up (the active website).
  useEffect(() => {
    onFooterContextChange?.(`web · ${task?.siteName ?? "Website"}`);
  }, [task, onFooterContextChange]);

  const webResult = job?.webResult ?? null;
  const trace = job?.trace ?? null;
  const prompts = job?.prompts ?? null;
  const hasRun = phase === "done" || phase === "error" || phase === "timeout";
  const status = webStatusLine(phase, job?.phase);

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

  const taskOptions: SelectOption[] = tasks.map((item) => ({ value: item.id, label: item.title }));
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

  const showResults = phase !== "idle";

  return (
    <div className="relative z-0 flex-1 overflow-y-auto custom-scrollbar bg-surface-dim">
      <div className="mx-auto w-full max-w-[1180px] px-6 py-7">
        {/* Header + application-type switch */}
        <div className="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-end">
          <div>
            <div className="hud mb-2 text-[10px] text-primary">PersonaEval · Cockpit</div>
            <h1 className="font-display text-[26px] font-bold tracking-tight text-text-main">Configure a simulation</h1>
            <p className="mt-1 text-[13px] text-text-variant">
              Pick a persona and a website task, then launch. A simulated visitor walks through the site and rates the
              experience.
            </p>
          </div>
          <AppTypeSwitch value={taskType} onChange={onTaskTypeChange} disabled={isRunning} />
        </div>

        {/* Pipeline strip: Persona → Website → Trace → Evaluation */}
        <WebPipeline
          phase={phase}
          jobPhase={job?.phase}
          hasPersona={persona !== null}
          hasResult={webResult !== null}
          hasTrace={trace !== null}
          task={task}
        />

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
          {/* LEFT: config + task/results + target persona */}
          <div className="space-y-5 lg:col-span-8">
            <RunConfigCard
              taskId={taskId}
              taskOptions={taskOptions}
              onTask={setTaskId}
              personaModel={personaModel}
              personaModelOptions={personaModelOptions}
              onPersonaModel={setPersonaModel}
              disabled={isRunning}
            />

            {showResults ? (
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
            ) : tasksQuery.isError ? (
              <ErrorCard
                title="Couldn’t load website tasks"
                body="We couldn’t load the website tasks. Check your connection and try again."
                onRetry={() => void tasksQuery.refetch()}
              />
            ) : tasksQuery.isLoading ? (
              <div className="space-y-2" aria-hidden>
                <p className="hud text-[10px] text-text-dim">Loading website tasks…</p>
                <div className="overflow-hidden rounded-md border border-outline bg-surface">
                  <div className="h-14 animate-rb-pulse border-b border-outline bg-surface-high" />
                  <div className="grid grid-cols-1 gap-3 px-4 py-3 sm:grid-cols-3">
                    <div className="h-12 animate-rb-pulse rounded bg-surface-high" />
                    <div className="h-12 animate-rb-pulse rounded bg-surface-high" />
                    <div className="h-12 animate-rb-pulse rounded bg-surface-high" />
                  </div>
                </div>
              </div>
            ) : task ? (
              <WebsiteTaskCard task={task} />
            ) : (
              <PlaceholderCard icon="language" body="Pick a website task above to preview its goal." />
            )}

            {prompts && <PromptsFold prompts={<PromptPanel prompts={prompts} />} />}

            <TargetPersonaPanel
              persona={persona}
              onBrowse={() => setCatalogOpen(true)}
              onViewRecord={() => setDrawerOpen(true)}
            />
          </div>

          {/* RIGHT: driver/artifacts + Run eval */}
          <div className="space-y-5 lg:col-span-4">
            <DriverArtifactsNote />

            <button
              type="button"
              onClick={handleRun}
              disabled={!persona || !task || isRunning}
              className={`glow flex w-full items-center justify-center gap-2.5 rounded-md bg-primary py-4 text-on-primary transition hover:bg-primary-dim active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              {isRunning ? (
                <Sym name="autorenew" size={20} className="animate-rb-spin" />
              ) : (
                <Sym name="play_arrow" fill={1} size={20} />
              )}
              <span className="font-display text-[18px] font-bold tracking-tight">
                {isRunning ? "Working…" : hasRun ? "Run it again" : "Run eval"}
              </span>
            </button>

            {exportSnapshot && webResult && (
              <button
                type="button"
                onClick={handleExport}
                className={`flex w-full items-center justify-center gap-2 rounded-md border border-outline bg-surface-low px-4 py-2.5 text-[12px] font-medium text-text-variant transition hover:border-primary hover:text-text-main active:scale-[0.98] ${FOCUS_RING}`}
              >
                <Sym name="download" size={16} />
                Download results
              </button>
            )}

            <p className="text-center text-[11px] leading-relaxed text-text-variant">
              A simulated visitor browses the site, then we show each step it took and how it rated the experience.
            </p>
          </div>
        </div>
      </div>

      {/* Persona picker overlay */}
      {catalogOpen && (
        <div className="fixed inset-0 z-50 flex">
          <div
            className="fade-in absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setCatalogOpen(false)}
            aria-hidden
          />
          <div className="fade-in relative z-10 flex h-full w-[88%] max-w-[320px] flex-col lg:w-[300px]">
            <PersonaCatalog
              selectedId={persona?.id ?? null}
              onSelect={(next) => {
                setPersona(next);
                setCatalogOpen(false);
              }}
            />
            <button
              type="button"
              onClick={() => setCatalogOpen(false)}
              aria-label="Close persona picker"
              className={`absolute right-3 top-3 z-20 grid h-8 w-8 place-items-center rounded-md border border-outline bg-surface-lowest text-text-variant transition hover:border-primary hover:text-text-main active:scale-95 ${FOCUS_RING}`}
            >
              <Sym name="close" size={18} />
            </button>
          </div>
        </div>
      )}

      <PersonaDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} persona={persona} context={null} />
    </div>
  );
}

/** Inline application-type segmented control (mockup `#appType`). */
function AppTypeSwitch({
  value,
  onChange,
  disabled,
}: {
  value: PersonaEvalTaskType;
  onChange: (value: PersonaEvalTaskType) => void;
  disabled?: boolean;
}) {
  const items: ReadonlyArray<{ value: PersonaEvalTaskType; label: string; icon: string; hint: string }> = [
    { value: "chatbot", label: "Chatbot", icon: "forum", hint: "A back-and-forth conversation." },
    { value: "survey", label: "Survey", icon: "fact_check", hint: "A fixed questionnaire the user fills out." },
    { value: "web", label: "Web", icon: "language", hint: "A website task the user completes." },
  ];
  return (
    <div className="shrink-0">
      <div className="hud mb-1.5 text-[9px] text-text-dim">Application type</div>
      <div className="inline-flex rounded-md border border-outline bg-surface-low p-1">
        {items.map((item) => {
          const active = item.value === value;
          return (
            <button
              key={item.value}
              type="button"
              disabled={disabled}
              title={item.hint}
              aria-pressed={active}
              onClick={() => onChange(item.value)}
              className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-[12px] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${FOCUS_RING} ${
                active ? "bg-primary text-on-primary" : "text-text-variant hover:bg-surface hover:text-text-main"
              }`}
            >
              <Sym name={item.icon} fill={active ? 1 : 0} size={14} />
              {item.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** Status-aware Persona → Website → Trace → Evaluation pipeline strip. */
function WebPipeline({
  phase,
  jobPhase,
  hasPersona,
  hasResult,
  hasTrace,
  task,
}: {
  phase: WebEvalRunPhase;
  jobPhase: string | null | undefined;
  hasPersona: boolean;
  hasResult: boolean;
  hasTrace: boolean;
  task: WebEvalTask | null;
}) {
  const idle = phase === "idle";
  const running = phase === "building" || phase === "running";
  const failed = phase === "error" || phase === "timeout";
  const rawPhase = (jobPhase ?? "").toLowerCase();

  const personaTone: PipelineTone = !hasPersona
    ? "idle"
    : failed
      ? "error"
      : phase === "done"
        ? "done"
        : running && rawPhase.includes("web")
          ? "active"
          : running
            ? "active"
            : "idle";
  const websiteTone: PipelineTone = failed ? "error" : phase === "done" ? "done" : running ? "active" : "idle";
  const traceTone: PipelineTone = failed ? "error" : hasTrace ? "done" : running ? "active" : "idle";
  const evalTone: PipelineTone = failed ? "error" : hasResult ? "done" : "idle";

  const nodes: Array<{ key: string; label: string; sub?: string; icon: string; tone: PipelineTone; title?: string }> = [
    { key: "persona", label: "Persona", icon: "badge", tone: personaTone },
    {
      key: "website",
      label: "Website",
      sub: "simulated walkthrough",
      icon: "language",
      tone: websiteTone,
      title: task ? `${task.title} · ${task.siteUrl}` : "Website host",
    },
    { key: "trace", label: "Trace", icon: "route", tone: traceTone },
    { key: "evaluation", label: "Evaluation", sub: "Objective result", icon: "rate_review", tone: evalTone },
  ];

  return (
    <section aria-label="Web pipeline" className="mb-5 rounded-md border border-outline bg-surface-lowest px-4 py-3">
      <div className="hud mb-2.5 text-[9px] text-text-dim">Pipeline</div>
      <div className="custom-scrollbar flex items-center gap-2 overflow-x-auto text-[11px]">
        {nodes.map((node, index) => (
          <Fragment key={node.key}>
            <span className="flex shrink-0 items-center gap-1.5" title={node.title}>
              <Sym name={node.icon} size={14} className={iconToneText(node.tone, idle)} />
              <span className="text-text-main">{node.label}</span>
              {node.sub && <span className="text-text-variant">· {node.sub}</span>}
              {!idle && (
                <span className={`hud ml-1 shrink-0 rounded border px-1.5 py-0.5 text-[8px] ${toneClass(node.tone)}`}>
                  {pillForTone(node.tone)}
                </span>
              )}
            </span>
            {index < nodes.length - 1 && (
              <Sym name="chevron_right" size={14} className="shrink-0 text-text-dim" />
            )}
          </Fragment>
        ))}
      </div>
    </section>
  );
}

/** "Run configuration" card: website task + simulated-user model selects. */
function RunConfigCard({
  taskId,
  taskOptions,
  onTask,
  personaModel,
  personaModelOptions,
  onPersonaModel,
  disabled,
}: {
  taskId: string;
  taskOptions: SelectOption[];
  onTask: (value: string) => void;
  personaModel: string;
  personaModelOptions: SelectOption[];
  onPersonaModel: (value: string) => void;
  disabled: boolean;
}) {
  return (
    <section className="rounded-md border border-outline bg-surface p-5">
      <div className="mb-5 flex items-center gap-2 border-b border-outline pb-3.5">
        <Sym name="tune" size={16} className="text-primary" />
        <h3 className="hud text-[10px] text-primary">Run configuration</h3>
      </div>
      <div className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2">
        <FieldSelect
          label="Website task"
          title="The site and goal the simulated visitor will attempt."
          value={taskId}
          options={taskOptions}
          onChange={onTask}
          disabled={disabled}
          accent
        />
        <FieldSelect
          label="Simulated-user model"
          title="Which AI model role-plays the simulated visitor."
          value={personaModel}
          options={personaModelOptions}
          onChange={onPersonaModel}
          disabled={disabled}
        />
      </div>
    </section>
  );
}

/** A labelled, mockup-styled native select. */
function FieldSelect({
  label,
  value,
  options,
  onChange,
  disabled,
  title,
  accent,
}: {
  label: string;
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  disabled?: boolean;
  title?: string;
  accent?: boolean;
}) {
  return (
    <label className="block">
      <span className="hud mb-1.5 block text-[9px] text-text-dim">{label}</span>
      <div className="relative">
        <select
          value={options.length === 0 ? "" : options.some((o) => o.value === value) ? value : options[0]?.value ?? ""}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled || options.length === 0}
          title={title}
          className={`w-full appearance-none rounded border bg-field px-3 py-2.5 pr-9 text-[13px] text-text-main outline-none transition-colors focus:border-primary enabled:hover:border-primary/70 disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING} ${
            accent ? "border-primary/60" : "border-outline"
          }`}
        >
          {options.length === 0 ? (
            <option value="">None available</option>
          ) : (
            options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))
          )}
        </select>
        <Sym
          name="expand_more"
          size={18}
          className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-text-dim"
        />
      </div>
    </label>
  );
}

/** "Website task" card (mockup lines 221-229) bound to the selected task. */
function WebsiteTaskCard({ task }: { task: WebEvalTask }) {
  return (
    <section className="panel rounded-md border border-outline bg-surface p-5">
      <div className="mb-3.5 flex items-start justify-between gap-3">
        <div>
          <h3 className="hud text-[10px] text-text-dim">Website task</h3>
          <p className="mt-0.5 text-[11px] text-text-variant">This is the goal the simulated visitor will try to complete.</p>
        </div>
        <span
          title={task.siteName}
          className="hud shrink-0 truncate rounded border border-outline px-1.5 py-0.5 text-[8px] text-text-dim"
        >
          {task.siteName}
        </span>
      </div>
      <div className="mb-1 font-display text-[15px] font-semibold text-text-main">{task.title}</div>
      <p className="mb-4 text-[12px] leading-snug text-text-variant">{task.description}</p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <InfoTile label="Website URL" value={task.siteUrl} />
        <InfoTile label="Results file" value={task.outputArtifact} />
        <InfoTile label="Recording" value="Step screenshots" />
      </div>
    </section>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded border border-outline bg-surface-low px-3 py-2.5">
      <div className="hud mb-1.5 text-[8px] text-text-dim">{label}</div>
      <div className="truncate font-mono text-[12px] text-text-main" title={value}>
        {value}
      </div>
    </div>
  );
}

/** The Web debrief column (modelled on the mockup `data-view="runs"` web body). */
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
  phase: WebEvalRunPhase;
  status: string | null;
  error: string | null;
  persona: PersonaEvalPersona | null;
  onRetry: () => void;
}) {
  const running = phase === "building" || phase === "running";
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

      {/* Score tiles + selected product */}
      {webResult && (
        <div className="rise-in grid grid-cols-1 gap-5 lg:grid-cols-12">
          <div className="grid grid-cols-3 gap-3 lg:col-span-5">
            <MetricTile value={`${webResult.needSatisfaction}`} unit="/10" caption="Need fit" lead
              hint="How well the chosen item met the persona's need (0 to 10)." />
            <MetricTile value={`${webResult.easeOfUse}`} unit="/10" caption="Ease of use"
              hint="How easy the site was to use (0 to 10)." />
            <MetricTile value={`${webResult.overallExperienceRating}`} unit="/10" caption="Overall UX"
              hint="The visitor's overall experience rating (0 to 10)." />
          </div>
          <div className="flex items-center gap-4 rounded-md border border-outline bg-surface p-5 lg:col-span-7">
            <div className="grid h-12 w-12 shrink-0 place-items-center rounded border border-outline bg-surface-high">
              <Sym name="inventory_2" size={22} className="text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[14px] font-semibold text-text-main">{webResult.selectedProductName}</span>
                <span
                  title="Complete means the run produced a full, usable result."
                  className={`hud rounded border px-1.5 py-0.5 text-[8px] ${
                    webResult.valid
                      ? "border-secondary/30 bg-secondary/10 text-secondary"
                      : "border-danger/30 bg-danger/10 text-danger"
                  }`}
                >
                  {webResult.valid ? "Complete" : "Incomplete"}
                </span>
              </div>
              <div className="mt-0.5 truncate font-mono text-[10px] text-text-variant" title={webResult.selectedProductId}>
                {webResult.selectedProductId}
              </div>
              <p className="mt-1 text-[11px] leading-snug text-text-variant">{webResult.reason}</p>
            </div>
          </div>
        </div>
      )}

      {/* Browser trace */}
      {trace && (
        <div className="space-y-3">
          <h3 className="hud flex items-center gap-2 text-[10px] text-primary">
            <Sym name="route" size={14} /> Browser trace · {trace.events.length} step
            {trace.events.length === 1 ? "" : "s"}
          </h3>
          <WebTraceGrid trace={trace} />
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

/** Screenshot-tile grid + an expandable per-step detail panel. */
function WebTraceGrid({ trace }: { trace: WebTrace }) {
  const [selected, setSelected] = useState<number | null>(null);
  const events = trace.events;

  if (events.length === 0) {
    return (
      <div className="rise-in rounded-md border border-dashed border-outline bg-surface-low px-4 py-6 text-center text-[12px] text-text-variant">
        This run finished without recording any steps.
      </div>
    );
  }

  const selectedEvent = selected != null ? events.find((event) => event.step === selected) ?? null : null;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {events.map((event, index) => (
          <TraceTile
            key={event.step}
            index={index}
            event={event}
            active={event.step === selected}
            onClick={() => setSelected((prev) => (prev === event.step ? null : event.step))}
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

/** Right-column driver & artifacts contract note. */
function DriverArtifactsNote() {
  return (
    <section className="rounded-md border border-outline bg-surface-lowest p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="hud flex items-center gap-1.5 text-[10px] text-text-dim">
          <Sym name="monitor" size={14} /> Driver &amp; artifacts
        </h3>
        <span className="hud rounded border border-outline px-1.5 py-0.5 text-[8px] text-text-dim">simulated</span>
      </div>
      <p className="mb-3 text-[12px] leading-relaxed text-text-variant">
        The persona reasons through the site step by step; the walkthrough and screenshots are captured as a trace.
      </p>
      <div className="hud mb-1.5 text-[8px] text-text-dim">Artifacts produced</div>
      <div className="flex flex-wrap gap-1.5">
        {["trajectory", "application_result", "objective_result"].map((name) => (
          <span key={name} className="rounded border border-outline px-2 py-0.5 font-mono text-[10px] text-text-variant">
            {fmtDomain(name)}
          </span>
        ))}
      </div>
    </section>
  );
}

/** Shared "Target persona" panel (mockup lines 233-244) bound to the selected persona. */
function TargetPersonaPanel({
  persona,
  onBrowse,
  onViewRecord,
}: {
  persona: PersonaEvalPersona | null;
  onBrowse: () => void;
  onViewRecord: () => void;
}) {
  const detail = usePersonaDetail(persona?.id ?? null);
  const demographics = useMemo(() => {
    if (!persona) return [];
    const fromContext = detail.data?.context ? parseDemographics(detail.data.context) : [];
    return fromContext.length > 0 ? fromContext : parseDemographicsFromBlurb(persona.blurb);
  }, [persona, detail.data?.context]);

  return (
    <section className="panel rounded-md border border-outline bg-surface p-5">
      <div className="mb-3.5 flex items-center justify-between">
        <h3 className="hud text-[10px] text-text-dim">Target persona</h3>
        <button
          type="button"
          onClick={onBrowse}
          className={`hud rounded text-[9px] text-primary transition-colors hover:underline active:text-primary-dim ${FOCUS_RING}`}
        >
          Browse catalog →
        </button>
      </div>

      {persona ? (
        <div className="flex items-center gap-4">
          <div className="grid h-14 w-14 shrink-0 place-items-center rounded-md border border-outline bg-surface-high">
            <Sym name="person" fill={1} size={24} className="text-primary" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-display text-[16px] font-semibold text-text-main">
                {personaDescriptiveTitle(detail.data?.context ?? null, persona.blurb, persona.source)}
              </span>
              {persona.source && (
                <span
                  className={`hud rounded border px-1.5 py-0.5 text-[8px] ${SOURCE_TONE[persona.source] ?? NEUTRAL_SOURCE_TONE}`}
                >
                  {persona.source}
                </span>
              )}
              <span className="font-mono text-[10px] text-text-dim">{personaCodename(persona.name, persona.id)}</span>
            </div>
            <p className="mt-0.5 line-clamp-2 text-[12px] leading-snug text-text-variant">
              {demographics.length > 0
                ? `${demographics.map((d) => d.full).join(" · ")}`
                : persona.blurb || "No preview available."}
            </p>
            <button
              type="button"
              onClick={onViewRecord}
              className={`mt-1.5 inline-flex items-center gap-1 text-[11px] font-medium text-text-variant transition-colors hover:text-primary active:text-primary-dim ${FOCUS_RING}`}
            >
              <Sym name="data_object" size={14} /> View full record
            </button>
          </div>
          <button
            type="button"
            onClick={onBrowse}
            className={`shrink-0 rounded-md border border-outline bg-surface-low px-3.5 py-2 text-[12px] text-text-variant transition hover:border-primary hover:text-text-main active:scale-[0.98] ${FOCUS_RING}`}
          >
            Change
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-4">
          <div className="grid h-14 w-14 shrink-0 place-items-center rounded-md border border-dashed border-outline bg-surface-high">
            <Sym name="person_search" size={24} className="text-text-dim" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-display text-[15px] font-semibold text-text-main">Choose a persona to start</div>
            <p className="mt-0.5 text-[12px] leading-snug text-text-variant">
              PersonaEval needs a target persona before it can run a website test.
            </p>
          </div>
          <button
            type="button"
            onClick={onBrowse}
            className={`shrink-0 rounded-md border border-outline bg-surface-low px-3.5 py-2 text-[12px] text-text-variant transition hover:border-primary hover:text-text-main active:scale-[0.98] ${FOCUS_RING}`}
          >
            Browse
          </button>
        </div>
      )}
    </section>
  );
}

/** Collapsible "Prompts used" panel (preserves the prompts inspector feature). */
function PromptsFold({ prompts }: { prompts: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="overflow-hidden rounded-md border border-outline bg-surface">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className={`flex w-full items-center justify-between gap-2 px-4 py-3 text-left transition-colors hover:bg-surface-low active:bg-surface-high ${FOCUS_RING}`}
      >
        <span className="hud flex items-center gap-1.5 text-[10px] text-text-dim">
          <Sym name="terminal" size={14} /> Prompts used
        </span>
        <Sym name={open ? "expand_more" : "chevron_right"} size={18} className="text-text-dim" />
      </button>
      {open && <div className="rise-in border-t border-outline">{prompts}</div>}
    </section>
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
      className={`rounded-md border border-outline bg-surface p-4 ${lead ? "border-l-4 border-l-secondary" : ""}`}
    >
      <span className={`hud text-[9px] ${lead ? "text-secondary" : "text-text-dim"}`}>{caption}</span>
      <div className="mt-1.5 flex items-baseline gap-0.5">
        <span className="font-display text-[24px] font-bold tabular-nums text-text-main">{value}</span>
        {unit && <span className="font-sans text-[12px] text-text-dim">{unit}</span>}
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
    <div className="rise-in rounded-md border border-danger/30 bg-danger/10 p-4">
      <div className="flex items-start gap-3">
        <Sym name="error" fill={1} size={20} className="mt-0.5 text-danger" />
        <div className="min-w-0 flex-1">
          <h4 className="font-display text-[15px] font-semibold text-danger">{title}</h4>
          <p className="mt-1 break-words text-[13px] leading-relaxed text-text-variant">{body}</p>
          <button
            type="button"
            onClick={onRetry}
            className={`mt-3 inline-flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-3 py-1.5 text-xs font-medium text-danger transition-colors hover:bg-danger/20 ${FOCUS_RING}`}
          >
            <Sym name="refresh" size={16} />
            {retryLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

function PlaceholderCard({ icon, body }: { icon: string; body: string }) {
  return (
    <div className="rounded-md border border-dashed border-outline bg-surface-low px-4 py-10 text-center">
      <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
        <Sym name={icon} size={22} className="text-primary" />
      </div>
      <p className="text-[13px] leading-relaxed text-text-variant">{body}</p>
    </div>
  );
}

export default WebEvalCockpit;
