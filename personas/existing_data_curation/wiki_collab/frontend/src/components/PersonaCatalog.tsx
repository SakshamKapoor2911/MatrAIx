/**
 * LEFT column — a searchable catalog of the curated Wikipedia person profiles.
 * Search filters by title or QID (case-insensitive). The selected row is tinted
 * with the primary accent; every row is a focus-ringed button.
 */
import { useMemo, useState } from "react";

import { Sym, FOCUS_RING } from "@/components/cockpit/cockpitShared";
import { Chip, Empty, SectionLabel } from "@/components/cockpit/Primitives";
import { fmtInt } from "@/lib/format";
import type { Profile } from "@/lib/types";

export function PersonaCatalog({
  profiles,
  selectedIdx,
  onSelect,
}: {
  profiles: Profile[];
  selectedIdx: number;
  onSelect: (global_idx: number) => void;
}) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return profiles;
    return profiles.filter(
      (p) => p.title.toLowerCase().includes(q) || p.qid.toLowerCase().includes(q),
    );
  }, [profiles, query]);

  return (
    <div className="flex h-full flex-col border-r border-border-soft bg-surface-container-low">
      <div className="flex flex-col gap-sm border-b border-border-soft px-md py-sm">
        <div className="flex items-center justify-between">
          <SectionLabel>Personas</SectionLabel>
          <Chip tone="neutral" title="profiles in catalog">
            {fmtInt(filtered.length)}
            {filtered.length !== profiles.length ? ` / ${fmtInt(profiles.length)}` : ""}
          </Chip>
        </div>
        <div className="relative">
          <Sym
            name="search"
            size={16}
            className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-outline"
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search title or QID…"
            spellCheck={false}
            className={`w-full rounded-lg border border-border-soft bg-surface-container-lowest py-2 pl-8 pr-2 font-body-md text-on-surface placeholder:text-outline ${FOCUS_RING}`}
          />
        </div>
      </div>

      <div className="custom-scrollbar flex-1 overflow-y-auto px-2 py-2">
        {filtered.length === 0 ? (
          <Empty icon="person_search" title="No matches" hint="Adjust the search query." />
        ) : (
          <ul className="flex flex-col gap-1">
            {filtered.map((p) => {
              const selected = p.global_idx === selectedIdx;
              return (
                <li key={p.global_idx}>
                  <button
                    type="button"
                    onClick={() => onSelect(p.global_idx)}
                    aria-current={selected}
                    className={[
                      "flex w-full flex-col gap-1 rounded-lg border px-3 py-2 text-left transition-colors",
                      FOCUS_RING,
                      selected
                        ? "border-primary bg-primary-tint"
                        : "border-transparent hover:border-border-soft hover:bg-surface-container-lowest",
                    ].join(" ")}
                  >
                    <div className="flex items-start justify-between gap-sm">
                      <span
                        className={`font-body-md font-semibold ${selected ? "text-on-primary-container" : "text-on-surface"}`}
                      >
                        {p.title}
                      </span>
                      <span className="shrink-0 font-mono-sm tabular-nums text-outline">#{p.global_idx}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-1">
                      <Chip tone={selected ? "primary" : "neutral"} title={p.qid}>
                        {p.qid}
                      </Chip>
                      {p.entity_type ? (
                        <Chip tone="neutral" title={p.entity_type}>
                          {p.entity_type}
                        </Chip>
                      ) : null}
                      <span className="font-mono-sm tabular-nums text-on-surface-variant">
                        {fmtInt(p.profile_text.length)} ch
                      </span>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
