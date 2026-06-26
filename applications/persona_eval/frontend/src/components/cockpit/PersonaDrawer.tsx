/**
 * PersonaDrawer — the full persona context, shown in a dismissible modal.
 *
 * The Persona inspector tab shows a curated summary; the "Raw" affordance opens
 * this drawer with the persona's complete record — its full humanized context
 * block (verbatim) plus its identity — for the operator who wants everything.
 * It is honest: it renders exactly the text the backend provides, with no
 * fabricated structure.
 *
 * A focus-trapped, Escape-dismissible dialog (role="dialog", aria-modal) that
 * restores focus to the opener on close.
 */
import { useEffect, useRef } from "react";

import { FOCUS_RING, Sym, personaCodename, personaDescriptiveTitle } from "./cockpitShared";
import { usePersonaDetail } from "@/lib/usePersonaEval";
import type { PersonaEvalPersona } from "@/lib/types";

/** Per-source provenance-chip tone; unknown sources fall to the neutral default. */
const SOURCE_TONE: Record<string, string> = {
  Nemotron: "text-secondary border-secondary/30 bg-secondary/10",
  OASIS: "text-primary border-primary/30 bg-primary/10",
  PersonaHub: "text-warn border-warn/30 bg-warn/10",
};
const NEUTRAL_TONE = "text-text-variant border-outline bg-surface-high";

export interface PersonaDrawerProps {
  open: boolean;
  onClose: () => void;
  persona: PersonaEvalPersona | null;
  /** A run-loaded context, if richer than the catalog's; otherwise the drawer
   * fetches the persona's full record itself. */
  context: string | null;
}

export function PersonaDrawer({ open, onClose, persona, context }: PersonaDrawerProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);
  // Fetch the complete humanized profile (cached by id) so the drawer shows the
  // *full* persona, not the truncated list blurb. Prefer a run-loaded context.
  const detail = usePersonaDetail(persona?.id ?? null);

  useEffect(() => {
    if (!open) return;
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previouslyFocused.current?.focus?.();
    };
  }, [open, onClose]);

  if (!open || !persona) return null;

  const fullContext = context && context.trim() ? context : detail.data?.context ?? null;
  // Human-readable heading (descriptive role) + machine codename, instead of the
  // raw "Source · ID" name repeated alongside the codename.
  const title = personaDescriptiveTitle(fullContext, persona.blurb, persona.source);
  const codename = personaCodename(persona.name, persona.id);
  const tone = SOURCE_TONE[persona.source ?? ""] ?? NEUTRAL_TONE;
  const loading = detail.isLoading && !fullContext;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Full profile for ${title}`}
        className="relative z-10 flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-md border border-outline bg-surface-lowest shadow-2xl"
      >
        <div className="flex items-center gap-3 border-b border-outline px-4 py-3">
          <div
            className="flex h-10 w-10 flex-none items-center justify-center rounded border border-outline bg-surface-high"
            aria-hidden
          >
            <Sym name="person" fill={1} size={22} className="text-text-variant" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="hud text-[9px] text-text-dim">Persona</div>
            <h2 className="truncate font-display text-[18px] font-bold text-text-main">{title}</h2>
            <p className="mt-0.5 flex items-center gap-2 text-[12px] text-text-variant">
              {persona.source && (
                <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${tone}`}>
                  {persona.source}
                </span>
              )}
              <span className="font-mono text-[10px] text-text-dim">{codename}</span>
            </p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close persona detail"
            className={`flex h-8 w-8 flex-none items-center justify-center rounded-md border border-outline text-text-variant transition-colors hover:border-primary hover:text-text-main ${FOCUS_RING}`}
          >
            <Sym name="close" size={20} />
          </button>
        </div>
        <div className="custom-scrollbar overflow-y-auto p-5 space-y-5">
          {loading ? (
            <div className="space-y-2" aria-label="Loading full persona" aria-busy>
              {[5, 7, 6, 4, 7, 5].map((w, i) => (
                <div
                  key={i}
                  className="h-3 animate-pulse rounded bg-surface-high"
                  style={{ width: `${w * 10}%` }}
                />
              ))}
            </div>
          ) : fullContext || persona.blurb ? (
            <div className="rounded-md border border-outline bg-surface p-4">
              <div className="hud mb-2 text-[10px] text-text-dim">Raw record</div>
              <pre className="whitespace-pre-wrap break-words rounded border border-outline bg-field p-3 font-mono text-[10.5px] leading-relaxed text-primary">
                {fullContext || persona.blurb}
              </pre>
            </div>
          ) : (
            <p className="text-[12px] italic leading-relaxed text-text-dim">
              This persona has no extra profile text — the summary above is all we have.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default PersonaDrawer;
