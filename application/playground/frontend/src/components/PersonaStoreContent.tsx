/**
 * PersonaStoreContent: bench-dev-sample persona grid (shared by Persona Store page + ⌘K drawer).
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { BenchPersonaCard } from "./cockpit/setup/BenchPersonaCard";
import { BenchPersonaDetailPanel } from "./cockpit/setup/BenchPersonaDetailPanel";
import { PersonaFilterModal } from "./cockpit/setup/PersonaFilterModal";
import {
  activeFilterCount,
  emptyPersonaDimensionFilters,
  type PersonaDimensionFilters,
} from "./cockpit/setup/personaSamplingTypes";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { StudioGlassPanel } from "./studio/StudioShell";
import { api } from "@/lib/api";
import { personaPoolEmptyMessage } from "@/lib/personaPoolCopy";
import type { PersonaPoolCatalog, PersonaPoolPersonaCard } from "@/lib/types";

/** Page size when loading the full bench-dev-sample pool (API max per request). */
const PERSONA_POOL_PAGE = 50;

function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

function personaSearchHaystack(persona: PersonaPoolPersonaCard): string {
  const parts = [
    persona.personaId,
    persona.name ?? "",
    persona.source ?? "",
    ...Object.entries(persona.dimensions).flatMap(([key, value]) => [key, value]),
  ];
  return parts.join(" ").toLowerCase();
}

function matchesPersonaFilters(
  persona: PersonaPoolPersonaCard,
  filters: PersonaDimensionFilters,
): boolean {
  if (filters.sources.length > 0) {
    const source = persona.source ?? persona.dimensions.source ?? "";
    if (!filters.sources.includes(source)) return false;
  }
  for (const [dimId, values] of Object.entries(filters.dimensionFilters)) {
    if (values.length === 0) continue;
    const actual = persona.dimensions[dimId];
    if (!actual || !values.includes(actual)) return false;
  }
  return true;
}

export interface PersonaStoreContentProps {
  enabled?: boolean;
  selectedId?: string | null;
  onSelect?: (persona: PersonaPoolPersonaCard) => void;
  autoFocusSearch?: boolean;
}

export function PersonaStoreContent({
  enabled = true,
  selectedId,
  onSelect,
  autoFocusSearch = false,
}: PersonaStoreContentProps) {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<PersonaDimensionFilters>(emptyPersonaDimensionFilters());
  const [filterModalOpen, setFilterModalOpen] = useState(false);
  const [viewing, setViewing] = useState<PersonaPoolPersonaCard | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debouncedQuery = useDebounced(query.trim(), 220);

  useEffect(() => {
    if (!autoFocusSearch) return;
    const id = window.setTimeout(() => inputRef.current?.focus(), 40);
    return () => window.clearTimeout(id);
  }, [autoFocusSearch]);

  const catalogQuery = useQuery<PersonaPoolCatalog>({
    queryKey: ["persona-pool-catalog"],
    queryFn: () => api.getPersonaPoolCatalog(),
    enabled,
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000,
  });

  const personasQuery = useQuery({
    queryKey: ["persona-pool-store", "all", PERSONA_POOL_PAGE],
    queryFn: () => api.listAllPersonaPoolCards(PERSONA_POOL_PAGE),
    enabled,
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000,
  });

  const all = useMemo(() => personasQuery.data?.personas ?? [], [personasQuery.data]);
  const personaSources = useMemo(() => {
    const fromCatalog = catalogQuery.data?.dimensionCategories?.personaSources ?? [];
    if (fromCatalog.length > 0) return fromCatalog;
    return [...new Set(all.map((persona) => persona.source).filter((s): s is string => Boolean(s)))];
  }, [all, catalogQuery.data]);
  const poolCount = catalogQuery.data?.count ?? all.length;
  const filterCount = activeFilterCount(filters);

  const personas = useMemo(() => {
    const q = debouncedQuery.toLowerCase();
    return all.filter((persona) => {
      if (!matchesPersonaFilters(persona, filters)) return false;
      if (!q) return true;
      return personaSearchHaystack(persona).includes(q);
    });
  }, [all, debouncedQuery, filters]);

  const loadedLabel =
    personasQuery.isLoading && all.length === 0 ? "…" : poolCount.toLocaleString();

  function setSourceFilter(source: string | null) {
    setFilters((prev) => ({
      ...prev,
      sources: source ? [source] : [],
    }));
  }

  function handleSelect(persona: PersonaPoolPersonaCard) {
    onSelect?.(persona);
  }

  const activeSource =
    filters.sources.length === 1 ? filters.sources[0] : filters.sources.length === 0 ? "all" : null;

  return (
    <>
      <StudioGlassPanel className="mb-5 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="flex h-9 min-w-0 flex-1 items-center rounded-lg border border-outline/50 bg-surface/60 backdrop-blur transition-colors focus-within:border-primary/50">
            <Sym name="search" size={16} className="ml-3 flex-none text-text-dim" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search persona id or name…"
              aria-label="Search personas"
              className="h-full w-full min-w-0 bg-transparent px-3 text-[13px] text-text-main outline-none placeholder:text-text-variant"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Clear search"
                className={`mr-2 flex-none rounded p-1 text-text-dim transition-colors hover:bg-surface-high hover:text-text-main ${FOCUS_RING}`}
              >
                <Sym name="close" size={16} />
              </button>
            )}
          </div>
          <div className="rounded-lg border border-outline/50 bg-surface/60 px-3 py-1.5 text-center backdrop-blur sm:shrink-0">
            <div className="hud text-[8px] text-text-dim">Pool</div>
            <div className="font-mono text-[16px] font-bold text-primary">{loadedLabel}</div>
          </div>
        </div>

        <div className="mt-3 flex flex-col gap-2.5 border-t border-outline/20 pt-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3">
            <span className="cockpit-field-label shrink-0 text-[10px] text-text-dim">Source</span>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by data source">
              <FilterChip
                label="All"
                active={activeSource === "all"}
                onClick={() => setSourceFilter(null)}
              />
              {personaSources.map((source) => (
                <FilterChip
                  key={source}
                  label={source}
                  title={`Source: ${source}`}
                  active={activeSource === source}
                  onClick={() => setSourceFilter(source)}
                />
              ))}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2 lg:pl-4">
            <span className="hidden h-6 w-px bg-outline/30 lg:block" aria-hidden />
            <span className="cockpit-field-label shrink-0 text-[10px] text-text-dim lg:sr-only">
              Dimensions
            </span>
            <button
              type="button"
              onClick={() => setFilterModalOpen(true)}
              className={`inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-[11px] font-medium transition-colors ${FOCUS_RING} ${
                filterCount > filters.sources.length
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-outline/50 bg-surface/50 text-text-variant hover:border-primary/40 hover:text-text-main"
              }`}
            >
              <Sym name="tune" size={15} />
              Dimension filters
              {filterCount > filters.sources.length ? (
                <span className="rounded bg-primary px-1.5 py-0.5 text-[9px] font-bold text-on-primary">
                  {filterCount - filters.sources.length}
                </span>
              ) : null}
            </button>
          </div>
        </div>

        {(filterCount > 0 || debouncedQuery) && (
          <p className="mt-3 text-[11px] text-text-variant">
            Showing <span className="font-semibold text-text-main">{personas.length}</span> of{" "}
            {all.length} loaded · bench-dev-sample
          </p>
        )}
      </StudioGlassPanel>

      {personasQuery.isLoading && all.length === 0 ? (
        <CatalogSkeleton />
      ) : personasQuery.isError ? (
        <CatalogError
          onRetry={() => {
            void personasQuery.refetch();
            void catalogQuery.refetch();
          }}
        />
      ) : personas.length === 0 ? (
        <CatalogEmpty
          query={debouncedQuery}
          hasFilters={filterCount > 0}
          emptyPoolMessage={personaPoolEmptyMessage(catalogQuery.data)}
        />
      ) : (
        <div className={`flex min-h-0 gap-4 ${viewing ? "items-stretch" : ""}`}>
          <div className="min-w-0 flex-1">
            <div className="grid grid-cols-1 items-stretch gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {personas.map((persona, i) => (
                <div
                  key={persona.personaId}
                  className="rise-in h-full"
                  style={{ animationDelay: `${Math.min(i, 6) * 30}ms` }}
                >
                  <BenchPersonaCard
                    persona={persona}
                    selected={persona.personaId === (selectedId ?? null) || persona.personaId === viewing?.personaId}
                    onToggle={() => {
                      setViewing((current) =>
                        current?.personaId === persona.personaId ? null : persona,
                      );
                    }}
                    onOpenDetail={() => setViewing(persona)}
                  />
                </div>
              ))}
            </div>
          </div>

          {viewing ? (
            <BenchPersonaDetailPanel
              persona={viewing}
              onClose={() => setViewing(null)}
              onUse={onSelect ? handleSelect : undefined}
              className="hidden w-[min(100%,22rem)] shrink-0 lg:flex"
            />
          ) : null}
        </div>
      )}

      {viewing ? (
        <BenchPersonaDetailPanel
          persona={viewing}
          onClose={() => setViewing(null)}
          onUse={onSelect ? handleSelect : undefined}
          className="mt-4 lg:hidden"
        />
      ) : null}

      <PersonaFilterModal
        open={filterModalOpen}
        catalog={catalogQuery.data ?? null}
        filters={filters}
        onClose={() => setFilterModalOpen(false)}
        onConfirm={(next) => {
          setFilters(next);
          setFilterModalOpen(false);
        }}
      />

    </>
  );
}

function FilterChip({
  label,
  active,
  onClick,
  title,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  title?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-pressed={active}
      className={`inline-flex h-8 items-center rounded-md border px-3 text-[11px] font-medium transition-colors ${FOCUS_RING} ${
        active
          ? "border-primary bg-primary text-on-primary"
          : "border-outline/50 bg-surface/50 text-text-variant hover:border-primary/40 hover:text-text-main"
      }`}
    >
      {label}
    </button>
  );
}

function CatalogSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" aria-hidden>
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="glass-panel rounded-xl p-4">
          <div className="mb-3 flex items-start justify-between">
            <div className="h-10 w-10 animate-rb-pulse rounded bg-surface-high" />
            <div className="h-3.5 w-14 animate-rb-pulse rounded bg-surface-high" />
          </div>
          <div className="h-3.5 w-2/3 animate-rb-pulse rounded bg-surface-high" />
          <div className="mt-2 h-2.5 w-1/2 animate-rb-pulse rounded bg-surface-high" />
        </div>
      ))}
    </div>
  );
}

function CatalogEmpty({
  query,
  hasFilters,
  emptyPoolMessage,
}: {
  query: string;
  hasFilters: boolean;
  emptyPoolMessage: string;
}) {
  return (
    <div className="glass-panel rise-in flex flex-col items-center rounded-xl px-4 py-16 text-center">
      <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-lg border border-dashed border-outline/50 bg-surface/50">
        <Sym name="search_off" size={26} className="text-text-dim" />
      </div>
      <p className="font-display text-[15px] font-semibold text-text-main">
        {query || hasFilters ? "No matches" : "No personas yet"}
      </p>
      <p className="mt-1 max-w-[320px] text-[12px] leading-snug text-text-variant">
        {query
          ? `Nothing matches "${query}". Try a dimension value or persona id.`
          : hasFilters
            ? "No personas match the current dimension filters. Try clearing filters."
            : emptyPoolMessage}
      </p>
    </div>
  );
}

function CatalogError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="glass-panel rise-in mx-auto max-w-md rounded-xl border-l-4 border-l-danger px-4 py-6 text-center">
      <Sym name="error" size={24} className="mx-auto mb-2 text-danger" />
      <p className="font-display text-[15px] font-semibold text-text-main">Couldn&apos;t load personas</p>
      <p className="mx-auto mt-1 max-w-[300px] text-[12px] leading-snug text-text-variant">
        Check the backend is running, then retry.
      </p>
      <button
        type="button"
        onClick={onRetry}
        className={`mt-3 inline-flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-3 py-1.5 text-[11px] font-medium text-danger ${FOCUS_RING}`}
      >
        <Sym name="refresh" size={15} />
        Try again
      </button>
    </div>
  );
}
