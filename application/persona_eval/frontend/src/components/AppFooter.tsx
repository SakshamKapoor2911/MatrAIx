/**
 * AppFooter: the slim, honest status footer (mockup `app-redesign-v3.html:1279`).
 *
 * Left: the product name + the active surface context (e.g. "chatbot · RecAI ·
 * movie"). Only real values already in scope. Right: a dot + the live backend
 * connection status, read from the SHARED preflight query cache (same key as
 * `PreflightChip`); no new request and no extra polling here.
 *
 * Mounted once in each shell branch of `App.tsx` so it spans every surface.
 */
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { PreflightResponse } from "@/lib/types";

export interface AppFooterProps {
  /** The active surface context, e.g. "chatbot · RecAI · movie" (real values). */
  context: string;
}

export function AppFooter({ context }: AppFooterProps) {
  // Read-only: shares PreflightChip's cache. No refetchInterval -> no extra poll.
  const preflight = useQuery<PreflightResponse>({
    queryKey: ["preflight"],
    queryFn: api.getPreflight,
  });

  let dot = "bg-warn";
  let label = "Checking…";
  let pulse = false;
  if (preflight.isLoading) {
    dot = "bg-warn";
    label = "Checking…";
    pulse = true;
  } else if (preflight.isError || !preflight.data) {
    dot = "bg-danger";
    label = "Backend offline";
  } else if (preflight.data.ready) {
    dot = "bg-secondary";
    label = "Connected";
  } else {
    dot = "bg-warn";
    label = "Finishing setup";
  }

  return (
    <footer className="flex-shrink-0 border-t border-outline bg-surface-lowest">
      <div className="flex items-center justify-between gap-4 px-5 py-2 text-text-dim">
        <div className="hud flex min-w-0 items-center gap-3 text-[9px]">
          <span className="flex-none text-text-variant">
            Matr<span className="text-primary">AI</span>x
          </span>
          <span className="flex-none text-outline">·</span>
          <span className="min-w-0 truncate" title={context}>{context}</span>
        </div>
        <div
          className="hud flex flex-shrink-0 items-center gap-2 text-[9px] text-text-variant"
          aria-label="Backend connection status"
        >
          <span
            className={`h-1.5 w-1.5 rounded-full transition-colors ${dot} ${pulse ? "animate-rb-pulse" : ""}`}
            aria-hidden
          />
          {label}
        </div>
      </div>
    </footer>
  );
}

export default AppFooter;
