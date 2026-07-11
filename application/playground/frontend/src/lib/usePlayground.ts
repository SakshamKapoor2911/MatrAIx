import { useQuery } from "@tanstack/react-query";

import { getPlaygroundPersona } from "./api";
import type { PlaygroundPersona } from "./types";

export type PlaygroundRunPhase = "idle" | "building" | "running" | "done" | "error" | "timeout";

export function usePlaygroundPersonaDetail(personaId: string | null) {
  return useQuery<PlaygroundPersona>({
    queryKey: ["playground", "persona", personaId],
    queryFn: () => getPlaygroundPersona(personaId as string),
    enabled: personaId !== null,
    staleTime: 10 * 60 * 1000,
  });
}
