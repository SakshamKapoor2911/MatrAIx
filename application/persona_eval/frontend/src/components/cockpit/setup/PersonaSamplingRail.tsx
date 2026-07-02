import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import { PERSONA_BENCH_POOL, type PersonaPoolPersonaCard } from "@/lib/types";
import { FOCUS_RING, Sym } from "../cockpitShared";
import { BenchPersonaCard } from "./BenchPersonaCard";
import { BenchPersonaDetailModal } from "./BenchPersonaDetailModal";
import { CockpitRailHeader } from "./CockpitRailHeader";
import { PersonaFilterModal } from "./PersonaFilterModal";
import {
  activeFilterCount,
  filtersForSampleApi,
  type PersonaDimensionFilters,
  type PersonaSamplingMode,
} from "./personaSamplingTypes";
import type { PersonaEvalTaskType } from "../TaskTypeSwitch";

const TAB_LABELS: Record<PersonaSamplingMode, string> = {
  single: "Quick pick",
  random: "Random sample",
  stratified: "Stratified",
};

/** Default showcase personas from bench-dev-sample (smoke + spread). */
const QUICK_PICK_PERSONA_IDS = ["0042", "0001", "0328", "0058", "0012", "0020", "0030", "0040"];

function fallbackQuickPickCards(): PersonaPoolPersonaCard[] {
  return QUICK_PICK_PERSONA_IDS.map((personaId) => ({
    personaId,
    name: `persona-${personaId}`,
    source: "bench-dev-sample",
    dimensions: {},
  }));
}

export interface PersonaSamplingRailProps {
  personaModel: string;
  onPersonaModelChange: (model: string) => void;
  personaModelOptions: Array<{ value: string; label: string }>;
  mode: PersonaSamplingMode;
  onModeChange: (mode: PersonaSamplingMode) => void;
  selectedPersonaIds: string[];
  onSelectedPersonaIdsChange: (ids: string[]) => void;
  sampleSize: number;
  onSampleSizeChange: (size: number) => void;
  seed: number;
  filters: PersonaDimensionFilters;
  onFiltersChange: (filters: PersonaDimensionFilters) => void;
  stratifyFields: string[];
  onStratifyFieldsChange: (fields: string[]) => void;
  taskType?: PersonaEvalTaskType;
  disabled?: boolean;
}

export function PersonaSamplingRail({
  personaModel,
  onPersonaModelChange,
  personaModelOptions,
  mode,
  onModeChange,
  selectedPersonaIds,
  onSelectedPersonaIdsChange,
  sampleSize,
  onSampleSizeChange,
  seed,
  filters,
  onFiltersChange,
  stratifyFields,
  onStratifyFieldsChange,
  taskType,
  disabled,
}: PersonaSamplingRailProps) {
  const [filterOpen, setFilterOpen] = useState(false);
  const [detailPersona, setDetailPersona] = useState<PersonaPoolPersonaCard | null>(null);
  const [generatedCards, setGeneratedCards] = useState<PersonaPoolPersonaCard[]>([]);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  const catalogQuery = useQuery({
    queryKey: ["persona-pool-catalog"],
    queryFn: () => api.getPersonaPoolCatalog(),
    staleTime: 60_000,
  });

  const defaultCardsQuery = useQuery({
    queryKey: ["persona-pool-default-cards", QUICK_PICK_PERSONA_IDS.join(",")],
    queryFn: async () => {
      try {
        return await api.getPersonaPoolCards({
          limit: QUICK_PICK_PERSONA_IDS.length,
          personaIds: QUICK_PICK_PERSONA_IDS,
        });
      } catch {
        return { pool: PERSONA_BENCH_POOL, personas: fallbackQuickPickCards() };
      }
    },
    staleTime: 60_000,
  });

  const quickPickCards = useMemo(() => {
    const fromApi = defaultCardsQuery.data?.personas ?? [];
    if (fromApi.length > 0) return fromApi;
    if (defaultCardsQuery.isError) return fallbackQuickPickCards();
    return [];
  }, [defaultCardsQuery.data?.personas, defaultCardsQuery.isError]);

  const displayCards = useMemo(() => {
    if (mode === "single") return quickPickCards;
    return generatedCards;
  }, [quickPickCards, generatedCards, mode]);

  useEffect(() => {
    if (mode === "single") setGeneratedCards([]);
  }, [mode]);

  const togglePersona = useCallback(
    (personaId: string) => {
      if (mode === "single") {
        onSelectedPersonaIdsChange(
          selectedPersonaIds.includes(personaId) ? [] : [personaId],
        );
        return;
      }
      onSelectedPersonaIdsChange(
        selectedPersonaIds.includes(personaId)
          ? selectedPersonaIds.filter((id) => id !== personaId)
          : [...selectedPersonaIds, personaId],
      );
    },
    [mode, onSelectedPersonaIdsChange, selectedPersonaIds],
  );

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    setGenerateError(null);
    try {
      const dimensionFilters = filtersForSampleApi(filters);
      const result = await api.samplePersonaPool({
        sampleSize,
        seed,
        sources: filters.sources.length ? filters.sources : undefined,
        dimensionFilters,
        stratifyFields: mode === "stratified" ? stratifyFields : undefined,
        sampleSizePerValueGroup: mode === "stratified" ? 1 : undefined,
      });
      const cards = result.personas.map((row) => ({
        personaId: row.personaId,
        name: row.name ?? `persona-${row.personaId}`,
        source: row.source,
        path: row.path,
        dimensions: row.dimensions ?? {},
      }));
      setGeneratedCards(cards);
      onSelectedPersonaIdsChange(result.personaIds);
    } catch (err) {
      setGenerateError(err instanceof ApiError ? err.message : "Could not generate sample.");
    } finally {
      setGenerating(false);
    }
  }, [filters, mode, onSelectedPersonaIdsChange, sampleSize, seed, stratifyFields]);

  const filterCount = activeFilterCount(filters);
  const modelLabel =
    taskType === "survey" || taskType === "chatbot" ? "Persona model" : null;
  const modelHint =
    taskType === "survey"
      ? "Model that simulates the user side of the evaluation."
      : taskType === "chatbot"
        ? "Model that simulates the user side of the evaluation."
        : null;
  const showModelSelector = modelLabel !== null;

  return (
    <aside className="glass-panel glass-panel-rail relative flex h-full min-h-0 flex-col rounded-xl p-4">
      <CockpitRailHeader
        eyebrow="Personas"
        title="Simulated users"
        subtitle="bench-dev-sample · pick or sample a cohort"
      />

      <div className="mb-4">
        {showModelSelector && (
          <label className="cockpit-field-label flex flex-col gap-2">
            {modelLabel}
            <select
              value={personaModel}
              disabled={disabled}
              onChange={(e) => onPersonaModelChange(e.target.value)}
              className="h-9 rounded-lg border border-outline/50 bg-surface/60 px-2.5 text-[13px] font-medium text-text-main backdrop-blur"
            >
              {personaModelOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {modelHint && (
              <span className="text-[10px] leading-relaxed text-text-dim">{modelHint}</span>
            )}
          </label>
        )}
      </div>

      <div className="cockpit-segment cockpit-segment--grid mb-3 grid-cols-3">
        {(Object.keys(TAB_LABELS) as PersonaSamplingMode[]).map((tab) => (
          <button
            key={tab}
            type="button"
            disabled={disabled}
            onClick={() => onModeChange(tab)}
            className={`cockpit-segment__btn w-full ${FOCUS_RING} ${
              mode === tab ? "cockpit-segment__btn--active" : ""
            }`}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {mode !== "single" && (
        <div className="mb-3 space-y-3 rounded-lg border border-outline/35 bg-surface/25 p-3">
          <label className="flex flex-col gap-2 text-[11px] text-text-variant">
            <div className="flex items-center justify-between">
              <span>Sample size</span>
              <span className="font-mono text-[12px] text-text-main">{sampleSize}</span>
            </div>
            <input
              type="range"
              min={2}
              max={24}
              value={sampleSize}
              disabled={disabled}
              onChange={(e) => onSampleSizeChange(Number(e.target.value))}
              className="accent-primary"
            />
          </label>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={disabled}
              onClick={() => setFilterOpen(true)}
              className={`inline-flex items-center gap-1.5 rounded-md border border-outline/50 bg-surface/50 px-3 py-1.5 text-[11px] text-text-main ${FOCUS_RING}`}
            >
              <Sym name="tune" size={14} />
              Filters
              {filterCount > 0 && (
                <span className="rounded-full bg-primary/20 px-1.5 text-[9px] text-primary">{filterCount}</span>
              )}
            </button>
            {filterCount > 0 && (
              <span className="text-[10px] text-text-dim">{filterCount} groups active</span>
            )}
          </div>
          <button
            type="button"
            disabled={disabled || generating}
            onClick={() => void handleGenerate()}
            className={`flex w-full items-center justify-center gap-2 rounded-md bg-surface-high/80 py-2 text-[12px] text-text-main hover:bg-surface-high ${FOCUS_RING}`}
          >
            <Sym name="auto_awesome" size={16} className="text-primary" />
            {generating ? "Generating…" : "Generate preview"}
          </button>
          {generateError && <p className="text-[10px] text-danger">{generateError}</p>}
        </div>
      )}

      <div className="custom-scrollbar min-h-0 flex-1 space-y-2 overflow-y-auto pr-0.5">
        {mode === "single" && defaultCardsQuery.isLoading && quickPickCards.length === 0 && (
          <p className="text-[11px] text-text-variant">Loading bench-dev-sample…</p>
        )}
        {mode === "single" && defaultCardsQuery.isError && quickPickCards.length > 0 && (
          <p className="text-[10px] text-warn">Using offline persona list — restart backend for full dimensions.</p>
        )}
        {displayCards.map((persona) => (
          <BenchPersonaCard
            key={persona.personaId}
            persona={persona}
            selected={selectedPersonaIds.includes(persona.personaId)}
            onToggle={() => togglePersona(persona.personaId)}
            onOpenDetail={() => setDetailPersona(persona)}
          />
        ))}
        {mode === "single" && !defaultCardsQuery.isLoading && displayCards.length === 0 && (
          <p className="rounded-lg border border-dashed border-outline/40 p-4 text-center text-[11px] text-text-dim">
            No personas loaded. Check that the backend is running.
          </p>
        )}
        {mode !== "single" && displayCards.length === 0 && (
          <p className="rounded-lg border border-dashed border-outline/40 p-4 text-center text-[11px] text-text-dim">
            Set filters and generate a preview cohort.
          </p>
        )}
      </div>

      <p className="mt-3 text-center font-mono text-[10px] tracking-wide text-text-dim">
        <span className="font-semibold text-primary">{selectedPersonaIds.length}</span> selected · bench-dev-sample
      </p>

      <PersonaFilterModal
        open={filterOpen}
        catalog={catalogQuery.data ?? null}
        filters={filters}
        stratifyMode={mode === "stratified"}
        stratifyFields={stratifyFields}
        onStratifyFieldsChange={onStratifyFieldsChange}
        onClose={() => setFilterOpen(false)}
        onConfirm={onFiltersChange}
      />

      <BenchPersonaDetailModal
        open={detailPersona !== null}
        persona={detailPersona}
        onClose={() => setDetailPersona(null)}
      />
    </aside>
  );
}
