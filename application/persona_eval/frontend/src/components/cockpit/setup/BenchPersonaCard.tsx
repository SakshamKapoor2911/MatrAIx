import { FOCUS_RING, Sym } from "../cockpitShared";
import type { PersonaPoolPersonaCard } from "@/lib/types";
import { DIMENSION_CHIP_TONES, ToneChip } from "./ToneChip";

const DIM_LABELS: Record<string, string> = {
  age_bracket: "Age",
  region: "Region",
  domain: "Domain",
  intent: "Intent",
  life_stage: "Life stage",
  source: "Source",
};

export interface BenchPersonaCardProps {
  persona: PersonaPoolPersonaCard;
  selected?: boolean;
  onToggle?: () => void;
  onOpenDetail?: () => void;
}

export function BenchPersonaCard({
  persona,
  selected = false,
  onToggle,
  onOpenDetail,
}: BenchPersonaCardProps) {
  const dims = Object.entries(persona.dimensions ?? {}).slice(0, 4);
  return (
    <div
      className={`w-full rounded-lg border p-3 transition-all duration-200 ${
        selected
          ? "persona-card--selected"
          : "border-outline/45 bg-surface/40 hover:border-primary/30 hover:bg-surface/70"
      }`}
    >
      <div className="mb-2.5 flex items-start justify-between gap-2">
        <button
          type="button"
          onClick={onToggle}
          className={`min-w-0 flex-1 text-left ${FOCUS_RING}`}
        >
          <p className="font-display text-[14px] font-semibold leading-tight text-text-main">
            {persona.name ?? `persona-${persona.personaId}`}
          </p>
          <p className="mt-0.5 font-mono text-[10px] tracking-wide text-text-dim">{persona.personaId}</p>
        </button>
        <div className="flex shrink-0 items-center gap-1">
          {onOpenDetail && (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onOpenDetail();
              }}
              aria-label={`View details for ${persona.name ?? persona.personaId}`}
              className={`rounded-md p-1.5 text-text-dim transition hover:bg-surface-high hover:text-primary ${FOCUS_RING}`}
            >
              <Sym name="info" size={16} />
            </button>
          )}
          {selected && (
            <ToneChip tone="primary" solid className="text-[9px] uppercase tracking-wide">
              Selected
            </ToneChip>
          )}
        </div>
      </div>
      <button type="button" onClick={onToggle} className={`w-full text-left ${FOCUS_RING}`}>
        <div className="flex flex-wrap gap-1.5">
          {dims.map(([key, value], index) => (
            <span key={key} title={key}>
              <ToneChip tone={DIMENSION_CHIP_TONES[index % DIMENSION_CHIP_TONES.length]}>
                <span className="tone-chip__key">{DIM_LABELS[key] ?? key}: </span>
                {value}
              </ToneChip>
            </span>
          ))}
        </div>
      </button>
    </div>
  );
}
