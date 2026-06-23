/**
 * RunDetail — one persisted persona-eval run, full-bleed.
 *
 * Header: persona + source, domain, goal context, date, and the `RatingChip`.
 * Body: the run's `transcript` rendered as alternating persona/RecBot rows. A
 * turn whose RecBot message reads as an error/empty hiccup is styled in
 * `text-error` so the failure shows honestly rather than passing as a normal
 * reply. Recommended items render as compact chips. The run's evaluator
 * scorecard closes the page via the cockpit's `Scorecard`.
 *
 * Styled to the Executive Precision tokens; skeleton loading, plain-language
 * error, and not-found states.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { RatingChip } from "./RatingChip";
import { Scorecard } from "./cockpit/Scorecard";
import {
  DomainPill,
  GroundingChip,
  RecChip,
  SourceTag,
  asRunDetail,
  fmtGoalContext,
  fmtRunDate,
  isAgentHiccup,
  type RunTranscriptTurn,
} from "./runsShared";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { Markdown } from "./Markdown";
import { api, ApiError } from "@/lib/api";
import type { PersonaEvalResult } from "@/lib/types";

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

  return (
    <div className="min-h-0 flex-1 overflow-auto bg-background">
      <div className="mx-auto w-full max-w-[860px] px-lg py-6">
        <BackButton onBack={onBack} />

        {query.isLoading ? (
          <DetailLoading />
        ) : query.isError ? (
          <DetailError error={query.error} onRetry={() => query.refetch()} />
        ) : !run ? (
          <DetailNotFound />
        ) : (
          <RunDetailBody run={run} runId={runId} />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loaded body
// ---------------------------------------------------------------------------

function RunDetailBody({ run, runId }: { run: ReturnType<typeof asRunDetail>; runId: string }) {
  const persona = run.persona ?? {};
  const config = run.config ?? {};
  const transcript = run.transcript ?? [];
  const overall = run.questionnaire?.overallRating ?? null;

  return (
    <>
      {/* Header card */}
      <header className="mt-3 rounded-xl border border-border-soft bg-surface-container-lowest p-4 shadow-soft">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <h1 className="text-headline-md font-headline-md text-on-surface">
            {persona.name ?? "Unnamed persona"}
          </h1>
          <SourceTag source={persona.source ?? null} />
          <DomainPill domain={config.domain ?? null} />
          <div className="ml-auto flex items-center gap-2">
            <GroundingChip metrics={run.metricScores} />
            <RatingChip rating={overall} size="md" />
          </div>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-body-sm text-on-surface-variant">
          <span className="flex items-center gap-1.5">
            <Sym name="theater_comedy" size={14} className="text-outline" />
            {fmtGoalContext(config.goalContextId)}
          </span>
          <span className="font-mono-sm text-mono-sm">{fmtRunDate(run.createdAt)}</span>
          <span className="font-mono-sm text-mono-sm" title="Run id">
            {runId}
          </span>
        </div>
      </header>

      {/* Trajectory */}
      <section className="mt-5">
        <div className="mb-2.5 text-label-md font-label-md uppercase tracking-wider text-on-surface-variant">
          Trajectory
        </div>
        {transcript.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border-soft bg-surface-container-lowest px-4 py-8 text-center text-body-sm text-on-surface-variant">
            This run has no recorded turns.
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {transcript.map((turn, i) => (
              <TranscriptTurnRow key={turn.turnIndex ?? i} turn={turn} index={i} />
            ))}
          </div>
        )}
      </section>

      {/* Evaluation scorecard (reuses the cockpit's Scorecard) */}
      {run.questionnaire && run.metricScores ? (
        <section className="mt-5">
          <div className="mb-2.5 text-label-md font-label-md uppercase tracking-wider text-on-surface-variant">
            Evaluation
          </div>
          <div className="-mx-md">
            <Scorecard questionnaire={run.questionnaire} metrics={run.metricScores} phase="done" />
          </div>
        </section>
      ) : (
        <section className="mt-5 rounded-xl border border-dashed border-border-soft bg-surface-container-lowest px-4 py-6 text-center text-body-sm text-on-surface-variant">
          This run finished without a recorded evaluation.
        </section>
      )}
    </>
  );
}

/** One turn: a persona row and a RecBot row, with recommended-item chips. */
function TranscriptTurnRow({ turn, index }: { turn: RunTranscriptTurn; index: number }) {
  const hiccup = isAgentHiccup(turn.assistantMessage);
  const recs = turn.recommendedItems ?? [];
  return (
    <article className="rounded-xl border border-border-soft bg-surface-container-lowest p-4 shadow-soft">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-label-md font-label-md uppercase tracking-wider text-on-surface-variant">
          Turn {index + 1}
        </span>
        {turn.decision && turn.decision !== "continue" && <DecisionTag decision={turn.decision} />}
      </div>

      {/* Persona */}
      <div className="mb-2.5">
        <div className="mb-1 flex items-center gap-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10" aria-hidden>
            <Sym name="face" fill={1} size={12} className="text-primary" />
          </span>
          <span className="text-label-md font-label-md font-semibold text-on-surface-variant">Persona</span>
        </div>
        <p className="whitespace-pre-wrap text-body-md leading-relaxed text-on-surface-variant">
          {turn.userMessage || <span className="italic text-outline">(no message)</span>}
        </p>
      </div>

      {/* RecBot */}
      <div>
        <div className="mb-1 flex items-center gap-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-surface-container-high" aria-hidden>
            <Sym name="smart_toy" fill={1} size={12} className="text-on-surface-variant" />
          </span>
          <span className="text-label-md font-label-md font-semibold text-on-surface-variant">RecBot</span>
        </div>
        {hiccup ? (
          <p className="whitespace-pre-wrap text-body-md italic leading-relaxed text-error">
            RecBot did not return a reply for this turn.
          </p>
        ) : (
          <Markdown className="text-body-md text-on-surface">{turn.assistantMessage ?? ""}</Markdown>
        )}

        {recs.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {recs.map((item, ri) => (
              <RecChip key={`${item.id}-${ri}`} item={item} />
            ))}
          </div>
        )}
      </div>
    </article>
  );
}

/** A small tag for a non-`continue` persona decision (satisfied / gave up). */
function DecisionTag({ decision }: { decision: string }) {
  const satisfied = decision === "satisfied";
  const cls = satisfied
    ? "bg-success-container text-on-success-container"
    : "bg-warning-container text-on-warning-container";
  const label = satisfied ? "satisfied" : decision === "give_up" ? "gave up" : decision;
  return (
    <span className={`inline-flex items-center rounded-md px-1.5 py-px text-label-md font-label-md font-medium ${cls}`}>
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Chrome + states
// ---------------------------------------------------------------------------

function BackButton({ onBack }: { onBack: () => void }) {
  return (
    <button
      type="button"
      onClick={onBack}
      className={`flex items-center gap-1.5 rounded-md border border-outline-variant px-3 py-1.5 text-label-md font-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface ${FOCUS_RING}`}
    >
      <Sym name="arrow_back" size={16} />
      Runs
    </button>
  );
}

function DetailLoading() {
  return (
    <div className="mt-3 space-y-4" aria-hidden>
      <div className="h-24 animate-rb-pulse rounded-xl bg-surface-container" />
      <div className="h-32 animate-rb-pulse rounded-xl bg-surface-container" />
      <div className="h-32 animate-rb-pulse rounded-xl bg-surface-container" />
    </div>
  );
}

function DetailNotFound() {
  return (
    <div className="mt-5 rounded-xl border border-dashed border-border-soft bg-surface-container-lowest px-6 py-14 text-center">
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-surface-container">
        <Sym name="search_off" size={26} className="text-on-surface-variant" />
      </div>
      <h2 className="text-headline-md font-headline-md text-on-surface">Run not found</h2>
      <p className="mx-auto mt-2 max-w-sm text-body-md leading-relaxed text-on-surface-variant">
        This run may have been removed. Head back to the list to pick another.
      </p>
    </div>
  );
}

function DetailError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const notFound = error instanceof ApiError && error.status === 404;
  if (notFound) return <DetailNotFound />;
  const message = error instanceof ApiError ? error.message : "This run could not be loaded.";
  return (
    <div className="mt-5 rounded-xl border border-error/40 bg-error-container/40 px-5 py-8 text-center">
      <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-error/10">
        <Sym name="error" fill={1} size={22} className="text-error" />
      </div>
      <h2 className="text-headline-md font-headline-md text-on-surface">Couldn&apos;t load this run</h2>
      <p className="mx-auto mt-1.5 max-w-md break-words text-body-sm leading-relaxed text-on-surface-variant">
        {message}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className={`mt-4 inline-flex items-center gap-1.5 rounded-md border border-outline-variant px-4 py-2 text-label-md font-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface ${FOCUS_RING}`}
      >
        <Sym name="refresh" size={16} />
        Try again
      </button>
    </div>
  );
}

export default RunDetail;
