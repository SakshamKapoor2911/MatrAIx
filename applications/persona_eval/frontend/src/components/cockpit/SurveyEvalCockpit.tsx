import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { listSurveyInstruments } from "@/lib/api";
import type {
  ConfigOptionsResponse,
  PersonaEvalPersona,
  PersonaModel,
  SurveyAnswer,
  SurveyInstrument,
  SurveyInstrumentsResponse,
  SurveyResult,
  SurveyTrajectoryEvent,
} from "@/lib/types";
import { useSurveyEval, type SurveyEvalRunPhase } from "@/lib/useSurveyEval";
import { PersonaCatalog } from "./PersonaCatalog";
import { PersonaDrawer } from "./PersonaDrawer";
import { PersonaPanel } from "./PersonaPanel";
import { PromptPanel } from "./PromptPanel";
import { InspectorTabs, type InspectorTab } from "./InspectorTabs";
import { KnobSelect, type KnobOption } from "./KnobSelect";
import { FOCUS_RING, Sym, personaCodename, personaDescriptiveTitle } from "./cockpitShared";
import { TaskTypeSwitch, type PersonaEvalTaskType } from "./TaskTypeSwitch";

export interface SurveyEvalCockpitProps {
  options: ConfigOptionsResponse | null;
  taskType: PersonaEvalTaskType;
  onTaskTypeChange: (value: PersonaEvalTaskType) => void;
}

function optionsFor(options: ConfigOptionsResponse | null, key: string): KnobOption[] {
  const knob = options?.knobs.find((item) => item.key === key);
  return knob ? knob.options.map((item) => ({ value: item.value, label: item.label, description: item.description })) : [];
}

function surveyStatusLine(phase: SurveyEvalRunPhase, jobPhase: string | null | undefined): string | null {
  if (phase === "building") return "Setting up the questionnaire…";
  if (phase !== "running") return null;
  const raw = (jobPhase ?? "").toLowerCase();
  if (raw.includes("collect")) return "Saving the answers…";
  if (raw.includes("harbor")) return "The simulated user is filling out the questionnaire…";
  return "Running the questionnaire…";
}

/** Friendly chip word + tint + tooltip for a survey question type. Presentation only. */
function questionTypeMeta(type: string): { label: string; tone: string; tooltip: string } {
  switch (type) {
    case "likert":
      return { label: "Likert", tone: "text-primary border-primary/30 bg-primary/10", tooltip: "Rate on a 1–5 scale" };
    case "single_choice":
      return { label: "Single", tone: "text-secondary border-secondary/30 bg-secondary/10", tooltip: "Choose one option" };
    case "multi_choice":
      return { label: "Multi", tone: "text-warn border-warn/30 bg-warn/10", tooltip: "Choose all that apply" };
    case "free_text":
      return { label: "Free", tone: "text-text-dim border-outline bg-surface-high", tooltip: "Answer in their own words" };
    default:
      return { label: type, tone: "text-text-dim border-outline bg-surface-high", tooltip: type };
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

export function SurveyEvalCockpit({ options, taskType, onTaskTypeChange }: SurveyEvalCockpitProps) {
  const { run, job, phase, isRunning, error, timedOut, retry } = useSurveyEval();
  const [persona, setPersona] = useState<PersonaEvalPersona | null>(null);
  const [personaModel, setPersonaModel] = useState<string>(
    options?.environment.personaModel ?? "anthropic/claude-haiku-4-5",
  );
  const [instrumentId, setInstrumentId] = useState<string>("product_attitudes_v1");
  const [tab, setTab] = useState<InspectorTab>("evaluation");
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

  const surveyResult = job?.surveyResult ?? null;
  const prompts = job?.prompts ?? surveyResult?.prompts ?? null;
  const hasRun = phase === "done" || phase === "error" || phase === "timeout";
  const status = surveyStatusLine(phase, job?.phase);
  const title = persona ? personaDescriptiveTitle(null, persona.blurb, persona.source) : "No persona chosen yet";
  const codename = persona ? personaCodename(persona.name, persona.id) : null;

  useEffect(() => {
    if (phase === "done") {
      setExportSnapshot((prev) => prev ?? {
        persona: persona ? { id: persona.id, name: persona.name, source: persona.source } : null,
        instrumentId,
        personaModel,
      });
    }
  }, [phase, persona, instrumentId, personaModel]);

  const instrumentOptions: KnobOption[] = instruments.map((item) => ({
    value: item.id,
    label: item.title,
    description: item.description,
  }));
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
              disabled={!exportSnapshot || !surveyResult}
              className={`flex items-center gap-2 rounded-md border border-outline px-4 py-2 text-xs font-medium text-text-variant transition-colors hover:bg-surface-low hover:text-text-main disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              <Sym name="download" size={18} />
              Download results
            </button>
            <button
              type="button"
              onClick={handleRun}
              disabled={!persona || !instrument || isRunning}
              className={`glow flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-xs font-medium text-on-primary transition-colors hover:bg-primary-dim disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              {isRunning ? <Sym name="autorenew" size={18} className="animate-spin" /> : <Sym name="play_arrow" fill={1} size={18} />}
              {isRunning ? "Working…" : hasRun ? "Run it again" : "Run questionnaire"}
            </button>
          </div>
        </div>

        <SurveyConfigBar
          instrument={instrumentId}
          instrumentOptions={instrumentOptions}
          onInstrument={setInstrumentId}
          personaModel={personaModel}
          personaModelOptions={personaModelOptions}
          onPersonaModel={setPersonaModel}
          disabled={isRunning}
        />
        {phase === "idle" && (
          <div className="flex shrink-0 items-start gap-2.5 border-b border-outline-dim bg-primary/10 px-lg py-2.5">
            <Sym name="lightbulb" fill={1} size={16} className="mt-0.5 flex-shrink-0 text-primary" />
            <p className="text-[12px] leading-snug text-text-variant">
              <span className="font-medium text-text-main">New here?</span> Pick a persona on the left and a
              questionnaire above, then press Run. PersonaEval plays a simulated user who fills out the form, and
              you&apos;ll see its answers and ratings.
            </p>
          </div>
        )}
        <SurveyPipeline
          phase={phase}
          jobPhase={job?.phase}
          hasPersona={persona !== null}
          hasResult={surveyResult !== null}
          personaModel={personaModel}
          instrument={instrument}
        />
        <SurveyWorkspace
          instrument={instrument}
          surveyResult={surveyResult}
          phase={phase}
          status={status}
          error={error}
          hasPersona={persona !== null}
          onRetry={handleRetry}
          instrumentsLoading={instrumentsQuery.isLoading}
          instrumentsError={instrumentsQuery.isError}
          onReloadInstruments={() => {
            void instrumentsQuery.refetch();
          }}
        />
      </main>

      <InspectorTabs
        active={tab}
        onChange={setTab}
        evaluation={<SurveyResults result={surveyResult} instrument={instrument} phase={phase} />}
        persona={<PersonaPanel persona={persona} context={null} onOpenRaw={() => setDrawerOpen(true)} />}
        prompts={<PromptPanel prompts={prompts} />}
      />

      <PersonaDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} persona={persona} context={null} />
    </div>
  );
}

function SurveyConfigBar({
  instrument,
  instrumentOptions,
  onInstrument,
  personaModel,
  personaModelOptions,
  onPersonaModel,
  disabled,
}: {
  instrument: string;
  instrumentOptions: KnobOption[];
  onInstrument: (value: string) => void;
  personaModel: string;
  personaModelOptions: KnobOption[];
  onPersonaModel: (value: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-x-5 gap-y-2 border-b border-outline-dim bg-surface-lowest px-lg py-2.5">
      {instrumentOptions.length > 0 && (
        <KnobSelect
          label="Questionnaire"
          value={instrument}
          options={instrumentOptions}
          onChange={onInstrument}
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

function SurveyPipeline({
  phase,
  jobPhase,
  hasPersona,
  hasResult,
  personaModel,
  instrument,
}: {
  phase: SurveyEvalRunPhase;
  jobPhase: string | null | undefined;
  hasPersona: boolean;
  hasResult: boolean;
  personaModel: string;
  instrument: SurveyInstrument | null;
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
      detail: "Acts as the user, guided by the persona profile",
      icon: "badge",
      status: !hasPersona ? "Select persona" : failed ? "Stopped" : phase === "done" ? "Complete" : running && rawPhase.includes("harbor") ? "Active" : "Ready",
      tone: !hasPersona ? "idle" : failed ? "error" : phase === "done" ? "done" : running ? "active" : "idle",
    },
    {
      key: "survey",
      label: "Survey",
      owner: "Questionnaire form",
      ownerTitle: "survey_form",
      detail: instrument ? `${instrument.title} · ${instrument.questions.length} questions` : "Choose a questionnaire to preview it",
      icon: "fact_check",
      status: failed ? "Needs a look" : phase === "done" ? "Complete" : running ? "Filling it in" : "Ready",
      tone: failed ? "error" : phase === "done" ? "done" : running ? "active" : "idle",
    },
    {
      key: "artifact",
      label: "Answers",
      owner: "Saved answers",
      ownerTitle: "survey_result.json",
      detail: "The answers, a step-by-step log, and a completeness check",
      icon: "description",
      status: failed ? "No answers yet" : hasResult ? "Ready to view" : running ? "Waiting" : "Waiting",
      tone: failed ? "error" : hasResult ? "done" : "idle",
    },
  ] as const;

  return (
    <section aria-label="Survey component pipeline" className="border-b border-outline-dim bg-surface-lowest px-lg py-2.5">
      <div className="grid grid-cols-1 gap-2 2xl:grid-cols-3">
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

function SurveyWorkspace({
  instrument,
  surveyResult,
  phase,
  status,
  error,
  hasPersona,
  onRetry,
  instrumentsLoading,
  instrumentsError,
  onReloadInstruments,
}: {
  instrument: SurveyInstrument | null;
  surveyResult: SurveyResult | null;
  phase: SurveyEvalRunPhase;
  status: string | null;
  error: string | null;
  hasPersona: boolean;
  onRetry: () => void;
  instrumentsLoading: boolean;
  instrumentsError: boolean;
  onReloadInstruments: () => void;
}) {
  const running = phase === "building" || phase === "running";
  const failed = phase === "error" || phase === "timeout" || (!running && !!error);

  if (!hasPersona && phase === "idle") {
    return (
      <div className="custom-scrollbar flex flex-1 items-center justify-center overflow-y-auto p-lg">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-md bg-primary/10">
            <Sym name="groups" fill={1} size={26} className="text-primary" />
          </div>
          <h3 className="font-display text-lg font-semibold text-text-main">Choose a persona to start</h3>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-text-variant">
            Pick a persona on the left and a questionnaire above, then press Run. A simulated user will fill it out and
            you&apos;ll see its answers and ratings.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="custom-scrollbar flex flex-1 justify-center overflow-y-auto p-lg">
      <div className="flex w-full max-w-4xl flex-col gap-md">
        {instrumentsError ? (
          <div className="rounded-md border border-danger/30 bg-danger/10 p-4">
            <div className="flex items-start gap-3">
              <Sym name="error" fill={1} size={20} className="mt-0.5 text-danger" />
              <div className="min-w-0 flex-1">
                <h4 className="font-display text-[15px] font-semibold text-danger">Couldn&apos;t load questionnaires</h4>
                <p className="mt-1 break-words text-[13px] leading-relaxed text-text-variant">
                  We couldn&apos;t load the questionnaires. Check your connection and try again.
                </p>
                <button
                  type="button"
                  onClick={onReloadInstruments}
                  className={`mt-3 inline-flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-3 py-1.5 text-xs font-medium text-danger transition-colors hover:bg-danger/20 ${FOCUS_RING}`}
                >
                  <Sym name="refresh" size={16} />
                  Try again
                </button>
              </div>
            </div>
          </div>
        ) : instrumentsLoading ? (
          <div className="space-y-2" aria-hidden>
            <p className="hud text-[10px] text-text-dim">Loading questionnaires…</p>
            <div className="h-12 animate-pulse rounded-md bg-surface-high" />
            <div className="h-12 animate-pulse rounded-md bg-surface-high" />
            <div className="h-12 animate-pulse rounded-md bg-surface-high" />
          </div>
        ) : instrument ? (
          <InstrumentPreview instrument={instrument} />
        ) : (
          <div className="rounded-md border border-dashed border-outline bg-surface-low px-4 py-10 text-center">
            <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
              <Sym name="fact_check" size={22} className="text-primary" />
            </div>
            <p className="text-[13px] leading-relaxed text-text-variant">
              Pick a questionnaire above to preview its questions.
            </p>
          </div>
        )}
        {running && (
          <div className="rounded-md border border-outline bg-surface-lowest px-4 py-4">
            <div className="flex items-center gap-2">
              <Sym name="autorenew" size={16} className="animate-spin text-primary" />
              <span className="hud text-[10px] text-primary">Running</span>
            </div>
            <p className="mt-2 text-[13px] text-text-main">Simulated user is answering…</p>
            {status && <p className="mt-0.5 text-[12px] text-text-dim">{status}</p>}
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-field">
              {surveyResult ? (
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{
                    width: `${Math.round(
                      (surveyResult.completion.numAnswered / Math.max(1, surveyResult.completion.numQuestions)) * 100,
                    )}%`,
                  }}
                />
              ) : (
                <div className="h-full w-1/3 animate-pulse rounded-full bg-primary/60" />
              )}
            </div>
            {surveyResult && (
              <p className="mt-1.5 hud text-[9px] text-text-dim">
                {surveyResult.completion.numAnswered} of {surveyResult.completion.numQuestions} answered
              </p>
            )}
          </div>
        )}
        {failed && (
          <div className="rounded-md border border-danger/30 bg-danger/10 p-4">
            <div className="flex items-start gap-3">
              <Sym name="error" fill={1} size={20} className="mt-0.5 text-danger" />
              <div className="min-w-0 flex-1">
                <h4 className="font-display text-[15px] font-semibold text-danger">The questionnaire didn&apos;t finish</h4>
                <p className="mt-1 break-words text-[13px] leading-relaxed text-text-variant">
                  {error ?? "Something interrupted the run. Your setup is still here — press Try again."}
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
        {surveyResult && <SurveyArtifact result={surveyResult} />}
      </div>
    </div>
  );
}

function InstrumentPreview({ instrument }: { instrument: SurveyInstrument }) {
  return (
    <section className="panel overflow-hidden rounded-md border border-outline bg-surface">
      <div className="border-b border-outline px-4 py-3">
        <p className="hud text-[10px] text-text-dim">Questionnaire preview</p>
        <div className="mt-1 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-display text-[15px] font-semibold text-text-main">{instrument.title}</h3>
            <p className="mt-1 text-[12px] leading-snug text-text-variant">{instrument.description}</p>
          </div>
          <span className="shrink-0 hud text-[9px] text-text-dim">{instrument.questions.length} questions</span>
        </div>
      </div>
      <div className="divide-y divide-outline-dim">
        {instrument.questions.map((question, index) => {
          const meta = questionTypeMeta(question.type);
          return (
            <div
              key={question.id}
              className="grid grid-cols-[48px_minmax(0,1fr)_120px] gap-3 px-4 py-3 transition-colors hover:bg-surface-low"
            >
              <span className="hud text-[10px] text-text-dim">Q{index + 1}</span>
              <div className="min-w-0">
                <p className="text-[13px] leading-relaxed text-text-main">{question.prompt}</p>
                {question.options.length > 0 && (
                  <p className="mt-1 truncate text-[11px] text-text-variant">
                    Choices: {question.options.join(", ")}
                  </p>
                )}
              </div>
              <span
                title={meta.tooltip}
                className={`justify-self-end self-start rounded border px-1.5 py-0.5 hud text-[8px] ${meta.tone}`}
              >
                {meta.label}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function SurveyArtifact({ result }: { result: SurveyResult }) {
  return (
    <section className="panel overflow-hidden rounded-md border border-outline bg-surface">
      <div className="flex items-center justify-between border-b border-outline px-4 py-3">
        <div>
          <h3 className="font-display text-[15px] font-semibold text-text-main">Completed questionnaire</h3>
          <p className="mt-1 text-[12px] text-text-variant">
            {result.completion.numAnswered} / {result.completion.numQuestions} questions answered
          </p>
        </div>
        <span
          title="Complete means the persona answered every required question."
          className={`rounded border px-1.5 py-0.5 hud text-[8px] ${result.completion.valid ? "text-secondary border-secondary/30 bg-secondary/10" : "text-danger border-danger/30 bg-danger/10"}`}
        >
          {result.completion.valid ? "Complete" : "Incomplete"}
        </span>
      </div>
      <div className="divide-y divide-outline-dim">
        {result.answers.map((answer) => (
          <AnswerRow key={answer.questionId} answer={answer} instrument={result.instrument} />
        ))}
      </div>
    </section>
  );
}

function SurveyResults({
  result,
  instrument,
  phase,
}: {
  result: SurveyResult | null;
  instrument: SurveyInstrument | null;
  phase: SurveyEvalRunPhase;
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
            <Sym name="fact_check" size={22} className="text-primary" />
          </div>
          <p className="text-[13px] leading-relaxed text-text-variant">
            Run a questionnaire to see the simulated user&apos;s answers and ratings here.
          </p>
        </div>
      </div>
    );
  }
  const meanLikert = result.completion.meanLikert;
  return (
    <div className="space-y-3 p-md">
      <section className="panel rounded-md border border-outline bg-surface p-3">
        <div className="flex items-center justify-between">
          <h3 className="hud text-[10px] text-primary">Result summary</h3>
          <Sym name="verified" fill={1} size={18} className={result.completion.valid ? "text-secondary" : "text-danger"} />
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2">
          <MetricTile value={`${result.completion.numAnswered}/${result.completion.numQuestions}`} caption="Answered" />
          <MetricTile value={result.completion.valid ? "Yes" : "No"} caption="Valid" />
          <MetricTile
            value={meanLikert == null ? "—" : meanLikert.toFixed(1)}
            caption="Average rating"
            hint="Average of the 1–5 ratings the persona gave across Likert questions."
          />
        </div>
      </section>
      <section className="panel overflow-hidden rounded-md border border-outline bg-surface">
        <div className="border-b border-outline px-3 py-2">
          <h3 className="hud text-[10px] text-text-dim">Answers</h3>
        </div>
        <div className="divide-y divide-outline-dim">
          {result.answers.map((answer) => (
            <AnswerRow key={answer.questionId} answer={answer} instrument={instrument ?? result.instrument} compact />
          ))}
        </div>
      </section>
      <section className="panel overflow-hidden rounded-md border border-outline bg-surface">
        <div className="border-b border-outline px-3 py-2">
          <h3 className="hud text-[10px] text-text-dim">Step-by-step log</h3>
        </div>
        <div className="max-h-72 divide-y divide-outline-dim overflow-auto">
          {result.trajectory.map((event, index) => (
            <TrajectoryEventRow key={`${event.timestamp}-${index}`} event={event} />
          ))}
        </div>
      </section>
    </div>
  );
}

function AnswerRow({
  answer,
  instrument,
  compact,
}: {
  answer: SurveyAnswer;
  instrument: SurveyInstrument;
  compact?: boolean;
}) {
  const question = instrument.questions.find((item) => item.id === answer.questionId);
  return (
    <div className={compact ? "px-3 py-3" : "grid grid-cols-[minmax(0,1fr)_180px] gap-4 px-4 py-3"}>
      <div className="min-w-0">
        <p className="font-mono text-[10px] text-primary">{answer.questionId}</p>
        <p className="mt-1 text-[13px] leading-relaxed text-text-main">{question?.prompt ?? answer.questionId}</p>
        {answer.rationale && (
          <p className="mt-1 font-mono text-[11px] leading-relaxed text-text-dim">{answer.rationale}</p>
        )}
      </div>
      <div className={compact ? "mt-2" : "justify-self-end text-right"}>
        <p className="font-mono text-[12px] text-text-main">{formatSurveyValue(answer.value)}</p>
        {answer.confidence != null && (
          <p className="mt-1 font-mono text-[11px] text-text-variant">
            {(answer.confidence * 100).toFixed(0)}% sure
          </p>
        )}
      </div>
    </div>
  );
}

function TrajectoryEventRow({ event }: { event: SurveyTrajectoryEvent }) {
  return (
    <div className="px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-[12px] font-medium text-text-main">
          {trajectoryActor(event.actor)} · {event.action}
        </span>
        <span className="flex-shrink-0 font-mono text-[11px] text-text-dim">{event.timestamp}</span>
      </div>
      <pre className="mt-1 max-h-20 overflow-auto whitespace-pre-wrap break-words rounded bg-field p-2 font-mono text-[11px] text-text-variant">
        {JSON.stringify({ context: event.context, outcome: event.outcome }, null, 2)}
      </pre>
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

function formatSurveyValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => String(item)).join(", ");
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default SurveyEvalCockpit;
