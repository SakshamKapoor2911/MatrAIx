/**
 * PersonaPanel — the cockpit's Persona inspector panel.
 *
 * Ports the mockup's persona detail: an avatar + name + codename header, a
 * demographics grid, a context block, and trait sections, closed by a "Raw"
 * affordance that opens the full record.
 *
 * Honest data: the live job only exposes the persona's `name` (plus the catalog
 * `{id, source, blurb}`); the full humanized `context` is available only after
 * a run persists. So the panel renders structured demographics where they can
 * be parsed (the catalog blurb / a loaded context), the context block when one
 * is available, and any genuinely-present trait sections — never the mockup's
 * fabricated preference/dislike tags when the data doesn't carry them. The
 * heading pairs a human descriptive title with the machine codename.
 */
import { useMemo } from "react";

import {
  FOCUS_RING,
  Sym,
  humanizeToken,
  parseDemographics,
  parseDemographicsFromBlurb,
  parsePersonaSections,
  personaCodename,
  personaDescriptiveTitle,
} from "./cockpitShared";
import { usePersonaDetail } from "@/lib/usePersonaEval";
import type { PersonaEvalPersona } from "@/lib/types";

export interface PersonaPanelProps {
  persona: PersonaEvalPersona | null;
  /** A run-loaded context, if richer than the catalog's; otherwise the panel
   * fetches the full persona itself. */
  context: string | null;
  /** Open the full-persona drawer. */
  onOpenRaw: () => void;
}

export function PersonaPanel({ persona, context, onOpenRaw }: PersonaPanelProps) {
  // The full humanized profile for the selected persona (cached by id). This is
  // what makes demographics / sections / context complete from the catalog —
  // not just after a run. Prefer an explicitly-passed (run-loaded) context.
  const detail = usePersonaDetail(persona?.id ?? null);
  const fullContext = context && context.trim() ? context : detail.data?.context ?? null;

  const demographics = useMemo(() => {
    if (fullContext) {
      const fromContext = parseDemographics(fullContext);
      if (fromContext.length > 0) return fromContext;
    }
    return parseDemographicsFromBlurb(persona?.blurb);
  }, [fullContext, persona?.blurb]);

  // Context sections (Demographics/Personas/Background/…). Drop the leading
  // "Demographics" section — it's already surfaced as the grid above.
  const sections = useMemo(() => {
    if (!fullContext) return [];
    return parsePersonaSections(fullContext).filter((s) => !/^demographics$/i.test(s.label));
  }, [fullContext]);

  if (!persona) {
    return (
      <div className="p-md">
        <div className="rounded-xl border border-dashed border-border-soft bg-surface-container-low px-4 py-10 text-center">
          <Sym name="person_search" size={28} className="text-outline" />
          <p className="mt-2 text-body-sm leading-relaxed text-on-surface-variant">
            Select a persona from the catalog to see its profile.
          </p>
        </div>
      </div>
    );
  }

  const codename = personaCodename(persona.name, persona.id);
  const title = personaDescriptiveTitle(fullContext, persona.blurb, persona.source);

  return (
    <div className="p-md">
      {/* Avatar & header */}
      <div className="mb-lg flex flex-col items-center">
        <div
          className="relative mb-2 flex h-20 w-20 items-center justify-center rounded-full border-2 border-primary/20 bg-primary/10 p-1"
          aria-hidden
        >
          <Sym name="face" fill={1} size={48} className="text-primary" />
        </div>
        {/* Human framing for the codename: descriptive title as the heading. */}
        <h3 className="text-center text-headline-md font-headline-md text-on-surface">{title}</h3>
        <p className="mt-1 text-center text-body-sm text-on-surface-variant">{persona.source || "Persona"}</p>
        <p className="mt-1 flex items-center gap-1 text-body-sm text-on-surface-variant">
          <Sym name="badge" size={14} />
          <span className="font-mono-sm">{codename}</span>
        </p>
      </div>

      {/* Demographics */}
      {demographics.length > 0 && (
        <Section label="Demographics">
          <div className="grid grid-cols-2 gap-x-2 gap-y-2.5">
            {demographics.map((d) => (
              <div key={d.key} className={d.key === "occupation" || d.key === "location" ? "col-span-2" : ""}>
                <p className="text-[11px] uppercase text-on-surface-variant">{humanizeToken(d.key)}</p>
                <p className="text-body-sm text-on-surface" title={d.full}>
                  {d.full}
                </p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Context block — a readable preview of the full profile (the complete
          record is one tap away via "Full persona"). */}
      <Section label="Context">
        <p className="rounded-md border border-border-soft bg-surface-container-low p-3 text-body-sm leading-relaxed text-on-surface-variant">
          {fullContext && fullContext.trim()
            ? firstParagraph(fullContext)
            : detail.isLoading
              ? "Loading full persona…"
              : persona.blurb || "No context available."}
        </p>
      </Section>

      {/* Trait sections from the parsed context (only those present). */}
      {sections.slice(0, 4).map((s) => (
        <Section key={s.label} label={s.label}>
          <p className="whitespace-pre-wrap text-body-sm leading-relaxed text-on-surface-variant">{s.body}</p>
        </Section>
      ))}

      {/* Raw affordance */}
      <div className="pt-1">
        <button
          type="button"
          onClick={onOpenRaw}
          className={`flex items-center gap-1 rounded-md px-1 py-0.5 text-label-md font-label-md text-on-surface-variant transition-colors hover:text-primary ${FOCUS_RING}`}
        >
          <Sym name="data_object" size={16} />
          Full persona
          <Sym name="chevron_right" size={14} />
        </button>
      </div>
    </div>
  );
}

/** A labelled inspector section with an underlined header. */
function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-md">
      <h4 className="mb-2 border-b border-border-soft pb-1 text-label-md font-label-md uppercase tracking-wider text-on-surface-variant">
        {label}
      </h4>
      {children}
    </div>
  );
}

/** The first non-empty paragraph of a context block (for the Context preview). */
function firstParagraph(context: string): string {
  // Skip the structured "Demographics:" preamble; take the first prose-ish block.
  const sections = parsePersonaSections(context).filter((s) => !/^demographics$/i.test(s.label));
  const prose = sections.find((s) => s.body && s.body.length > 40);
  const text = prose?.body ?? sections[0]?.body ?? context;
  return text.length > 420 ? text.slice(0, 417).trimEnd() + "…" : text;
}

export default PersonaPanel;
