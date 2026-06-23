/**
 * CatalogDrawer — a slide-over panel for browsing the recommendation catalog.
 *
 * Opened from the rail's "Catalog" item or the ⌘K palette. It debounces the
 * search box, hits `GET /api/catalog/search`, and lists matching items with
 * their item ids, year/genre meta, and a short description. Selecting an item
 * expands its full record (description + metadata) inline.
 *
 * Styled to the Executive Precision tokens; skeleton results, teaching empty
 * state, and a plain-language error. Mounts only when `open`.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { api, ApiError } from "@/lib/api";
import type { CatalogItem, CatalogSearchResponse, Domain } from "@/lib/types";

/** Debounce a fast-changing value (the search box) by `delay` ms. */
function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

/** Compact "1995 · Adventure, Animation" meta line for a catalog item. */
function metaLine(item: CatalogItem): string {
  const parts: string[] = [];
  const meta = item.metadata ?? {};
  // Bundle items carry `releaseDate`; tolerate the older `release_year` shape.
  const year = meta.releaseDate ?? meta.release_year;
  if (year !== undefined && year !== null && String(year).trim()) {
    parts.push(String(year).slice(0, 10));
  }
  const cats = (item.categories ?? []).slice(0, 3);
  if (cats.length) parts.push(cats.join(", "));
  return parts.join(" · ");
}

function ResultRow({
  item,
  expanded,
  onToggle,
  onInspect,
}: {
  item: CatalogItem;
  expanded: boolean;
  onToggle: () => void;
  onInspect?: (itemId: string) => void;
}) {
  const meta = metaLine(item);
  const desc = item.description || item.displayText || "";
  return (
    <div className="overflow-hidden rounded-lg border border-border-soft bg-surface-container-lowest transition-colors hover:border-primary">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        className={`flex w-full items-center gap-3 px-3 py-2.5 text-left ${FOCUS_RING}`}
      >
        <span className="flex h-9 w-9 flex-none items-center justify-center rounded-md bg-primary/10" aria-hidden>
          <Sym name="movie" size={18} className="text-primary" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-body-md font-semibold text-on-surface">
            {item.title || item.itemId}
          </span>
          {meta && <span className="mt-px block truncate text-body-sm text-on-surface-variant">{meta}</span>}
        </span>
        <span className="flex-none rounded bg-surface-container px-1.5 py-0.5 font-mono-sm text-mono-sm text-on-surface-variant">
          {item.itemId}
        </span>
      </button>
      {expanded && (
        <div className="border-t border-border-soft px-3 py-2.5">
          {desc ? (
            <p className="line-clamp-6 text-body-sm leading-relaxed text-on-surface-variant">{desc}</p>
          ) : (
            <p className="text-body-sm italic text-outline">No description in the catalog.</p>
          )}
          {onInspect && (
            <button
              type="button"
              onClick={() => onInspect(item.itemId)}
              className={`mt-2 inline-flex items-center gap-1 rounded text-label-md font-label-md font-medium text-primary hover:underline ${FOCUS_RING}`}
            >
              <Sym name="content_copy" size={14} />
              Copy id → {item.itemId}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export interface CatalogDrawerProps {
  open: boolean;
  onClose: () => void;
  /** Which domain's catalog to browse (the active surface's domain). */
  domain?: Domain;
  /** Optional: surface a selected id (e.g. copy to clipboard) to the parent. */
  onInspectItem?: (itemId: string) => void;
}

export function CatalogDrawer({ open, onClose, domain, onInspectItem }: CatalogDrawerProps) {
  const [query, setQuery] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debouncedQuery = useDebounced(query, 220);

  // Focus the search box and close on Escape while open.
  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(() => inputRef.current?.focus(), 40);
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => {
      window.clearTimeout(id);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  const search = useQuery<CatalogSearchResponse>({
    queryKey: ["catalog", "search", domain ?? "", debouncedQuery],
    queryFn: () => api.searchCatalog({ q: debouncedQuery, limit: 50, domain }),
    enabled: open,
    placeholderData: (prev) => prev,
  });

  const items = useMemo(() => search.data?.items ?? [], [search.data]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Catalog search">
      {/* Scrim */}
      <div
        className="absolute inset-0 bg-[oklch(0.3_0.03_280/.28)] backdrop-blur-[1px]"
        onClick={onClose}
        aria-hidden
      />

      {/* Panel */}
      <div className="relative flex h-full w-[460px] max-w-[92vw] flex-col border-l border-border-soft bg-surface-container-low shadow-pop">
        {/* Header */}
        <div className="flex flex-shrink-0 items-center gap-2.5 border-b border-border-soft px-md py-3.5">
          <Sym name="search" size={18} className="text-primary" />
          <span className="text-headline-sm font-headline-sm uppercase tracking-wider text-on-surface">Catalog</span>
          <span className="font-mono-sm text-mono-sm text-on-surface-variant">
            {search.data ? `${search.data.total.toLocaleString()} matches` : "RecAI corpus"}
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close catalog"
            className={`ml-auto flex h-7 w-7 items-center justify-center rounded-md border border-outline-variant bg-surface-container-lowest text-on-surface-variant transition-colors hover:text-on-surface ${FOCUS_RING}`}
          >
            <Sym name="close" size={16} />
          </button>
        </div>

        {/* Search box */}
        <div className="flex-shrink-0 border-b border-border-soft px-md py-3">
          <div className="flex items-center gap-2 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 focus-within:border-primary focus-within:shadow-[0_0_0_3px_var(--primary-tint)]">
            <Sym name="search" size={16} className="flex-none text-outline" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search titles, descriptions, genres…"
              className="w-full bg-transparent text-body-md text-on-surface outline-none placeholder:text-outline"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Clear search"
                className={`flex-none rounded text-outline hover:text-on-surface ${FOCUS_RING}`}
              >
                <Sym name="close" size={16} />
              </button>
            )}
          </div>
        </div>

        {/* Results */}
        <div className="custom-scrollbar min-h-0 flex-1 space-y-2 overflow-auto px-md py-3">
          {search.isError ? (
            <CatalogError error={search.error} onRetry={() => search.refetch()} />
          ) : search.isLoading ? (
            <CatalogSkeleton />
          ) : items.length === 0 ? (
            <div className="px-1 py-8 text-center text-body-sm leading-relaxed text-on-surface-variant">
              {debouncedQuery
                ? `No catalog items match “${debouncedQuery}”.`
                : "Type to search the catalog, or browse the first results below."}
            </div>
          ) : (
            items.map((item) => (
              <ResultRow
                key={item.itemId}
                item={item}
                expanded={expandedId === item.itemId}
                onToggle={() => setExpandedId((id) => (id === item.itemId ? null : item.itemId))}
                onInspect={onInspectItem}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

/** Shimmering skeleton rows while the catalog search resolves. */
function CatalogSkeleton() {
  return (
    <div className="space-y-2" aria-hidden>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 rounded-lg border border-border-soft px-3 py-2.5">
          <div className="h-9 w-9 flex-none animate-rb-pulse rounded-md bg-surface-container-high" />
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="h-3 w-2/3 animate-rb-pulse rounded bg-surface-container-high" />
            <div className="h-2.5 w-1/3 animate-rb-pulse rounded bg-surface-container" />
          </div>
        </div>
      ))}
    </div>
  );
}

function CatalogError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message = error instanceof ApiError ? error.message : "Catalog search failed.";
  return (
    <div className="rounded-lg border border-error/40 bg-error-container/40 px-4 py-6 text-center">
      <Sym name="error" fill={1} size={22} className="text-error" />
      <p className="mt-1.5 break-words text-body-sm leading-relaxed text-on-surface-variant">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className={`mt-3 inline-flex items-center gap-1.5 rounded-md border border-outline-variant px-3 py-1.5 text-label-md font-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface ${FOCUS_RING}`}
      >
        <Sym name="refresh" size={15} />
        Try again
      </button>
    </div>
  );
}
