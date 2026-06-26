/**
 * PersonaCard — one selectable row in the cockpit's left persona catalog.
 *
 * Leads with the persona's role/occupation (a human descriptive title derived
 * from real persona text — never fabricated), demotes the dataset source to a
 * tinted provenance chip in the top-right, and carries an `Age · Sex · id` HUD
 * micro-label. An optional one-line trait sits below when it adds something the
 * heading does not. The selected row shows the matrAIx corner bracket (`.panel`)
 * with a cyan border and `aria-pressed`; idle rows stay quiet until hover.
 *
 * Purely presentational: the parent owns selection + the persona data.
 */
import { memo } from "react";

import {
  FOCUS_RING,
  Sym,
  parseDemographicsFromBlurb,
  personaCodename,
  personaDescriptiveTitle,
} from "./cockpitShared";
import type { PersonaEvalPersona } from "@/lib/types";

/**
 * Per-source provenance-chip tone (port of the mockup's `srcColor`). Unknown
 * sources fall to the neutral default — we never invent a tone for a source we
 * don't recognise.
 */
const SOURCE_TONE: Record<string, string> = {
  Nemotron: "text-secondary border-secondary/30 bg-secondary/10",
  OASIS: "text-primary border-primary/30 bg-primary/10",
  PersonaHub: "text-warn border-warn/30 bg-warn/10",
};
const NEUTRAL_TONE = "text-text-variant border-outline bg-surface-high";

export interface PersonaCardProps {
  persona: PersonaEvalPersona;
  selected: boolean;
  onSelect: (persona: PersonaEvalPersona) => void;
}

function PersonaCardInner({ persona, selected, onSelect }: PersonaCardProps) {
  const codename = personaCodename(persona.name, persona.id);
  const heading = personaDescriptiveTitle(null, persona.blurb, persona.source);
  const demographics = parseDemographicsFromBlurb(persona.blurb);
  const age = demographics.find((c) => c.key === "age");
  const sex = demographics.find((c) => c.key === "gender");
  const occupation = demographics.find((c) => c.key === "occupation");
  // Age · Sex · id — render only the parts that genuinely parse (id is always present).
  const metaLabel = [age?.text, sex?.text, codename].filter(Boolean).join(" · ");
  // Surface the parsed occupation as a secondary line only when it adds something
  // the heading does not (avoid repeating the heading).
  const traitLine = occupation && occupation.full !== heading ? occupation.full : null;
  const tone = SOURCE_TONE[persona.source ?? ""] ?? NEUTRAL_TONE;

  return (
    <button
      type="button"
      onClick={() => onSelect(persona)}
      aria-pressed={selected}
      aria-label={persona.source ? `${heading}, ${persona.source}` : heading}
      className={`group relative mb-1 w-full rounded-md border p-4 text-left transition-colors duration-200 ${FOCUS_RING} ${
        selected ? "panel border-primary bg-surface" : "border-outline bg-surface hover:border-primary"
      }`}
    >
      <div className="flex items-start gap-sm">
        <div
          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded border border-outline ${
            selected ? "bg-primary/10" : "bg-surface-high"
          }`}
          aria-hidden
        >
          <Sym
            name="person"
            fill={1}
            size={22}
            className={selected ? "text-primary" : "text-text-variant group-hover:text-primary"}
          />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-start justify-between gap-2">
            <h3
              className={`min-w-0 flex-1 truncate font-display text-[14px] font-semibold ${
                selected ? "text-primary" : "text-text-main"
              }`}
            >
              {heading}
            </h3>
            {persona.source && (
              <span
                title={`Source dataset: ${persona.source}`}
                className={`flex-none rounded border px-1.5 py-0.5 text-[10px] font-medium ${tone}`}
              >
                {persona.source}
              </span>
            )}
          </div>
          {metaLabel && (
            <p title="Age · sex · persona id" className="hud truncate text-[8px] text-text-dim">
              {metaLabel}
            </p>
          )}
          {traitLine && (
            <p className="mt-1 truncate text-[11px] leading-snug text-text-variant">{traitLine}</p>
          )}
        </div>
      </div>
    </button>
  );
}

export const PersonaCard = memo(PersonaCardInner);

export default PersonaCard;
