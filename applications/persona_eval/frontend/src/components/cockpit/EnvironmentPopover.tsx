/**
 * EnvironmentPopover — the read-only "Fixed environment" facts.
 *
 * The cockpit separates *editable knobs* (Model/Domain/Conversation style/Max
 * turns) from the *fixed* parts of the stack the operator cannot change. This
 * renders that read-only block — Runtime (Harbor), persona agent, application
 * API sidecar, application scorer, persona model default, cache policy, adapter
 * resources, adapter agent, and the Harbor/application prompt boundary — from the
 * backend `environment` block of `GET /api/config/options`, behind a button
 * that toggles a popover.
 *
 * The button is distinct from the knobs (a quiet "lock" affordance, not a
 * primary-bordered dropdown) so it reads as facts, not controls. The popover is
 * keyboard-dismissible (Escape) and closes on outside click.
 */
import { useEffect, useId, useRef, useState } from "react";

import { FOCUS_RING, Sym } from "./cockpitShared";
import type { ConfigEnvironment } from "@/lib/types";

export interface EnvironmentPopoverProps {
  environment: ConfigEnvironment | null;
}

/** Plain-language tooltips for the fixed-stack rows (teaching, not data). */
const ROW_TOOLTIPS: Record<string, string> = {
  Selection: "How the app picks candidate items.",
  Agent: "The agent that drives the app.",
  Resources: "The data the agent draws on.",
  Scorer: "Turns the user's self-report into scores.",
};

export function EnvironmentPopover({ environment }: EnvironmentPopoverProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const panelId = useId();

  // Close on outside click + Escape.
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

  const runtime = environment?.runtime ?? "Harbor";
  const runtimeRows: Array<{ label: string; value: string }> = [
    { label: "Runtime", value: runtime },
    { label: "Persona", value: environment?.personaAgent ?? "PersonaEval task controller" },
    { label: "Persona default", value: environment?.personaModel ?? "anthropic/claude-haiku-4-5" },
    { label: "Chatbot API", value: environment?.applicationApi ?? "chatbot-api sidecar" },
    { label: "Scorer", value: environment?.scorer ?? "PersonaEval self-report scorer" },
    { label: "Cache", value: environment?.cache ?? "Docker image + model cache volumes" },
  ];
  const stackRows: Array<{ label: string; value: string }> = [
    { label: "Selection", value: environment?.ranker ?? "application-specific ranking / tool selection" },
    { label: "Resources", value: environment?.resources ?? "adapter-specific resources" },
    { label: "Agent", value: environment?.agent ?? "chatbot application adapter" },
  ];
  const promptOwnership = environment?.promptOwnership ?? {
    personaSystemPrompt: "Persona prompt from task runtime",
    taskPrompt: "Application-provided chatbot simulation prompt",
  };
  const promptRows: Array<{ label: string; value: string }> = [
    { label: "System prompt", value: promptOwnership.personaSystemPrompt },
    { label: "Task prompt", value: promptOwnership.taskPrompt },
  ];

  return (
    <div ref={rootRef} className="relative ml-auto flex flex-shrink-0 items-center gap-2 border-l border-outline-dim pl-6">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        className={`flex items-center gap-1.5 rounded border border-outline bg-surface-low px-3 py-1.5 text-[13px] font-medium text-text-variant transition-colors hover:border-primary ${FOCUS_RING}`}
      >
        <Sym name="hub" size={16} className="text-text-dim" />
        {runtime}
        <Sym name={open ? "expand_less" : "expand_more"} size={16} className="text-text-dim" />
      </button>

      {open && (
        <div
          id={panelId}
          role="region"
          aria-label="Fixed environment"
          className="panel absolute right-0 top-full z-30 mt-2 w-80 rounded-md border border-outline bg-surface-lowest p-3 shadow-2xl"
        >
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="flex items-center gap-1 hud text-[10px] text-text-dim">
              <Sym name="lock" size={13} />
              Test environment (Harbor)
            </p>
            <span
              className="hud rounded border border-outline px-1.5 py-0.5 text-[8px] text-text-dim"
              title="These are fixed by the Harbor test sandbox and can't be changed for this run."
            >
              Read-only
            </span>
          </div>
          <div className="space-y-2">
            {runtimeRows.map((r) => (
              <div key={r.label} className="flex items-center justify-between gap-3">
                <span className="hud text-[9px] text-text-dim" title={ROW_TOOLTIPS[r.label]}>
                  {r.label}
                </span>
                <span className="truncate font-mono text-[11px] text-text-variant">
                  {r.value}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-3 border-t border-outline-dim pt-3">
            <p className="mb-2 flex items-center gap-1 hud text-[10px] text-text-dim">
              <Sym name="storage" size={13} />
              What&apos;s running inside the app
            </p>
            <div className="space-y-2">
              {stackRows.map((r) => (
                <div key={r.label} className="flex items-center justify-between gap-3">
                  <span className="hud text-[9px] text-text-dim" title={ROW_TOOLTIPS[r.label]}>
                    {r.label}
                  </span>
                  <span className="truncate font-mono text-[11px] text-text-variant">
                    {r.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-3 border-t border-outline-dim pt-3">
            <p className="mb-2 flex items-center gap-1 hud text-[10px] text-text-dim">
              <Sym name="account_tree" size={13} />
              Who writes which prompt
            </p>
            <div className="space-y-2">
              {promptRows.map((r) => (
                <div key={r.label} className="flex items-start justify-between gap-3">
                  <span className="shrink-0 hud text-[9px] text-text-dim">{r.label}</span>
                  <span className="max-w-[12.5rem] text-right text-[11px] leading-relaxed text-text-dim">
                    {r.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default EnvironmentPopover;
