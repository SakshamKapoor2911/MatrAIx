/** Merge API task rows onto a built-in catalog so stale backends still show every task. */
export function mergeTaskCatalog<T extends { id: string }>(
  fallback: T[],
  apiTasks: T[] | undefined,
  enrich?: (row: T, api?: T, base?: T) => T,
): T[] {
  const byId = new Map<string, T>(fallback.map((task) => [task.id, task]));
  for (const api of apiTasks ?? []) {
    const base = byId.get(api.id);
    const merged = { ...(base ?? ({} as T)), ...api } as T;
    byId.set(api.id, enrich ? enrich(merged, api, base) : merged);
  }
  return Array.from(byId.values());
}
