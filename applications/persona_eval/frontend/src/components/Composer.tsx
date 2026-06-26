/**
 * Composer — the message input at the bottom of the Chat workbench.
 *
 * An auto-growing textarea framed by a focus ring, with the cold-start hint on
 * the left and a send button on the right. `⌘↵` / `Ctrl+↵` submits. Styled to
 * the matrAIx tokens.
 *
 * Sending is delegated to the parent (which owns `useTurnJob`); the composer is
 * disabled while a turn is in flight and clears itself once a message is sent.
 */
import { useLayoutEffect, useRef, useState } from "react";

import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import type { TurnPhase } from "@/lib/useTurnJob";

export interface ComposerProps {
  /** Submit a user message. The parent runs it through `useTurnJob`. */
  onSend: (message: string) => void;
  /** Live turn phase — disables input and swaps the send glyph while pending. */
  phase: TurnPhase;
  /** Disable entirely (e.g. before a session exists). */
  disabled?: boolean;
}

/** Max textarea height before it scrolls instead of growing (px). */
const MAX_TEXTAREA_HEIGHT = 168;

export function Composer({ onSend, phase, disabled }: ComposerProps) {
  const [value, setValue] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);
  const isPending = phase === "building" || phase === "running";
  const blocked = Boolean(disabled) || isPending;

  // Auto-size the textarea to its content, capped at MAX_TEXTAREA_HEIGHT.
  useLayoutEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`;
  }, [value]);

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || blocked) return;
    onSend(trimmed);
    setValue("");
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // ⌘↵ (mac) / Ctrl+↵ (win/linux) sends; plain Enter inserts a newline.
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="flex-shrink-0 border-t border-outline bg-surface-lowest px-lg pb-4 pt-3">
      <div className="mx-auto max-w-thread overflow-hidden rounded-md border border-outline bg-field transition-colors focus-within:border-primary">
        <textarea
          ref={taRef}
          rows={1}
          value={value}
          disabled={blocked}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Type a message as the user you're playing — press ⌘↵ to send"
          aria-label="Type a message to RecAI"
          className="block w-full resize-none bg-transparent px-3.5 pb-1 pt-3 text-[13px] leading-relaxed text-text-main outline-none placeholder:text-text-dim disabled:cursor-not-allowed"
        />
        <div className="flex items-center gap-2 px-2.5 pb-2 pt-1.5">
          <span className="flex items-center gap-1.5 text-[11px] text-text-variant">
            <Sym name="schedule" size={14} className="text-text-dim" />
            {isPending
              ? phase === "building"
                ? "Waking the recommender — the first message takes about a minute"
                : "Sending your message…"
              : "The first message wakes the recommender (about a minute), then replies are quick"}
          </span>
          <button
            type="button"
            onClick={submit}
            disabled={blocked || value.trim().length === 0}
            aria-label="Send message"
            className={`ml-auto flex h-8 w-8 items-center justify-center rounded-md bg-primary text-on-primary transition-colors hover:bg-primary-dim disabled:opacity-45 ${FOCUS_RING}`}
          >
            {isPending ? (
              <Sym name="autorenew" size={16} className="animate-rb-spin" />
            ) : (
              <Sym name="arrow_forward" size={16} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
