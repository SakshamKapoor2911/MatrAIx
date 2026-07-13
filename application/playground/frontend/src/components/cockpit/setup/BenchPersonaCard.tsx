import { FOCUS_RING, Sym } from "../cockpitShared";
import { personaDisplayId, personaPrimaryName } from "@/lib/personaDisplay";
import type { PersonaPoolPersonaCard } from "@/lib/types";
import { PersonaAvatar } from "./PersonaAvatar";
import { personaRosterLines } from "./simulatedPersonaVisual";
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
  const displayName = personaPrimaryName(persona.name, persona.personaId, persona.dimensions ?? {});
  const codename = personaDisplayId(persona.personaId);
  const roster = personaRosterLines(persona.dimensions ?? {});
  const blurb = roster
    ? roster.secondary
      ? `${roster.primary} · ${roster.secondary}`
      : roster.primary
    : null;

  return (
    <div
      className={`flex min-h-[10.5rem] w-full flex-col overflow-hidden rounded-xl border p-3 transition-all duration-200 ${
        selected
          ? "persona-card--selected"
          : disabled
            ? "border-outline/45 bg-surface/30 opacity-80"
            : "border-outline/45 bg-surface/40 hover:border-primary/30 hover:bg-surface/70"
      }`}
    >
      <div className="mb-2 flex items-start gap-2.5">
        <button
          type="button"
          disabled={disabled}
          onClick={onToggle}
          className={`shrink-0 disabled:cursor-default disabled:opacity-80 ${FOCUS_RING}`}
          aria-label={`Select ${displayName}`}
        >
          <PersonaAvatar personaId={persona.personaId} dimensions={persona.dimensions} size="md" />
        </button>

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <button
              type="button"
              disabled={disabled}
              onClick={onToggle}
              className={`min-w-0 flex-1 text-left disabled:cursor-default disabled:opacity-80 ${FOCUS_RING}`}
            >
              <p className="truncate font-display text-[14px] font-semibold leading-tight text-text-main">
                {displayName}
              </p>
              <p className="mt-0.5 font-mono text-[12px] tracking-wide text-text-dim">{codename}</p>
            </button>
            <div className="flex shrink-0 items-center gap-1">
              {persona.source ? (
                <ToneChip tone="primary" className={CHIP_TEXT_CLASS}>
                  {persona.source}
                </ToneChip>
              ) : null}
              {onOpenDetail && (
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onOpenDetail();
                  }}
                  aria-label={`View details for ${displayName}`}
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
        </div>
      </div>

      {blurb ? (
        <p className="mb-2 line-clamp-2 text-[13px] leading-snug text-text-variant">{blurb}</p>
      ) : null}

      <button
        type="button"
        disabled={disabled}
        onClick={onToggle}
        className={`mt-auto w-full text-left disabled:cursor-default disabled:opacity-80 ${FOCUS_RING}`}
      >
        <div className="grid grid-cols-2 gap-1.5 overflow-hidden">
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
