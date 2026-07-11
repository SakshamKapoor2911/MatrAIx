import type { HarborCockpitTaskKind } from "@/lib/harborCockpitMappers";
import type { TaskPersonaStrategy } from "@/lib/types";

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
  parallelTrials: number;
  personaModel: string;
  /** When true, sampling follows the task's persona_strategy.json and custom filters stay locked. */
  useTaskDefaultStrategy: boolean;
}

type CockpitPersonaSetupStore = {
  byTaskPath?: Record<string, CockpitPersonaSetupRecord>;
  /** Legacy kind-keyed entries (pre task-path storage). */
  byKind?: Partial<Record<HarborCockpitTaskKind, CockpitPersonaSetupRecord>>;
};

const STORAGE_KEY = "playground.cockpitPersonaSetupByTaskPath";
const LEGACY_STORAGE_KEY = "playground.cockpitPersonaSetupByTask";

function readStore(): CockpitPersonaSetupStore {
  if (typeof window === "undefined") return {};
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
    parallelTrials:
      typeof record.parallelTrials === "number" && record.parallelTrials > 0 ? record.parallelTrials : 2,
    personaModel:
      typeof record.personaModel === "string" && record.personaModel
        ? record.personaModel
        : fallbackPersonaModel,
    // Legacy entries omit this flag — prefer task default until the user turns it off.
    useTaskDefaultStrategy:
      typeof record.useTaskDefaultStrategy === "boolean" ? record.useTaskDefaultStrategy : true,
  };
}

export function defaultPersonaSetup(fallbackPersonaModel: string): CockpitPersonaSetupRecord {
  return {
    selectedPersonaIds: [],
    samplingMode: "single",
    groupFilters: emptyPersonaDimensionFilters(),
    stratifyFields: ["age_bracket", "region"],
    sampleSize: 4,
    parallelTrials: 2,
    personaModel: fallbackPersonaModel,
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

  if (typeof strategy.sampleSize === "number" && strategy.sampleSize > 0) {
    next.sampleSize = Math.min(500, Math.max(2, Math.round(strategy.sampleSize)));
  }

  // Fresh strategy apply clears prior preview selection and locks custom filters.
  next.selectedPersonaIds = [];
  next.useTaskDefaultStrategy = true;
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
