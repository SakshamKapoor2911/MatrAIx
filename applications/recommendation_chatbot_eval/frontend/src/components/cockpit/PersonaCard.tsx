/**
 * PersonaCard — one selectable row in the cockpit's left persona catalog.
 *
 * Ports the mockup's rich persona row: a round avatar, the persona's source as
 * the bold heading, a monospace id chip, a one-line descriptive title (human
 * framing derived from real persona text — never fabricated), and demographic
 * chips parsed best-effort from the blurb. The selected row gets the indigo
 * left bar + border the mockup uses; inactive rows are quiet until hover.
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

export interface PersonaCardProps {
  persona: PersonaEvalPersona;
  selected: boolean;
  onSelect: (persona: PersonaEvalPersona) => void;
}

function PersonaCardInner({ persona, selected, onSelect }: PersonaCardProps) {
  const codename = personaCodename(persona.name, persona.id);
  const heading = persona.source || persona.name;
  const title = personaDescriptiveTitle(null, persona.blurb, persona.source);
  const chips = parseDemographicsFromBlurb(persona.blurb).slice(0, 3);

  return (
    <button
      type="button"
      onClick={() => onSelect(persona)}
      aria-pressed={selected}
      aria-label={`${heading}, ${title}`}
      className={`group relative mb-1 w-full overflow-hidden rounded-lg p-sm text-left transition-colors duration-200 ${FOCUS_RING} ${
        selected
          ? "border border-primary bg-surface-container-lowest shadow-soft"
          : "border border-transparent bg-transparent hover:border-outline-variant hover:bg-surface-variant"
      }`}
    >
      {selected && <div className="absolute bottom-0 left-0 top-0 w-1 bg-primary" aria-hidden />}
      <div className="flex items-start gap-sm pl-2">
        <div
          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full ${
            selected ? "bg-primary/10" : "bg-surface-container-highest"
          }`}
          aria-hidden
        >
          <Sym name="person" fill={1} size={22} className={selected ? "text-primary" : "text-on-surface-variant"} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-0.5 flex items-center justify-between gap-2">
            <h3
              className={`truncate text-body-md font-semibold ${selected ? "text-primary" : "text-on-surface"}`}
            >
              {heading}
            </h3>
            <span
              className={`rounded px-1.5 py-0.5 font-mono-sm text-mono-sm ${
                selected ? "bg-surface-container text-on-surface-variant" : "text-on-surface-variant"
              }`}
            >
              {codename}
            </span>
          </div>
          <p className="mb-2 truncate text-body-sm text-on-surface-variant">{title}</p>
          {chips.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {chips.map((c) => (
                <span
                  key={c.key}
                  title={c.full}
                  className="max-w-[96px] truncate rounded bg-surface-container px-1.5 py-0.5 text-[10px] font-medium text-on-surface-variant"
                >
                  {c.text}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}

export const PersonaCard = memo(PersonaCardInner);

export default PersonaCard;
