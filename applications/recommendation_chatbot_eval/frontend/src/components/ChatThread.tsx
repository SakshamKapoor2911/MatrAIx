/**
 * ChatThread — the centre conversation pane of the Chat workbench.
 *
 * Renders the persisted turns of a session as alternating user / assistant
 * rows (via `ChatMessage`). Assistant turns that produced recommendations show
 * the recommendation cards; selecting an assistant row focuses that turn in the
 * inspector (via `onSelectTurn`).
 *
 * The bottom of the thread reflects the live `useTurnJob` phase: an optimistic
 * user bubble for the message in flight, a skeleton "warming / thinking"
 * assistant placeholder during `building` / `running`, and a plain-language
 * error row (with Retry) on failure.
 *
 * Each persisted turn is keyed by its array index because `RecBotSession`
 * appends turns in order and never reorders them, so the index is a stable
 * identity.
 */
import { useEffect, useRef } from "react";

import { ChatMessage } from "./ChatMessage";
import { Markdown } from "./Markdown";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import type { TurnView } from "@/lib/types";
import type { TurnPhase } from "@/lib/useTurnJob";

/** Two-letter avatar initials for the "You" side, from an email/name. */
function userInitials(identity: string | undefined): string {
  if (!identity) return "You";
  const local = identity.split("@")[0];
  const parts = local.split(/[.\-_\s]+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  if (parts.length === 1 && parts[0].length >= 2) return parts[0].slice(0, 2).toUpperCase();
  return "You";
}

/** Tag shown next to "RecBot" describing what the assistant turn did. */
function assistantTag(turn: TurnView, index: number): string {
  const n = turn.recommendedItems?.length ?? 0;
  if (n > 0) {
    return `· turn ${index + 1} · ${n} recommendation${n === 1 ? "" : "s"}`;
  }
  return `· turn ${index + 1} · asked a clarifying question`;
}

/** Teaching empty-state shown when a fresh session has no turns yet. */
function EmptyThread() {
  return (
    <div className="flex h-full items-center justify-center px-6">
      <div className="max-w-md text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
          <Sym name="forum" fill={1} size={26} className="text-primary" />
        </div>
        <h3 className="text-headline-md font-headline-md text-on-surface">Start the conversation</h3>
        <p className="mx-auto mt-2 max-w-sm text-body-md leading-relaxed text-on-surface-variant">
          Reply as the user below to send the first turn. The first message warms the recommender
          (about a minute); after that, turns run fast.
        </p>
      </div>
    </div>
  );
}

/** A shimmering placeholder while the agent warms / thinks (skeleton, not spinner). */
function ThinkingSkeleton({ phase }: { phase: TurnPhase }) {
  const building = phase === "building";
  return (
    <div className="px-lg py-2">
      <div className="mx-auto max-w-thread">
        <div className="mb-1.5 flex items-center gap-2">
          <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-primary/10" aria-hidden>
            <Sym name="smart_toy" fill={1} size={14} className="text-primary" />
          </span>
          <span className="text-label-md font-label-md font-semibold text-on-surface">RecBot</span>
          <span className="flex items-center gap-1.5 text-label-md font-label-md text-on-surface-variant">
            <Sym name="more_horiz" size={16} className="animate-rb-pulse" />
            {building ? "warming the recommender…" : "thinking…"}
          </span>
        </div>
        <div className="space-y-2" aria-hidden>
          <div className="h-3.5 w-11/12 animate-rb-pulse rounded bg-surface-container-high" />
          <div className="h-3.5 w-3/4 animate-rb-pulse rounded bg-surface-container" />
        </div>
        <p className="mt-2 text-body-sm leading-relaxed text-on-surface-variant">
          {building
            ? "Cold start — loading the catalog and resources. This first turn can take a minute."
            : "Planning tools and ranking candidates from the catalog…"}
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
  /** Identity used for the user avatar initials (e.g. the operator's email). */
  userId?: string;
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
  userId,
  onSelectTurn,
  onSelectItem,
  onRetry,
}: ChatThreadProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isPending = phase === "building" || phase === "running";
  const nextTurnNumber = turns.length + 1;
  const initials = userInitials(userId);

  // Keep the latest content in view as turns land or the phase changes.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns.length, pendingMessage, phase, error]);

  const empty = turns.length === 0 && !pendingMessage && !error;

  return (
    <div ref={scrollRef} className="custom-scrollbar min-h-0 flex-1 overflow-auto pb-2 pt-6">
      {empty ? (
        <EmptyThread />
      ) : (
        <>
          {turns.map((turn, i) => (
            <div key={i}>
              {turn.userMessage != null && (
                <ChatMessage role="user" avatar={initials} name="You" tag={`· turn ${i + 1}`}>
                  {turn.userMessage}
                </ChatMessage>
              )}
              <ChatMessage
                role="assistant"
                avatar="RB"
                name="RecBot"
                tag={assistantTag(turn, i)}
                recommendations={turn.recommendedItems ?? []}
                onSelectItem={onSelectItem}
                onClick={() => onSelectTurn(i)}
                active={i === activeTurnIndex}
              >
                <Markdown>{turn.assistantMessage ?? ""}</Markdown>
              </ChatMessage>
            </div>
          ))}

          {/* Optimistic user bubble for the in-flight message */}
          {pendingMessage && (
            <ChatMessage role="user" avatar={initials} name="You" tag={`· turn ${nextTurnNumber}`}>
              {pendingMessage}
            </ChatMessage>
          )}

          {/* Skeleton "thinking" placeholder while the job runs */}
          {isPending && <ThinkingSkeleton phase={phase} />}

          {/* Plain-language error row + Retry */}
          {error && !isPending && (
            <div className="px-lg py-2">
              <div className="mx-auto max-w-thread">
                <div className="flex items-start gap-3 rounded-lg border border-error/40 bg-error-container/40 px-3.5 py-3">
                  <Sym name="error" fill={1} size={20} className="mt-0.5 flex-none text-error" />
                  <div className="min-w-0 flex-1">
                    <div className="text-body-md font-semibold text-on-surface">This turn didn&apos;t finish</div>
                    <div className="mt-0.5 break-words text-body-sm leading-relaxed text-on-surface-variant">
                      {error}
                    </div>
                    {onRetry && (
                      <button
                        type="button"
                        onClick={onRetry}
                        className={`mt-3 inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-label-md font-label-md text-on-primary shadow-sm transition-colors hover:bg-primary-container ${FOCUS_RING}`}
                      >
                        <Sym name="refresh" size={16} />
                        Retry
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ChatThread;
