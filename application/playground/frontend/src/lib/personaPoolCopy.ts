import type { PersonaPoolCatalog } from "./types";

export function poolSlugLabel(poolPath: string): string {
  const slug = poolPath.split("/").filter(Boolean).pop() ?? poolPath;
  return slug.replace(/-/g, " ");
}

export function personaPoolEmptyMessage(
  catalog: PersonaPoolCatalog | null | undefined,
): string {
  const pool = catalog?.pool ? poolSlugLabel(catalog.pool) : "persona pool";
  return `${pool} is empty or could not be loaded.`;
}
