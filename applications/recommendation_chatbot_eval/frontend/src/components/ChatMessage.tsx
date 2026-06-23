/**
 * ChatMessage — a single conversational row in the Chat workbench thread.
 *
 * The debug thread keeps a calm, scannable row layout (not the cockpit's
 * left/right bubble trajectory): an avatar + name + descriptor on top, then the
 * message body, then (for assistant turns) the recommendation cards. Styled to
 * the Executive Precision tokens.
 *
 * It is intentionally presentational: the parent `ChatThread` decides what to
 * render (persisted turns, the optimistic in-flight bubble, the thinking
 * placeholder) and passes the pieces in. Assistant rows can be made clickable
 * (to focus the turn in the inspector) via `onClick`.
 */
import type { ReactNode } from "react";

import { RecommendationCard } from "./RecommendationCard";
import { Sym } from "./cockpit/cockpitShared";
import type { RecommendedItem } from "@/lib/types";

export interface ChatMessageProps {
  role: "user" | "assistant";
  /** Avatar label: initials for the user, unused for the bot (icon). */
  avatar: string;
  /** Display name shown next to the avatar ("You" / "RecBot"). */
  name: string;
  /** Small grey descriptor after the name ("· turn 3 · 3 recommendations"). */
  tag?: string;
  /** The message body. A string renders as the reply text; a node is used
   *  verbatim (e.g. the "thinking" placeholder). */
  children: ReactNode;
  /** Recommendation cards to render under an assistant message. */
  recommendations?: RecommendedItem[];
  /** Inspect a recommended item. */
  onSelectItem?: (itemId: string) => void;
  /** Make the assistant row clickable to focus the turn. */
  onClick?: () => void;
  /** Highlight this row as the inspector's active turn. */
  active?: boolean;
}

export function ChatMessage({
  role,
  avatar,
  name,
  tag,
  children,
  recommendations,
  onSelectItem,
  onClick,
  active,
}: ChatMessageProps) {
  const isUser = role === "user";

  const body = (
    <div className="mx-auto max-w-thread">
      <div className="mb-1.5 flex items-center gap-2">
        {isUser ? (
          <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-surface-container-high text-[10px] font-semibold text-on-surface-variant">
            {avatar}
          </span>
        ) : (
          <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-primary/10" aria-hidden>
            <Sym name="smart_toy" fill={1} size={14} className="text-primary" />
          </span>
        )}
        <span className="text-label-md font-label-md font-semibold text-on-surface">{name}</span>
        {tag && <span className="text-label-md font-label-md text-on-surface-variant">{tag}</span>}
      </div>
      <div
        className={`text-body-md leading-relaxed ${
          isUser ? "whitespace-pre-wrap text-on-surface-variant" : "text-on-surface"
        }`}
      >
        {children}
      </div>
      {!isUser && recommendations && recommendations.length > 0 && (
        <div className="mt-2.5 flex flex-col gap-1.5">
          {recommendations.map((r) => (
            <RecommendationCard key={r.itemId} item={r} onSelect={onSelectItem} />
          ))}
        </div>
      )}
    </div>
  );

  // Assistant rows are clickable (focus the turn); user rows are static. The row
  // is a non-button focusable wrapper (not a <button>) because RecommendationCard
  // renders its own <button> inside `body` — nesting interactive controls is
  // invalid HTML and would let item clicks bubble to the row's inspect action.
  if (!isUser && onClick) {
    return (
      <div
        role="button"
        tabIndex={0}
        onClick={onClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick();
          }
        }}
        className={`block w-full px-lg py-2 text-left transition-colors focus-visible:outline-none ${
          active ? "bg-primary/5" : "hover:bg-surface-container-low"
        }`}
        title="Inspect this turn"
      >
        {body}
      </div>
    );
  }

  return <div className="px-lg py-2">{body}</div>;
}

export default ChatMessage;
