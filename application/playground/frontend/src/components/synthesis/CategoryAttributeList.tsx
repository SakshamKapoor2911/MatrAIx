/**
 * Attribute list for one selected category, with client-side search.
 * Clicking an attribute drives the drill-down pane.
 */
import { useMemo, useState } from "react";

import type { SynthesisCategorySummary } from "@/lib/types";
import { FOCUS_RING } from "../cockpit/cockpitShared";

export function CategoryAttributeList({
  category,
  onSelectAttribute,
}: {
  category: SynthesisCategorySummary;
  onSelectAttribute: (id: string) => void;
}) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return category.attributes;
    return category.attributes.filter(
      (a) => a.id.toLowerCase().includes(q) || a.label.toLowerCase().includes(q),
    );
  }, [category, query]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4">
      <div>
        <div className="hud text-text-dim">Category</div>
        <h3 className="font-display text-base text-text-main">{category.name}</h3>
        <p className="text-xs text-text-dim">
          {category.attributeCount} attributes · {category.helperCount} helper nodes ·{" "}
          {category.internalEdgeCount} internal edges
        </p>
      </div>
      <input
        type="search"
        aria-label="Filter attributes"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Filter attributes…"
        className={`h-9 rounded-md border border-outline bg-field px-3 text-sm text-text-main placeholder:text-text-dim ${FOCUS_RING}`}
      />
      <ul className="custom-scrollbar min-h-0 flex-1 space-y-1 overflow-y-auto">
        {filtered.map((attr) => (
          <li key={attr.id}>
            <button
              type="button"
              onClick={() => onSelectAttribute(attr.id)}
              className={`flex w-full items-baseline justify-between gap-2 rounded-md px-2.5 py-1.5 text-left transition-colors hover:bg-surface-low ${FOCUS_RING}`}
            >
              <span className="min-w-0 truncate text-sm text-text-variant">{attr.label}</span>
              <span className="flex-none font-mono text-[11px] text-text-dim">
                deg {attr.degree}
              </span>
            </button>
          </li>
        ))}
        {filtered.length === 0 ? (
          <li className="px-2.5 py-2 text-sm text-text-dim">No attributes match.</li>
        ) : null}
      </ul>
    </div>
  );
}
