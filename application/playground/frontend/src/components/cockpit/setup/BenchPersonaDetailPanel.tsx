import { useQuery } from "@tanstack/react-query";

import { Markdown } from "@/components/Markdown";
import { api, ApiError } from "@/lib/api";
import { personaDisplayId, personaPrimaryName } from "@/lib/personaDisplay";
import { PERSONA_BENCH_POOL, type PersonaPoolPersonaCard } from "@/lib/types";
import { FOCUS_RING, Sym } from "../cockpitShared";
import { PersonaAvatar } from "./PersonaAvatar";
import { personaRosterLines } from "./simulatedPersonaVisual";
import { CHIP_TEXT_CLASS, personaDimChipTone } from "./taskCardLabels";
import { ToneChip } from "./ToneChip";

const DIM_SECTIONS: Array<{ key: string; label: string }> = [
  { key: "source", label: "Source" },
  { key: "age_bracket", label: "Age bracket" },
  { key: "life_stage", label: "Life stage" },
  { key: "domain", label: "Domain" },
  { key: "region", label: "Region" },
  { key: "intent", label: "Intent" },
];

export interface BenchPersonaDetailPanelProps {
  persona: PersonaPoolPersonaCard | null;
  onClose: () => void;
  onUse?: (persona: PersonaPoolPersonaCard) => void;
  /** Inline inside the cockpit persona rail — no nested glass card chrome. */
  embedded?: boolean;
  className?: string;
}

export function BenchPersonaDetailPanel({
  persona,
  onClose,
  onUse,
  embedded = false,
  className = "",
}: BenchPersonaDetailPanelProps) {
  const personaId = persona?.personaId ?? null;
  const detailQuery = useQuery({
    queryKey: ["persona-pool-detail", personaId],
    queryFn: () => api.getPersonaPoolPersona(personaId!),
    enabled: Boolean(personaId),
    staleTime: 120_000,
    retry: 1,
  });

  if (!persona) return null;

  const displayName = personaPrimaryName(persona.name, persona.personaId, persona.dimensions ?? {});
  const codename = personaDisplayId(persona.personaId);
  const roster = personaRosterLines(persona.dimensions ?? {});
  const blurb = roster
    ? roster.secondary
      ? `${roster.primary} · ${roster.secondary}`
      : roster.primary
    : null;
  const markdown = detailQuery.data?.profileMarkdown?.trim() ?? "";
  const shellClass = embedded
    ? `flex h-full min-h-0 w-full flex-col overflow-hidden ${className}`
    : `glass-panel flex h-full min-h-0 w-full flex-col overflow-hidden rounded-xl border border-outline/40 ${className}`;

  return (
    <aside
      className={shellClass}
      aria-label={`Persona details for ${displayName}`}
    >
      <div
        className={`flex items-start justify-between gap-2 border-outline/30 px-0 py-3 ${
          embedded ? "border-b" : "border-b px-4"
        }`}
      >
        <div className="min-w-0">
          <p className="cockpit-field-label text-[10px] text-text-dim">Persona profile</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close persona details"
          className={`shrink-0 rounded-md p-1.5 text-text-dim transition hover:bg-surface-high hover:text-text-main ${FOCUS_RING}`}
        >
          <Sym name="close" size={18} />
        </button>
      </div>

      <div className={`custom-scrollbar min-h-0 flex-1 overflow-y-auto py-4 ${embedded ? "" : "px-4"}`}>
        <div className="flex items-start gap-3">
          <PersonaAvatar
            personaId={persona.personaId}
            dimensions={persona.dimensions}
            size="lg"
          />
          <div className="min-w-0 flex-1 pt-0.5">
            <h2 className="font-display text-[18px] font-semibold leading-tight text-text-main">
              {displayName}
            </h2>
            <p className="mt-0.5 font-mono text-[11px] tracking-wide text-text-dim">{codename}</p>
            {persona.source ? (
              <ToneChip tone="primary" className={`${CHIP_TEXT_CLASS} mt-2`}>
                {persona.source}
              </ToneChip>
            ) : null}
          </div>
        </div>

        {blurb ? (
          <p className="mt-4 text-[12px] leading-relaxed text-text-variant">{blurb}</p>
        ) : null}

        <div className="mt-4 grid grid-cols-2 gap-3">
          {DIM_SECTIONS.map(({ key, label }, index) => {
            const value = persona.dimensions?.[key];
            if (!value) return null;
            return (
              <div key={key} className="min-w-0">
                <p className="cockpit-field-label mb-1 text-[9px] text-text-dim">{label}</p>
                <ToneChip tone={personaDimChipTone(key, index)} className={CHIP_TEXT_CLASS}>
                  {value}
                </ToneChip>
              </div>
            );
          })}
        </div>

        {detailQuery.isLoading && (
          <p className="mt-4 text-[12px] text-text-dim">Loading persona record…</p>
        )}
        {detailQuery.isError && (
          <p className="mt-4 text-[12px] text-danger">
            {detailQuery.error instanceof ApiError
              ? detailQuery.error.message
              : "Could not load persona record."}
          </p>
        )}
        {markdown ? (
          <div className="mt-4 border-t border-outline/25 pt-4">
            <p className="cockpit-field-label mb-2 text-[10px] text-text-dim">Record</p>
            <Markdown className="text-[12px] leading-relaxed text-text-variant">{markdown}</Markdown>
          </div>
        ) : null}

        <p className="mt-4 font-mono text-[10px] text-text-dim">{PERSONA_BENCH_POOL}</p>
      </div>

      {onUse ? (
        <div className={`border-t border-outline/30 py-3 ${embedded ? "" : "px-4"}`}>
          <button
            type="button"
            onClick={() => onUse(persona)}
            className={`inline-flex h-9 w-full items-center justify-center rounded-md bg-primary text-[12px] font-medium text-on-primary transition hover:bg-primary/90 ${FOCUS_RING}`}
          >
            Use persona
          </button>
        </div>
      ) : null}
    </aside>
  );
}
