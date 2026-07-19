import type { HarborCockpitTaskKind } from "@/lib/harborCockpitMappers";
import type { TaskPersonaStrategy } from "@/lib/types";
import { PERSONA_BENCH_POOL } from "@/lib/types";

import { readCockpitBatch } from "./cockpitBatchStorage";
import {
  emptyPersonaDimensionFilters,
  type PersonaDimensionFilters,
  type PersonaSamplingMode,
} from "./personaSamplingTypes";

export interface CockpitPersonaSetupRecord {
  selectedPersonaIds: string[];
  samplingMode: PersonaSamplingMode;
  groupFilters: PersonaDimensionFilters;
  stratifyFields: string[];
  sampleSize: number;
  /**
   * Personas per stratify combination (stratified mode).
   * `null` = not set — sample with 1/cell then cap at `sampleSize`.
   * Only an explicit number skips the sampleSize ceiling (per-cell is primary).
   */
  sampleSizePerValueGroup: number | null;
  parallelTrials: number;
  personaModel: string;
  /** Pool used for the current cohort (may be an auto-generated ``_generated`` path). */
  personaPool: string;
  /** When true, sampling follows the task's persona_strategy.json and custom filters stay locked. */
  useTaskDefaultStrategy: boolean;
  /**
   * Set only when the operator explicitly turns Task default strategy off.
   * Distinguishes intentional opt-out from the pre-hydrate false that used to
   * poison localStorage before persona_strategy.json loaded.
   */
  taskDefaultStrategyDismissed?: boolean;
}

type CockpitPersonaSetupStore = {
  byTaskPath?: Record<string, CockpitPersonaSetupRecord>;
  /** Legacy kind-keyed entries (pre task-path storage). */
  byKind?: Partial<Record<HarborCockpitTaskKind, CockpitPersonaSetupRecord>>;
};

const STORAGE_KEY = "playground.cockpitPersonaSetupByTaskPath";
const LEGACY_STORAGE_KEY = "playground.cockpitPersonaSetupByTask";
const MODEL_MIGRATION_KEY = "playground.cockpitModelMigrated_v2";
const OLD_DEFAULT_MODEL = "anthropic/claude-sonnet-4-6";
const NEW_DEFAULT_MODEL = "anthropic/claude-haiku-4-5";

/**
 * One-shot migration: replace the old os-app default (Sonnet 4.6) with
 * the new default (Haiku 4.5) in every cached persona setup record.
 */
function migrateDefaultModelOnce(): void {
  if (typeof window === "undefined") return;
  if (window.localStorage.getItem(MODEL_MIGRATION_KEY)) return;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const store = JSON.parse(raw) as CockpitPersonaSetupStore;
      let changed = false;
      if (store.byTaskPath) {
        for (const record of Object.values(store.byTaskPath)) {
          if (record.personaModel === OLD_DEFAULT_MODEL) {
            record.personaModel = NEW_DEFAULT_MODEL;
            changed = true;
          }
        }
      }
      if (store.byKind) {
        for (const record of Object.values(store.byKind)) {
          if (record && record.personaModel === OLD_DEFAULT_MODEL) {
            record.personaModel = NEW_DEFAULT_MODEL;
            changed = true;
          }
        }
      }
      if (changed) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
      }
    }
  } catch {
    /* ignore */
  }
  window.localStorage.setItem(MODEL_MIGRATION_KEY, "1");
}

function readStore(): CockpitPersonaSetupStore {
  if (typeof window === "undefined") return {};
  migrateDefaultModelOnce();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as CockpitPersonaSetupStore;
      if (parsed && typeof parsed === "object") return parsed;
    }
  } catch {
    /* ignore */
  }
  // Migrate legacy kind-keyed blob once.
  try {
    const legacyRaw = window.localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!legacyRaw) return {};
    const legacy = JSON.parse(legacyRaw) as Partial<
      Record<HarborCockpitTaskKind, CockpitPersonaSetupRecord>
    >;
    if (!legacy || typeof legacy !== "object") return {};
    return { byKind: legacy };
  } catch {
    return {};
  }
}

function writeStore(store: CockpitPersonaSetupStore): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

function normalizeRecord(
  record: Partial<CockpitPersonaSetupRecord> | null | undefined,
  fallbackPersonaModel: string,
): CockpitPersonaSetupRecord | null {
  if (!record) return null;
  return {
    selectedPersonaIds: Array.isArray(record.selectedPersonaIds)
      ? record.selectedPersonaIds.filter((id): id is string => typeof id === "string")
      : [],
    samplingMode:
      record.samplingMode === "random" || record.samplingMode === "stratified"
        ? record.samplingMode
        : "single",
    groupFilters: record.groupFilters ?? emptyPersonaDimensionFilters(),
    stratifyFields: Array.isArray(record.stratifyFields)
      ? record.stratifyFields.filter((field): field is string => typeof field === "string")
      : ["age_bracket", "region"],
    sampleSize: typeof record.sampleSize === "number" && record.sampleSize > 0 ? record.sampleSize : 4,
    sampleSizePerValueGroup:
      record.sampleSizePerValueGroup === null
        ? null
        : typeof record.sampleSizePerValueGroup === "number" && record.sampleSizePerValueGroup >= 1
          ? Math.round(record.sampleSizePerValueGroup)
          : 1,
    parallelTrials:
      typeof record.parallelTrials === "number" && record.parallelTrials > 0 ? record.parallelTrials : 2,
    personaModel:
      typeof record.personaModel === "string" && record.personaModel && record.personaModel !== OLD_DEFAULT_MODEL
        ? record.personaModel
        : fallbackPersonaModel,
    personaPool:
      typeof record.personaPool === "string" && record.personaPool.trim()
        ? record.personaPool.trim()
        : PERSONA_BENCH_POOL,
    // Legacy entries omit this flag — prefer task default until the user turns it off.
    useTaskDefaultStrategy:
      typeof record.useTaskDefaultStrategy === "boolean" ? record.useTaskDefaultStrategy : true,
    taskDefaultStrategyDismissed: record.taskDefaultStrategyDismissed === true,
  };
}

export function defaultPersonaSetup(fallbackPersonaModel: string): CockpitPersonaSetupRecord {
  return {
    selectedPersonaIds: [],
    samplingMode: "single",
    groupFilters: emptyPersonaDimensionFilters(),
    stratifyFields: ["age_bracket", "region"],
    sampleSize: 4,
    sampleSizePerValueGroup: 1,
    parallelTrials: 2,
    personaModel: fallbackPersonaModel,
    personaPool: PERSONA_BENCH_POOL,
    useTaskDefaultStrategy: false,
  };
}

export function setupFromPersonaStrategy(
  strategy: TaskPersonaStrategy | null | undefined,
  fallbackPersonaModel: string,
  base?: CockpitPersonaSetupRecord,
): CockpitPersonaSetupRecord {
  const next = base ? { ...base } : defaultPersonaSetup(fallbackPersonaModel);
  if (!strategy) return next;

  const mode = strategy.defaultMode;
  if (mode === "single" || mode === "random" || mode === "stratified") {
    next.samplingMode = mode;
  }

  next.groupFilters = {
    sources: Array.isArray(strategy.sources)
      ? strategy.sources.filter(
          (value): value is string => typeof value === "string" && Boolean(value.trim()),
        )
      : [],
    dimensionFilters:
      strategy.dimensionFilters && typeof strategy.dimensionFilters === "object"
        ? Object.fromEntries(
            Object.entries(strategy.dimensionFilters)
              .map(([key, values]) => [
                key,
                Array.isArray(values)
                  ? values.filter(
                      (value): value is string =>
                        typeof value === "string" && Boolean(value.trim()),
                    )
                  : [],
              ])
              .filter(([, values]) => (values as string[]).length > 0),
          )
        : {},
  };

  if (Array.isArray(strategy.stratifyFields) && strategy.stratifyFields.length > 0) {
    next.stratifyFields = strategy.stratifyFields.filter(
      (field): field is string => typeof field === "string" && Boolean(field.trim()),
    );
  }

  // Stratified quotas are mutually exclusive in persona_strategy.json.
  const hasPerCell =
    typeof strategy.sampleSizePerValueGroup === "number" &&
    strategy.sampleSizePerValueGroup >= 1;
  const hasSampleSize =
    typeof strategy.sampleSize === "number" && strategy.sampleSize > 0;

  if (hasPerCell) {
    next.sampleSizePerValueGroup = Math.min(
      50,
      Math.max(1, Math.round(strategy.sampleSizePerValueGroup as number)),
    );
  } else if (hasSampleSize) {
    next.sampleSize = Math.min(500, Math.max(2, Math.round(strategy.sampleSize as number)));
    next.sampleSizePerValueGroup = null;
  } else {
    next.sampleSizePerValueGroup = null;
  }

  if (typeof strategy.pool === "string" && strategy.pool.trim()) {
    next.personaPool = strategy.pool.trim();
  }

  // Fresh strategy apply clears prior preview selection and locks custom filters.
  next.selectedPersonaIds = [];
  next.useTaskDefaultStrategy = true;
  next.taskDefaultStrategyDismissed = false;
  return next;
}

export function hasStoredPersonaSetup(taskPath: string | null | undefined): boolean {
  const path = taskPath?.trim() ?? "";
  if (!path) return false;
  const store = readStore();
  return Boolean(store.byTaskPath?.[path]);
}

export function readCockpitPersonaSetup(
  taskKind: HarborCockpitTaskKind,
  fallbackPersonaModel: string,
  taskPath?: string | null,
): CockpitPersonaSetupRecord {
  const store = readStore();
  const path = taskPath?.trim() ?? "";
  if (path) {
    const byPath = normalizeRecord(store.byTaskPath?.[path], fallbackPersonaModel);
    if (byPath) return byPath;
  }

  const byKind = normalizeRecord(store.byKind?.[taskKind], fallbackPersonaModel);
  if (byKind) return byKind;

  // Legacy key without wrapper.
  if (typeof window !== "undefined") {
    try {
      const legacyRaw = window.localStorage.getItem(LEGACY_STORAGE_KEY);
      if (legacyRaw) {
        const legacy = JSON.parse(legacyRaw) as Partial<
          Record<HarborCockpitTaskKind, CockpitPersonaSetupRecord>
        >;
        const fromLegacy = normalizeRecord(legacy?.[taskKind], fallbackPersonaModel);
        if (fromLegacy) return fromLegacy;
      }
    } catch {
      /* ignore */
    }
  }

  const batch = readCockpitBatch(taskKind);
  if (batch?.personaIds.length) {
    return {
      ...defaultPersonaSetup(fallbackPersonaModel),
      selectedPersonaIds: batch.personaIds,
    };
  }

  return defaultPersonaSetup(fallbackPersonaModel);
}

export function writeCockpitPersonaSetup(
  taskKind: HarborCockpitTaskKind,
  record: CockpitPersonaSetupRecord,
  taskPath?: string | null,
): void {
  const store = readStore();
  const path = taskPath?.trim() ?? "";
  if (path) {
    store.byTaskPath = { ...(store.byTaskPath ?? {}), [path]: record };
  } else {
    store.byKind = { ...(store.byKind ?? {}), [taskKind]: record };
  }
  writeStore(store);
}
