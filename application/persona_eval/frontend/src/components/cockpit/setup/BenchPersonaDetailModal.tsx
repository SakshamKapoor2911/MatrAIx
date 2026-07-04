import { useQuery } from "@tanstack/react-query";

import { Markdown } from "@/components/Markdown";
import { api, ApiError } from "@/lib/api";
import { PERSONA_BENCH_POOL, type PersonaPoolPersonaCard } from "@/lib/types";
import { RailInsetModal } from "./RailInsetModal";

export interface BenchPersonaDetailModalProps {
  open: boolean;
  persona: PersonaPoolPersonaCard | null;
  onClose: () => void;
  onUse?: (persona: PersonaPoolPersonaCard) => void;
}

export function BenchPersonaDetailModal({
  open,
  persona,
  onClose,
  onUse,
}: BenchPersonaDetailModalProps) {
  const personaId = persona?.personaId ?? null;
  const detailQuery = useQuery({
    queryKey: ["persona-pool-detail", personaId],
    queryFn: () => api.getPersonaPoolPersona(personaId!),
    enabled: open && Boolean(personaId),
    staleTime: 120_000,
    retry: 1,
  });

  const markdown = detailQuery.data?.profileMarkdown?.trim() ?? "";

  return (
    <RailInsetModal
      open={open && Boolean(persona)}
      title={persona?.name ?? (personaId ? `persona-${personaId}` : "Persona")}
      subtitle={`Persona · ${PERSONA_BENCH_POOL}`}
      onClose={onClose}
    >
      {detailQuery.isLoading && (
        <p className="text-[12px] text-text-dim">Loading persona record…</p>
      )}
      {detailQuery.isError && (
        <p className="text-[12px] text-danger">
          {detailQuery.error instanceof ApiError
            ? detailQuery.error.message
            : "Could not load persona record."}
        </p>
      )}
      {markdown && (
        <Markdown className="text-[12px] leading-relaxed text-text-variant">{markdown}</Markdown>
      )}
      {onUse && persona && (
        <div className="mt-4 flex justify-end border-t border-outline/30 pt-4">
          <button
            type="button"
            onClick={() => {
              onUse(persona);
              onClose();
            }}
            className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-[12px] font-medium text-on-primary transition hover:bg-primary/90"
          >
            Use persona
          </button>
        </div>
      )}
    </RailInsetModal>
  );
}
