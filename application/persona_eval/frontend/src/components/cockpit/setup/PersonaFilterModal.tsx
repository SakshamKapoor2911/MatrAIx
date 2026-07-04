import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

import type { PersonaPoolCatalog } from "@/lib/types";
import { FOCUS_RING, Sym } from "../cockpitShared";
import {
  activeFilterCount,
  type PersonaDimensionFilters,
} from "./personaSamplingTypes";

export interface PersonaFilterModalProps {
  open: boolean;
  catalog: PersonaPoolCatalog | null;
  filters: PersonaDimensionFilters;
  stratifyMode?: boolean;
  stratifyFields?: string[];
  onStratifyFieldsChange?: (fields: string[]) => void;
  onClose: () => void;
  onConfirm: (filters: PersonaDimensionFilters) => void;
}

export function PersonaFilterModal({
  open,
  catalog,
  filters,
  stratifyMode = false,
  stratifyFields = [],
  onStratifyFieldsChange,
  onClose,
  onConfirm,
}: PersonaFilterModalProps) {
  const [draft, setDraft] = useState(filters);
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);
  const [expandedDim, setExpandedDim] = useState<string | null>(null);

  useEffect(() => {
    if (open) setDraft(filters);
  }, [open, filters]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  const sources = catalog?.dimensionCategories?.personaSources ?? [];
  const groups = catalog?.dimensionCategories?.devProfile?.groups ?? [];

  const selectedChips = useMemo(() => {
    const chips: Array<{ key: string; label: string; value: string }> = [];
    for (const source of draft.sources) {
      chips.push({ key: `source:${source}`, label: "Source", value: source });
    }
    for (const [dimId, values] of Object.entries(draft.dimensionFilters)) {
      for (const value of values) {
        chips.push({ key: `${dimId}:${value}`, label: dimId, value });
      }
    }
    return chips;
  }, [draft]);

  if (!open) return null;

  const toggleSource = (source: string) => {
    setDraft((prev) => ({
      ...prev,
      sources: prev.sources.includes(source)
        ? prev.sources.filter((item) => item !== source)
        : [...prev.sources, source],
    }));
  };

  const toggleDimensionValue = (dimId: string, value: string) => {
    setDraft((prev) => {
      const current = prev.dimensionFilters[dimId] ?? [];
      const nextValues = current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value];
      const nextFilters = { ...prev.dimensionFilters };
      if (nextValues.length === 0) delete nextFilters[dimId];
      else nextFilters[dimId] = nextValues;
      return { ...prev, dimensionFilters: nextFilters };
    });
  };

  const removeChip = (chip: { key: string; label: string; value: string }) => {
    if (chip.key.startsWith("source:")) {
      setDraft((prev) => ({
        ...prev,
        sources: prev.sources.filter((item) => item !== chip.value),
      }));
      return;
    }
    const dimId = chip.label;
    setDraft((prev) => {
      const nextValues = (prev.dimensionFilters[dimId] ?? []).filter((item) => item !== chip.value);
      const nextFilters = { ...prev.dimensionFilters };
      if (nextValues.length === 0) delete nextFilters[dimId];
      else nextFilters[dimId] = nextValues;
      return { ...prev, dimensionFilters: nextFilters };
    });
  };

  const toggleStratifyField = (dimId: string) => {
    if (!onStratifyFieldsChange) return;
    const next = stratifyFields.includes(dimId)
      ? stratifyFields.filter((item) => item !== dimId)
      : [...stratifyFields, dimId];
    onStratifyFieldsChange(next);
  };

  return createPortal(
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 sm:p-6">
      <button
        type="button"
        className="absolute inset-0 bg-surface-dim/75 backdrop-blur-sm"
        aria-label="Close filters"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="persona-filter-modal-title"
        className="glass-panel-strong relative z-10 flex max-h-[min(88vh,760px)] w-full max-w-4xl flex-col overflow-hidden rounded-xl shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-outline/40 px-5 py-4">
          <div>
            <p className="hud text-[9px] text-primary">bench-dev-sample</p>
            <h2 id="persona-filter-modal-title" className="font-display text-[18px] font-semibold text-text-main">
              Persona filters
            </h2>
          </div>
          <button type="button" onClick={onClose} className={`rounded-md p-2 text-text-variant hover:bg-surface-high ${FOCUS_RING}`}>
            <Sym name="close" size={20} />
          </button>
        </div>

        <div className="custom-scrollbar flex-1 overflow-y-auto px-5 py-4">
          <p className="mb-2 text-[11px] text-text-variant">Provenance</p>
          <div className="mb-5 flex flex-wrap gap-2">
            {sources.map((source) => {
              const active = draft.sources.includes(source);
              const count = catalog?.sourceCounts?.[source];
              return (
                <button
                  key={source}
                  type="button"
                  onClick={() => toggleSource(source)}
                  className={`rounded-full border px-3 py-1.5 text-[11px] transition ${FOCUS_RING} ${
                    active
                      ? "border-primary bg-primary/15 text-primary"
                      : "border-outline/50 bg-surface/50 text-text-variant hover:border-primary/40"
                  }`}
                >
                  {source}
                  {typeof count === "number" ? ` · ${count}` : ""}
                </button>
              );
            })}
          </div>

          <p className="mb-2 text-[11px] text-text-variant">Profile dimensions</p>
          <div className="space-y-2">
            {groups.map((group) => {
              const groupOpen = expandedGroup === group.id;
              return (
                <div key={group.id} className="rounded-lg border border-outline/40 bg-surface/30">
                  <button
                    type="button"
                    onClick={() => setExpandedGroup(groupOpen ? null : group.id)}
                    className={`flex w-full items-center justify-between px-3 py-2.5 text-left text-[12px] font-medium text-text-main ${FOCUS_RING}`}
                  >
                    {group.label}
                    <Sym name={groupOpen ? "expand_less" : "expand_more"} size={18} className="text-text-dim" />
                  </button>
                  {groupOpen && (
                    <div className="space-y-1 border-t border-outline/30 px-2 py-2">
                      {group.dimensions.map((dim) => {
                        const dimOpen = expandedDim === dim.id;
                        const selected = draft.dimensionFilters[dim.id] ?? [];
                        const stratified = stratifyFields.includes(dim.id);
                        return (
                          <div key={dim.id} className="rounded-md border border-outline/30 bg-surface/20">
                            <button
                              type="button"
                              onClick={() => setExpandedDim(dimOpen ? null : dim.id)}
                              className={`flex w-full items-center justify-between gap-2 px-2.5 py-2 text-left text-[11px] ${FOCUS_RING}`}
                            >
                              <span className={selected.length ? "text-primary" : "text-text-main"}>
                                {dim.id.replace(/_/g, " ")}
                                {selected.length > 0 ? ` · ${selected.length}` : ""}
                              </span>
                              <div className="flex items-center gap-2">
                                {stratifyMode && (
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      toggleStratifyField(dim.id);
                                    }}
                                    className={`rounded-full border px-2 py-0.5 text-[9px] ${
                                      stratified
                                        ? "border-secondary/40 bg-secondary/10 text-secondary"
                                        : "border-outline/40 text-text-dim"
                                    }`}
                                  >
                                    stratify
                                  </button>
                                )}
                                <Sym name={dimOpen ? "expand_less" : "expand_more"} size={16} className="text-text-dim" />
                              </div>
                            </button>
                            {dimOpen && (
                              <div className="flex flex-wrap gap-1.5 border-t border-outline/20 px-2.5 py-2">
                                {dim.values.map((value) => {
                                  const active = selected.includes(value);
                                  return (
                                    <button
                                      key={value}
                                      type="button"
                                      onClick={() => toggleDimensionValue(dim.id, value)}
                                      className={`rounded-full border px-2.5 py-1 text-[10px] ${FOCUS_RING} ${
                                        active
                                          ? "border-primary bg-primary/15 text-primary"
                                          : "border-outline/40 text-text-variant hover:border-primary/35"
                                      }`}
                                    >
                                      {value}
                                    </button>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="border-t border-outline/40 bg-surface/40 px-5 py-4">
          {selectedChips.length > 0 ? (
            <div className="mb-3 flex flex-wrap gap-1.5">
              {selectedChips.map((chip) => (
                <button
                  key={chip.key}
                  type="button"
                  onClick={() => removeChip(chip)}
                  className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[10px] text-primary"
                >
                  <span className="text-text-dim">{chip.label}:</span> {chip.value}
                  <Sym name="close" size={12} />
                </button>
              ))}
            </div>
          ) : (
            <p className="mb-3 text-[11px] text-text-dim">No filters — full pool eligible.</p>
          )}
          <div className="flex items-center justify-between gap-3">
            <p className="text-[11px] text-text-variant">
              <span className="font-mono text-text-main">{activeFilterCount(draft)}</span> filter groups
              {stratifyMode && stratifyFields.length > 0 && (
                <span>
                  {" "}
                  · stratify on <span className="font-mono text-text-main">{stratifyFields.join(", ")}</span>
                </span>
              )}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className={`rounded-md border border-outline px-3 py-2 text-[12px] text-text-variant ${FOCUS_RING}`}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  onConfirm(draft);
                  onClose();
                }}
                className={`rounded-md bg-primary px-4 py-2 text-[12px] font-medium text-on-primary ${FOCUS_RING}`}
              >
                Apply filters
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
