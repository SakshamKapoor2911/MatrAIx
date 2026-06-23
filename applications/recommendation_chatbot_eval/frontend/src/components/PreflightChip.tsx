/**
 * PreflightChip — the live readiness status in the top bar.
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
  ready: "border-success/40 bg-success-container text-on-success-container",
  setup: "border-warning/40 bg-warning-container text-on-warning-container",
  offline: "border-error/40 bg-error-container text-on-error-container",
  checking: "border-warning/40 bg-warning-container text-on-warning-container",
};

const DOT_CLASS: Record<Tone, string> = {
  ready: "bg-success",
  setup: "bg-warning",
  offline: "bg-error",
  checking: "bg-warning",
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
    label = "API offline";
    sub = "Start the API to run turns";
  } else if (data.ready) {
    tone = "ready";
    label = "Ready";
  } else {
    const failing = data.checks.filter((c) => !c.ok).length;
    tone = "setup";
    label = "Setup needed";
    sub = `${failing} item${failing === 1 ? "" : "s"} need attention`;
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => data && setOpen((v) => !v)}
        aria-expanded={data ? open : undefined}
        aria-label={`Readiness: ${label}`}
        className={`flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-label-md font-label-md transition-opacity ${TONE_CLASS[tone]} ${FOCUS_RING} ${
          data ? "cursor-pointer hover:opacity-90" : "cursor-default"
        }`}
      >
        <span
          className={`h-2 w-2 rounded-full ${DOT_CLASS[tone]} ${tone === "checking" ? "animate-rb-pulse" : ""}`}
          aria-hidden
        />
        {label}
        {sub && <span className="font-normal opacity-80">· {sub}</span>}
      </button>

      {open && data && (
        <div
          role="region"
          aria-label="Readiness checks"
          className="absolute right-0 top-full z-30 mt-2 w-80 rounded-lg border border-border-soft bg-surface-container-lowest p-3 shadow-pop"
        >
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-on-surface-variant">
            Readiness checks
          </p>
          <ul className="space-y-2">
            {data.checks.map((check) => (
              <li key={check.name} className="flex items-start gap-2">
                <Sym
                  name={check.ok ? "check_circle" : "error"}
                  fill={1}
                  size={16}
                  className={`mt-px flex-none ${check.ok ? "text-success" : "text-warning"}`}
                />
                <div className="min-w-0">
                  <div className="text-body-sm font-medium text-on-surface">{check.name}</div>
                  <div className="text-label-md font-label-md leading-relaxed text-on-surface-variant">
                    {check.detail}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
