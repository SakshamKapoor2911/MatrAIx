import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import {
  PERSONA_BENCH_POOL,
  type PersonaPoolPersonaCard,
  type TaskPersonaStrategy,
} from "@/lib/types";
import { syntheticDisplayName } from "@/lib/personaDisplay";
import { FOCUS_RING, Sym, humanizeToken } from "../cockpitShared";
import { CockpitSelect, type CockpitSelectOption } from "./CockpitSelect";
import { CockpitToggle } from "./CockpitToggle";
import { BenchPersonaCard } from "./BenchPersonaCard";
import { BenchPersonaDetailPanel } from "./BenchPersonaDetailPanel";
import { CockpitRailHeader } from "./CockpitRailHeader";
import { PersonaFilterModal } from "./PersonaFilterModal";
import {
  activeFilterCount,
  filtersForSampleApi,
  type PersonaDimensionFilters,
  type PersonaSamplingMode,
} from "./personaSamplingTypes";
import type { PlaygroundTaskType } from "../TaskTypeSwitch";

const TAB_LABELS: Record<PersonaSamplingMode, string> = {
  single: "Quick pick",
  random: "Random sample",
  stratified: "Stratified",
};

/** Default showcase personas from bench-dev-sample (smoke + spread). */
const QUICK_PICK_PERSONA_IDS = ["0042", "0001", "0328", "0058", "0012", "0020", "0030", "0040"];

const SAMPLE_SIZE_MAX = 500;

function clampSampleSize(value: number): number {
  if (!Number.isFinite(value)) return 4;
  return Math.min(SAMPLE_SIZE_MAX, Math.max(2, Math.round(value)));
}

function strategyModeLabel(mode: string | null | undefined): string {
  if (mode === "stratified") return "Stratified";
  if (mode === "random") return "Random sample";
  if (mode === "single") return "Quick pick";
  return "Custom";
}

function TaskStrategySummary({ strategy }: { strategy: TaskPersonaStrategy }) {
  const dimEntries = Object.entries(strategy.dimensionFilters ?? {}).filter(
    ([, values]) => Array.isArray(values) && values.length > 0,
  );
  const sources = (strategy.sources ?? []).filter((value) => value.trim());
  const stratify = (strategy.stratifyFields ?? []).filter((value) => value.trim());
  const sample =
    typeof strategy.sampleSize === "number" && strategy.sampleSize > 0
      ? strategy.sampleSize
      : null;

  return (
    <div className="space-y-1.5 border-t border-primary/15 pt-2">
      <p className="text-[10px] font-medium text-text-main">
        {strategyModeLabel(strategy.defaultMode)}
        {sample != null ? ` · sample ${sample}` : ""}
      </p>
      {sources.length > 0 ? (
        <p className="text-[10px] leading-snug text-text-variant">
          <span className="text-text-dim">Sources · </span>
          {sources.join(", ")}
        </p>
      ) : null}
      {dimEntries.map(([dim, values]) => (
        <p key={dim} className="text-[10px] leading-snug text-text-variant">
          <span className="text-text-dim">{humanizeToken(dim)} · </span>
          {values.join(", ")}
        </p>
      ))}
      {stratify.length > 0 ? (
        <p className="text-[10px] leading-snug text-text-variant">
          <span className="text-text-dim">Stratify · </span>
          {stratify.map(humanizeToken).join(", ")}
        </p>
      ) : null}
      {sources.length === 0 && dimEntries.length === 0 && stratify.length === 0 && sample == null ? (
        <p className="text-[10px] text-text-dim">No filters — full pool.</p>
      ) : null}
    </div>
  );
}

function fallbackQuickPickCards(): PersonaPoolPersonaCard[] {
  return QUICK_PICK_PERSONA_IDS.map((personaId) => ({
    personaId,
    name: syntheticDisplayName(personaId),
    source: "bench-dev-sample",
    dimensions: {},
  }));
}

export interface PersonaSamplingRailProps {
  personaModel: string;
  onPersonaModelChange: (model: string) => void;
  personaModelOptions: CockpitSelectOption[];
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
  taskType?: PlaygroundTaskType;
  hasTaskStrategy?: boolean;
  taskPersonaStrategy?: TaskPersonaStrategy | null;
  useTaskDefaultStrategy?: boolean;
  onUseTaskDefaultStrategyChange?: (useDefault: boolean) => void;
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
  hasTaskStrategy = false,
  taskPersonaStrategy = null,
  useTaskDefaultStrategy = false,
  onUseTaskDefaultStrategyChange,
  disabled,
}: PersonaSamplingRailProps) {
  const [filterOpen, setFilterOpen] = useState(false);
  const [detailPersona, setDetailPersona] = useState<PersonaPoolPersonaCard | null>(null);
  const [generatedCards, setGeneratedCards] = useState<PersonaPoolPersonaCard[]>([]);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  /** Local draft so users can clear/retype without clamp fighting every keystroke. */
  const [sampleSizeDraft, setSampleSizeDraft] = useState<string | null>(null);

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

  const lockedCohortQuery = useQuery({
    queryKey: ["persona-pool-locked-cohort", selectedPersonaIds.join(",")],
    queryFn: () =>
      api.getPersonaPoolCards({
        personaIds: selectedPersonaIds,
        limit: selectedPersonaIds.length,
      }),
    enabled: Boolean(disabled) && mode !== "single" && selectedPersonaIds.length > 0,
    staleTime: 300_000,
  });

  const quickPickCards = useMemo(() => {
    const fromApi = defaultCardsQuery.data?.personas ?? [];
    if (fromApi.length > 0) return fromApi;
    if (defaultCardsQuery.isError) return fallbackQuickPickCards();
    return [];
  }, [defaultCardsQuery.data?.personas, defaultCardsQuery.isError]);

  const displayCards = useMemo(() => {
    if (mode === "single") return quickPickCards;
    if (disabled && selectedPersonaIds.length > 0) {
      const locked = lockedCohortQuery.data?.personas ?? [];
      if (locked.length > 0) return locked;
      return selectedPersonaIds.map((personaId) => ({
        personaId,
        name: syntheticDisplayName(personaId),
        source: "bench-dev-sample",
        dimensions: {},
      }));
    }
    return generatedCards;
  }, [
    quickPickCards,
    generatedCards,
    mode,
    disabled,
    selectedPersonaIds,
    lockedCohortQuery.data?.personas,
  ]);

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
  const poolCount = catalogQuery.data?.count;
  const showModelSelector =
    taskType === "survey" || taskType === "chatbot" || taskType === "web" || taskType === "os-app";
  const strategyLocked = hasTaskStrategy && useTaskDefaultStrategy;
  const customSamplingUnlocked = !strategyLocked;

  return (
    <aside className="glass-panel glass-panel-rail relative flex h-full min-h-0 flex-col rounded-xl p-4">
      <CockpitRailHeader label="Persona" />

      <div className="mb-3">
        {showModelSelector && (
          <CockpitSelect
            label="Model"
            value={personaModel}
            options={personaModelOptions}
            disabled={disabled}
            onChange={onPersonaModelChange}
          />
        )}
      </div>

      <div className="cockpit-segment cockpit-segment--grid mb-3 grid-cols-3">
        {(Object.keys(TAB_LABELS) as PersonaSamplingMode[]).map((tab) => (
          <button
            key={tab}
            type="button"
            disabled={disabled || strategyLocked}
            onClick={() => onModeChange(tab)}
            className={`cockpit-segment__btn w-full ${FOCUS_RING} ${
              mode === tab ? "cockpit-segment__btn--active" : ""
            }`}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {disabled && selectedPersonaIds.length > 0 ? (
        <p className="mb-2 rounded-lg border border-primary/25 bg-primary/10 px-2.5 py-2 text-[10px] leading-relaxed text-text-variant">
          Cohort locked for this run — use Reset to change personas or sample settings.
        </p>
      ) : null}

      {mode !== "single" && (
        <div className="mb-2 space-y-2">
          {hasTaskStrategy && taskPersonaStrategy ? (
            <div className="rounded-lg border border-primary/20 bg-primary/5 px-2.5 py-2">
              <CockpitToggle
                label="Task default strategy"
                description={
                  useTaskDefaultStrategy
                    ? "Filters follow persona_strategy.json"
                    : "Off — edit filters yourself"
                }
                checked={useTaskDefaultStrategy}
                disabled={disabled}
                onChange={(checked) => onUseTaskDefaultStrategyChange?.(checked)}
              />
              {useTaskDefaultStrategy ? (
                <TaskStrategySummary strategy={taskPersonaStrategy} />
              ) : null}
            </div>
          ) : null}

          {customSamplingUnlocked ? (
            <button
              type="button"
              disabled={disabled}
              onClick={() => setFilterOpen(true)}
              className={`flex w-full items-center gap-2 rounded-lg border border-outline/40 bg-surface/40 px-2.5 py-2 text-left transition hover:border-primary/35 hover:bg-surface/55 ${FOCUS_RING}`}
            >
              <Sym name="tune" size={16} className="shrink-0 text-primary" />
              <span className="min-w-0 flex-1 text-[11px] font-medium text-text-main">
                Persona filters
              </span>
              {filterCount > 0 ? (
                <span className="rounded-full bg-primary/15 px-1.5 font-mono text-[9px] text-primary">
                  {filterCount}
                </span>
              ) : null}
              <Sym name="chevron_right" size={16} className="shrink-0 text-text-dim" />
            </button>
          ) : null}

          <div className="flex items-end gap-2">
            {customSamplingUnlocked ? (
              <label className="flex w-[4.25rem] shrink-0 flex-col gap-0.5">
                <span className="text-[10px] text-text-dim">
                  Sample{typeof poolCount === "number" ? ` · ${poolCount}` : ""}
                </span>
                <input
                  type="number"
                  inputMode="numeric"
                  min={2}
                  max={SAMPLE_SIZE_MAX}
                  step={1}
                  value={sampleSizeDraft ?? sampleSize}
                  disabled={disabled}
                  onFocus={() => setSampleSizeDraft(String(sampleSize))}
                  onChange={(e) => {
                    const raw = e.target.value;
                    // Keep empty / partial values while typing; clamp only on blur.
                    if (raw === "" || /^\d+$/.test(raw)) {
                      setSampleSizeDraft(raw);
                    }
                  }}
                  onBlur={() => {
                    const raw = sampleSizeDraft;
                    setSampleSizeDraft(null);
                    onSampleSizeChange(
                      clampSampleSize(raw === "" || raw == null ? sampleSize : Number(raw)),
                    );
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      (e.target as HTMLInputElement).blur();
                    }
                  }}
                  className={`h-9 w-full rounded-lg border border-outline/50 bg-surface/60 px-1.5 text-center font-mono text-[13px] text-text-main disabled:opacity-50 ${FOCUS_RING}`}
                />
              </label>
            ) : null}
            <button
              type="button"
              disabled={disabled || generating}
              onClick={() => void handleGenerate()}
              className={`flex h-9 min-w-0 flex-1 items-center justify-center gap-1.5 rounded-lg bg-surface-high/90 text-[11px] font-medium text-text-main hover:bg-surface-high disabled:opacity-50 ${FOCUS_RING}`}
            >
              <Sym name="auto_awesome" size={15} className="text-primary" />
              {generating ? "Generating…" : "Generate preview"}
            </button>
          </div>
          {generateError && <p className="text-[10px] text-danger">{generateError}</p>}
        </div>
      )}

      <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto pr-0.5">
        {detailPersona ? (
          <BenchPersonaDetailPanel
            embedded
            persona={detailPersona}
            onClose={() => setDetailPersona(null)}
            className="min-h-0"
          />
        ) : (
          <div className="space-y-2">
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
            disabled={disabled}
            onToggle={() => togglePersona(persona.personaId)}
            onOpenDetail={() => setDetailPersona(persona)}
          />
        ))}
        {mode === "single" && !defaultCardsQuery.isLoading && displayCards.length === 0 && (
          <p className="rounded-lg border border-dashed border-outline/40 p-4 text-center text-[11px] text-text-dim">
            No personas loaded. Check that the backend is running.
          </p>
        )}
        {mode !== "single" && displayCards.length === 0 && !disabled && (
          <p className="rounded-lg border border-dashed border-outline/40 p-4 text-center text-[11px] text-text-dim">
            {strategyLocked
              ? "Generate a preview cohort from the task default strategy."
              : "Set filters and generate a preview cohort."}
          </p>
        )}
        {mode !== "single" && displayCards.length === 0 && disabled && lockedCohortQuery.isLoading && (
          <p className="text-[11px] text-text-variant">Loading cohort personas…</p>
        )}
          </div>
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

    </aside>
  );
}
