import { FOCUS_RING, Sym } from "../cockpitShared";
import type { PersonaPoolPersonaCard } from "@/lib/types";
import { CHIP_TEXT_CLASS, personaDimChipTone } from "./taskCardLabels";
import { ToneChip } from "./ToneChip";

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
  disabled?: boolean;
  onToggle?: () => void;
  onOpenDetail?: () => void;
}

export function BenchPersonaCard({
  persona,
  selected = false,
  disabled = false,
  onToggle,
  onOpenDetail,
}: BenchPersonaCardProps) {
  const dims = Object.entries(persona.dimensions ?? {}).slice(0, 4);
  return (
    <div
      className={`flex h-[8.75rem] w-full flex-col overflow-hidden rounded-lg border p-3 transition-all duration-200 ${
        selected
          ? "persona-card--selected"
          : disabled
            ? "border-outline/45 bg-surface/30 opacity-80"
            : "border-outline/45 bg-surface/40 hover:border-primary/30 hover:bg-surface/70"
      }`}
    >
      <div className="mb-2.5 flex h-[2.25rem] items-start justify-between gap-2">
        <button
          type="button"
          disabled={disabled}
          onClick={onToggle}
          className={`min-w-0 flex-1 text-left disabled:cursor-default disabled:opacity-80 ${FOCUS_RING}`}
        >
          <p className="truncate font-display text-[14px] font-semibold leading-tight text-text-main">
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
            <ToneChip tone="primary" solid className={CHIP_TEXT_CLASS}>
              Selected
            </ToneChip>
          )}
        </div>
      </div>
      <button
        type="button"
        disabled={disabled}
        onClick={onToggle}
        className={`mt-auto w-full text-left disabled:cursor-default disabled:opacity-80 ${FOCUS_RING}`}
      >
        <div className="grid h-[3.25rem] grid-cols-2 gap-1.5 overflow-hidden">
          {dims.map(([key, value], index) => (
            <span key={key} title={`${DIM_LABELS[key] ?? key}: ${value}`} className="block min-w-0">
              <ToneChip
                tone={personaDimChipTone(key, index)}
                className={`${CHIP_TEXT_CLASS} flex w-full min-w-0`}
              >
                <span className="tone-chip__key">{DIM_LABELS[key] ?? key}: </span>
                <span className="min-w-0 truncate">{value}</span>
              </ToneChip>
            </span>
          ))}
        </div>
      </button>
    </div>
  );
}
