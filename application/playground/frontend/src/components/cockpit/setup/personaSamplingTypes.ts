/** Persona sampling state shared by the cockpit left rail. */

export type PersonaSamplingMode = "single" | "random" | "stratified" | "all";

export interface PersonaDimensionFilters {
  sources: string[];
  /** dimension id → selected values (multi-select per dimension). */
  dimensionFilters: Record<string, string[]>;
}

export function emptyPersonaDimensionFilters(): PersonaDimensionFilters {
  return { sources: [], dimensionFilters: {} };
}

export function activeFilterCount(filters: PersonaDimensionFilters): number {
  const dimCount = Object.values(filters.dimensionFilters).filter((values) => values.length > 0).length;
  return filters.sources.length + dimCount;
}

export function filtersForSampleApi(
  filters: PersonaDimensionFilters,
): Record<string, string | string[]> | undefined {
  const entries = Object.entries(filters.dimensionFilters).filter(([, values]) => values.length > 0);
  if (entries.length === 0) return undefined;
  return Object.fromEntries(entries.map(([key, values]) => [key, values.length === 1 ? values[0] : values]));
}
