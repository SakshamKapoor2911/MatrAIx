import { useQuery } from "@tanstack/react-query";

import { getPersonaEvalPersona } from "./api";
import type { PersonaEvalPersona } from "./types";

export type PersonaEvalRunPhase = "idle" | "building" | "running" | "done" | "error" | "timeout";

export function usePersonaDetail(personaId: string | null) {
  return useQuery<PersonaEvalPersona>({
    queryKey: ["persona-eval", "persona", personaId],
    queryFn: () => getPersonaEvalPersona(personaId as string),
    enabled: personaId !== null,
    staleTime: 10 * 60 * 1000,
  });
}
