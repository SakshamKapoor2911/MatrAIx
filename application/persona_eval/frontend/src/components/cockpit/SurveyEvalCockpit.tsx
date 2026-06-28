/**
 * SurveyEvalCockpit: the Survey PersonaEval surface.
 *
 * Reproduces the approved redesign mockup's `data-view="cockpit"` setup form
 * (the same centered shell as the canonical chatbot cockpit: header +
 * application-type switch + pipeline strip + run-config card + target-persona
 * panel + Run-eval CTA), with the Survey-specific body (an instrument picker +
 * an "Instrument preview" panel and a driver/artifacts note instead of an
 * environment panel.
 * environment). Once a run starts, the left column flips to the live answering /
 * results view modelled on `data-view="surveylive"` (completion progress +
 * mean-Likert summary + per-question answer cards with likert / single / multi /
 * free-text rendering).
 *
 * The data layer is untouched: `useSurveyEval`, the `listSurveyInstruments`
 * query, the export logic, and every result/trajectory shape are wired exactly
 * as before. Only the structure and presentation are rebuilt.
 */
import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import { listSurveyInstruments } from "@/lib/api";
import type {
  ConfigOptionsResponse,
  PersonaEvalPersona,
  PersonaModel,
  SurveyAnswer,
  SurveyInstrument,
  SurveyInstrumentsResponse,
  SurveyQuestion,
  SurveyResult,
  SurveyTrajectoryEvent,
} from "@/lib/types";
import { useSurveyEval, type SurveyEvalRunPhase } from "@/lib/useSurveyEval";
import { usePersonaDetail } from "@/lib/usePersonaEval";
import { PersonaCatalog } from "./PersonaCatalog";
import { PersonaDrawer } from "./PersonaDrawer";
import { PromptPanel } from "./PromptPanel";
import {
  FOCUS_RING,
  Sym,
  humanizeToken,
  parseDemographics,
  parseDemographicsFromBlurb,
  personaCodename,
  personaDescriptiveTitle,
} from "./cockpitShared";
import { fmtDomain } from "../runsShared";
import type { PersonaEvalTaskType } from "./TaskTypeSwitch";

export interface SurveyEvalCockpitProps {
  options: ConfigOptionsResponse | null;
  taskType: PersonaEvalTaskType;
  onTaskTypeChange: (value: PersonaEvalTaskType) => void;
  /** Report the honest footer context up (the active questionnaire). */
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

function surveyStatusLine(phase: SurveyEvalRunPhase, jobPhase: string | null | undefined): string | null {
  if (phase === "building") return "Setting up the questionnaire…";
  if (phase !== "running") return null;
  const raw = (jobPhase ?? "").toLowerCase();
  if (raw.includes("collect")) return "Saving the answers…";
  if (raw.includes("survey")) return "The simulated user is filling out the questionnaire…";
  return "Running the questionnaire…";
}

/** Friendly chip word + tint + tooltip for a survey question type. Presentation only. */
function questionTypeMeta(type: string): { label: string; tone: string; tooltip: string } {
  switch (type) {
    case "likert":
      return { label: "Likert", tone: "text-primary border-primary/30 bg-primary/10", tooltip: "Rate on a 1 to 5 scale" };
    case "single_choice":
      return { label: "Single", tone: "text-secondary border-secondary/30 bg-secondary/10", tooltip: "Choose one option" };
    case "multi_choice":
      return { label: "Multi", tone: "text-warn border-warn/30 bg-warn/10", tooltip: "Choose all that apply" };
    case "free_text":
      return { label: "Free", tone: "text-text-variant border-outline bg-surface-high", tooltip: "Answer in their own words" };
    default:
      return { label: type, tone: "text-text-variant border-outline bg-surface-high", tooltip: type };
  }
}

/** Friendly actor name for a trajectory row. Presentation only. */
function trajectoryActor(actor: string): string {
  const value = actor.toLowerCase();
  if (value === "agent") return "Simulated user";
  if (value === "system") return "System";
  if (value === "scorer") return "Scorer";
  return actor;
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

function formatSurveyValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => String(item)).join(", ");
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function SurveyEvalCockpit({ options, taskType, onTaskTypeChange, onFooterContextChange }: SurveyEvalCockpitProps) {
  const { run, job, phase, isRunning, error, timedOut, retry } = useSurveyEval();
  const [persona, setPersona] = useState<PersonaEvalPersona | null>(null);
  const [personaModel, setPersonaModel] = useState<string>(
    options?.environment.personaModel ?? "anthropic/claude-haiku-4-5",
  );
  const [instrumentId, setInstrumentId] = useState<string>("chatgpt_images_market_research_v1");
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [exportSnapshot, setExportSnapshot] = useState<{
    persona: { id: string; name: string; source: string } | null;
    instrumentId: string;
    personaModel: string;
  } | null>(null);

  const adoptedDefaults = useRef(false);
  useEffect(() => {
    if (adoptedDefaults.current || !options) return;
    adoptedDefaults.current = true;
    setPersonaModel(options.environment.personaModel ?? "anthropic/claude-haiku-4-5");
  }, [options]);

  const instrumentsQuery = useQuery<SurveyInstrumentsResponse>({
    queryKey: ["survey-eval-instruments"],
    queryFn: listSurveyInstruments,
    staleTime: 10 * 60_000,
    refetchOnWindowFocus: false,
  });
  const instruments = instrumentsQuery.data?.instruments ?? [];
  const instrument = instruments.find((item) => item.id === instrumentId) ?? instruments[0] ?? null;

  useEffect(() => {
    if (!instrument && instruments.length > 0) setInstrumentId(instruments[0].id);
  }, [instrument, instruments]);

  // Report the honest footer context up (the active questionnaire).
  useEffect(() => {
    onFooterContextChange?.(`survey · ${instrument?.title ?? "Questionnaire"}`);
  }, [instrument, onFooterContextChange]);

  const surveyResult = job?.surveyResult ?? null;
  const prompts = job?.prompts ?? surveyResult?.prompts ?? null;
  const hasRun = phase === "done" || phase === "error" || phase === "timeout";
  const status = surveyStatusLine(phase, job?.phase);

  useEffect(() => {
    if (phase === "done") {
      setExportSnapshot(
        (prev) =>
          prev ?? {
            persona: persona ? { id: persona.id, name: persona.name, source: persona.source } : null,
            instrumentId,
            personaModel,
          },
      );
    }
  }, [phase, persona, instrumentId, personaModel]);

  const instrumentOptions: SelectOption[] = instruments.map((item) => ({ value: item.id, label: item.title }));
  const personaModelOptions = optionsFor(options, "personaModel");

  const handleRun = useCallback(() => {
    if (!persona || !instrument || isRunning) return;
    setExportSnapshot(null);
    run({
      personaId: persona.id,
      instrumentId: instrument.id,
      personaModel: personaModel as PersonaModel,
    });
  }, [persona, instrument, isRunning, run, personaModel]);

  const handleRetry = useCallback(() => {
    if (timedOut || phase === "error") retry();
    else handleRun();
  }, [timedOut, phase, retry, handleRun]);

  const handleExport = useCallback(() => {
    if (!exportSnapshot || !surveyResult) return;
    const payload = {
      applicationType: "survey",
      config: exportSnapshot,
      surveyResult,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `survey-eval-${exportSnapshot.persona?.id ?? "run"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [exportSnapshot, surveyResult]);

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
              Pick a persona and a questionnaire, then launch. A simulated user fills out the form and we score how it
              responds.
            </p>
          </div>
          <AppTypeSwitch value={taskType} onChange={onTaskTypeChange} disabled={isRunning} />
        </div>

        {/* Pipeline strip: Persona → Survey → Artifact */}
        <SurveyPipeline
          phase={phase}
          jobPhase={job?.phase}
          hasPersona={persona !== null}
          hasResult={surveyResult !== null}
          instrument={instrument}
        />

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
          {/* LEFT: config + preview/results + target persona */}
          <div className="space-y-5 lg:col-span-8">
            <RunConfigCard
              instrumentId={instrumentId}
              instrumentOptions={instrumentOptions}
              onInstrument={setInstrumentId}
              personaModel={personaModel}
              personaModelOptions={personaModelOptions}
              onPersonaModel={setPersonaModel}
              disabled={isRunning}
            />

            {showResults ? (
              <SurveyLive
                instrument={instrument}
                result={surveyResult}
                phase={phase}
                status={status}
                error={error}
                persona={persona}
                onRetry={handleRetry}
              />
            ) : instrumentsQuery.isError ? (
              <ErrorCard
                title="Couldn’t load questionnaires"
                body="We couldn’t load the questionnaires. Check your connection and try again."
                onRetry={() => void instrumentsQuery.refetch()}
              />
            ) : instrumentsQuery.isLoading ? (
              <div className="space-y-2" aria-hidden>
                <p className="hud text-[10px] text-text-dim">Loading questionnaires…</p>
                <div className="h-12 animate-rb-pulse rounded-md bg-surface-high" />
                <div className="h-12 animate-rb-pulse rounded-md bg-surface-high" />
                <div className="h-12 animate-rb-pulse rounded-md bg-surface-high" />
              </div>
            ) : instrument ? (
              <InstrumentPreview instrument={instrument} />
            ) : (
              <PlaceholderCard
                icon="fact_check"
                body="Pick a questionnaire above to preview its questions."
              />
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
              disabled={!persona || !instrument || isRunning}
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

            {exportSnapshot && surveyResult && (
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
              A simulated user fills out the questionnaire, then we show its answers and an average rating.
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
    { value: "web", label: "Web", icon: "language", hint: "A real browser task the user completes." },
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

/** Status-aware Persona → Survey → Artifact pipeline strip (mockup cockpit + liverun). */
function SurveyPipeline({
  phase,
  jobPhase,
  hasPersona,
  hasResult,
  instrument,
}: {
  phase: SurveyEvalRunPhase;
  jobPhase: string | null | undefined;
  hasPersona: boolean;
  hasResult: boolean;
  instrument: SurveyInstrument | null;
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
        : running && rawPhase.includes("survey")
          ? "active"
          : running
            ? "active"
            : "idle";
  const surveyTone: PipelineTone = failed ? "error" : phase === "done" ? "done" : running ? "active" : "idle";
  const artifactTone: PipelineTone = failed ? "error" : hasResult ? "done" : "idle";

  const nodes: Array<{ key: string; label: string; sub?: string; icon: string; tone: PipelineTone; title?: string }> = [
    { key: "persona", label: "Persona", icon: "badge", tone: personaTone },
    {
      key: "survey",
      label: "Survey",
      sub: "Survey form driver",
      icon: "fact_check",
      tone: surveyTone,
      title: instrument ? `${instrument.title} · ${instrument.questions.length} questions` : "Survey form",
    },
    { key: "artifact", label: "Artifact", sub: "Survey result", icon: "description", tone: artifactTone },
  ];

  return (
    <section
      aria-label="Survey pipeline"
      className="mb-5 rounded-md border border-outline bg-surface-lowest px-4 py-3"
    >
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

/** "Run configuration" card: questionnaire + simulated-user model selects. */
function RunConfigCard({
  instrumentId,
  instrumentOptions,
  onInstrument,
  personaModel,
  personaModelOptions,
  onPersonaModel,
  disabled,
}: {
  instrumentId: string;
  instrumentOptions: SelectOption[];
  onInstrument: (value: string) => void;
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
          label="Questionnaire"
          title="The questionnaire the simulated user will fill out."
          value={instrumentId}
          options={instrumentOptions}
          onChange={onInstrument}
          disabled={disabled}
          accent
        />
        <FieldSelect
          label="Simulated-user model"
          title="Which AI model role-plays the simulated user."
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

/** "Instrument preview": a compact type-badged question list (mockup lines 198-207). */
function InstrumentPreview({ instrument }: { instrument: SurveyInstrument }) {
  return (
    <section className="panel rounded-md border border-outline bg-surface p-5">
      <div className="mb-3.5 flex items-center justify-between gap-3">
        <h3 className="hud text-[10px] text-text-dim">Instrument preview</h3>
        <span className="hud shrink-0 truncate text-[9px] text-text-dim" title={instrument.title}>
          {instrument.title} · {instrument.questions.length} items
        </span>
      </div>
      <div className="space-y-2">
        {instrument.questions.map((question) => {
          const meta = questionTypeMeta(question.type);
          return (
            <div
              key={question.id}
              className="flex items-start gap-3 rounded border border-outline bg-surface-low px-3 py-2.5"
            >
              <span
                title={meta.tooltip}
                className={`hud min-w-[3.5rem] shrink-0 rounded border px-1.5 py-0.5 text-center text-[8px] ${meta.tone}`}
              >
                {meta.label}
              </span>
              <span className="min-w-0 flex-1 break-words text-[12px] text-text-variant">{question.prompt}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

/** The Survey live / results column (modelled on `data-view="surveylive"`). */
function SurveyLive({
  instrument,
  result,
  phase,
  status,
  error,
  persona,
  onRetry,
}: {
  instrument: SurveyInstrument | null;
  result: SurveyResult | null;
  phase: SurveyEvalRunPhase;
  status: string | null;
  error: string | null;
  persona: PersonaEvalPersona | null;
  onRetry: () => void;
}) {
  const running = phase === "building" || phase === "running";
  const failed = phase === "error" || phase === "timeout";
  const activeInstrument = result?.instrument ?? instrument;
  const completion = result?.completion ?? null;
  const total = completion?.numQuestions ?? activeInstrument?.questions.length ?? 0;
  const answered = completion?.numAnswered ?? result?.answers.length ?? 0;
  const pct = total > 0 ? Math.round((answered / total) * 100) : 0;

  const personaTitle = persona
    ? personaDescriptiveTitle(null, persona.blurb, persona.source)
    : "Persona";
  const personaCode = persona ? personaCodename(persona.name, persona.id) : null;

  const freeTextCount = useMemo(() => {
    if (!result || !activeInstrument) return 0;
    return result.answers.filter((answer) => {
      const question = activeInstrument.questions.find((q) => q.id === answer.questionId);
      return question?.type === "free_text";
    }).length;
  }, [result, activeInstrument]);

  return (
    <section className="space-y-4">
      {/* Header */}
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div className="min-w-0">
          <div className="hud mb-2 break-words text-[10px] text-primary">
            Survey · {humanizeToken(activeInstrument?.id ?? activeInstrument?.title ?? "questionnaire")}
          </div>
          <h2 className="font-display text-[22px] font-bold tracking-tight text-text-main">
            {running ? "Persona is answering" : failed ? "The questionnaire didn’t finish" : "Completed questionnaire"}
          </h2>
          {running && (
            <div className="mt-2 flex items-center gap-2 text-[12px] text-text-variant">
              <Sym name="autorenew" size={14} className="animate-rb-spin text-primary" />
              <span>{result ? `Answering Q${Math.min(answered + 1, total)} of ${total}` : status ?? "Simulated user is answering…"}</span>
            </div>
          )}
        </div>
        {persona && (
          <div className="flex shrink-0 items-center gap-2.5 rounded-md border border-outline bg-surface-lowest px-3 py-2">
            <div className="grid h-9 w-9 place-items-center rounded border border-outline bg-surface-high">
              <Sym name="person" fill={1} size={16} className="text-primary" />
            </div>
            <div className="min-w-0">
              <div className="truncate text-[12px] font-semibold leading-tight text-text-main" title={personaTitle}>{personaTitle}</div>
              <div className="hud mt-1 whitespace-nowrap text-[8px] text-text-dim">
                {[persona.source, personaCode].filter(Boolean).join(" · ")}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Completion progress (running) */}
      {running && (
        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <span className="hud text-[9px] text-text-dim">
              {result ? `${answered} / ${total} answered` : "Working…"}
            </span>
            <span className="hud text-[9px] text-primary">{result ? `${pct}%` : ""}</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-field">
            {result ? (
              <div className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out" style={{ width: `${pct}%` }} />
            ) : (
              <div className="h-full w-1/3 animate-pulse rounded-full bg-primary/60" />
            )}
          </div>
        </div>
      )}

      {/* Summary tiles (done) */}
      {result && completion && (
        <div className="rise-in grid grid-cols-2 gap-3 sm:grid-cols-4">
          <MetricTile value={`${answered}/${total}`} caption="Completion" lead />
          <ValidityTile valid={completion.valid} />
          <MetricTile
            value={completion.meanLikert == null ? "n/a" : completion.meanLikert.toFixed(1)}
            unit={completion.meanLikert == null ? undefined : "/5"}
            caption="Mean Likert"
            hint="Average of the 1 to 5 ratings the persona gave across Likert questions."
          />
          <MetricTile value={`${freeTextCount}`} caption="Free-text" />
        </div>
      )}

      {/* Error */}
      {failed && (
        <ErrorCard
          title="The questionnaire didn’t finish"
          body={error ?? "Something interrupted the run. Your setup is still here. Press Try again."}
          onRetry={onRetry}
          retryLabel="Try again"
        />
      )}

      {/* Answer cards */}
      {result && activeInstrument ? (
        <div className="space-y-4">
          {result.answers.map((answer, index) => (
            <SurveyAnswerCard
              key={answer.questionId}
              index={index}
              answer={answer}
              question={activeInstrument.questions.find((q) => q.id === answer.questionId) ?? null}
            />
          ))}
        </div>
      ) : running ? (
        <div className="space-y-4" aria-hidden>
          <div className="h-36 animate-rb-pulse rounded-md bg-surface-high" />
          <div className="h-36 animate-rb-pulse rounded-md bg-surface-high" />
        </div>
      ) : null}

      {/* Footer + trajectory */}
      {result && (
        <>
          <div className="flex items-center justify-center gap-2 pt-1">
            <span className="hud text-[9px] text-text-dim">{answered} of {total} answered</span>
            {total - answered > 0 && (
              <>
                <span className="text-outline-dim">·</span>
                <span className="hud text-[9px] text-text-dim">{total - answered} remaining</span>
              </>
            )}
          </div>
          {result.trajectory.length > 0 && <TrajectoryFold events={result.trajectory} />}
        </>
      )}
    </section>
  );
}

/** One answered question, rendered by type (likert / single / multi / free-text). */
function SurveyAnswerCard({
  index,
  answer,
  question,
}: {
  index: number;
  answer: SurveyAnswer;
  question: SurveyQuestion | null;
}) {
  const meta = questionTypeMeta(question?.type ?? "");
  const confidence = answer.confidence;
  return (
    <div
      className="rise-in rounded-md border border-outline bg-surface p-5"
      style={{ animationDelay: `${Math.min(index, 6) * 30}ms` }}
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="hud text-[10px] text-text-dim">Q{index + 1}</span>
          <span title={meta.tooltip} className={`hud rounded border px-1.5 py-0.5 text-[8px] ${meta.tone}`}>
            {meta.label}
          </span>
        </div>
        <Sym name="check_circle" fill={1} size={16} className="text-secondary" />
      </div>
      <p className="mb-4 text-[13px] leading-relaxed text-text-main">{question?.prompt ?? answer.questionId}</p>

      <AnswerValue answer={answer} question={question} />

      {(answer.rationale || confidence != null) && (
        <div className="mt-5 border-t border-outline pt-3.5">
          <p className="font-mono text-[11px] leading-relaxed text-text-variant">
            {answer.rationale ? `persona rationale: ${answer.rationale}` : "persona answered"}{" "}
            {confidence != null && <span className="text-text-variant">(conf {confidence.toFixed(2)})</span>}
          </p>
        </div>
      )}
    </div>
  );
}

function AnswerValue({ answer, question }: { answer: SurveyAnswer; question: SurveyQuestion | null }) {
  const type = question?.type;

  if (type === "likert") {
    const chosen = Number(answer.value);
    const min = question?.minValue ?? 1;
    const max = question?.maxValue ?? 5;
    if (Number.isFinite(chosen) && max >= min && max - min <= 12) {
      const scale = Array.from({ length: max - min + 1 }, (_, i) => min + i);
      const lowLabel = question?.options?.[0];
      const highLabel = question?.options && question.options.length > 1 ? question.options[question.options.length - 1] : undefined;
      return (
        <div>
          <div className="flex items-center justify-between gap-2">
            {scale.map((n) => (
              <span
                key={n}
                className={`grid h-11 w-11 shrink-0 place-items-center rounded-full border font-mono text-[13px] ${
                  n === chosen
                    ? "border-primary bg-primary font-bold text-on-primary"
                    : "border-outline text-text-variant"
                }`}
              >
                {n}
              </span>
            ))}
          </div>
          {(lowLabel || highLabel) && (
            <div className="mt-2.5 flex items-center justify-between">
              <span className="hud text-[8px] text-text-dim">{lowLabel}</span>
              <span className="hud text-[8px] text-text-dim">{highLabel}</span>
            </div>
          )}
        </div>
      );
    }
  }

  if ((type === "single_choice" || type === "multi_choice") && question && question.options.length > 0) {
    const multi = type === "multi_choice";
    const selected = Array.isArray(answer.value)
      ? answer.value.map((v) => String(v))
      : [String(answer.value)];
    return (
      <div className="space-y-2">
        {multi && (
          <p className="hud text-[8px] text-text-dim">Select all that apply · {selected.length} selected</p>
        )}
        {question.options.map((option) => {
          const isSelected = selected.includes(option);
          return (
            <div
              key={option}
              className={`flex items-center gap-3 rounded border px-3.5 py-2.5 ${
                isSelected ? "border-primary bg-primary/10" : "border-outline bg-surface-low"
              }`}
            >
              {multi ? (
                <span
                  className={`grid h-4 w-4 shrink-0 place-items-center rounded-sm border ${
                    isSelected ? "border-primary bg-primary" : "border-outline"
                  }`}
                >
                  {isSelected && <Sym name="check" size={12} className="text-on-primary" />}
                </span>
              ) : (
                <span
                  className={`grid h-4 w-4 shrink-0 place-items-center rounded-full border ${
                    isSelected ? "border-2 border-primary" : "border-outline"
                  }`}
                >
                  {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-primary" />}
                </span>
              )}
              <span className={`text-[12px] ${isSelected ? "font-medium text-text-main" : "text-text-variant"}`}>
                {option}
              </span>
            </div>
          );
        })}
      </div>
    );
  }

  if (type === "free_text") {
    return (
      <div className="rounded border border-outline bg-field p-4">
        <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-text-variant">
          {formatSurveyValue(answer.value) || "(no response)"}
        </p>
      </div>
    );
  }

  // Fallback for unknown types / missing question metadata.
  return (
    <div className="rounded border border-outline bg-field px-3 py-2.5">
      <p className="font-mono text-[12px] text-text-main">{formatSurveyValue(answer.value) || "(no answer)"}</p>
    </div>
  );
}

/** Collapsible telemetry trajectory. */
function TrajectoryFold({ events }: { events: SurveyTrajectoryEvent[] }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="panel overflow-hidden rounded-md border border-outline bg-surface">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className={`flex w-full items-center justify-between gap-2 border-b border-outline px-4 py-3 text-left transition-colors hover:bg-surface-low active:bg-surface-high ${FOCUS_RING}`}
      >
        <span className="hud text-[10px] text-text-dim">Trajectory</span>
        <span className="flex items-center gap-2">
          <span className="hud text-[9px] text-text-dim">{events.length} events</span>
          <Sym name={open ? "expand_more" : "chevron_right"} size={18} className="text-text-dim" />
        </span>
      </button>
      {open && (
        <div className="rise-in custom-scrollbar max-h-80 divide-y divide-outline-dim overflow-auto">
          {events.map((event, index) => (
            <div key={`${event.timestamp}-${index}`} className="px-4 py-2.5">
              <div className="flex items-center justify-between gap-2">
                <span
                  className="truncate text-[12px] font-medium text-text-main"
                  title={`${trajectoryActor(event.actor)} · ${event.action}`}
                >
                  {trajectoryActor(event.actor)} · {event.action}
                </span>
                <span className="shrink-0 font-mono text-[11px] text-text-dim">{event.timestamp}</span>
              </div>
              <pre className="mt-1 max-h-24 overflow-auto whitespace-pre-wrap break-words rounded bg-field p-2 font-mono text-[11px] text-text-variant">
                {JSON.stringify({ context: event.context, outcome: event.outcome }, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

/** Right-column driver & artifacts contract note. */
function DriverArtifactsNote() {
  return (
    <section className="rounded-md border border-outline bg-surface-lowest p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="hud flex items-center gap-1.5 text-[10px] text-text-dim">
          <Sym name="fact_check" size={14} /> Driver &amp; artifacts
        </h3>
        <span className="hud rounded border border-outline px-1.5 py-0.5 text-[8px] text-text-dim">Survey form</span>
      </div>
      <p className="mb-3 text-[12px] leading-relaxed text-text-variant">
        No fixed application stack. The persona fills the questionnaire directly.
      </p>
      <div className="hud mb-1.5 text-[8px] text-text-dim">Artifacts produced</div>
      <div className="flex flex-wrap gap-1.5">
        {["survey_result", "answers", "trajectory", "metrics"].map((name) => (
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
              PersonaEval needs a target persona before it can run a questionnaire.
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

function ValidityTile({ valid }: { valid: boolean }) {
  return (
    <div
      title="Complete means the persona answered every required question."
      className="rounded-md border border-outline bg-surface p-4"
    >
      <span className="hud text-[9px] text-text-dim">Validity</span>
      <div className="mt-1.5">
        <span
          className={`hud rounded border px-2 py-1 text-[9px] ${
            valid ? "border-secondary/30 bg-secondary/10 text-secondary" : "border-danger/30 bg-danger/10 text-danger"
          }`}
        >
          {valid ? "Complete" : "Incomplete"}
        </span>
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

export default SurveyEvalCockpit;
