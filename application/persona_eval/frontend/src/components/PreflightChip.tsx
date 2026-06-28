/**
 * PreflightChip: the live readiness status in the top bar.
 *
 * Polls `GET /api/preflight` and reports readiness in plain language. The chip
 * itself is calm; clicking it opens a popover that lists each readiness check by
 * its human name with a pass/fail marker and the (already user-facing) detail.
 * It never surfaces raw environment-variable names.
 *
 * Three states:
 *   - checking (amber, pulsing) → the probe is in flight
 *   - ready    (green)          → every check passed
 *   - setup    (amber)          → some checks need attention, API reachable
 *   - offline  (red)            → the API itself is unreachable
 */
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { api } from "@/lib/api";
import type { PreflightResponse } from "@/lib/types";

type Tone = "ready" | "setup" | "offline" | "checking";

/** Tokenized chip classes per tone (tinted backgrounds + matching text). */
const TONE_CLASS: Record<Tone, string> = {
  ready: "border-secondary/30 bg-secondary/10 text-secondary",
  setup: "border-warn/30 bg-warn/10 text-warn",
  offline: "border-danger/30 bg-danger/10 text-danger",
  checking: "border-warn/30 bg-warn/10 text-warn",
};

const DOT_CLASS: Record<Tone, string> = {
  ready: "bg-secondary",
  setup: "bg-warn",
  offline: "bg-danger",
  checking: "bg-warn",
};

export function PreflightChip() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const preflight = useQuery<PreflightResponse>({
    queryKey: ["preflight"],
    queryFn: api.getPreflight,
    // Re-probe occasionally so a resource that comes online is reflected.
    refetchInterval: 20_000,
  });

  // Close the popover on outside click + Escape.
  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // Resolve the tone + label + sub-line.
  let tone: Tone;
  let label: string;
  let sub: string | null = null;
  const data = preflight.data;

  if (preflight.isLoading) {
    tone = "checking";
    label = "Checking…";
  } else if (preflight.isError || !data) {
    tone = "offline";
    label = "Backend offline";
    sub = "Start the PersonaEval backend to send messages";
  } else if (data.ready) {
    tone = "ready";
    label = "Ready";
  } else {
    const failing = data.checks.filter((c) => !c.ok).length;
    tone = "setup";
    label = "Almost ready";
    sub = `${failing} thing${failing === 1 ? "" : "s"} left to finish`;
  }

  // Group the checks by area (Core · Chatbot · Survey · Web) for the popover.
  const grouped = data
    ? data.checks.reduce<{ group: string; items: PreflightResponse["checks"] }[]>(
        (acc, c) => {
          const g = c.group ?? "Checks";
          const bucket = acc.find((x) => x.group === g);
          if (bucket) bucket.items.push(c);
          else acc.push({ group: g, items: [c] });
          return acc;
        },
        [],
      )
    : [];

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => data && setOpen((v) => !v)}
        aria-expanded={data ? open : undefined}
        aria-label={`Readiness: ${label}`}
        className={`flex h-9 items-center gap-2 rounded-md border px-2.5 text-xs font-medium transition ${TONE_CLASS[tone]} ${FOCUS_RING} ${
          data ? "cursor-pointer hover:opacity-90 active:scale-[0.98]" : "cursor-default"
        }`}
      >
        <span
          className={`h-2 w-2 rounded-full ${DOT_CLASS[tone]} ${tone === "checking" ? "animate-rb-pulse" : ""}`}
          aria-hidden
        />
        {label}
        {sub && <span className="hidden font-normal opacity-80 sm:inline">· {sub}</span>}
      </button>

      {open && data && (
        <div
          role="region"
          aria-label="Setup checklist"
          className="pop-in absolute right-0 top-full z-30 mt-2 w-80 max-w-[calc(100vw-1.5rem)] max-h-[70vh] overflow-y-auto custom-scrollbar rounded-md border border-outline bg-surface-lowest p-3 shadow-2xl"
        >
          <p className="hud mb-2.5 text-[10px] text-text-dim">System readiness</p>
          <div className="space-y-3.5">
            {grouped.map((g) => (
              <div key={g.group}>
                <div className="hud mb-1.5 text-[9px] text-primary">{g.group}</div>
                <ul className="space-y-2">
                  {g.items.map((check) => {
                    // An optional adapter that's down isn't an error — render it
                    // muted ("optional, not running") rather than as a warning.
                    const optionalDown = Boolean(check.optional) && !check.ok;
                    const iconName = check.ok
                      ? "check_circle"
                      : optionalDown
                        ? "radio_button_unchecked"
                        : "error";
                    const iconClass = check.ok
                      ? "text-secondary"
                      : optionalDown
                        ? "text-text-dim"
                        : "text-warn";
                    return (
                      <li key={check.name} className="flex items-start gap-2">
                        <Sym name={iconName} fill={1} size={16} className={`mt-px flex-none ${iconClass}`} />
                        <div className="min-w-0">
                          <div className="text-[12px] font-medium text-text-main">
                            {check.name}
                            {check.optional && (
                              <span className="hud ml-1.5 text-[8px] text-text-dim">optional</span>
                            )}
                          </div>
                          <div className="text-[11px] leading-relaxed text-text-variant">
                            {check.detail}
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
