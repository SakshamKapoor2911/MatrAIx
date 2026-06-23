/**
 * EnvironmentPopover — the read-only "Fixed environment" facts.
 *
 * The cockpit separates *editable knobs* (Model/Domain/Conversation style/Max
 * turns) from the *fixed* parts of the stack the operator cannot change. This
 * renders that read-only block — Runtime (Harbor), persona agent, application
 * API sidecar, cache policy, Ranker (native SASRec), Catalog (`all_resources`),
 * Agent (InteRecAgent), and the Harbor/application prompt boundary — from the
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
    { label: "Persona", value: environment?.personaAgent ?? "Harbor persona-claude-code" },
    { label: "Rec API", value: environment?.applicationApi ?? "rec-agent-api sidecar" },
    { label: "Cache", value: environment?.cache ?? "Docker image + model cache volumes" },
  ];
  const stackRows: Array<{ label: string; value: string }> = [
    { label: "Ranker", value: environment?.ranker ?? "SASRec (native)" },
    { label: "Catalog", value: environment?.resources ?? "all_resources" },
    { label: "Agent", value: environment?.agent ?? "InteRecAgent" },
  ];
  const promptOwnership = environment?.promptOwnership ?? {
    personaSystemPrompt: "Harbor native persona injection",
    taskPrompt: "Application-provided recommender simulation prompt",
  };
  const promptRows: Array<{ label: string; value: string }> = [
    { label: "System prompt", value: promptOwnership.personaSystemPrompt },
    { label: "Task prompt", value: promptOwnership.taskPrompt },
  ];

  return (
    <div ref={rootRef} className="relative ml-auto flex flex-shrink-0 items-center gap-2 border-l border-border-soft pl-6">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        className={`flex items-center gap-1.5 rounded bg-surface-container-low px-3 py-1.5 text-body-sm font-medium text-on-surface-variant transition-colors hover:bg-surface-container ${FOCUS_RING}`}
      >
        <Sym name="hub" size={16} className="text-outline" />
        {runtime}
        <Sym name={open ? "expand_less" : "expand_more"} size={16} className="text-outline" />
      </button>

      {open && (
        <div
          id={panelId}
          role="region"
          aria-label="Fixed environment"
          className="absolute right-0 top-full z-30 mt-2 w-80 rounded-lg border border-border-soft bg-surface-container-lowest p-3 shadow-pop"
        >
          <p className="mb-2 flex items-center gap-1 text-[11px] font-medium uppercase tracking-wider text-on-surface-variant">
            <Sym name="lock" size={13} />
            Harbor environment
          </p>
          <div className="space-y-2">
            {runtimeRows.map((r) => (
              <div key={r.label} className="flex items-center justify-between gap-3">
                <span className="text-body-sm text-on-surface-variant">{r.label}</span>
                <span className="truncate rounded bg-surface-container px-1.5 py-0.5 font-mono-sm text-mono-sm text-on-surface">
                  {r.value}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-3 border-t border-border-soft pt-3">
            <p className="mb-2 flex items-center gap-1 text-[11px] font-medium uppercase tracking-wider text-on-surface-variant">
              <Sym name="storage" size={13} />
              RecAI stack
            </p>
            <div className="space-y-2">
              {stackRows.map((r) => (
                <div key={r.label} className="flex items-center justify-between gap-3">
                  <span className="text-body-sm text-on-surface-variant">{r.label}</span>
                  <span className="truncate rounded bg-surface-container px-1.5 py-0.5 font-mono-sm text-mono-sm text-on-surface">
                    {r.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-3 border-t border-border-soft pt-3">
            <p className="mb-2 flex items-center gap-1 text-[11px] font-medium uppercase tracking-wider text-on-surface-variant">
              <Sym name="account_tree" size={13} />
              Prompt boundary
            </p>
            <div className="space-y-2">
              {promptRows.map((r) => (
                <div key={r.label} className="flex items-start justify-between gap-3">
                  <span className="shrink-0 text-body-sm text-on-surface-variant">{r.label}</span>
                  <span className="max-w-[12.5rem] text-right text-body-sm font-medium leading-snug text-on-surface">
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
