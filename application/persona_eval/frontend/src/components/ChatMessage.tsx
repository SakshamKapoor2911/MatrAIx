/**
 * ChatMessage: a single conversational bubble in the Chat workbench thread.
 *
 * Ports the PersonaEval chat bubble design (mockup `app-redesign-v3.html:309-321`):
 * the user ("You") sits on the RIGHT with a top-right-clipped bubble; RecAI sits
 * on the LEFT with a top-left-clipped, full-width bubble that holds the reply
 * text and (when the turn recommended items) a 2-up grid of recommendation
 * cards. A row of honest meta chips (tool-call OK / item count / latency) sits
 * just below the RecAI bubble.
 *
 * It is intentionally presentational: the parent `ChatThread` decides what to
 * render (persisted turns, the optimistic in-flight bubble) and passes the
 * pieces in. The RecAI bubble can be made clickable (to focus the turn in the
 * inspector) via `onClick`; it stays a focusable `role=button` wrapper (not a
 * `<button>`) so the inner RecommendationCard buttons remain valid HTML.
 */
import type { ReactNode } from "react";

import { RecommendationCard } from "./RecommendationCard";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import type { RecommendedItem } from "@/lib/types";

/** One small fact chip shown under a RecAI bubble. */
export interface MetaChip {
  key: string;
  label: string;
  /** `positive` → mint (connected/ok); default → quiet outline. */
  tone?: "positive" | "default";
}

export interface ChatMessageProps {
  role: "user" | "assistant";
  /** Display name shown in the label above the bubble ("You" / "RecAI"). */
  name: string;
  /** The message body. A string (user) or a node (assistant markdown). */
  children: ReactNode;
  /** Recommendation cards to render inside an assistant bubble. */
  recommendations?: RecommendedItem[];
  /** Honest fact chips shown below an assistant bubble. */
  meta?: MetaChip[];
  /** Inspect a recommended item. */
  onSelectItem?: (itemId: string) => void;
  /** Make the assistant bubble clickable to focus the turn. */
  onClick?: () => void;
  /** Highlight this bubble as the inspector's active turn. */
  active?: boolean;
  /** Tooltip / aria description for the clickable assistant bubble. */
  title?: string;
}

const CHIP_TONE: Record<NonNullable<MetaChip["tone"]>, string> = {
  positive: "border-secondary/25 bg-secondary/10 text-secondary",
  default: "border-outline text-text-variant",
};

export function ChatMessage({
  role,
  name,
  children,
  recommendations,
  meta,
  onSelectItem,
  onClick,
  active,
  title,
}: ChatMessageProps) {
  // --- User: right-aligned bubble ----------------------------------------
  if (role === "user") {
    return (
      <div className="flex flex-col items-end pl-10">
        <div className="hud mb-1.5 mr-1 text-[9px] text-text-dim">{name}</div>
        <div className="whitespace-pre-wrap break-words rounded-md rounded-tr-sm border border-outline bg-surface px-4 py-3 text-[13px] leading-relaxed text-text-main">
          {children}
        </div>
      </div>
    );
  }

  // --- Assistant (RecAI): left-aligned, full-width bubble ----------------
  const hasRecs = Boolean(recommendations && recommendations.length > 0);
  const clickable = Boolean(onClick);

  const bubble = (
    <div
      className={`w-full rounded-md rounded-tl-sm border bg-surface px-4 py-4 transition-colors ${
        active ? "border-primary/60" : "border-outline"
      } ${clickable ? "hover:border-primary/60" : ""}`}
    >
      <div className={hasRecs ? "mb-4 border-b border-outline pb-4 text-[13px] leading-relaxed" : "text-[13px] leading-relaxed"}>
        {children}
      </div>
      {hasRecs && (
        <div
          className="grid grid-cols-1 gap-3 sm:grid-cols-2"
          // Inspecting an item shouldn't also fire the bubble's focus-turn click.
          onClick={(e) => e.stopPropagation()}
        >
          {recommendations!.map((r) => (
            <RecommendationCard key={r.itemId} item={r} onSelect={onSelectItem} />
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="flex flex-col items-start pr-10">
      <div className="hud mb-1.5 ml-1 flex items-center gap-2 text-[9px] text-primary">
        <Sym name="smart_toy" fill={1} size={14} className="text-primary" />
        {name}
      </div>
      {clickable ? (
        <div
          role="button"
          tabIndex={0}
          onClick={onClick}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onClick!();
            }
          }}
          title={title ?? "Inspect this turn"}
          className={`w-full cursor-pointer text-left ${FOCUS_RING}`}
        >
          {bubble}
        </div>
      ) : (
        bubble
      )}
      {meta && meta.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-2">
          {meta.map((chip) => (
            <span
              key={chip.key}
              className={`hud rounded border px-2 py-1 text-[8px] ${CHIP_TONE[chip.tone ?? "default"]}`}
            >
              {chip.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default ChatMessage;
