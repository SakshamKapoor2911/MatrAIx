/**
 * RecommendationCard: one recommended catalog item, rendered as a card inside
 * the RecAI reply bubble (PersonaEval chat, mockup `app-redesign-v3.html:315`).
 *
 * A compact card: a mono cyan rank ("01"), the title, a one-line meta blurb,
 * and a quiet machine-id footer. Rank 1 carries a "Best match" corner ribbon
 * (derived honestly from `rank`). The whole card is a button; clicking it
 * focuses the item (the parent opens the catalog drawer on it).
 */
import { FOCUS_RING } from "./cockpit/cockpitShared";
import type { RecommendedItem } from "@/lib/types";

export interface RecommendationCardProps {
  item: RecommendedItem;
  /** Focus / inspect this item (open the catalog drawer on it). */
  onSelect?: (itemId: string) => void;
}

/** Zero-pad a 1-based rank for the mono badge ("1" → "01"); blank when absent. */
function fmtRank(rank: number | null | undefined): string {
  if (rank === null || rank === undefined || Number.isNaN(rank)) return "";
  return String(rank).padStart(2, "0");
}

export function RecommendationCard({ item, onSelect }: RecommendationCardProps) {
  const title = item.title ?? item.itemId;
  const rank = fmtRank(item.rank);
  const isBest = item.rank === 1;
  const hasScore = item.score !== null && item.score !== undefined && !Number.isNaN(item.score);

  return (
    <button
      type="button"
      onClick={() => onSelect?.(item.itemId)}
      aria-label={`Inspect ${title}`}
      className={`relative block w-full rounded border border-outline bg-surface-low p-3 text-left transition hover:border-primary/60 active:scale-[0.98] ${FOCUS_RING}`}
    >
      {isBest && (
        <span className="hud absolute right-0 top-0 rounded-bl border-b border-l border-secondary/25 bg-secondary/10 px-1 py-0.5 text-[7px] text-secondary">
          Best match
        </span>
      )}
      <div className="mb-1 flex items-start gap-2">
        {rank && <span className="flex-none font-mono text-[10px] font-bold text-primary">{rank}</span>}
        <span className={`min-w-0 break-words text-[12px] font-semibold text-text-main ${isBest ? "pr-12" : ""}`}>
          {title}
        </span>
      </div>
      {item.meta && (
        <p className="line-clamp-2 text-[11px] leading-snug text-text-variant">{item.meta}</p>
      )}
      <div className="mt-1.5 flex items-center gap-2 font-mono text-[10px] text-text-dim">
        <span className="min-w-0 truncate" title={item.itemId}>{item.itemId}</span>
        {hasScore && <span className="ml-auto flex-none tabular-nums">{item.score!.toFixed(3)}</span>}
      </div>
    </button>
  );
}

export default RecommendationCard;
