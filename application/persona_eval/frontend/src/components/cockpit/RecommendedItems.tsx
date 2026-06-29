/**
 * RecommendedItems: the recommended-item cards under an app reply.
 *
 * Ports the mockup's item grid (`app-redesign-v3.html:498-508`): a 1/2-col grid
 * of cards, each a `01`-style mono rank badge + title + a one-line blurb, with a
 * "Best match" corner tag on rank 1. Item titles fall back to the raw id when
 * the catalog couldn't resolve a name (honest: we show the real id rather than
 * fabricate a title), and the real id is surfaced as a mono caption when a title
 * is present. Purely presentational.
 */
import type { Domain, RecommendedItem } from "@/lib/types";

export interface RecommendedItemsProps {
  items: RecommendedItem[];
  /** Run domain (kept for callers; cards are domain-agnostic). */
  domain?: Domain;
}

export function RecommendedItems({ items }: RecommendedItemsProps) {
  if (items.length === 0) return null;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {items.map((item) => {
        const title = item.title ?? item.itemId;
        const isBest = item.rank === 1;
        return (
          <div
            key={`${item.itemId}-${item.rank}`}
            className="relative rounded border border-outline bg-surface-low p-3 transition-colors hover:border-primary/60"
          >
            {isBest && (
              <div className="hud absolute right-0 top-0 rounded-bl border-b border-l border-secondary/25 bg-secondary/10 px-1 py-0.5 text-[7px] text-secondary">
                Best match
              </div>
            )}
            <div className="mb-1 flex items-start gap-2">
              <span className="shrink-0 font-mono text-[10px] font-bold text-primary">{String(item.rank).padStart(2, "0")}</span>
              <span
                className={`min-w-0 break-words text-[12px] font-semibold text-text-main ${isBest ? "pr-12" : ""}`}
                title={title}
              >
                {title}
              </span>
            </div>
            {item.meta && <p className="text-[11px] leading-snug text-text-variant">{item.meta}</p>}
            {item.title && (
              <p className="mt-1 truncate font-mono text-[10px] text-text-dim" title={item.itemId}>
                {item.itemId}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default RecommendedItems;
