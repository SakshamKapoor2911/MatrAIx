/**
 * RunsView: the Runs history surface, folded inside PersonaEval.
 *
 * Rendered below the TopBar when the PersonaEval runs sub-view is active. The
 * sub-route is driven entirely by the URL (via App's handlers):
 *
 *   view=runs (no `run`)           → the LIST (this file)
 *   `run` set, no `compareWith`    → <RunDetail/>
 *   `run` + `compareWith`          → <RunCompare/>
 *
 * The list is a calm, scannable table of persisted persona-eval runs styled to
 * the PersonaEval tokens. Each row is a keyboard-focusable button that opens the
 * run; the only loud element is the `RatingChip`, the surface's signature. A
 * "Compare" toggle turns rows into a two-pick selection that launches the
 * baseline-anchored side-by-side compare.
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { RatingChip } from "./RatingChip";
import { RunDetail } from "./RunDetail";
import { RunCompare } from "./RunCompare";
import {
  AppTypeTag,
  DomainPill,
  SourceTag,
  fmtGoalContext,
  fmtRunDate,
  runSummaryAppType,
} from "./runsShared";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { api, ApiError } from "@/lib/api";
import type { PersonaEvalRunSummary, PersonaEvalRunsResponse } from "@/lib/types";

export interface RunsViewProps {
  /** The run currently open (from the URL); `null` = show the list. */
  runId: string | null;
  /** The second run to compare against; `null` = no compare. */
  compareWith: string | null;
  /** Open a single run's detail view. */
  openRun: (id: string) => void;
  /** Open the side-by-side compare for two runs. */
  compareRuns: (a: string, b: string) => void;
  /** Return to the list (clears `run` + `compareWith`). */
  backToList: () => void;
  /** Leave the Runs sub-view entirely, back to the cockpit. */
  onClose: () => void;
}

export function RunsView({
  runId,
  compareWith,
  openRun,
  compareRuns,
  backToList,
  onClose,
}: RunsViewProps) {
  // Sub-route: compare wins, then detail, else the list below.
  if (runId && compareWith) {
    return <RunCompare runIdA={runId} runIdB={compareWith} onBack={backToList} />;
  }
  if (runId) {
    return <RunDetail runId={runId} onBack={backToList} />;
  }
  return <RunsList openRun={openRun} compareRuns={compareRuns} onClose={onClose} />;
}

// ---------------------------------------------------------------------------
// The list
// ---------------------------------------------------------------------------

interface RunsListProps {
  openRun: (id: string) => void;
  compareRuns: (a: string, b: string) => void;
  onClose: () => void;
}

function RunsList({ openRun, compareRuns, onClose }: RunsListProps) {
  const query = useQuery<PersonaEvalRunsResponse>({
    queryKey: ["persona-eval-runs"],
    queryFn: api.listPersonaEvalRuns,
  });

  // Compare mode: rows become a two-pick selection. We keep the picks in
  // insertion order so the first-picked run lands on the left of the compare
  // (the baseline that the second is read against).
  const [comparing, setComparing] = useState(false);
  const [picks, setPicks] = useState<string[]>([]);

  const runs = useMemo(() => query.data?.runs ?? [], [query.data]);

  function toggleCompareMode() {
    setComparing((on) => !on);
    setPicks([]);
  }

  function togglePick(id: string) {
    setPicks((prev) => {
      if (prev.includes(id)) return prev.filter((p) => p !== id);
      if (prev.length >= 2) return prev; // cap at two
      return [...prev, id];
    });
  }

  function launchCompare() {
    if (picks.length === 2) compareRuns(picks[0], picks[1]);
  }

  return (
    <div className="min-h-0 flex-1 overflow-auto bg-surface-dim custom-scrollbar">
      <div className="mx-auto w-full max-w-[1180px] px-6 py-7">
        {/* Header */}
        <div className="mb-5 flex flex-wrap items-center gap-x-3 gap-y-2">
          <button
            type="button"
            onClick={onClose}
            className={`flex items-center gap-1.5 rounded-md border border-outline bg-surface-low h-9 px-3 text-[12px] text-text-variant transition ease-out hover:border-primary hover:bg-surface hover:text-text-main active:scale-[0.97] ${FOCUS_RING}`}
          >
            <Sym name="arrow_back" size={16} />
            Back to cockpit
          </button>
          <div className="flex flex-col">
            <span className="hud text-[10px] text-primary">PersonaEval · Runs</span>
            <h1 className="font-display text-[22px] font-bold tracking-tight text-text-main">Runs</h1>
          </div>
          {!query.isLoading && !query.isError && (
            <span className="font-mono text-[11px] text-text-variant">
              {runs.length} {runs.length === 1 ? "saved run" : "saved runs"}
            </span>
          )}

          <div className="ml-auto flex items-center gap-2">
            {runs.length >= 2 && (
              <button
                type="button"
                onClick={toggleCompareMode}
                aria-pressed={comparing}
                className={`flex items-center gap-1.5 rounded-md h-9 px-3 text-[12px] transition ease-out active:scale-[0.97] ${FOCUS_RING} ${
                  comparing
                    ? "bg-primary text-on-primary hover:bg-primary-dim"
                    : "border border-outline bg-surface-low text-text-variant hover:border-primary hover:bg-surface hover:text-text-main"
                }`}
              >
                <Sym name="compare_arrows" size={16} />
                {comparing ? "Cancel" : "Compare two runs"}
              </button>
            )}
            <button
              type="button"
              onClick={() => query.refetch()}
              disabled={query.isFetching}
              className={`flex items-center gap-1.5 rounded-md border border-outline bg-surface-low h-9 px-3 text-[12px] text-text-variant transition ease-out hover:border-primary hover:bg-surface hover:text-text-main active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              <Sym name="refresh" size={16} className={query.isFetching ? "animate-rb-spin" : ""} />
              {query.isFetching ? "Checking for new runs…" : "Refresh"}
            </button>
          </div>

          <p className="w-full max-w-2xl text-[13px] leading-relaxed text-text-variant">
            Each row is one simulation. Click it to read the full transcript and scores, or turn on
            Compare to put two side by side.
          </p>

          {comparing && (
            <div className="flex w-full items-center gap-3 rounded-md border border-primary/30 bg-primary/10 px-3 py-2 rise-in">
              <Sym name="compare_arrows" size={18} className="shrink-0 text-primary" />
              <span className="min-w-0 text-[13px] text-text-variant">
                Pick two runs to compare. The first one you choose is the baseline; the second is
                measured against it.{" "}
                <span className="font-mono text-[11px] text-text-variant">({picks.length} of 2 chosen)</span>
              </span>
              <button
                type="button"
                onClick={launchCompare}
                disabled={picks.length !== 2}
                className={`ml-auto flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md bg-primary h-9 px-3 text-[12px] text-on-primary transition ease-out hover:bg-primary-dim active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
              >
                Compare these two
              </button>
            </div>
          )}
        </div>

        {/* Body: loading / error / empty / table */}
        {query.isLoading ? (
          <ListLoading />
        ) : query.isError ? (
          <ListError error={query.error} onRetry={() => query.refetch()} />
        ) : runs.length === 0 ? (
          <ListEmpty onClose={onClose} />
        ) : (
          <RunsTable
            runs={runs}
            comparing={comparing}
            picks={picks}
            onOpen={openRun}
            onTogglePick={togglePick}
          />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Table
// ---------------------------------------------------------------------------

interface RunsTableProps {
  runs: PersonaEvalRunSummary[];
  comparing: boolean;
  picks: string[];
  onOpen: (id: string) => void;
  onTogglePick: (id: string) => void;
}

/** Shared grid template so the header and every row align exactly. */
const ROW_GRID =
  "grid grid-cols-[28px_64px_72px_minmax(0,1.6fr)_minmax(0,0.9fr)_minmax(0,1.1fr)_64px_80px] items-center gap-3";

function RunsTable({ runs, comparing, picks, onOpen, onTogglePick }: RunsTableProps) {
  return (
    <div className="panel overflow-hidden rounded-md border border-outline bg-surface rise-in">
      {/* Column header */}
      <div
        className={`${ROW_GRID} border-b border-outline bg-surface-low px-3.5 py-2 hud text-[9px] text-text-dim`}
      >
        <span aria-hidden />
        <span title="The simulated user's overall rating, out of 10. Green is great, amber is mixed, red means it fell short.">
          Score
        </span>
        <span title="Which kind of app was tested: a chatbot, a survey, or a website.">Kind</span>
        <span>Simulated user</span>
        <span>Domain</span>
        <span>Conversation style</span>
        <span className="text-right">Turns</span>
        <span className="text-right">When</span>
      </div>

      <ul className="divide-y divide-outline-dim">
        {runs.map((run) => {
          const picked = picks.includes(run.id);
          const pickDisabled = comparing && !picked && picks.length >= 2;
          return (
            <li key={run.id}>
              <button
                type="button"
                onClick={() => (comparing ? onTogglePick(run.id) : onOpen(run.id))}
                disabled={pickDisabled}
                aria-pressed={comparing ? picked : undefined}
                className={`${ROW_GRID} w-full px-3.5 py-2.5 text-left transition-colors ${FOCUS_RING} ${
                  picked
                    ? "bg-primary/10 active:bg-primary/20"
                    : "hover:bg-surface-low active:bg-surface-high"
                } ${pickDisabled ? "cursor-not-allowed opacity-45" : ""}`}
              >
                {/* Selection affordance (compare mode only) */}
                <span className="flex justify-center" aria-hidden>
                  {comparing ? (
                    <span
                      className={`flex h-4 w-4 items-center justify-center rounded border ${
                        picked
                          ? "border-primary bg-primary text-on-primary"
                          : "border-outline bg-surface-lowest"
                      }`}
                    >
                      {picked ? <Sym name="check" size={12} /> : null}
                    </span>
                  ) : null}
                </span>

                {/* Rating: the scannable signature */}
                <span className="flex">
                  <RatingChip rating={run.overallRating ?? null} />
                </span>

                {/* Kind: app-type tag (chatbot today; forward-compatible) */}
                <span className="flex">
                  <AppTypeTag type={runSummaryAppType(run)} />
                </span>

                {/* Persona + source */}
                <span className="flex min-w-0 items-center gap-2">
                  <span
                    className="truncate text-[13px] font-medium text-text-main"
                    title={run.personaName ?? "Unnamed persona"}
                  >
                    {run.personaName ?? "Unnamed persona"}
                  </span>
                  <SourceTag source={run.source} />
                </span>

                {/* Domain */}
                <span className="flex">
                  <DomainPill domain={run.domain} />
                </span>

                {/* Goal context */}
                <span className="truncate text-[13px] text-text-variant">
                  {fmtGoalContext(run.goalContextId)}
                </span>

                {/* Turns */}
                <span className="text-right font-mono text-[11px] tabular-nums text-text-variant">
                  {run.numTurns ?? "-"}
                </span>

                {/* When */}
                <span className="text-right font-mono text-[11px] tabular-nums text-text-variant">
                  {fmtRunDate(run.createdAt)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// List states (loading / error / empty)
// ---------------------------------------------------------------------------

function ListLoading() {
  return (
    <div className="overflow-hidden rounded-md border border-outline bg-surface" aria-hidden>
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 border-b border-outline-dim px-3.5 py-3.5 last:border-b-0"
        >
          <div className="h-5 w-12 animate-rb-pulse rounded-md bg-surface-high" />
          <div className="h-3.5 w-48 animate-rb-pulse rounded bg-surface-high" />
          <div className="h-5 w-16 animate-rb-pulse rounded-md bg-surface-high" />
          <div className="ml-auto h-3.5 w-16 animate-rb-pulse rounded bg-surface-high" />
        </div>
      ))}
    </div>
  );
}

function ListEmpty({ onClose }: { onClose: () => void }) {
  return (
    <div className="rounded-md border border-dashed border-outline bg-surface px-6 py-14 text-center rise-in">
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-md border border-dashed border-outline bg-surface-high">
        <Sym name="history" size={26} className="text-text-dim" />
      </div>
      <h2 className="font-display text-[15px] font-semibold text-text-main">No saved runs yet</h2>
      <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-text-variant">
        Once you run a simulation, it&apos;s saved here so you can reopen it, read the full transcript
        and scores, or compare two runs side by side. Head to the cockpit to start your first one.
      </p>
      <button
        type="button"
        onClick={onClose}
        className={`mt-4 inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-[12px] text-on-primary glow transition ease-out hover:bg-primary-dim active:scale-[0.97] ${FOCUS_RING}`}
      >
        <Sym name="play_arrow" fill={1} size={16} />
        Start your first run
      </button>
    </div>
  );
}

function ListError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message =
    error instanceof ApiError
      ? error.message
      : "Something went wrong fetching your saved runs. This is usually a brief connection hiccup.";
  return (
    <div className="rounded-md border border-outline border-l-4 border-l-danger bg-surface px-5 py-8 text-center rise-in">
      <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-md border border-danger/30 bg-danger/10">
        <Sym name="error" fill={1} size={22} className="text-danger" />
      </div>
      <h2 className="font-display text-[15px] font-semibold text-text-main">We couldn&apos;t load your runs</h2>
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

export default RunsView;
