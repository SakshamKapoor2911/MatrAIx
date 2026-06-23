/**
 * Trajectory — the cockpit's centre conversation feed.
 *
 * Ports the mockup's pure-conversation view: a slim scenario banner, then the
 * turn-by-turn trajectory (a "Turn N" marker, the persona bubble on the right,
 * the RecBot reply on the left with its recommended-item card + tool-plan
 * fold), closed by a "Run complete" marker once the run finishes.
 *
 * Each job turn carries both the persona message and the RecBot reply, so one
 * `TurnView` renders one marker + two bubbles. The component covers the live
 * states the run can be in:
 *   - loading: a skeleton transcript while a run is building / before turns land;
 *   - failed: a plain-language cause + a Retry that preserves the config;
 *   - empty: a teaching empty state when no persona is selected / no run yet.
 *
 * Tool-plan fold state + the focused turn (for J/K navigation) are owned by the
 * parent so the keyboard shortcuts can drive every fold/turn at once; this
 * component registers each turn's DOM node so the parent can scroll to it.
 */
import { useEffect, useRef } from "react";

import { PersonaBubble, RecBotBubble, TurnMarker } from "./TurnBubble";
import { FOCUS_RING, Sym } from "./cockpitShared";
import type { Domain, GoalContext, TurnView } from "@/lib/types";
import type { PersonaEvalRunPhase } from "@/lib/usePersonaEval";

export interface TrajectoryProps {
  turns: TurnView[];
  domain: Domain;
  personaName: string;
  /** SUT description for the scenario banner. */
  sutDescription: string | null;
  /** The goal-context the run used (for the scenario heading). */
  goalContext: GoalContext | null;
  /** Run lifecycle phase. */
  phase: PersonaEvalRunPhase;
  /** A coarse "what's happening now" line while running. */
  liveStatus: string | null;
  /** Error text from a failed / timed-out run, if any. */
  error: string | null;
  /** Whether a persona is selected (drives the empty state). */
  hasPersona: boolean;
  /** Which tool-plan folds are open (by turn index). */
  expandedTurns: Set<number>;
  onToggleTurn: (index: number) => void;
  /** The focused turn (J/K navigation), or null. */
  focusedTurnIndex: number | null;
  /** Register a turn's DOM node so the parent can scroll to it. */
  registerTurnRef: (index: number, el: HTMLDivElement | null) => void;
  /** Retry the run, preserving the current config. */
  onRetry: () => void;
}

export function Trajectory({
  turns,
  domain,
  personaName,
  sutDescription,
  goalContext,
  phase,
  liveStatus,
  error,
  hasPersona,
  expandedTurns,
  onToggleTurn,
  focusedTurnIndex,
  registerTurnRef,
  onRetry,
}: TrajectoryProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isRunning = phase === "building" || phase === "running";
  // A run failed when it ended in error/timeout, OR when the start call itself
  // failed (e.g. the backend was unreachable) — that surfaces as an `error`
  // with no in-flight run, which we still want to show as a failure + Retry.
  const failed = phase === "error" || phase === "timeout" || (!isRunning && !!error);
  const done = phase === "done";

  // Auto-scroll to the latest content as turns land while running.
  useEffect(() => {
    if (!isRunning) return;
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns.length, isRunning, liveStatus]);

  // --- Empty: no persona selected (teach) ---------------------------------
  if (!hasPersona && phase === "idle" && turns.length === 0) {
    return (
      <div ref={scrollRef} className="custom-scrollbar flex flex-1 items-center justify-center overflow-y-auto p-lg">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
            <Sym name="groups" fill={1} size={26} className="text-primary" />
          </div>
          <h3 className="text-headline-md font-headline-md text-on-surface">Pick a persona to begin</h3>
          <p className="mx-auto mt-2 max-w-sm text-body-md leading-relaxed text-on-surface-variant">
            Choose one of the curated personas on the left, set the run knobs above, then run the eval to watch a
            persona drive a real conversation against RecBot.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="custom-scrollbar flex flex-1 flex-col items-center gap-md overflow-y-auto p-lg">
      {/* Scenario banner */}
      {(sutDescription || goalContext) && (
        <div className="flex w-full max-w-3xl shrink-0 items-start gap-3 rounded-lg border border-border-soft bg-surface-container-lowest p-sm shadow-soft">
          <Sym name="info" size={18} className="mt-0.5 text-primary" />
          <div>
            <h4 className="mb-1 text-body-md font-semibold text-on-surface">
              Scenario · {goalContext?.label ?? "Realistic scenario"}
            </h4>
            <p className="text-body-sm leading-relaxed text-on-surface-variant">
              {sutDescription ?? goalContext?.description ?? ""}
            </p>
          </div>
        </div>
      )}

      {/* Trajectory feed */}
      <div className="flex w-full max-w-3xl shrink-0 flex-col gap-lg pb-md">
        {turns.map((turn, i) => {
          const focused = i === focusedTurnIndex;
          return (
            <div
              key={turn.turnId ?? i}
              ref={(el) => registerTurnRef(i, el)}
              className={`flex flex-col gap-lg rounded-xl transition-colors ${
                focused ? "bg-primary/5 ring-1 ring-primary/20" : ""
              }`}
            >
              <TurnMarker label={`Turn ${i + 1}`} />
              <PersonaBubble message={turn.userMessage} personaName={personaName} />
              <RecBotBubble
                turn={turn}
                domain={domain}
                foldOpen={expandedTurns.has(i)}
                onToggleFold={() => onToggleTurn(i)}
              />
            </div>
          );
        })}

        {/* Loading skeleton while building, or while running before turns land. */}
        {isRunning && (turns.length === 0 || phase === "building") && (
          <SkeletonTurn label={phase === "building" ? "Warming the recommender…" : liveStatus} />
        )}

        {/* Live "thinking" line once turns are streaming. */}
        {isRunning && turns.length > 0 && phase !== "building" && liveStatus && (
          <div className="flex items-center justify-center gap-2 py-2">
            <Sym name="more_horiz" size={18} className="animate-rb-pulse text-on-surface-variant" />
            <span className="text-body-sm text-on-surface-variant">{liveStatus}</span>
          </div>
        )}

        {/* Failed run — plain-language cause + Retry (preserves config). */}
        {failed && (
          <div className="mx-auto w-full max-w-xl rounded-lg border border-error/40 bg-error-container/40 p-4">
            <div className="flex items-start gap-3">
              <Sym name="error" fill={1} size={20} className="mt-0.5 text-error" />
              <div className="min-w-0 flex-1">
                <h4 className="text-body-md font-semibold text-on-surface">This run didn&apos;t finish</h4>
                <p className="mt-1 break-words text-body-sm leading-relaxed text-on-surface-variant">
                  {error ?? "The persona eval stopped unexpectedly. Your configuration is unchanged."}
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

        {/* End-of-run marker. */}
        {done && turns.length > 0 && (
          <div className="my-1 flex w-full items-center">
            <div className="flex-1 border-t border-border-soft" />
            <span className="flex items-center gap-1 bg-background px-3 text-label-md font-label-md uppercase tracking-widest text-on-success-container">
              <Sym name="flag" fill={1} size={14} />
              Run complete
            </span>
            <div className="flex-1 border-t border-border-soft" />
          </div>
        )}

        {/* Empty: persona selected, no run yet — invite the operator to run. */}
        {hasPersona && phase === "idle" && turns.length === 0 && !failed && (
          <div className="mx-auto mt-8 max-w-md text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-surface-container">
              <Sym name="play_circle" size={26} className="text-on-surface-variant" />
            </div>
            <h3 className="text-headline-md font-headline-md text-on-surface">Ready to run</h3>
            <p className="mx-auto mt-2 max-w-sm text-body-md leading-relaxed text-on-surface-variant">
              Press <kbd className="rounded border border-border-soft bg-surface-container px-1.5 py-0.5 font-mono-sm text-mono-sm">R</kbd>{" "}
              or use the Run button to start the eval for this persona.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

/** A shimmering placeholder turn shown while a run warms / before turns land. */
function SkeletonTurn({ label }: { label: string | null }) {
  return (
    <div className="flex w-full flex-col gap-lg" aria-hidden>
      <TurnMarker label="Turn 1" />
      {/* Persona side (right) */}
      <div className="flex w-full flex-col items-end gap-1 pl-12">
        <div className="h-3 w-28 animate-rb-pulse rounded bg-surface-container" />
        <div className="h-16 w-2/3 animate-rb-pulse rounded-2xl rounded-tr-sm bg-surface-container-high" />
      </div>
      {/* RecBot side (left) */}
      <div className="mt-3 flex w-full flex-col items-start gap-1 pr-12">
        <div className="h-3 w-20 animate-rb-pulse rounded bg-surface-container" />
        <div className="h-24 w-full animate-rb-pulse rounded-2xl rounded-tl-sm bg-surface-container-high" />
      </div>
      {label && (
        <div className="flex items-center justify-center gap-2 py-1">
          <Sym name="autorenew" size={16} className="animate-rb-spin text-primary" />
          <span className="text-body-sm text-on-surface-variant">{label}</span>
        </div>
      )}
    </div>
  );
}

export default Trajectory;
