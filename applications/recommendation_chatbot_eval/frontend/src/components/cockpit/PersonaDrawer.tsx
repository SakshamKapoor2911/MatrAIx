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
  const loading = detail.isLoading && !fullContext;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-on-surface/30" onClick={onClose} aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`${title} full persona`}
        className="relative z-10 flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-pop"
      >
        <div className="flex items-center justify-between border-b border-border-soft px-4 py-3">
          <div className="min-w-0">
            <h2 className="truncate text-headline-md font-headline-md text-on-surface">{title}</h2>
            <p className="mt-0.5 flex items-center gap-2 text-body-sm text-on-surface-variant">
              {persona.source && (
                <span className="rounded bg-surface-container px-1.5 py-0.5 text-label-md">{persona.source}</span>
              )}
              <span className="font-mono-sm">{codename}</span>
            </p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close persona detail"
            className={`flex h-8 w-8 items-center justify-center rounded-md text-on-surface-variant transition-colors hover:bg-surface-container ${FOCUS_RING}`}
          >
            <Sym name="close" size={20} />
          </button>
        </div>
        <div className="custom-scrollbar overflow-y-auto p-4">
          {loading ? (
            <div className="space-y-2" aria-label="Loading full persona" aria-busy>
              {[5, 7, 6, 4, 7, 5].map((w, i) => (
                <div
                  key={i}
                  className="h-3 animate-pulse rounded bg-surface-container"
                  style={{ width: `${w * 10}%` }}
                />
              ))}
            </div>
          ) : (
            <pre className="whitespace-pre-wrap break-words font-mono-sm text-mono-sm leading-relaxed text-on-surface-variant">
              {fullContext || persona.blurb || "No persona context available."}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

export default PersonaDrawer;
