/**
 * RunDetail: one persisted run, rebuilt as the mockup's "Run debrief".
 *
 * Shape mirrors `data-view="runs"` (app-redesign-v3.html:340-429): a back link +
 * "Run debrief" H1 with a run-type reflection on the right, a one-line run-meta
 * breadcrumb, a headline score band + metric tiles, then the body.
 *
 * Option-aware, honestly scoped (spec §05): the runs data layer only persists
 * chatbot (`PersonaEvalResult`) runs today, so `runApplicationType` resolves to
 * "chatbot" and the chatbot debrief renders. The survey/web bodies render the
 * `SurveyResult` / `WebResult` / `WebTrace` shapes already declared in types.ts
 * and light up unchanged once those run kinds persist. See the TODO in
 * `runsShared.tsx`. No endpoint, query key, or type is changed here.
 */
import { useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  GroundingChip,
  RecChip,
  StatTile,
  appName,
  asRunDetail,
  bandBorderL,
  fmtDomain,
  fmtRunDate,
  isAgentHiccup,
  runApplicationType,
  runWebTrace,
  type RunApplicationType,
  type RunDetailView,
  type RunTranscriptTurn,
} from "./runsShared";
import { PromptPanel } from "./cockpit/PromptPanel";
import { FOCUS_RING, SCORE_BAND_CLASS, Sym, humanizeToken, scoreBand } from "./cockpit/cockpitShared";
import { Markdown } from "./Markdown";
import { api, ApiError } from "@/lib/api";
import type {
  PersonaEvalQuestionnaire,
  PersonaEvalResult,
  SurveyAnswer,
  SurveyQuestion,
  SurveyTrajectoryEvent,
  WebTraceEvent,
} from "@/lib/types";

export interface RunDetailProps {
  runId: string;
  onBack: () => void;
}

export function RunDetail({ runId, onBack }: RunDetailProps) {
  const query = useQuery<PersonaEvalResult>({
    queryKey: ["persona-eval-run", runId],
    queryFn: () => api.getPersonaEvalRun(runId),
  });

  const run = useMemo(() => (query.data ? asRunDetail(query.data) : null), [query.data]);
  const appType: RunApplicationType = run ? runApplicationType(run) : "chatbot";

  return (
    <div className="min-h-0 flex-1 overflow-auto bg-surface-dim custom-scrollbar">
      <div className="mx-auto w-full max-w-[1240px] px-6 py-7">
        {/* Header: back link + H1 (left) · run-type reflection (right) */}
        <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
          <div>
            <BackButton onBack={onBack} />
            <h1 className="font-display text-[22px] font-bold tracking-tight text-text-main">Run debrief</h1>
          </div>
          {run && <RunTypeReflection active={appType} />}
        </div>

        {query.isLoading ? (
          <DetailLoading />
        ) : query.isError ? (
          <DetailError error={query.error} onRetry={() => query.refetch()} />
        ) : !run ? (
          <DetailNotFound />
        ) : (
          <>
            <div className="mb-5">
              <PersonaPanel persona={run.persona ?? {}} />
            </div>
            {appType === "survey" ? (
              <SurveyDebrief run={run} />
            ) : appType === "web" ? (
              <WebDebrief run={run} />
            ) : (
              <ChatbotDebrief run={run} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared chrome
// ---------------------------------------------------------------------------

function BackButton({ onBack }: { onBack: () => void }) {
  return (
    <button
      type="button"
      onClick={onBack}
      className={`mb-2 flex items-center gap-1 hud text-[9px] text-primary transition-opacity hover:underline active:opacity-70 ${FOCUS_RING}`}
    >
      <Sym name="arrow_back" size={14} />
      All runs
    </button>
  );
}

/**
 * The run-type segmented control from the mockup, rendered as a reflection of
 * the loaded run's kind (a run has one fixed type, so it is not a switcher).
 */
function RunTypeReflection({ active }: { active: RunApplicationType }) {
  const items: ReadonlyArray<{ key: RunApplicationType; label: string }> = [
    { key: "chatbot", label: "Chatbot" },
    { key: "survey", label: "Survey" },
    { key: "web", label: "Web" },
  ];
  return (
    <div
      className="inline-flex rounded-md border border-outline bg-surface-low p-1"
      role="group"
      aria-label={`This run is a ${active} run`}
    >
      {items.map((it) => {
        const on = it.key === active;
        return (
          <span
            key={it.key}
            aria-current={on ? "true" : undefined}
            title={on ? `This run is a ${it.label} run.` : `${it.label} runs show up here when you run one.`}
            className={`rounded px-3 py-1.5 text-[12px] font-medium transition-colors ${
              on ? "bg-primary text-on-primary" : "text-text-dim"
            }`}
          >
            {it.label}
          </span>
        );
      })}
    </div>
  );
}

/** The one-line telemetry breadcrumb that opens each debrief body. */
function RunMetaLine({ icon, children }: { icon: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-2 hud text-[9px] leading-relaxed text-text-variant">
      <Sym name={icon} size={16} className="mt-px shrink-0 text-primary" />
      <span>{children}</span>
    </div>
  );
}

/** A short, friendly intro under the meta line (per option). */
function DebriefIntro({ children }: { children: ReactNode }) {
  return <p className="max-w-2xl text-[13px] leading-relaxed text-text-variant">{children}</p>;
}

/** Collapsible profile of the simulated persona behind a run (shared by every
 *  debrief). The full saved context is shown on demand so a reviewer can see
 *  exactly who the simulated user was. */
function PersonaPanel({
  persona,
}: {
  persona: { id?: string | null; name?: string | null; source?: string | null; context?: string | null };
}) {
  const [open, setOpen] = useState(false);
  const context = (persona.context ?? "").trim();
  const name = persona.name || "Persona";
  if (!persona.name && !context) return null;
  return (
    <section className="overflow-hidden rounded-md border border-outline bg-surface-lowest">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={`flex w-full items-center justify-between gap-2 px-4 py-3 text-left transition-colors hover:bg-surface-low ${FOCUS_RING}`}
      >
        <span className="flex min-w-0 items-center gap-2">
          <Sym name="person" fill={1} size={16} className="flex-none text-text-dim" />
          <span className="hud text-[9px] text-text-dim">Persona</span>
          <span className="truncate text-[13px] font-medium text-text-main">{name}</span>
          {persona.source && (
            <span className="hud flex-none rounded border border-outline px-1.5 py-0.5 text-[8px] text-text-dim">
              {persona.source}
            </span>
          )}
        </span>
        <span className="flex flex-none items-center gap-2">
          {context && <span className="hud text-[9px] text-text-dim">{open ? "Hide profile" : "View profile"}</span>}
          <Sym name={open ? "expand_more" : "chevron_right"} size={18} className="text-text-dim" />
        </span>
      </button>
      {open && context && (
        <div className="border-t border-outline px-4 py-3">
          <pre className="custom-scrollbar max-h-96 overflow-auto whitespace-pre-wrap break-words font-sans text-[12px] leading-relaxed text-text-variant">
            {context}
          </pre>
        </div>
      )}
    </section>
  );
}

/** A quiet dashed "nothing here" note, reused by empty bodies. */
function DashedNote({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-outline bg-surface-low px-4 py-8 text-center text-[13px] text-text-variant">
      {children}
    </div>
  );
}

/** A mint/danger validity badge (survey "Valid"/web "Valid pick"). */
function ValidityBadge({
  valid,
  validLabel,
  invalidLabel,
}: {
  valid: boolean;
  validLabel: string;
  invalidLabel: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-1 hud text-[9px] ${
        valid
          ? "border-secondary/30 bg-secondary/10 text-secondary"
          : "border-danger/30 bg-danger/10 text-danger"
      }`}
    >
      {valid ? validLabel : invalidLabel}
    </span>
  );
}

function clamp(value: number, max: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(max, value));
}

// ===========================================================================
// Chatbot debrief
// ===========================================================================

function ChatbotDebrief({ run }: { run: RunDetailView }) {
  const persona = run.persona ?? {};
  const config = run.config ?? {};
  const transcript = run.transcript ?? [];
  const q = run.questionnaire;
  const metrics = run.metricScores;
  const app = appName(config.applicationId);

  const overall = q?.overallRating ?? null;
  const band = scoreBand(overall == null ? null : overall / 10);
  const color = SCORE_BAND_CLASS[band];

  return (
    <div className="space-y-5">
      <RunMetaLine icon="forum">
        {`Chatbot run · ${app} on the ${fmtDomain(config.domain)} catalog · persona “${
          persona.name ?? "Unknown persona"
        }” · ${fmtRunDate(run.createdAt)}`}
      </RunMetaLine>
      <DebriefIntro>
        A simulated user chatted with the app for a few turns, then rated how well it understood and
        met their needs.
      </DebriefIntro>

      {/* Headline band: overall lead tile + three metric tiles */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div
          className={`rounded-md border border-outline bg-surface p-5 lg:col-span-4 border-l-4 ${
            overall == null ? "border-l-outline" : bandBorderL(band)
          }`}
        >
          <span className={`hud text-[9px] ${overall == null ? "text-text-dim" : color.text}`}>
            Overall satisfaction
          </span>
          <div className="mt-1.5 flex items-baseline gap-1.5">
            <span
              className={`font-display text-[44px] font-bold leading-none tabular-nums ${
                overall == null ? "text-text-dim" : color.text
              }`}
            >
              {overall == null ? "-" : overall}
            </span>
            <span className="text-[13px] text-text-dim">/ 10</span>
          </div>
          <p className="mt-4 text-[12px] leading-relaxed text-text-variant">
            {q?.ratingReason || "How the simulated user rated the experience, out of 10."}
          </p>
          {metrics && <GroundingChip metrics={metrics} className="mt-3" />}
        </div>

        <div className="grid grid-cols-3 gap-5 lg:col-span-8">
          <StatTile
            caption="Turns before first suggestion"
            value={metrics?.turnsToRecommendation ?? "-"}
          />
          <StatTile caption="Total turns" value={metrics?.numTurns ?? "-"} />
          <StatTile caption="Items suggested" value={metrics?.recommendedItemCount ?? "-"} />
        </div>
      </div>

      {/* Two-column: transcript & trace | self-report scorecard */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div className="space-y-3 lg:col-span-7">
          <h2 className="hud text-[10px] text-primary">Transcript &amp; trace</h2>
          {transcript.length === 0 ? (
            <DashedNote>No conversation turns were recorded for this run.</DashedNote>
          ) : (
            <div className="space-y-6 rounded-md border border-outline bg-surface p-5">
              {transcript.map((turn, i) => (
                <TranscriptTurn key={turn.turnIndex ?? i} turn={turn} index={i} appLabel={app} />
              ))}
            </div>
          )}
        </div>

        <div className="space-y-3 lg:col-span-5">
          <h2 className="hud text-[10px] text-primary">Self-report scorecard</h2>
          {q ? (
            <DebriefScorecard q={q} />
          ) : (
            <DashedNote>
              This run finished before a score was produced. There&apos;s no scorecard to show.
            </DashedNote>
          )}
        </div>
      </div>

      {/* Prompts (preserved feature; not in the mockup, kept below the fold) */}
      {run.prompts && (
        <div className="space-y-3">
          <h2 className="hud text-[10px] text-primary">Prompts</h2>
          <div className="overflow-hidden rounded-md border border-outline bg-surface">
            <PromptPanel prompts={run.prompts} />
          </div>
        </div>
      )}
    </div>
  );
}

/** One conversational turn: a persona bubble (left) + an app bubble (right). */
function TranscriptTurn({
  turn,
  index,
  appLabel,
}: {
  turn: RunTranscriptTurn;
  index: number;
  appLabel: string;
}) {
  const hiccup = isAgentHiccup(turn.assistantMessage);
  const recs = turn.recommendedItems ?? [];
  return (
    <div
      className="space-y-3 rise-in"
      style={{ animationDelay: `${Math.min(index, 6) * 30}ms`, animationFillMode: "backwards" }}
    >
      {/* Persona (left) */}
      <div className="flex gap-3">
        <div
          className="grid h-8 w-8 shrink-0 place-items-center rounded border border-primary/25 bg-primary/10"
          aria-hidden
        >
          <Sym name="face" fill={1} size={16} className="text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="rounded border border-outline bg-primary/5 p-3.5">
            <div className="mb-1.5 flex items-center justify-between gap-2">
              <span className="hud text-[9px] text-primary">Simulated user</span>
              <span className="hud text-[9px] text-text-dim">turn {index + 1}</span>
            </div>
            <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-text-main">
              {turn.userMessage || <span className="italic text-text-variant">(no message)</span>}
            </p>
            {turn.decision && turn.decision !== "continue" && (
              <div className="mt-2">
                <DecisionTag decision={turn.decision} />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* App (right) */}
      <div className="flex flex-row-reverse gap-3">
        <div
          className="grid h-8 w-8 shrink-0 place-items-center rounded border border-outline bg-surface-high"
          aria-hidden
        >
          <Sym name="smart_toy" fill={1} size={16} className="text-text-variant" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="rounded border border-outline bg-surface-low p-3.5">
            <div className="mb-1.5 flex items-center justify-between gap-2">
              <span className="hud text-[9px] text-text-dim">turn {index + 1}</span>
              <span className="hud text-[9px] text-text-variant">{appLabel}</span>
            </div>
            {hiccup ? (
              <p className="text-[13px] italic leading-relaxed text-danger">
                The app didn&apos;t reply on this turn (it may have hit an error).
              </p>
            ) : (
              <Markdown className="text-[13px] text-text-main">{turn.assistantMessage ?? ""}</Markdown>
            )}
            {recs.length > 0 && (
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {recs.map((item, ri) => (
                  <RecChip key={`${item.id}-${ri}`} item={item} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** A small tag for a non-`continue` persona decision (satisfied / gave up). */
function DecisionTag({ decision }: { decision: string }) {
  const satisfied = decision === "satisfied";
  const cls = satisfied
    ? "text-secondary border border-secondary/30 bg-secondary/10"
    : "text-warn border border-warn/30 bg-warn/10";
  const label = satisfied ? "Got what they needed" : decision === "give_up" ? "Gave up" : humanizeToken(decision);
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-px hud text-[9px] ${cls}`}>{label}</span>
  );
}

/** The right-column scorecard: the two criterion bars + the clarifying line. */
function DebriefScorecard({ q }: { q: PersonaEvalQuestionnaire }) {
  return (
    <div className="space-y-5 rounded-md border border-outline bg-surface p-5">
      <CriterionBar
        label="Stayed within my requirements"
        score={q.constraintSatisfaction}
        max={5}
        rationale={q.constraintRationale}
      />
      <CriterionBar
        label="Matched my preferences"
        score={q.preferenceSatisfaction}
        max={5}
        rationale={q.preferenceRationale}
      />
      <div className="border-t border-outline pt-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[12px] font-medium text-text-main">Asked helpful follow-up questions</span>
          <span
            className={`inline-flex items-center rounded border px-2 py-1 hud text-[9px] ${
              q.askedUsefulClarifyingQuestions
                ? "border-secondary/30 bg-secondary/10 text-secondary"
                : "border-outline bg-surface-high text-text-variant"
            }`}
          >
            {q.askedUsefulClarifyingQuestions ? "Yes" : "Not this time"}
          </span>
        </div>
        {q.clarifyingNotes && (
          <p className="mt-1.5 text-[11px] leading-snug text-text-variant">{q.clarifyingNotes}</p>
        )}
      </div>
    </div>
  );
}

/** One criterion: label + score + threshold-coloured bar + rationale. */
function CriterionBar({
  label,
  score,
  max,
  rationale,
}: {
  label: string;
  score: number;
  max: number;
  rationale: string;
}) {
  const value = clamp(score, max);
  const band = scoreBand(value / max);
  const color = SCORE_BAND_CLASS[band];
  const pct = (value / max) * 100;
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="text-[12px] font-medium text-text-main">{label}</span>
        <span className={`font-mono text-[12px] font-bold tabular-nums ${color.text}`}>
          {value} / {max}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-field">
        <div className={`h-full ${color.bar}`} style={{ width: `${pct}%` }} />
      </div>
      {rationale && <p className="mt-1.5 text-[11px] leading-snug text-text-variant">{rationale}</p>}
    </div>
  );
}

// ===========================================================================
// Survey debrief: reads `SurveyResult` (types.ts)
// ===========================================================================

function SurveyDebrief({ run }: { run: RunDetailView }) {
  const survey = run.surveyResult;
  const persona = run.persona ?? {};
  if (!survey) {
    return (
      <div className="space-y-5">
        <RunMetaLine icon="fact_check">Survey run</RunMetaLine>
        <DashedNote>No survey results were recorded for this run.</DashedNote>
      </div>
    );
  }

  const c = survey.completion;
  const questionsById = new Map<string, SurveyQuestion>(
    survey.instrument.questions.map((qq) => [qq.id, qq]),
  );
  const freeTextCount = survey.answers.filter(
    (a) => questionsById.get(a.questionId)?.type === "free_text",
  ).length;
  const instrumentLabel = survey.instrument.title || run.instrumentTitle || survey.instrument.id;
  const meanBand = c.meanLikert == null ? undefined : scoreBand(c.meanLikert / 5);

  return (
    <div className="space-y-5">
      <RunMetaLine icon="fact_check">
        {`Survey run · ${instrumentLabel}${persona.name ? ` · persona “${persona.name}”` : ""} · ${fmtRunDate(
          survey.createdAt ?? run.createdAt,
        )}`}
      </RunMetaLine>
      <DebriefIntro>
        A simulated user filled out this questionnaire; here are their answers and how complete they
        were.
      </DebriefIntro>

      {/* Stat tiles */}
      <div className="grid grid-cols-2 gap-5 sm:grid-cols-4">
        <StatTile lead caption="Questions answered" value={`${c.numAnswered}/${c.numQuestions}`} />
        <div className="flex flex-col justify-center rounded-md border border-outline bg-surface p-4">
          <span className="hud text-[9px] text-text-dim">Answers look valid</span>
          <div className="mt-1.5">
            <ValidityBadge valid={c.valid} validLabel="Valid" invalidLabel="Needs review" />
          </div>
        </div>
        <StatTile
          caption="Average agreement"
          value={c.meanLikert == null ? "-" : c.meanLikert.toFixed(1)}
          unit="/5"
          band={meanBand}
        />
        <StatTile caption="Written answers" value={freeTextCount} />
      </div>

      {/* Two-column: answers | trajectory */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div className="space-y-3 lg:col-span-7">
          <h2 className="hud text-[10px] text-primary">Answers</h2>
          {survey.answers.length === 0 ? (
            <DashedNote>No answers were recorded for this survey run.</DashedNote>
          ) : (
            <div className="divide-y divide-outline-dim rounded-md border border-outline bg-surface">
              {survey.answers.map((a, i) => (
                <SurveyAnswerRow
                  key={a.questionId}
                  answer={a}
                  question={questionsById.get(a.questionId)}
                  index={i}
                />
              ))}
            </div>
          )}
        </div>

        <div className="space-y-3 lg:col-span-5">
          <h2 className="hud text-[10px] text-primary">Trajectory</h2>
          {survey.trajectory.length === 0 ? (
            <DashedNote>No trajectory was recorded for this run.</DashedNote>
          ) : (
            <div className="space-y-2 rounded-md border border-outline bg-surface p-4 font-mono text-[11px] leading-relaxed">
              {survey.trajectory.map((e, i) => (
                <SurveyTrajectoryRow key={`${e.timestamp}-${i}`} event={e} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** One survey answer row: prompt + a type-aware value + rationale/confidence. */
function SurveyAnswerRow({
  answer,
  question,
  index,
}: {
  answer: SurveyAnswer;
  question: SurveyQuestion | undefined;
  index: number;
}) {
  const type = question?.type;
  const prompt = question?.prompt ?? answer.questionId;
  const conf = answer.confidence;
  const valueText = fmtAnswerValue(answer.value);
  const freeText = type === "free_text";
  const likert = type === "likert";
  const max = question?.maxValue ?? 5;
  const numeric = Number(answer.value);
  const band = likert && Number.isFinite(numeric) ? scoreBand(numeric / (max || 5)) : "none";
  const color = SCORE_BAND_CLASS[band];

  return (
    <div
      className="p-4 rise-in"
      style={{ animationDelay: `${Math.min(index, 6) * 30}ms`, animationFillMode: "backwards" }}
    >
      <div className="mb-1 flex items-start justify-between gap-3">
        <span className="text-[12px] font-medium text-text-main">
          Q{index + 1} · {prompt}
        </span>
        {freeText ? (
          <span className="shrink-0 font-mono text-[11px] text-text-dim">free text</span>
        ) : likert ? (
          <span className={`shrink-0 font-mono text-[12px] font-bold tabular-nums ${color.text}`}>
            {valueText} / {max}
          </span>
        ) : (
          <span className="shrink-0 font-mono text-[12px] text-text-variant">{valueText}</span>
        )}
      </div>
      {freeText ? (
        <p className="text-[11px] leading-snug text-text-variant">&ldquo;{valueText}&rdquo;</p>
      ) : answer.rationale ? (
        <p className="text-[11px] leading-snug text-text-variant">
          Why: {answer.rationale}
          {conf != null && (
            <span className="text-text-variant"> · How sure: {(conf * 100).toFixed(0)}%</span>
          )}
        </p>
      ) : conf != null ? (
        <p className="text-[11px] text-text-variant">How sure: {(conf * 100).toFixed(0)}%</p>
      ) : null}
    </div>
  );
}

/** One survey trajectory event: time · action · actor (submit highlighted). */
function SurveyTrajectoryRow({ event }: { event: SurveyTrajectoryEvent }) {
  const submit = event.action.toLowerCase().includes("submit");
  return (
    <div className="flex gap-2.5">
      <span className="shrink-0 text-text-dim">{event.timestamp}</span>
      <span className={submit ? "font-bold text-secondary" : "text-primary"}>{event.action}</span>
      <span className="truncate text-text-variant">{trajectoryActor(event.actor)}</span>
    </div>
  );
}

function fmtAnswerValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => String(item)).join(", ");
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function trajectoryActor(actor: string): string {
  const value = actor.toLowerCase();
  if (value === "agent") return "Simulated user";
  if (value === "system") return "System";
  if (value === "scorer") return "Scorer";
  return humanizeToken(actor);
}

// ===========================================================================
// Web debrief: reads `WebResult` + `WebTrace` (types.ts)
// ===========================================================================

function WebDebrief({ run }: { run: RunDetailView }) {
  const result = run.webResult;
  const persona = run.persona ?? {};
  const trace = runWebTrace(run);
  const events = trace?.events ?? [];

  if (!result) {
    return (
      <div className="space-y-5">
        <RunMetaLine icon="language">Web run</RunMetaLine>
        <DashedNote>No web result was recorded for this run.</DashedNote>
      </div>
    );
  }

  const taskLabel = run.taskTitle || run.siteName || "website task";

  return (
    <div className="space-y-5">
      <RunMetaLine icon="language">
        {`Web run · ${taskLabel}${run.siteName ? ` on ${run.siteName}` : ""}${
          persona.name ? ` · persona “${persona.name}”` : ""
        } · ${fmtRunDate(result.createdAt ?? run.createdAt)}`}
      </RunMetaLine>
      <DebriefIntro>
        A simulated user browsed the site to finish a task; here are the UX ratings and a replay of
        every step they took.
      </DebriefIntro>

      {/* UX score tiles | selected product */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div className="grid grid-cols-3 gap-3 lg:col-span-5">
          <StatTile
            lead
            caption="Met the persona's need"
            value={result.needSatisfaction}
            unit="/10"
            band={scoreBand(result.needSatisfaction / 10)}
          />
          <StatTile
            caption="Ease of use"
            value={result.easeOfUse}
            unit="/10"
            band={scoreBand(result.easeOfUse / 10)}
          />
          <StatTile
            caption="Overall experience"
            value={result.overallExperienceRating}
            unit="/10"
            band={scoreBand(result.overallExperienceRating / 10)}
          />
        </div>

        <div className="flex items-center gap-4 rounded-md border border-outline bg-surface p-5 lg:col-span-7">
          <div
            className="grid h-12 w-12 shrink-0 place-items-center rounded border border-outline bg-surface-high"
            aria-hidden
          >
            <Sym name="inventory_2" size={22} className="text-primary" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[14px] font-semibold text-text-main">
                {result.selectedProductName || "(no product chosen)"}
              </span>
              <ValidityBadge valid={result.valid} validLabel="Valid pick" invalidLabel="Invalid pick" />
            </div>
            {result.selectedProductId && (
              <div className="mt-0.5 font-mono text-[10px] text-text-dim">{result.selectedProductId}</div>
            )}
            {result.reason && (
              <p className="mt-1 text-[11px] leading-snug text-text-variant">
                Why this one: {result.reason}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Browser trace screenshot grid */}
      <div className="space-y-3">
        <h2 className="flex items-center gap-2 hud text-[10px] text-primary">
          <Sym name="route" size={14} />
          Browser trace · {events.length} step{events.length === 1 ? "" : "s"}
        </h2>
        {events.length === 0 ? (
          <DashedNote>No browser steps were captured for this run.</DashedNote>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {events.map((event, i) => (
              <WebStepCard key={event.step} event={event} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** One browser-trace step: a screenshot (or fallback) + a step caption. */
function WebStepCard({ event, index }: { event: WebTraceEvent; index: number }) {
  const [imgError, setImgError] = useState(false);
  const showImg = Boolean(event.screenshotUrl) && !imgError;
  return (
    <div
      className="overflow-hidden rounded-md border border-outline bg-surface rise-in"
      style={{ animationDelay: `${Math.min(index, 6) * 30}ms`, animationFillMode: "backwards" }}
    >
      <div className="aspect-video border-b border-outline bg-surface-low">
        {showImg ? (
          <img
            src={event.screenshotUrl ?? undefined}
            alt={`Screenshot for step ${event.step}`}
            loading="lazy"
            onError={() => setImgError(true)}
            className="h-full w-full bg-surface-lowest object-cover"
          />
        ) : (
          <div
            className="grid h-full place-items-center text-text-dim"
            title="Screenshot not available for this step"
          >
            <Sym name="image" size={22} />
          </div>
        )}
      </div>
      <div className="p-2.5">
        <div className="truncate hud text-[8px] text-text-dim">
          Step {event.step} · {webActionLabel(event)}
        </div>
        <div className="mt-0.5 truncate font-mono text-[10px] text-text-variant">
          {webActionDetail(event)}
        </div>
      </div>
    </div>
  );
}

/** The verb for a step's first action (e.g. "click", "navigate"). */
function webActionLabel(event: WebTraceEvent): string {
  const action = event.actions[0];
  if (action?.name) return action.name.replace(/_/g, " ");
  if (event.source) return event.source;
  return "step";
}

/** A compact `name(arg)` signature for a step's first action. */
function webActionDetail(event: WebTraceEvent): string {
  const action = event.actions[0];
  if (action?.name) {
    let arg: string | null = null;
    for (const value of Object.values(action.arguments ?? {})) {
      if (typeof value === "string" && value.trim()) {
        arg = value.trim();
        break;
      }
      if (typeof value === "number") {
        arg = String(value);
        break;
      }
    }
    const clip = (text: string) => (text.length > 22 ? text.slice(0, 21) + "…" : text);
    return arg ? `${action.name}(${clip(arg)})` : `${action.name}()`;
  }
  const message = (event.message || "").trim();
  return message ? clip40(message) : "-";
}

function clip40(text: string): string {
  return text.length > 40 ? text.slice(0, 39) + "…" : text;
}

// ===========================================================================
// States
// ===========================================================================

function DetailLoading() {
  return (
    <div className="space-y-5" aria-hidden>
      <div className="h-4 w-72 animate-rb-pulse rounded bg-surface-high" />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div className="h-36 animate-rb-pulse rounded-md bg-surface-high lg:col-span-4" />
        <div className="grid grid-cols-3 gap-5 lg:col-span-8">
          <div className="h-36 animate-rb-pulse rounded-md bg-surface-high" />
          <div className="h-36 animate-rb-pulse rounded-md bg-surface-high" />
          <div className="h-36 animate-rb-pulse rounded-md bg-surface-high" />
        </div>
      </div>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div className="h-72 animate-rb-pulse rounded-md bg-surface-high lg:col-span-7" />
        <div className="h-72 animate-rb-pulse rounded-md bg-surface-high lg:col-span-5" />
      </div>
    </div>
  );
}

function DetailNotFound() {
  return (
    <div className="rounded-md border border-dashed border-outline bg-surface px-6 py-14 text-center rise-in">
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-md border border-dashed border-outline bg-surface-high">
        <Sym name="search_off" size={26} className="text-text-dim" />
      </div>
      <h2 className="font-display text-[15px] font-semibold text-text-main">
        We couldn&apos;t find this run
      </h2>
      <p className="mx-auto mt-2 max-w-sm text-[13px] leading-relaxed text-text-variant">
        It may have been deleted. Go back to the list to pick another.
      </p>
    </div>
  );
}

function DetailError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const notFound = error instanceof ApiError && error.status === 404;
  if (notFound) return <DetailNotFound />;
  const message =
    error instanceof ApiError
      ? error.message
      : "Something went wrong loading the details. Try again in a moment.";
  return (
    <div className="rounded-md border border-outline border-l-4 border-l-danger bg-surface px-5 py-8 text-center rise-in">
      <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-md border border-danger/30 bg-danger/10">
        <Sym name="error" fill={1} size={22} className="text-danger" />
      </div>
      <h2 className="font-display text-[15px] font-semibold text-text-main">
        We couldn&apos;t open this run
      </h2>
      <p className="mx-auto mt-1.5 max-w-md break-words text-[13px] leading-relaxed text-text-variant">
        {message}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className={`mt-4 inline-flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-4 py-2 text-[12px] text-danger transition ease-out hover:border-danger/60 hover:bg-danger/20 active:scale-[0.97] ${FOCUS_RING}`}
      >
        <Sym name="refresh" size={16} />
        Try again
      </button>
    </div>
  );
}

export default RunDetail;
