/**
 * RecommendationCard — one recommended catalog item in the chat thread.
 *
 * A compact row in the Executive Precision language: a primary-tinted rank
 * badge, the title, and the machine item-id chip on the right. The whole card
 * is a button; clicking it focuses the item (the parent opens the catalog
 * drawer / scrolls the inspector to it).
 */
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import type { RecommendedItem } from "@/lib/types";

export interface RecommendationCardProps {
  item: RecommendedItem;
  /** Focus / inspect this item (open the catalog drawer on it). */
  onSelect?: (itemId: string) => void;
}

export function RecommendationCard({ item, onSelect }: RecommendationCardProps) {
  const title = item.title ?? item.itemId;
  return (
    <button
      type="button"
      onClick={() => onSelect?.(item.itemId)}
      aria-label={`Inspect ${title}`}
      className={`flex w-full items-center gap-3 rounded-lg border border-border-soft bg-surface-container-lowest px-3 py-2 text-left transition-colors hover:border-primary hover:bg-surface-container-low ${FOCUS_RING}`}
    >
      <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-primary/10 text-[11px] font-bold tabular-nums text-primary">
        {item.rank ?? ""}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-body-md text-on-surface">{title}</span>
        {item.meta && <span className="mt-px block truncate text-body-sm text-on-surface-variant">{item.meta}</span>}
      </span>
      <span className="flex flex-none items-center gap-2">
        {item.score !== null && item.score !== undefined && !Number.isNaN(item.score) && (
          <span className="font-mono-sm text-mono-sm tabular-nums text-on-surface-variant">{item.score.toFixed(3)}</span>
        )}
        <span className="whitespace-nowrap rounded bg-surface-container px-1.5 py-0.5 font-mono-sm text-mono-sm text-on-surface-variant">
          {item.itemId}
        </span>
      </span>
      <Sym name="chevron_right" size={16} className="flex-none text-outline" />
    </button>
  );
}

export default RecommendationCard;
