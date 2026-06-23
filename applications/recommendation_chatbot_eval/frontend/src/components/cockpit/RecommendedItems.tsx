/**
 * RecommendedItems — the recommended-item card under a RecBot turn.
 *
 * Ports the mockup's "Recommended games/items" card: a titled header (icon +
 * label + count) over a divided list of ranked rows (rank badge · title · mono
 * id). Item titles fall back to the id when the catalog couldn't resolve a name
 * (honest: we show the real id rather than a fabricated title).
 *
 * Purely presentational. The header label adapts to the run domain so a movie
 * run reads "Recommended movies" and a game run "Recommended games".
 */
import { Sym } from "./cockpitShared";
import type { Domain, RecommendedItem } from "@/lib/types";

/** Domain → {icon, noun} for the card header. */
const DOMAIN_META: Record<Domain, { icon: string; noun: string }> = {
  movie: { icon: "movie", noun: "movies" },
  game: { icon: "stadia_controller", noun: "games" },
  beauty_product: { icon: "self_care", noun: "products" },
};

export interface RecommendedItemsProps {
  items: RecommendedItem[];
  domain: Domain;
  /** Override the header noun (e.g. "Final picks"); defaults to "Recommended <domain>". */
  title?: string;
  icon?: string;
}

export function RecommendedItems({ items, domain, title, icon }: RecommendedItemsProps) {
  if (items.length === 0) return null;
  const meta = DOMAIN_META[domain] ?? DOMAIN_META.movie;
  const headerLabel = title ?? `Recommended ${meta.noun}`;

  return (
    <div className="mb-3 overflow-hidden rounded-lg border border-border-soft">
      <div className="flex items-center justify-between border-b border-border-soft bg-surface-container-low px-3 py-2">
        <span className="flex items-center gap-1.5 text-label-md font-label-md uppercase tracking-wider text-on-surface-variant">
          <Sym name={icon ?? meta.icon} fill={1} size={16} className="text-primary" />
          {headerLabel}
        </span>
        <span className="font-mono-sm text-mono-sm text-on-surface-variant">
          {items.length} item{items.length === 1 ? "" : "s"}
        </span>
      </div>
      <ul className="divide-y divide-border-soft">
        {items.map((item) => (
          <li key={`${item.itemId}-${item.rank}`} className="flex items-start gap-3 px-3 py-2 transition-colors hover:bg-surface-container-low">
            <span
              className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-bold text-primary"
              aria-hidden
            >
              {item.rank}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="flex-1 truncate text-body-md text-on-surface" title={item.title ?? item.itemId}>
                  {item.title ?? item.itemId}
                </span>
                <span className="flex-shrink-0 rounded bg-surface-container px-1.5 py-0.5 font-mono-sm text-mono-sm text-on-surface-variant">
                  {item.itemId}
                </span>
              </div>
              {item.meta && <p className="mt-0.5 text-body-sm text-on-surface-variant">{item.meta}</p>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default RecommendedItems;
