/**
 * Composer — the `>_` terminal-style message input at the bottom of the Chat
 * workbench (mockup `app-redesign-v3.html:323`).
 *
 * A mono `>_` prompt prefix, a `bg-field` frame, an auto-growing textarea, and a
 * full-height primary send button on the right. `⌘↵` / `Ctrl+↵` submits; a slim
 * helper line below carries the cold-start / status hint.
 *
 * Sending is delegated to the parent (which owns `useTurnJob`); the composer is
 * disabled while a turn is in flight, clears itself once a message is sent, and
 * — honestly — blocks send with a helper when the backend is offline (read from
 * the cached preflight query; no new request, no extra polling).
 */
import { useLayoutEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { api } from "@/lib/api";
import type { PreflightResponse } from "@/lib/types";
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

  // Read the shared preflight cache (same key as PreflightChip) — read-only, no
  // refetchInterval here so it never adds a second poll.
  const preflight = useQuery<PreflightResponse>({
    queryKey: ["preflight"],
    queryFn: api.getPreflight,
  });
  const offline = preflight.isError;

  const blocked = Boolean(disabled) || isPending || offline;

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

  const hint = offline
    ? "The backend is offline — start it to send a message."
    : isPending
      ? phase === "building"
        ? "Waking the recommender — the first message takes about a minute"
        : "Sending your message…"
      : "The first message wakes the recommender (about a minute), then replies are quick";

  return (
    <div className="flex-shrink-0 border-t border-outline bg-surface-lowest px-5 py-4 md:px-8">
      <div className="mx-auto max-w-2xl">
        <div className="flex items-stretch rounded-md border border-outline bg-field transition-colors focus-within:border-primary">
          <span className="self-start pl-3.5 pt-3 font-mono font-bold text-primary" aria-hidden>
            &gt;_
          </span>
          <textarea
            ref={taRef}
            rows={1}
            value={value}
            disabled={blocked}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Type a message as the user you're playing — press ⌘↵ to send"
            aria-label="Type a message to RecAI"
            className="block w-full resize-none bg-transparent px-3 py-3 font-mono text-[13px] leading-relaxed text-text-main outline-none placeholder:text-text-dim disabled:cursor-not-allowed"
          />
          <button
            type="button"
            onClick={submit}
            disabled={blocked || value.trim().length === 0}
            aria-label="Send message"
            className={`grid flex-none place-items-center self-stretch rounded-r-md bg-primary px-5 text-on-primary transition-colors hover:bg-primary-dim disabled:opacity-45 ${FOCUS_RING}`}
          >
            {isPending ? (
              <Sym name="autorenew" size={16} className="animate-rb-spin" />
            ) : (
              <Sym name="arrow_upward" size={16} />
            )}
          </button>
        </div>
        <p className="hud mt-2 text-[8px] leading-relaxed text-text-dim">{hint}</p>
      </div>
    </div>
  );
}
