/**
 * RunDetail — one persisted persona-eval run, full-bleed.
 *
 * Header: persona + source, domain, goal context, date, and the `RatingChip`.
 * Body: the run's `transcript` rendered as alternating simulated-user / assistant
 * rows. A turn whose assistant message reads as an error/empty hiccup is styled
 * in the danger tone so the failure shows honestly rather than passing as a
 * normal reply. Recommended items render as compact chips. The run's evaluator
 * scorecard closes the page via the cockpit's `Scorecard`.
 *
 * Styled to the matrAIx tokens; skeleton loading, plain-language error, and
 * not-found states.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { RatingChip } from "./RatingChip";
import { PromptPanel } from "./cockpit/PromptPanel";
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
    <div className="min-h-0 flex-1 overflow-auto bg-surface-dim custom-scrollbar">
      <div className="mx-auto w-full max-w-[860px] px-6 py-6">
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
      <header className="mt-3 rounded-md border border-outline bg-surface p-4">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <h1 className="font-display text-[15px] font-semibold text-text-main">
            {persona.name ?? "Unnamed persona"}
          </h1>
          <SourceTag source={persona.source ?? null} />
          <DomainPill domain={config.domain ?? null} />
          <div className="ml-auto flex items-center gap-2">
            <GroundingChip metrics={run.metricScores} />
            <RatingChip rating={overall} size="md" />
          </div>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-text-variant">
          <span className="flex items-center gap-1.5">
            <Sym name="theater_comedy" size={14} className="text-text-dim" />
            {fmtGoalContext(config.goalContextId)}
          </span>
          <span className="font-mono text-[11px]">{fmtRunDate(run.createdAt)}</span>
          <span className="font-mono text-[11px]" title="Run id">
            {runId}
          </span>
        </div>
      </header>

      <p className="mt-3 max-w-2xl text-[13px] leading-relaxed text-text-dim">
        A simulated user chatted with the app for a few turns, then rated how well it understood and
        met their needs.
      </p>

      {/* Trajectory */}
      <section className="mt-5">
        <div className="mb-2.5 hud text-[10px] text-primary">Transcript &amp; trace</div>
        {transcript.length === 0 ? (
          <div className="rounded-md border border-dashed border-outline bg-surface-low px-4 py-8 text-center text-[13px] text-text-dim">
            No conversation turns were recorded for this run.
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
          <div className="mb-2.5 hud text-[10px] text-primary">Evaluation</div>
          <div className="-mx-md">
            <Scorecard questionnaire={run.questionnaire} metrics={run.metricScores} phase="done" />
          </div>
        </section>
      ) : (
        <section className="mt-5 rounded-md border border-dashed border-outline bg-surface-low px-4 py-6 text-center text-[13px] text-text-dim">
          This run finished before a score was produced — there&apos;s no scorecard to show.
        </section>
      )}

      {/* Prompts */}
      <section className="mt-5">
        <div className="mb-2.5 hud text-[10px] text-primary">Prompts</div>
        <div className="-mx-md">
          <PromptPanel prompts={run.prompts ?? null} />
        </div>
      </section>
    </>
  );
}

/** One turn: a persona row and an assistant row, with recommended-item chips. */
function TranscriptTurnRow({ turn, index }: { turn: RunTranscriptTurn; index: number }) {
  const hiccup = isAgentHiccup(turn.assistantMessage);
  const recs = turn.recommendedItems ?? [];
  return (
    <article className="rounded-md border border-outline bg-surface p-4">
      <div className="mb-2 flex items-center gap-2">
        <span className="hud text-[9px] text-text-dim">Turn {index + 1}</span>
        {turn.decision && turn.decision !== "continue" && <DecisionTag decision={turn.decision} />}
      </div>

      {/* Persona */}
      <div className="mb-2.5">
        <div className="mb-1 flex items-center gap-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10" aria-hidden>
            <Sym name="face" fill={1} size={12} className="text-primary" />
          </span>
          <span className="hud text-[9px] text-primary">Simulated user</span>
        </div>
        <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-text-variant">
          {turn.userMessage || <span className="italic text-text-dim">(no message)</span>}
        </p>
      </div>

      {/* Assistant */}
      <div>
        <div className="mb-1 flex items-center gap-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-full border border-outline bg-surface-high" aria-hidden>
            <Sym name="smart_toy" fill={1} size={12} className="text-text-variant" />
          </span>
          <span className="hud text-[9px] text-text-variant">Assistant</span>
        </div>
        {hiccup ? (
          <p className="whitespace-pre-wrap text-[13px] italic leading-relaxed text-danger">
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
    </article>
  );
}

/** A small tag for a non-`continue` persona decision (satisfied / gave up). */
function DecisionTag({ decision }: { decision: string }) {
  const satisfied = decision === "satisfied";
  const cls = satisfied
    ? "text-secondary border border-secondary/30 bg-secondary/10"
    : "text-warn border border-warn/30 bg-warn/10";
  const label = satisfied ? "Got what they needed" : decision === "give_up" ? "Gave up" : decision;
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-px hud text-[9px] ${cls}`}>
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
      className={`flex items-center gap-1.5 rounded-md border border-outline bg-surface-low px-3 py-1.5 text-[12px] text-text-variant transition-colors hover:border-primary hover:text-text-main ${FOCUS_RING}`}
    >
      <Sym name="arrow_back" size={16} />
      All runs
    </button>
  );
}

function DetailLoading() {
  return (
    <div className="mt-3 space-y-4" aria-hidden>
      <div className="h-24 animate-pulse rounded-md bg-surface-high" />
      <div className="h-32 animate-pulse rounded-md bg-surface-high" />
      <div className="h-32 animate-pulse rounded-md bg-surface-high" />
    </div>
  );
}

function DetailNotFound() {
  return (
    <div className="mt-5 rounded-md border border-dashed border-outline bg-surface px-6 py-14 text-center">
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-md border border-dashed border-outline bg-surface-high">
        <Sym name="search_off" size={26} className="text-text-dim" />
      </div>
      <h2 className="font-display text-[15px] font-semibold text-text-main">We couldn&apos;t find this run</h2>
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
    <div className="mt-5 rounded-md border border-outline border-l-4 border-l-danger bg-surface px-5 py-8 text-center">
      <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-md border border-danger/30 bg-danger/10">
        <Sym name="error" fill={1} size={22} className="text-danger" />
      </div>
      <h2 className="font-display text-[15px] font-semibold text-text-main">We couldn&apos;t open this run</h2>
      <p className="mx-auto mt-1.5 max-w-md break-words text-[13px] leading-relaxed text-text-variant">
        {message}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className={`mt-4 inline-flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-4 py-2 text-[12px] text-danger transition-colors hover:bg-danger/20 ${FOCUS_RING}`}
      >
        <Sym name="refresh" size={16} />
        Try again
      </button>
    </div>
  );
}

export default RunDetail;
