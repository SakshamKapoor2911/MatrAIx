/**
 * Trajectory: the live-run conversation thread.
 *
 * Ports the mockup's live-run thread (`app-redesign-v3.html:483-535`): a
 * centered `max-w-2xl` column of turns, each a persona bubble (left) and the
 * app reply (right) with its recommended-item cards + tool-plan fold. While a
 * turn is mid-flight, it shows a shimmering "generating" app bubble with a
 * blinking cursor.
 *
 * Each job turn carries both the persona message and the app reply, so one
 * `TurnView` renders both bubbles. The thread covers the live states a run can
 * be in: warming (a skeleton turn), streaming (bubbles + the generating
 * placeholder), failed (a plain-language cause + a Retry that preserves config),
 * and done (the settled transcript). Tool-plan fold state + the focused turn
 * (J/K nav) are owned by the parent; this component registers each turn's DOM
 * node so the parent can scroll to it.
 */
import { useEffect, useRef } from "react";

import { PersonaBubble, RecBotBubble } from "./TurnBubble";
import { ChatbotChatAvatar, PersonaChatAvatar } from "./ChatBubbleAvatar";
import { draftTurnToView } from "@/lib/harborCockpitMappers";
import { Sym, FOCUS_RING } from "./cockpitShared";
import type { Domain, HarborDraftTurn, TurnView } from "@/lib/types";
import type { PersonaEvalRunPhase } from "@/lib/usePersonaEval";

export interface TrajectoryProps {
  turns: TurnView[];
  /** In-progress turn (persona and/or assistant message before turn event). */
  draftTurn?: HarborDraftTurn | null;
  /** Agent phase string from events (application_thinking, persona_thinking, …). */
  livePhase?: string | null;
  domain: Domain;
  /** App display name (RecAI / OpenBB / Medical Assistant). */
  appName: string;
  /** Active persona id for transcript avatars. */
  personaId?: string | null;
  personaDimensions?: Record<string, string>;
  /** SUT description for the scenario banner. */
  sutDescription: string | null;
  /** Run lifecycle phase. */
  phase: PersonaEvalRunPhase;
  /** A coarse "what's happening now" line while running. */
  liveStatus: string | null;
  /** Error text from a failed / timed-out run, if any. */
  error: string | null;
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
  draftTurn = null,
  livePhase = null,
  domain,
  appName,
  personaId = null,
  personaDimensions = {},
  sutDescription,
  phase,
  liveStatus,
  error,
  expandedTurns,
  onToggleTurn,
  focusedTurnIndex,
  registerTurnRef,
  onRetry,
}: TrajectoryProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isRunning = phase === "building" || phase === "running";
  const failed = phase === "error" || phase === "timeout" || (!isRunning && !!error);
  const draft = draftTurn?.userMessage ? draftTurnToView(draftTurn) : null;
  const waitingForAssistant =
    isRunning && draftTurn?.userMessage && !draftTurn?.assistantMessage && livePhase === "application_thinking";
  const personaThinking =
    isRunning && draftTurn?.assistantMessage && livePhase === "persona_thinking";

  // Auto-scroll to the latest content as turns land / status changes.
  useEffect(() => {
    if (!isRunning) return;
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns.length, draftTurn?.userMessage, draftTurn?.assistantMessage, isRunning, liveStatus, livePhase]);

  return (
    <div ref={scrollRef} className="custom-scrollbar flex min-h-0 flex-1 flex-col overflow-y-auto bg-surface-dim px-5 py-7 md:px-8">
      <div className="mx-auto w-full max-w-2xl space-y-7">
        {/* Scenario banner: the real task-backed app context. */}
        {sutDescription && (
          <div className="rise-in flex items-start gap-2.5 rounded-md border border-outline bg-surface-lowest px-4 py-3">
            <Sym name="info" size={16} className="mt-0.5 shrink-0 text-primary" />
            <div className="min-w-0">
              <div className="hud mb-1 text-[9px] text-primary">Scenario</div>
              <p className="text-[12px] leading-relaxed text-text-variant">
                {sutDescription}
              </p>
            </div>
          </div>
        )}

        {/* Turns: persona ask + app reply. */}
        {turns.map((turn, i) => {
          const focused = i === focusedTurnIndex;
          return (
            <div
              key={turn.turnId || i}
              ref={(el) => registerTurnRef(i, el)}
              className={`rise-in space-y-7 rounded-md transition-colors ${focused ? "bg-primary/5 p-3 ring-1 ring-primary/30" : ""}`}
            >
              <PersonaBubble
                message={turn.userMessage}
                personaId={personaId}
                personaDimensions={personaDimensions}
              />
              <RecBotBubble
                turn={turn}
                domain={domain}
                appName={appName}
                foldOpen={expandedTurns.has(i)}
                onToggleFold={() => onToggleTurn(i)}
              />
            </div>
          );
        })}

        {/* In-progress turn: persona bubble, then assistant or generating placeholder. */}
        {draft && (
          <div className="rise-in space-y-7">
            <PersonaBubble
              message={draft.userMessage}
              personaId={personaId}
              personaDimensions={personaDimensions}
            />
            {draft.assistantMessage ? (
              <RecBotBubble
                turn={draft}
                domain={domain}
                appName={appName}
                foldOpen={false}
                onToggleFold={() => undefined}
              />
            ) : waitingForAssistant ? (
              <GeneratingBubble appName={appName} />
            ) : null}
            {personaThinking && (
              <PersonaThinkingBubble personaId={personaId} personaDimensions={personaDimensions} />
            )}
          </div>
        )}

        {/* Warming (cold start, before any turn): a skeleton turn. */}
        {isRunning && turns.length === 0 && !draft && (phase === "building" || !livePhase) && (
          <SkeletonTurn label={phase === "building" ? "Starting the app…" : liveStatus} />
        )}

        {/* Legacy fallback when no draft events yet but turns exist */}
        {isRunning && turns.length > 0 && !draft && livePhase === "application_thinking" && (
          <GeneratingBubble appName={appName} />
        )}

        {/* Failed: plain-language cause + Retry (preserves config). */}
        {failed && (
          <div className="rise-in rounded-md border border-danger/40 bg-danger/10 p-4">
            <div className="flex items-start gap-3">
              <Sym name="error" fill={1} size={20} className="mt-0.5 text-danger" />
              <div className="min-w-0 flex-1">
                <h4 className="text-sm font-semibold text-text-main">The simulation didn&apos;t finish</h4>
                <p className="mt-1 break-words text-[13px] leading-relaxed text-text-variant">
                  {error ?? "It stopped before completing. Your settings are untouched, so you can try again right away."}
                </p>
                <button
                  type="button"
                  onClick={onRetry}
                  className={`mt-3 inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-on-primary transition ease-out hover:bg-primary-dim active:scale-[0.98] ${FOCUS_RING}`}
                >
                  <Sym name="refresh" size={16} />
                  Retry
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/** Persona is composing the next message after the app replied. */
function PersonaThinkingBubble({
  personaId,
  personaDimensions = {},
}: {
  personaId?: string | null;
  personaDimensions?: Record<string, string>;
}) {
  return (
    <div className="flex w-full items-start gap-2.5 pr-10" aria-live="polite">
      <PersonaChatAvatar personaId={personaId} dimensions={personaDimensions} />
      <div className="flex min-w-0 flex-1 flex-col items-start">
        <div className="hud mb-1.5 flex items-center gap-2 text-[9px] text-text-dim">
          <span>Persona · thinking</span>
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" aria-hidden />
        </div>
        <div className="max-w-[70%] rounded-md rounded-tl-sm border border-outline bg-surface px-4 py-3">
          <div className="space-y-2" aria-hidden>
            <div className="h-2.5 w-40 animate-rb-pulse rounded bg-surface-high" />
            <div className="h-2.5 w-28 animate-rb-pulse rounded bg-surface-high" />
          </div>
        </div>
      </div>
    </div>
  );
}

/** A shimmering "generating" app bubble (mockup `:519-532`). */
function GeneratingBubble({ appName }: { appName: string }) {
  return (
    <div className="rise-in flex w-full justify-end pl-10" aria-live="polite">
      <div className="flex max-w-full items-start gap-2.5">
        <div className="flex min-w-0 flex-col items-end">
          <div className="hud mb-1.5 flex items-center gap-2 text-[9px] text-primary">
            <span>{appName} · generating</span>
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" aria-hidden />
          </div>
          <div className="w-full rounded-md rounded-tr-sm border border-outline bg-surface px-4 py-4">
            <div className="space-y-3" aria-hidden>
              <div className="h-2.5 w-[92%] animate-rb-pulse rounded bg-surface-high" />
              <div className="h-2.5 w-[76%] animate-rb-pulse rounded bg-surface-high" />
              <div className="flex items-center gap-1.5">
                <div className="h-2.5 w-[42%] animate-rb-pulse rounded bg-surface-high" />
                <span className="h-3.5 w-px animate-pulse bg-primary" />
              </div>
            </div>
          </div>
        </div>
        <ChatbotChatAvatar appName={appName} />
      </div>
    </div>
  );
}

/** A skeleton turn shown while a run warms / before turns land. */
function SkeletonTurn({ label }: { label: string | null }) {
  return (
    <div className="rise-in space-y-7" aria-hidden>
      {/* Persona side (left) */}
      <div className="flex w-full items-start gap-2.5 pr-10">
        <div className="h-8 w-8 shrink-0 animate-rb-pulse rounded-full bg-surface-high" />
        <div className="flex min-w-0 flex-1 flex-col items-start gap-1">
          <div className="h-3 w-20 animate-rb-pulse rounded bg-surface-high" />
          <div className="h-14 w-2/3 animate-rb-pulse rounded-md rounded-tl-sm bg-surface-high" />
        </div>
      </div>
      {/* App side (right) */}
      <div className="flex w-full justify-end pl-10">
        <div className="flex max-w-full items-start gap-2.5">
          <div className="flex min-w-0 flex-col items-end gap-1">
            <div className="h-3 w-16 animate-rb-pulse rounded bg-surface-high" />
            <div className="h-24 w-full min-w-[12rem] animate-rb-pulse rounded-md rounded-tr-sm bg-surface-high" />
          </div>
          <div className="h-8 w-8 shrink-0 animate-rb-pulse rounded-full bg-surface-high" />
        </div>
      </div>
      {label && (
        <div className="flex items-center justify-center gap-2 py-1">
          <Sym name="autorenew" size={16} className="animate-rb-spin text-primary" />
          <span className="text-[13px] text-text-variant">{label}</span>
        </div>
      )}
    </div>
  );
}

export default Trajectory;
