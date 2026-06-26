/**
 * RunCompare — two persisted runs read side by side, baseline-anchored.
 *
 * The left run (A) is the BASELINE; the right run (B) is read against it. Each
 * scored dimension shows the baseline value, the candidate value, and the delta
 * — tinted green for an improvement and red for a regression (for "turns to
 * first rec" a lower value is better, so the tint inverts). A "Order by
 * regressions" toggle floats the biggest regressions to the top so a reviewer
 * sees what got worse first.
 *
 * Above the deltas, the two run headers make the config delta obvious, and any
 * differences in domain / goal context / persona source are called out. The
 * per-turn trajectories are aligned row-for-row below, so the eye can read each
 * turn straight across.
 *
 * Styled to the matrAIx tokens; skeleton loading + plain-language error states.
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { RatingChip } from "./RatingChip";
import {
  DomainPill,
  SourceTag,
  asRunDetail,
  fmtDomain,
  fmtGoalContext,
  fmtRunDate,
  fmtSource,
  isAgentHiccup,
  type RunDetailView,
  type RunTranscriptTurn,
} from "./runsShared";
import { Markdown } from "./Markdown";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { api, ApiError } from "@/lib/api";
import type { PersonaEvalResult } from "@/lib/types";

export interface RunCompareProps {
  runIdA: string;
  runIdB: string;
  onBack: () => void;
}

export function RunCompare({ runIdA, runIdB, onBack }: RunCompareProps) {
  const qA = useQuery<PersonaEvalResult>({
    queryKey: ["persona-eval-run", runIdA],
    queryFn: () => api.getPersonaEvalRun(runIdA),
  });
  const qB = useQuery<PersonaEvalResult>({
    queryKey: ["persona-eval-run", runIdB],
    queryFn: () => api.getPersonaEvalRun(runIdB),
  });

  const runA = useMemo(() => (qA.data ? asRunDetail(qA.data) : null), [qA.data]);
  const runB = useMemo(() => (qB.data ? asRunDetail(qB.data) : null), [qB.data]);

  const loading = qA.isLoading || qB.isLoading;
  const errored = qA.isError || qB.isError;

  return (
    <div className="min-h-0 flex-1 overflow-auto bg-surface-dim custom-scrollbar">
      <div className="mx-auto w-full max-w-[1180px] px-6 py-7">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className={`flex items-center gap-1.5 rounded-md border border-outline bg-surface-low px-3 py-1.5 text-[12px] text-text-variant transition-colors hover:border-primary hover:text-text-main ${FOCUS_RING}`}
          >
            <Sym name="arrow_back" size={16} />
            All runs
          </button>
          <div className="flex flex-col">
            <span className="hud text-[10px] text-primary">PersonaEval · Compare</span>
            <h1 className="font-display text-[22px] font-bold tracking-tight text-text-main">Compare two runs</h1>
          </div>
        </div>

        {loading ? (
          <CompareLoading />
        ) : errored ? (
          <CompareError
            error={qA.error ?? qB.error}
            onRetry={() => {
              void qA.refetch();
              void qB.refetch();
            }}
          />
        ) : runA && runB ? (
          <CompareBody runA={runA} runB={runB} idA={runIdA} idB={runIdB} />
        ) : null}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Score dimensions + delta model
// ---------------------------------------------------------------------------

interface Dimension {
  label: string;
  max: number;
  a: number | null;
  b: number | null;
  /** When true a LOWER value is the better one (e.g. turns to first rec). */
  lowerIsBetter?: boolean;
}

/** The signed improvement of B over the baseline A (positive = better). */
function improvement(d: Dimension): number | null {
  if (d.a === null || d.b === null) return null;
  const raw = d.b - d.a;
  return d.lowerIsBetter ? -raw : raw;
}

// ---------------------------------------------------------------------------
// Loaded body
// ---------------------------------------------------------------------------

function CompareBody({
  runA,
  runB,
  idA,
  idB,
}: {
  runA: RunDetailView;
  runB: RunDetailView;
  idA: string;
  idB: string;
}) {
  const [orderByRegressions, setOrderByRegressions] = useState(false);
  const diffs = configDiffs(runA, runB);

  const dimensions: Dimension[] = [
    {
      label: "Overall satisfaction",
      max: 10,
      a: runA.questionnaire?.overallRating ?? null,
      b: runB.questionnaire?.overallRating ?? null,
    },
    {
      label: "Stayed within my requirements",
      max: 5,
      a: runA.questionnaire?.constraintSatisfaction ?? null,
      b: runB.questionnaire?.constraintSatisfaction ?? null,
    },
    {
      label: "Matched my preferences",
      max: 5,
      a: runA.questionnaire?.preferenceSatisfaction ?? null,
      b: runB.questionnaire?.preferenceSatisfaction ?? null,
    },
    {
      label: "Turns before first suggestion",
      max: Math.max(runA.metricScores?.numTurns ?? 0, runB.metricScores?.numTurns ?? 0, 1),
      a: runA.metricScores?.turnsToRecommendation ?? null,
      b: runB.metricScores?.turnsToRecommendation ?? null,
      lowerIsBetter: true,
    },
    {
      label: "Items suggested",
      max: Math.max(runA.metricScores?.recommendedItemCount ?? 0, runB.metricScores?.recommendedItemCount ?? 0, 1),
      a: runA.metricScores?.recommendedItemCount ?? null,
      b: runB.metricScores?.recommendedItemCount ?? null,
    },
  ];

  // Order by regressions: most-negative improvement first; ties keep input order.
  const ordered = orderByRegressions
    ? [...dimensions].sort((x, y) => (improvement(x) ?? 0) - (improvement(y) ?? 0))
    : dimensions;

  const regressionCount = dimensions.filter((d) => (improvement(d) ?? 0) < 0).length;

  return (
    <div className="mt-4">
      {/* Two headers, side by side: A = baseline, B = candidate. */}
      <div className="grid gap-4 sm:grid-cols-2">
        <SideHeader run={runA} runId={idA} role="Baseline" />
        <SideHeader run={runB} runId={idB} role="Candidate" />
      </div>

      {/* Config deltas, called out explicitly. */}
      <div className="mt-4 rounded-md border border-outline bg-surface p-4">
        <div className="mb-2 hud text-[10px] text-primary">What changed between the two</div>
        {diffs.length === 0 ? (
          <p className="text-[13px] text-text-variant">
            Both runs used the same settings — domain, conversation style, and persona source all
            match.
          </p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {diffs.map((d) => (
              <li key={d.label} className="flex flex-wrap items-baseline gap-x-2 text-[13px]">
                <span className="font-medium text-text-main">{d.label}</span>
                <span className="font-mono text-[11px] text-text-variant">{d.a}</span>
                <Sym name="arrow_forward" size={12} className="text-text-dim" />
                <span className="font-mono text-[11px] text-text-variant">{d.b}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Score deltas — the analytical core (baseline-anchored). */}
      <div className="mt-4 rounded-md border border-outline bg-surface p-4">
        <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <div className="hud text-[10px] text-primary">How the candidate scored vs the baseline</div>
          <span className="hud text-[9px] text-text-variant">
            {regressionCount} score{regressionCount === 1 ? "" : "s"} dropped
          </span>
          <button
            type="button"
            onClick={() => setOrderByRegressions((v) => !v)}
            aria-pressed={orderByRegressions}
            className={`ml-auto flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12px] transition-colors ${FOCUS_RING} ${
              orderByRegressions
                ? "bg-primary text-on-primary"
                : "border border-outline bg-surface-low text-text-variant hover:border-primary hover:text-text-main"
            }`}
          >
            <Sym name="sort" size={15} />
            Show biggest drops first
          </button>
        </div>

        {/* Column header */}
        <div className="grid grid-cols-[minmax(0,1.4fr)_72px_72px_minmax(0,1fr)] items-center gap-x-3 border-b border-outline pb-1.5 hud text-[9px] text-text-dim">
          <span>What we measured</span>
          <span className="text-right">Baseline</span>
          <span className="text-right">Candidate</span>
          <span className="text-right">Change</span>
        </div>

        <ul className="divide-y divide-outline-dim">
          {ordered.map((d) => (
            <DeltaRow key={d.label} dim={d} />
          ))}
        </ul>

        <p className="mt-2.5 text-[11px] leading-relaxed text-text-dim">
          Green = the candidate did better · red = it did worse · grey = no change. For turns before
          first suggestion, fewer turns is better.
        </p>
      </div>

      {/* Aligned per-turn trajectories. */}
      <div className="mt-4">
        <div className="mb-2.5 hud text-[10px] text-primary">The two conversations, turn by turn</div>
        <AlignedTrajectories runA={runA} runB={runB} />
      </div>
    </div>
  );
}

/** One side's header: persona / source / domain / goal / date + rating + role. */
function SideHeader({ run, runId, role }: { run: RunDetailView; runId: string; role: string }) {
  const persona = run.persona ?? {};
  const config = run.config ?? {};
  const baseline = role === "Baseline";
  return (
    <div
      className={`rounded-md border border-outline bg-surface p-4 ${
        baseline ? "" : "border-l-4 border-l-primary"
      }`}
    >
      <div className="mb-2 flex items-center gap-2">
        <span
          className={`inline-flex items-center rounded px-1.5 py-px hud text-[9px] ${
            baseline ? "bg-surface-high text-text-variant" : "bg-primary/10 text-primary"
          }`}
        >
          {baseline ? "Baseline" : "Candidate (measured against the baseline)"}
        </span>
        <div className="ml-auto">
          <RatingChip rating={run.questionnaire?.overallRating ?? null} />
        </div>
      </div>
      <div className="truncate text-[13px] font-semibold text-text-main" title={persona.name ?? undefined}>
        {persona.name ?? "Unnamed persona"}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <DomainPill domain={config.domain ?? null} />
        <SourceTag source={persona.source ?? null} />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-text-variant">
        <span>{fmtGoalContext(config.goalContextId)}</span>
        <span className="font-mono text-[11px]">{fmtRunDate(run.createdAt)}</span>
        <span className="truncate font-mono text-[11px]" title="Run id">
          {runId}
        </span>
      </div>
    </div>
  );
}

/** One score dimension: baseline · candidate · tinted delta + a mini bar pair. */
function DeltaRow({ dim }: { dim: Dimension }) {
  const imp = improvement(dim);
  const delta = dim.a !== null && dim.b !== null ? dim.b - dim.a : null;
  const tone =
    imp === null || imp === 0 ? "flat" : imp > 0 ? "up" : "down";
  const toneClass =
    tone === "up"
      ? "text-secondary bg-secondary/10"
      : tone === "down"
        ? "text-danger bg-danger/10"
        : "text-text-variant bg-surface-high";
  const arrow = tone === "up" ? "arrow_upward" : tone === "down" ? "arrow_downward" : "remove";

  const pct = (v: number | null) => (v === null ? 0 : (Math.max(0, Math.min(dim.max, v)) / dim.max) * 100);

  return (
    <li className="grid grid-cols-[minmax(0,1.4fr)_72px_72px_minmax(0,1fr)] items-center gap-x-3 py-2.5">
      <div className="min-w-0">
        <div className="truncate text-[13px] font-medium text-text-main">{dim.label}</div>
        {/* Mini paired bars: baseline (muted) over candidate (primary). */}
        <div className="mt-1 space-y-1" aria-hidden>
          <div className="h-1 overflow-hidden rounded-full bg-field">
            <div className="h-full rounded-full bg-outline" style={{ width: `${pct(dim.a)}%` }} />
          </div>
          <div className="h-1 overflow-hidden rounded-full bg-field">
            <div className="h-full rounded-full bg-primary" style={{ width: `${pct(dim.b)}%` }} />
          </div>
        </div>
      </div>
      <span className="text-right font-mono text-[11px] tabular-nums text-text-variant">
        {dim.a === null ? "—" : dim.a}
      </span>
      <span className="text-right font-mono text-[11px] tabular-nums text-text-main">
        {dim.b === null ? "—" : dim.b}
      </span>
      <span className="flex justify-end">
        <span
          className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 font-mono text-[11px] font-semibold tabular-nums ${toneClass}`}
        >
          <Sym name={arrow} size={13} />
          {delta === null ? "—" : `${delta > 0 ? "+" : ""}${delta}`}
        </span>
      </span>
    </li>
  );
}

/**
 * Aligned per-turn trajectories: row N of the baseline sits beside row N of the
 * candidate, so the eye reads each turn straight across. Hiccups are flagged.
 */
function AlignedTrajectories({ runA, runB }: { runA: RunDetailView; runB: RunDetailView }) {
  const a = runA.transcript ?? [];
  const b = runB.transcript ?? [];
  const rows = Math.max(a.length, b.length);

  if (rows === 0) {
    return (
      <div className="rounded-md border border-dashed border-outline bg-surface-low px-4 py-6 text-center text-[13px] text-text-dim">
        Neither run recorded a conversation.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-md border border-outline bg-surface">
      {/* Side labels */}
      <div className="grid grid-cols-2 gap-px border-b border-outline bg-outline">
        <div className="bg-surface-low px-3 py-2 hud text-[9px] text-text-dim">
          Baseline · {fmtDomain(runA.config?.domain ?? null)}
        </div>
        <div className="bg-surface-low px-3 py-2 hud text-[9px] text-text-dim">
          Candidate · {fmtDomain(runB.config?.domain ?? null)}
        </div>
      </div>
      <ul>
        {Array.from({ length: rows }).map((_, i) => (
          <li key={i} className="grid grid-cols-2 gap-px border-b border-outline-dim bg-outline-dim last:border-b-0">
            <TurnCell turn={a[i]} index={i} />
            <TurnCell turn={b[i]} index={i} />
          </li>
        ))}
      </ul>
    </div>
  );
}

/** One aligned turn cell (persona + assistant lines), or a quiet placeholder. */
function TurnCell({ turn, index }: { turn: RunTranscriptTurn | undefined; index: number }) {
  if (!turn) {
    return <div className="bg-surface px-3 py-2.5 text-[13px] italic text-text-dim">turn {index + 1} didn&apos;t happen</div>;
  }
  const hiccup = isAgentHiccup(turn.assistantMessage);
  return (
    <div className="bg-surface px-3 py-2.5">
      <div className="mb-1 hud text-[9px] text-text-dim">Turn {index + 1}</div>
      <p className="line-clamp-2 text-[13px] text-text-variant">{turn.userMessage || "(no message)"}</p>
      {hiccup ? (
        <p className="mt-1 line-clamp-2 text-[13px] italic text-danger">The app didn&apos;t reply here.</p>
      ) : (
        <Markdown className="mt-1 line-clamp-2 text-[13px] text-text-main">
          {turn.assistantMessage ?? ""}
        </Markdown>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Config-diff computation
// ---------------------------------------------------------------------------

interface ConfigDiff {
  label: string;
  a: string;
  b: string;
}

/** Collect the human-visible config differences worth calling out. */
function configDiffs(a: RunDetailView, b: RunDetailView): ConfigDiff[] {
  const out: ConfigDiff[] = [];
  const domA = fmtDomain(a.config?.domain ?? null);
  const domB = fmtDomain(b.config?.domain ?? null);
  if (domA !== domB) out.push({ label: "Domain", a: domA, b: domB });

  const goalA = fmtGoalContext(a.config?.goalContextId);
  const goalB = fmtGoalContext(b.config?.goalContextId);
  if (goalA !== goalB) out.push({ label: "Goal context", a: goalA, b: goalB });

  const srcA = fmtSource(a.persona?.source ?? null);
  const srcB = fmtSource(b.persona?.source ?? null);
  if (srcA !== srcB) out.push({ label: "Persona source", a: srcA, b: srcB });

  return out;
}

// ---------------------------------------------------------------------------
// States
// ---------------------------------------------------------------------------

function CompareLoading() {
  return (
    <div className="mt-4 space-y-4" aria-hidden>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="h-28 animate-pulse rounded-md bg-surface-high" />
        <div className="h-28 animate-pulse rounded-md bg-surface-high" />
      </div>
      <div className="h-48 animate-pulse rounded-md bg-surface-high" />
    </div>
  );
}

function CompareError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message =
    error instanceof ApiError
      ? error.message
      : "One of the two runs wouldn't load. Try again in a moment.";
  return (
    <div className="mt-5 rounded-md border border-outline border-l-4 border-l-danger bg-surface px-5 py-8 text-center">
      <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-md border border-danger/30 bg-danger/10">
        <Sym name="error" fill={1} size={22} className="text-danger" />
      </div>
      <h2 className="font-display text-[15px] font-semibold text-text-main">We couldn&apos;t load the comparison</h2>
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

export default RunCompare;
