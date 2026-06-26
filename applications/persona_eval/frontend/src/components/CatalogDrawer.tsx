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
    <div className="overflow-hidden rounded-md border border-outline bg-surface transition-colors hover:border-primary">
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
          <span className="block truncate text-sm font-semibold text-text-main">
            {item.title || item.itemId}
          </span>
          {meta && <span className="mt-px block truncate text-[12px] text-text-variant">{meta}</span>}
        </span>
        <span className="flex-none rounded bg-surface-low px-1.5 py-0.5 font-mono text-[10px] text-text-dim">
          {item.itemId}
        </span>
      </button>
      {expanded && (
        <div className="border-t border-outline px-3 py-2.5">
          {desc ? (
            <p className="line-clamp-6 text-[12px] leading-relaxed text-text-variant">{desc}</p>
          ) : (
            <p className="text-[12px] italic text-text-dim">This item has no description on file.</p>
          )}
          {onInspect && (
            <button
              type="button"
              onClick={() => onInspect(item.itemId)}
              title="Paste it into a prompt to reference this item"
              className={`mt-2 inline-flex items-center gap-1 rounded text-[11px] font-medium text-primary hover:underline ${FOCUS_RING}`}
            >
              <Sym name="content_copy" size={14} />
              Copy this item&apos;s id
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
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />

      {/* Panel */}
      <div className="relative flex h-full w-[460px] max-w-[92vw] flex-col border-l border-outline bg-surface-lowest shadow-2xl">
        {/* Header */}
        <div className="flex flex-shrink-0 items-start gap-2.5 border-b border-outline px-md py-3.5">
          <Sym name="search" size={18} className="mt-0.5 text-primary" />
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline gap-2">
              <span className="hud text-[10px] text-primary">Catalog search</span>
              <span className="font-mono text-[10px] text-text-dim">
                {search.data ? `${search.data.total.toLocaleString()} matches` : "Type to search the catalog"}
              </span>
            </div>
            <p className="mt-0.5 text-[11px] text-text-dim">Look up items the recommender can suggest</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close catalog"
            className={`flex h-7 w-7 flex-none items-center justify-center rounded-md border border-outline bg-surface-low text-text-variant transition-colors hover:border-primary hover:text-text-main ${FOCUS_RING}`}
          >
            <Sym name="close" size={16} />
          </button>
        </div>

        {/* Search box */}
        <div className="flex-shrink-0 border-b border-outline px-md py-3">
          <div className="flex items-center gap-2 rounded-md border border-outline bg-field px-3 py-2 focus-within:border-primary">
            <Sym name="search" size={16} className="flex-none text-text-dim" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search the catalog — titles, genres, or descriptions"
              className="w-full bg-transparent text-[13px] text-text-main outline-none placeholder:text-text-dim"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Clear search"
                className={`flex-none rounded text-text-dim hover:text-text-main ${FOCUS_RING}`}
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
            <div className="flex flex-col items-center px-4 py-10 text-center">
              <div
                className="mb-3 flex h-12 w-12 items-center justify-center rounded-md border border-dashed border-outline bg-surface-high"
                aria-hidden
              >
                <Sym name="search" size={22} className="text-text-dim" />
              </div>
              <p className="font-display text-[15px] font-semibold text-text-main">
                {debouncedQuery ? "No matches" : "Search the catalog"}
              </p>
              <p className="mt-1 max-w-[300px] text-[12px] leading-snug text-text-variant">
                {debouncedQuery
                  ? `No items match “${debouncedQuery}”. Try a shorter or different word.`
                  : "Start typing to find an item, or browse the first matches below."}
              </p>
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
        <div key={i} className="flex items-center gap-3 rounded-md border border-outline px-3 py-2.5">
          <div className="h-9 w-9 flex-none animate-pulse rounded-md bg-surface-high" />
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="h-3 w-2/3 animate-pulse rounded bg-surface-high" />
            <div className="h-2.5 w-1/3 animate-pulse rounded bg-surface-low" />
          </div>
        </div>
      ))}
    </div>
  );
}

function CatalogError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message =
    error instanceof ApiError
      ? error.message
      : "That search didn't go through. Check the connection and try again.";
  return (
    <div className="rounded-md border border-outline border-l-4 border-l-danger bg-surface px-4 py-5 text-center">
      <div
        className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-md border border-danger/30 bg-danger/10"
        aria-hidden
      >
        <Sym name="error" fill={1} size={22} className="text-danger" />
      </div>
      <p className="font-display text-[15px] font-semibold text-text-main">Search failed</p>
      <p className="mx-auto mt-1 max-w-[300px] break-words text-[12px] leading-snug text-text-variant">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className={`mt-3 inline-flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-3 py-1.5 text-[11px] font-medium text-danger transition-colors hover:bg-danger/20 ${FOCUS_RING}`}
      >
        <Sym name="refresh" size={15} />
        Try again
      </button>
    </div>
  );
}
