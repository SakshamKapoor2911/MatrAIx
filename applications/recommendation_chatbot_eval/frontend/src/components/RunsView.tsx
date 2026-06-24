/**
 * RunsView — the Runs history surface, folded inside PersonaEval.
 *
 * Rendered below the TopBar when the PersonaEval runs sub-view is active. The
 * sub-route is driven entirely by the URL (via App's handlers):
 *
 *   view=runs (no `run`)           → the LIST (this file)
 *   `run` set, no `compareWith`    → <RunDetail/>
 *   `run` + `compareWith`          → <RunCompare/>
 *
 * The list is a calm, scannable table of persisted persona-eval runs styled to
 * the Executive Precision tokens. Each row is a keyboard-focusable button that
 * opens the run; the only loud element is the `RatingChip`, the surface's
 * signature. A "Compare" toggle turns rows into a two-pick selection that
 * launches the baseline-anchored side-by-side compare.
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { RatingChip } from "./RatingChip";
import { RunDetail } from "./RunDetail";
import { RunCompare } from "./RunCompare";
import { DomainPill, SourceTag, fmtGoalContext, fmtRunDate } from "./runsShared";
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
    <div className="min-h-0 flex-1 overflow-auto bg-background">
      <div className="mx-auto w-full max-w-[1100px] px-lg py-7">
        {/* Header */}
        <div className="mb-5 flex flex-wrap items-center gap-x-3 gap-y-2">
          <button
            type="button"
            onClick={onClose}
            className={`flex items-center gap-1.5 rounded-md border border-outline-variant px-3 py-1.5 text-label-md font-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface ${FOCUS_RING}`}
          >
            <Sym name="arrow_back" size={16} />
            Cockpit
          </button>
          <h1 className="text-display font-display text-on-surface">Runs</h1>
          {!query.isLoading && !query.isError && (
            <span className="font-mono-sm text-mono-sm text-on-surface-variant">
              {runs.length} {runs.length === 1 ? "run" : "runs"}
            </span>
          )}

          <div className="ml-auto flex items-center gap-2">
            {runs.length >= 2 && (
              <button
                type="button"
                onClick={toggleCompareMode}
                aria-pressed={comparing}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-label-md font-label-md transition-colors ${FOCUS_RING} ${
                  comparing
                    ? "bg-primary text-on-primary shadow-sm hover:bg-primary-container"
                    : "border border-outline-variant text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                }`}
              >
                <Sym name="compare_arrows" size={16} />
                {comparing ? "Cancel compare" : "Compare"}
              </button>
            )}
            <button
              type="button"
              onClick={() => query.refetch()}
              disabled={query.isFetching}
              className={`flex items-center gap-1.5 rounded-md border border-outline-variant px-3 py-1.5 text-label-md font-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface disabled:opacity-55 ${FOCUS_RING}`}
            >
              <Sym name="refresh" size={16} className={query.isFetching ? "animate-rb-spin" : ""} />
              {query.isFetching ? "Refreshing…" : "Refresh"}
            </button>
          </div>

          {comparing && (
            <div className="flex w-full items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2">
              <Sym name="compare_arrows" size={18} className="text-primary" />
              <span className="text-body-sm text-on-surface-variant">
                Pick two runs — the first is the baseline.{" "}
                <span className="font-mono-sm text-on-surface-variant">{picks.length}/2 selected</span>
              </span>
              <button
                type="button"
                onClick={launchCompare}
                disabled={picks.length !== 2}
                className={`ml-auto flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-label-md font-label-md text-on-primary shadow-sm transition-colors hover:bg-primary-container disabled:opacity-55 ${FOCUS_RING}`}
              >
                Compare 2 runs
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
  "grid grid-cols-[28px_64px_minmax(0,1.6fr)_minmax(0,0.9fr)_minmax(0,1.1fr)_64px_80px] items-center gap-3";

function RunsTable({ runs, comparing, picks, onOpen, onTogglePick }: RunsTableProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
      {/* Column header */}
      <div
        className={`${ROW_GRID} border-b border-border-soft bg-surface-container-low px-3.5 py-2 text-[10.5px] font-semibold uppercase tracking-[0.04em] text-on-surface-variant`}
      >
        <span aria-hidden />
        <span>Rating</span>
        <span>Persona</span>
        <span>Domain</span>
        <span>Goal context</span>
        <span className="text-right">Turns</span>
        <span className="text-right">When</span>
      </div>

      <ul className="divide-y divide-border-soft">
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
                  picked ? "bg-primary/5" : "hover:bg-surface-container-low"
                } ${pickDisabled ? "cursor-not-allowed opacity-45" : ""}`}
              >
                {/* Selection affordance (compare mode only) */}
                <span className="flex justify-center" aria-hidden>
                  {comparing ? (
                    <span
                      className={`flex h-4 w-4 items-center justify-center rounded border ${
                        picked
                          ? "border-primary bg-primary text-on-primary"
                          : "border-outline-variant bg-surface-container-lowest"
                      }`}
                    >
                      {picked ? <Sym name="check" size={12} /> : null}
                    </span>
                  ) : null}
                </span>

                {/* Rating — the scannable signature */}
                <span className="flex">
                  <RatingChip rating={run.overallRating ?? null} />
                </span>

                {/* Persona + source */}
                <span className="flex min-w-0 items-center gap-2">
                  <span className="truncate text-body-md font-medium text-on-surface">
                    {run.personaName ?? "Unnamed persona"}
                  </span>
                  <SourceTag source={run.source} />
                </span>

                {/* Domain */}
                <span className="flex">
                  <DomainPill domain={run.domain} />
                </span>

                {/* Goal context */}
                <span className="truncate text-body-sm text-on-surface-variant">
                  {fmtGoalContext(run.goalContextId)}
                </span>

                {/* Turns */}
                <span className="text-right font-mono-sm text-mono-sm tabular-nums text-on-surface-variant">
                  {run.numTurns ?? "—"}
                </span>

                {/* When */}
                <span className="text-right font-mono-sm text-mono-sm tabular-nums text-on-surface-variant">
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
    <div className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft" aria-hidden>
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 border-b border-border-soft px-3.5 py-3.5 last:border-b-0"
        >
          <div className="h-5 w-12 animate-rb-pulse rounded-md bg-surface-container-high" />
          <div className="h-3.5 w-48 animate-rb-pulse rounded bg-surface-container-high" />
          <div className="h-5 w-16 animate-rb-pulse rounded-md bg-surface-container" />
          <div className="ml-auto h-3.5 w-16 animate-rb-pulse rounded bg-surface-container" />
        </div>
      ))}
    </div>
  );
}

function ListEmpty({ onClose }: { onClose: () => void }) {
  return (
    <div className="rounded-xl border border-dashed border-border-soft bg-surface-container-lowest px-6 py-14 text-center">
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-surface-container">
        <Sym name="history" size={26} className="text-on-surface-variant" />
      </div>
      <h2 className="text-headline-md font-headline-md text-on-surface">No runs yet</h2>
      <p className="mx-auto mt-2 max-w-md text-body-md leading-relaxed text-on-surface-variant">
        Launch a PersonaEval run from the cockpit. Completed runs land here, newest first — ready to
        open or compare side by side.
      </p>
      <button
        type="button"
        onClick={onClose}
        className={`mt-4 inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-label-md font-label-md text-on-primary shadow-sm transition-colors hover:bg-primary-container ${FOCUS_RING}`}
      >
        <Sym name="play_arrow" fill={1} size={16} />
        Go to the cockpit
      </button>
    </div>
  );
}

function ListError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message = error instanceof ApiError ? error.message : "The runs list could not be loaded.";
  return (
    <div className="rounded-xl border border-error/40 bg-error-container/40 px-5 py-8 text-center">
      <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-error/10">
        <Sym name="error" fill={1} size={22} className="text-error" />
      </div>
      <h2 className="text-headline-md font-headline-md text-on-surface">Couldn&apos;t load runs</h2>
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

export default RunsView;
