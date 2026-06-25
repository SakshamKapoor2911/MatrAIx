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
  if (phase === "building") return "Preparing the survey respondent environment…";
  if (phase !== "running") return null;
  const raw = (jobPhase ?? "").toLowerCase();
  if (raw.includes("collect")) return "Collecting survey artifact…";
  if (raw.includes("harbor")) return "Persona agent is completing the survey…";
  return "Running the survey task…";
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
  const title = persona ? personaDescriptiveTitle(null, persona.blurb, persona.source) : "No persona selected";
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
              disabled={!exportSnapshot || !surveyResult}
              className={`flex items-center gap-2 rounded-md border border-outline-variant px-4 py-2 text-label-md font-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              <Sym name="download" size={18} />
              Export log
            </button>
            <button
              type="button"
              onClick={handleRun}
              disabled={!persona || !instrument || isRunning}
              className={`flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-label-md font-label-md text-on-primary shadow-sm transition-colors hover:bg-primary-container disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              {isRunning ? <Sym name="autorenew" size={18} className="animate-rb-spin" /> : <Sym name="play_arrow" fill={1} size={18} />}
              {isRunning ? "Running…" : hasRun ? "Re-run survey" : "Run survey"}
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
    <div className="flex shrink-0 flex-wrap items-center gap-x-5 gap-y-2 border-b border-border-soft bg-surface-container-lowest px-lg py-2.5 shadow-sm">
      {instrumentOptions.length > 0 && (
        <KnobSelect
          label="Survey instrument"
          value={instrument}
          options={instrumentOptions}
          onChange={onInstrument}
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
      owner: "Persona task runtime",
      detail: `${personaModel} · persona prompt injection`,
      icon: "badge",
      status: !hasPersona ? "Select persona" : failed ? "Interrupted" : phase === "done" ? "Complete" : running && rawPhase.includes("harbor") ? "Active" : "Ready",
      tone: !hasPersona ? "idle" : failed ? "error" : phase === "done" ? "done" : running ? "active" : "idle",
    },
    {
      key: "survey",
      label: "Survey",
      owner: "survey_form task",
      detail: instrument ? `${instrument.title} · ${instrument.questions.length} questions` : "Load survey instrument",
      icon: "fact_check",
      status: failed ? "Check run" : phase === "done" ? "Complete" : running ? "Collecting responses" : "Ready",
      tone: failed ? "error" : phase === "done" ? "done" : running ? "active" : "idle",
    },
    {
      key: "artifact",
      label: "Artifact",
      owner: "survey_result.json",
      detail: "answers + trajectory + completion",
      icon: "description",
      status: failed ? "Missing artifact" : hasResult ? "Available" : running ? "Waiting" : "Waiting",
      tone: failed ? "error" : hasResult ? "done" : "idle",
    },
  ] as const;

  return (
    <section aria-label="Survey component pipeline" className="border-b border-border-soft bg-surface-container-lowest px-lg py-2.5">
      <div className="grid grid-cols-1 gap-2 2xl:grid-cols-3">
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
                <p className="mt-1 line-clamp-2 text-body-sm leading-snug text-on-surface-variant">{node.detail}</p>
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

function SurveyWorkspace({
  instrument,
  surveyResult,
  phase,
  status,
  error,
  hasPersona,
  onRetry,
}: {
  instrument: SurveyInstrument | null;
  surveyResult: SurveyResult | null;
  phase: SurveyEvalRunPhase;
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
            <Sym name="groups" fill={1} size={26} className="text-primary" />
          </div>
          <h3 className="text-headline-md font-headline-md text-on-surface">Pick a persona to begin</h3>
          <p className="mx-auto mt-2 max-w-sm text-body-md leading-relaxed text-on-surface-variant">
            Choose a persona and a survey instrument, then run the survey to collect the persona&apos;s structured response.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="custom-scrollbar flex flex-1 justify-center overflow-y-auto p-lg">
      <div className="flex w-full max-w-4xl flex-col gap-md">
        {instrument && <InstrumentPreview instrument={instrument} />}
        {running && (
          <div className="flex items-center justify-center gap-2 rounded-lg border border-border-soft bg-surface-container-lowest px-4 py-4">
            <Sym name="autorenew" size={18} className="animate-rb-spin text-primary" />
            <span className="text-body-sm text-on-surface-variant">{status ?? "Running the survey task…"}</span>
          </div>
        )}
        {failed && (
          <div className="rounded-lg border border-error/40 bg-error-container/40 p-4">
            <div className="flex items-start gap-3">
              <Sym name="error" fill={1} size={20} className="mt-0.5 text-error" />
              <div className="min-w-0 flex-1">
                <h4 className="text-body-md font-semibold text-on-surface">This survey run didn&apos;t finish</h4>
                <p className="mt-1 break-words text-body-sm leading-relaxed text-on-surface-variant">
                  {error ?? "The survey run stopped unexpectedly. Your configuration is unchanged."}
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
        {surveyResult && <SurveyArtifact result={surveyResult} />}
      </div>
    </div>
  );
}

function InstrumentPreview({ instrument }: { instrument: SurveyInstrument }) {
  return (
    <section className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
      <div className="border-b border-border-soft bg-surface-container-low px-4 py-3">
        <h3 className="text-headline-sm font-headline-sm text-on-surface">{instrument.title}</h3>
        <p className="mt-1 text-body-sm text-on-surface-variant">{instrument.description}</p>
      </div>
      <div className="divide-y divide-border-soft">
        {instrument.questions.map((question, index) => (
          <div key={question.id} className="grid grid-cols-[48px_minmax(0,1fr)_120px] gap-3 px-4 py-3">
            <span className="font-mono-sm text-mono-sm text-on-surface-variant">Q{index + 1}</span>
            <div className="min-w-0">
              <p className="text-body-md text-on-surface">{question.prompt}</p>
              {question.options.length > 0 && (
                <p className="mt-1 truncate text-body-sm text-on-surface-variant">
                  Options: {question.options.join(", ")}
                </p>
              )}
            </div>
            <span className="justify-self-end rounded border border-border-soft bg-surface-container px-2 py-1 font-mono-sm text-mono-sm text-on-surface-variant">
              {question.type}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function SurveyArtifact({ result }: { result: SurveyResult }) {
  return (
    <section className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
      <div className="flex items-center justify-between border-b border-border-soft bg-surface-container-low px-4 py-3">
        <div>
          <h3 className="text-headline-sm font-headline-sm text-on-surface">Survey artifact</h3>
          <p className="mt-1 text-body-sm text-on-surface-variant">
            {result.completion.numAnswered} / {result.completion.numQuestions} questions answered
          </p>
        </div>
        <span className={`rounded border px-2 py-1 text-label-md font-label-md ${result.completion.valid ? "border-success/40 bg-success-container text-on-success-container" : "border-error/40 bg-error-container text-on-error-container"}`}>
          {result.completion.valid ? "Valid" : "Incomplete"}
        </span>
      </div>
      <div className="divide-y divide-border-soft">
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
          <Sym name="fact_check" size={28} className="text-outline" />
          <p className="mt-2 text-body-sm leading-relaxed text-on-surface-variant">
            Run a survey to see the persona&apos;s completed answers here.
          </p>
        </div>
      </div>
    );
  }
  const meanLikert = result.completion.meanLikert;
  return (
    <div className="space-y-3 p-md">
      <section className="rounded-xl border border-border-soft bg-surface-container-lowest p-3 shadow-soft">
        <div className="flex items-center justify-between">
          <h3 className="text-headline-sm font-headline-sm uppercase tracking-wider text-on-surface">Survey result</h3>
          <Sym name="verified" fill={1} size={18} className={result.completion.valid ? "text-success" : "text-error"} />
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2">
          <MetricTile value={`${result.completion.numAnswered}/${result.completion.numQuestions}`} caption="Answered" />
          <MetricTile value={result.completion.valid ? "Yes" : "No"} caption="Valid" />
          <MetricTile value={meanLikert == null ? "—" : meanLikert.toFixed(1)} caption="Mean Likert" />
        </div>
      </section>
      <section className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
        <div className="border-b border-border-soft bg-surface-container-low px-3 py-2">
          <h3 className="text-headline-sm font-headline-sm text-on-surface">Answers</h3>
        </div>
        <div className="divide-y divide-border-soft">
          {result.answers.map((answer) => (
            <AnswerRow key={answer.questionId} answer={answer} instrument={instrument ?? result.instrument} compact />
          ))}
        </div>
      </section>
      <section className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
        <div className="border-b border-border-soft bg-surface-container-low px-3 py-2">
          <h3 className="text-headline-sm font-headline-sm text-on-surface">Trajectory</h3>
        </div>
        <div className="max-h-72 divide-y divide-border-soft overflow-auto">
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
        <p className="font-mono-sm text-mono-sm text-primary">{answer.questionId}</p>
        <p className="mt-1 text-body-md leading-relaxed text-on-surface">{question?.prompt ?? answer.questionId}</p>
        {answer.rationale && (
          <p className="mt-1 text-body-sm leading-relaxed text-on-surface-variant">{answer.rationale}</p>
        )}
      </div>
      <div className={compact ? "mt-2" : "justify-self-end text-right"}>
        <p className="font-mono text-sm text-on-surface">{formatSurveyValue(answer.value)}</p>
        {answer.confidence != null && (
          <p className="mt-1 font-mono-sm text-mono-sm text-on-surface-variant">
            confidence {(answer.confidence * 100).toFixed(0)}%
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
        <span className="truncate text-body-sm font-medium text-on-surface">
          {event.actor} / {event.action}
        </span>
        <span className="flex-shrink-0 font-mono-sm text-mono-sm text-on-surface-variant">{event.timestamp}</span>
      </div>
      <pre className="mt-1 max-h-20 overflow-auto whitespace-pre-wrap break-words rounded bg-surface-container-low p-2 font-mono-sm text-mono-sm text-on-surface-variant">
        {JSON.stringify({ context: event.context, outcome: event.outcome }, null, 2)}
      </pre>
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

function formatSurveyValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => String(item)).join(", ");
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default SurveyEvalCockpit;
