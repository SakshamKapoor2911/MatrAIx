import { useQuery } from "@tanstack/react-query";

import { Markdown } from "@/components/Markdown";
import { api, ApiError } from "@/lib/api";
import { PERSONA_BENCH_POOL, type PersonaPoolPersonaCard } from "@/lib/types";
import { RailInsetModal } from "./RailInsetModal";

export interface BenchPersonaDetailModalProps {
  open: boolean;
  persona: PersonaPoolPersonaCard | null;
  onClose: () => void;
}

export function BenchPersonaDetailModal({ open, persona, onClose }: BenchPersonaDetailModalProps) {
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
    </RailInsetModal>
  );
}
