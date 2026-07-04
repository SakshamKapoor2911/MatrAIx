import type { HarborCockpitTaskKind } from "@/lib/harborCockpitMappers";

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
}

type CockpitPersonaSetupStore = Partial<Record<HarborCockpitTaskKind, CockpitPersonaSetupRecord>>;

const STORAGE_KEY = "personaeval.cockpitPersonaSetupByTask";

function readStore(): CockpitPersonaSetupStore {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as CockpitPersonaSetupStore;
    return parsed && typeof parsed === "object" ? parsed : {};
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
  };
}

export function readCockpitPersonaSetup(
  taskKind: HarborCockpitTaskKind,
  fallbackPersonaModel: string,
): CockpitPersonaSetupRecord {
  const stored = normalizeRecord(readStore()[taskKind], fallbackPersonaModel);
  if (stored) return stored;

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
): void {
  const store = readStore();
  store[taskKind] = record;
  writeStore(store);
}
