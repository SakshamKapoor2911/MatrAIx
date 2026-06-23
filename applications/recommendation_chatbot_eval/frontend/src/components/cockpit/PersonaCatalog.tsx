/**
 * PersonaCatalog — the cockpit's left navigator (persona catalog).
 *
 * Ports the mockup's left column: a header with the total persona count, a
 * search box, and source-filter chips ("All" + the curated datasets); then a
 * scrollable list of `PersonaCard` rows. The catalog is domain-free and
 * searchable, so it queries `GET /api/persona-eval/personas?q=&limit=`
 * (debounced) and filters the result client-side by `source` for the chips.
 *
 * Every persona shipped is curated (the synthetic fixtures were removed), so
 * the "Curated" chip documents provenance; the remaining chips narrow to a
 * single curated dataset (Nemotron / OASIS / …) when the operator wants one.
 *
 * Owns its own search + filter UI state; selection is lifted to the parent.
 */
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { PersonaCard } from "./PersonaCard";
import { FOCUS_RING, Sym } from "./cockpitShared";
import { listPersonaEvalPersonas } from "@/lib/api";
import type { PersonaEvalPersona, PersonaEvalPersonasResponse } from "@/lib/types";

/** How many personas to fetch per search (the full catalog is ~336). */
const PERSONA_LIMIT = 400;

/** Debounce a fast-changing value (the search box) by `delay` ms. */
function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

/** The synthetic "All / Curated" filter, plus one chip per curated source. */
type SourceFilter = "all" | "curated" | string;

export interface PersonaCatalogProps {
  selectedId: string | null;
  onSelect: (persona: PersonaEvalPersona) => void;
}

export function PersonaCatalog({ selectedId, onSelect }: PersonaCatalogProps) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<SourceFilter>("all");
  const debouncedQuery = useDebounced(query.trim(), 200);

  const personasQuery = useQuery<PersonaEvalPersonasResponse>({
    queryKey: ["persona-eval-personas", debouncedQuery],
    queryFn: () => listPersonaEvalPersonas({ q: debouncedQuery, limit: PERSONA_LIMIT }),
    refetchOnWindowFocus: false,
    placeholderData: (prev) => prev,
    staleTime: 60 * 1000,
  });

  const all = useMemo(() => personasQuery.data?.personas ?? [], [personasQuery.data]);

  // Distinct curated sources, for the per-source filter chips.
  const sources = useMemo(() => {
    const set = new Set<string>();
    for (const p of all) if (p.source) set.add(p.source);
    return Array.from(set).sort();
  }, [all]);

  const personas = useMemo(() => {
    if (filter === "all" || filter === "curated") return all;
    return all.filter((p) => p.source === filter);
  }, [all, filter]);

  const totalLabel = personasQuery.isLoading && all.length === 0 ? "…" : String(all.length);

  return (
    <aside className="relative z-0 flex h-full w-[300px] flex-shrink-0 flex-col border-r border-border-soft bg-surface-container-low">
      {/* Header: title, count, search, filter chips */}
      <div className="flex-shrink-0 border-b border-border-soft p-md pb-sm">
        <h2 className="mb-xs text-headline-sm font-headline-sm uppercase tracking-[0.05em] text-on-surface">
          Persona Catalog
        </h2>
        <p className="mb-sm text-body-sm text-on-surface-variant">{totalLabel} personas</p>

        <div className="relative mb-sm w-full">
          <Sym
            name="search"
            size={18}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-outline"
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search personas…"
            aria-label="Search personas"
            className={`w-full rounded-md border border-outline-variant bg-surface-container-lowest py-1.5 pl-10 pr-3 text-body-sm text-on-surface outline-none transition-all placeholder:text-outline focus:border-primary ${FOCUS_RING}`}
          />
        </div>

        <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter by source">
          <FilterChip label="All" active={filter === "all"} onClick={() => setFilter("all")} />
          <FilterChip label="Curated" active={filter === "curated"} onClick={() => setFilter("curated")} />
          {sources.map((s) => (
            <FilterChip key={s} label={s} active={filter === s} onClick={() => setFilter(s)} />
          ))}
        </div>
      </div>

      {/* List */}
      <div className="custom-scrollbar flex-1 space-y-unit overflow-y-auto p-sm">
        {personasQuery.isLoading && all.length === 0 ? (
          <CatalogSkeleton />
        ) : personasQuery.isError ? (
          <CatalogError onRetry={() => personasQuery.refetch()} />
        ) : personas.length === 0 ? (
          <CatalogEmpty query={debouncedQuery} />
        ) : (
          personas.map((p) => (
            <PersonaCard key={p.id} persona={p} selected={p.id === selectedId} onSelect={onSelect} />
          ))
        )}
      </div>
    </aside>
  );
}

/** A pill-shaped source filter chip. */
function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`rounded-full px-2.5 py-1 text-label-md font-label-md transition-colors ${FOCUS_RING} ${
        active
          ? "bg-primary text-on-primary"
          : "bg-surface-container text-on-surface-variant hover:bg-surface-container-high"
      }`}
    >
      {label}
    </button>
  );
}

/** A handful of shimmering placeholder rows while the catalog loads. */
function CatalogSkeleton() {
  return (
    <div aria-hidden className="space-y-1">
      {Array.from({ length: 7 }).map((_, i) => (
        <div key={i} className="mb-1 flex items-start gap-sm rounded-lg p-sm pl-3">
          <div className="h-10 w-10 flex-shrink-0 animate-rb-pulse rounded-full bg-surface-container-high" />
          <div className="flex-1 space-y-2 py-1">
            <div className="h-3 w-2/3 animate-rb-pulse rounded bg-surface-container-high" />
            <div className="h-2.5 w-1/2 animate-rb-pulse rounded bg-surface-container" />
            <div className="flex gap-1">
              <div className="h-3.5 w-10 animate-rb-pulse rounded bg-surface-container" />
              <div className="h-3.5 w-6 animate-rb-pulse rounded bg-surface-container" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/** Empty state — no personas match the current search. */
function CatalogEmpty({ query }: { query: string }) {
  return (
    <div className="px-3 py-8 text-center">
      <Sym name="search_off" size={28} className="text-outline" />
      <p className="mt-2 text-body-sm text-on-surface-variant">
        {query ? `No personas match “${query}”.` : "No personas available."}
      </p>
    </div>
  );
}

/** Error state — the catalog failed to load, with a retry. */
function CatalogError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="px-3 py-8 text-center">
      <Sym name="error" size={28} className="text-error" />
      <p className="mt-2 text-body-sm text-on-surface-variant">Couldn&apos;t load the persona catalog.</p>
      <button
        type="button"
        onClick={onRetry}
        className={`mt-3 rounded-md border border-outline-variant bg-surface-container px-3 py-1.5 text-label-md font-label-md text-on-surface-variant transition-colors hover:border-primary hover:text-primary ${FOCUS_RING}`}
      >
        Retry
      </button>
    </div>
  );
}

export default PersonaCatalog;
