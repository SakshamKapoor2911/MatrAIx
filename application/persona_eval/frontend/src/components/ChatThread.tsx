/**
 * ChatThread: the centre conversation pane of the Chat workbench.
 *
 * Renders the persisted turns of a session as the PersonaEval bubble thread (mockup
 * `app-redesign-v3.html:308-322`): the user ("You") on the right, RecAI on the
 * left with its recommendation cards and a row of honest fact chips. Selecting a
 * RecAI bubble focuses that turn in the inspector (via `onSelectTurn`).
 *
 * The bottom of the thread reflects the live `useTurnJob` phase: an optimistic
 * user bubble for the message in flight, a shimmering RecAI "waking / thinking"
 * placeholder during `building` / `running`, and a plain-language error card
 * (with Retry) on failure.
 *
 * Each persisted turn is keyed by its array index because the session appends
 * turns in order and never reorders them, so the index is a stable identity.
 */
import { useEffect, useRef } from "react";

import { ChatMessage, type MetaChip } from "./ChatMessage";
import { Markdown } from "./Markdown";
import { FOCUS_RING, Sym, fmtLatency } from "./cockpit/cockpitShared";
import type { TurnView } from "@/lib/types";
import type { TurnPhase } from "@/lib/useTurnJob";

/** Honest fact chips for a RecAI bubble, derived only from real `TurnView` data. */
function assistantMeta(turn: TurnView): MetaChip[] {
  const chips: MetaChip[] = [];
  const plan = turn.plan ?? [];
  const recs = turn.recommendedItems ?? [];
  if (plan.length > 0 && plan.every((s) => s.status === "ok")) {
    chips.push({ key: "tool", label: "Tool call OK", tone: "positive" });
  }
  if (recs.length === 0) {
    chips.push({ key: "q", label: "Asked a question" });
  }
  const lat = fmtLatency(turn.durationSeconds);
  if (lat) chips.push({ key: "lat", label: lat });
  return chips;
}

/** Teaching empty-state shown when a fresh session has no turns yet. */
function EmptyThread({ appName, warmsUp }: { appName: string; warmsUp: boolean }) {
  return (
    <div className="flex h-full items-center justify-center px-6">
      <div className="rise-in flex max-w-md flex-col items-center gap-3 text-center">
        <div className="grid h-14 w-14 place-items-center rounded-md border border-dashed border-outline bg-surface-high">
          <Sym name="forum" fill={1} size={26} className="text-text-dim" />
        </div>
        <div>
          <h3 className="font-display text-[15px] font-semibold text-text-main">Start the conversation</h3>
          <p className="mx-auto mt-2 max-w-sm text-[13px] leading-relaxed text-text-variant">
            You&apos;ll play the user here. Type what they&apos;d want and {appName} will reply.
            {warmsUp
              ? " Heads up: the first message wakes the recommender (about a minute); after that, replies are quick."
              : ""}
          </p>
        </div>
        <p className="hud mt-1 max-w-xs text-[9px] leading-relaxed text-text-dim">
          New to PersonaEval? In Chat you role-play a user. When you want automated scoring, switch to the
          PersonaEval tab.
        </p>
      </div>
    </div>
  );
}

/** A shimmering assistant bubble shown while the agent wakes / thinks. */
function ThinkingSkeleton({
  phase,
  appName,
  warmsUp,
}: {
  phase: TurnPhase;
  appName: string;
  warmsUp: boolean;
}) {
  const building = phase === "building";
  const waking = building && warmsUp;
  return (
    <div className="rise-in flex flex-col items-start pr-10">
      <div className="hud mb-1.5 ml-1 flex items-center gap-2 text-[9px] text-primary">
        <Sym name="smart_toy" fill={1} size={14} className="text-primary" />
        <span>{appName} · {waking ? "waking" : "thinking"}</span>
        <span className="h-1.5 w-1.5 animate-rb-pulse rounded-full bg-primary" aria-hidden />
      </div>
      <div className="w-full rounded-md rounded-tl-sm border border-outline bg-surface px-4 py-4">
        <div className="space-y-3" aria-hidden>
          <div className="h-2.5 w-[92%] animate-rb-pulse rounded bg-surface-high" />
          <div className="h-2.5 w-[76%] animate-rb-pulse rounded bg-surface-high" />
          <div className="flex items-center gap-1.5">
            <div className="h-2.5 w-[42%] animate-rb-pulse rounded bg-surface-high" />
            <span className="h-3.5 w-px animate-rb-pulse bg-primary" />
          </div>
        </div>
        <p className="mt-3 text-[12px] leading-relaxed text-text-variant">
          {waking
            ? `First message: ${appName} is loading its catalog and tools. This one turn can take a minute.`
            : `${appName} is working on a reply…`}
        </p>
      </div>
    </div>
  );
}

export interface ChatThreadProps {
  turns: TurnView[];
  activeTurnIndex: number | null;
  /** The message currently being processed (optimistic user bubble). */
  pendingMessage: string | null;
  /** Live turn phase from `useTurnJob`. */
  phase: TurnPhase;
  /** Error text from a failed turn, if any. */
  error: string | null;
  /** Identity used for the user label (e.g. the operator's email). */
  userId?: string;
  /** Display name of the selected chatbot (RecAI / OpenBB / Medical assistant). */
  appName?: string;
  /** Whether the app has a cold-start warmup (RecAI only) for honest copy. */
  warmsUp?: boolean;
  onSelectTurn: (index: number) => void;
  onSelectItem: (itemId: string) => void;
  /** Re-send the failed turn (preserves the message). */
  onRetry?: () => void;
}

export function ChatThread({
  turns,
  activeTurnIndex,
  pendingMessage,
  phase,
  error,
  appName = "the app",
  warmsUp = true,
  onSelectTurn,
  onSelectItem,
  onRetry,
}: ChatThreadProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isPending = phase === "building" || phase === "running";

  // Keep the latest content in view as turns land or the phase changes.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns.length, pendingMessage, phase, error]);

  const empty = turns.length === 0 && !pendingMessage && !error;

  return (
    <div ref={scrollRef} className="custom-scrollbar min-h-0 flex-1 overflow-auto px-5 py-7 md:px-8">
      {empty ? (
        <EmptyThread appName={appName} warmsUp={warmsUp} />
      ) : (
        <div className="mx-auto max-w-2xl space-y-7">
          {turns.map((turn, i) => (
            <div
              key={i}
              className="rise-in space-y-7"
              style={{ animationDelay: `${Math.min(i, 6) * 30}ms` }}
            >
              {turn.userMessage != null && turn.userMessage !== "" && (
                <ChatMessage role="user" name="You">
                  {turn.userMessage}
                </ChatMessage>
              )}
              <ChatMessage
                role="assistant"
                name={appName}
                recommendations={turn.recommendedItems ?? []}
                meta={assistantMeta(turn)}
                onSelectItem={onSelectItem}
                onClick={() => onSelectTurn(i)}
                active={i === activeTurnIndex}
                title="Inspect this turn"
              >
                <Markdown>{turn.assistantMessage ?? ""}</Markdown>
              </ChatMessage>
            </div>
          ))}

          {/* Optimistic user bubble for the in-flight message */}
          {pendingMessage && (
            <ChatMessage role="user" name="You">
              {pendingMessage}
            </ChatMessage>
          )}

          {/* Shimmering assistant placeholder while the job runs */}
          {isPending && <ThinkingSkeleton phase={phase} appName={appName} warmsUp={warmsUp} />}

          {/* Plain-language error card + Retry */}
          {error && !isPending && (
            <div className="panel rise-in flex items-start gap-3 rounded-md border border-l-4 border-danger/40 border-l-danger bg-danger/10 px-3.5 py-3">
              <Sym name="error" fill={1} size={20} className="mt-0.5 flex-none text-danger" />
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-semibold text-text-main">That message didn&apos;t go through</div>
                <div className="mt-0.5 break-words text-[12px] leading-relaxed text-text-variant">{error}</div>
                {onRetry && (
                  <button
                    type="button"
                    onClick={onRetry}
                    className={`mt-3 inline-flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-3 py-1.5 text-xs font-medium text-danger transition hover:bg-danger/20 active:scale-[0.98] ${FOCUS_RING}`}
                  >
                    <Sym name="refresh" size={16} />
                    Retry
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ChatThread;
