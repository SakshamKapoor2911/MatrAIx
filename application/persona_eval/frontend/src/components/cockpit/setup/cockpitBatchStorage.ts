import type { HarborCockpitTaskKind } from "@/lib/harborCockpitMappers";

export interface CockpitBatchRecord {
  jobName: string;
  personaIds: string[];
  taskId?: string;
}

type CockpitBatchStore = Partial<Record<HarborCockpitTaskKind, CockpitBatchRecord | null>>;

const STORAGE_KEY = "personaeval.cockpitBatchesByTask";
const LEGACY_PERSONAS_KEY = "personaeval.cockpitBatchPersonas";
const LEGACY_URL_STATE_KEY = "personaeval.urlState";

type LegacyCockpitBatchStore = CockpitBatchStore & { cua?: CockpitBatchRecord | null };

function migrateLegacyTaskKinds(store: CockpitBatchStore): CockpitBatchStore {
  const legacy = (store as LegacyCockpitBatchStore).cua;
  if (!legacy) return store;
  const next: LegacyCockpitBatchStore = { ...store, "os-app": store["os-app"] ?? legacy };
  delete next.cua;
  return next;
}

function readStore(): CockpitBatchStore {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as CockpitBatchStore;
    if (!parsed || typeof parsed !== "object") return {};
    const migrated = migrateLegacyTaskKinds(parsed);
    if (migrated !== parsed) {
      writeStore(migrated);
    }
    return migrated;
  } catch {
    return {};
  }
}

function writeStore(store: CockpitBatchStore): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

function inferTaskKindFromJobName(jobName: string): HarborCockpitTaskKind | null {
  const normalized = jobName.toLowerCase();
  if (normalized.includes("-chat-") || normalized.includes("recommender-agent")) return "chatbot";
  if (normalized.includes("-survey-") || normalized.includes("survey")) return "survey";
  if (normalized.includes("-web-")) return "web";
  if (normalized.includes("-cua-") || normalized.includes("computer-use")) return "os-app";
  return null;
}

function migrateLegacyBatchStore(): void {
  if (typeof window === "undefined") return;
  if (window.localStorage.getItem(STORAGE_KEY)) return;
  try {
    const urlState = JSON.parse(
      window.localStorage.getItem(LEGACY_URL_STATE_KEY) ?? "{}",
    ) as { cockpitBatch?: string | null; peTask?: string | null };
    const legacyPersonas = JSON.parse(
      window.localStorage.getItem(LEGACY_PERSONAS_KEY) ?? "[]",
    ) as unknown;
    const jobName = urlState.cockpitBatch;
    if (!jobName) return;
    const taskKind =
      inferTaskKindFromJobName(jobName) ??
      (urlState.peTask === "cua"
        ? "os-app"
        : (urlState.peTask as HarborCockpitTaskKind | undefined));
    if (!taskKind) return;
    const personaIds = Array.isArray(legacyPersonas)
      ? legacyPersonas.filter((id): id is string => typeof id === "string")
      : [];
    writeStore({ [taskKind]: { jobName, personaIds } });
    window.localStorage.removeItem(LEGACY_PERSONAS_KEY);
  } catch {
    // Ignore corrupt legacy payloads.
  }
}

migrateLegacyBatchStore();

export function readCockpitBatch(taskKind: HarborCockpitTaskKind): CockpitBatchRecord | null {
  const record = readStore()[taskKind];
  if (!record?.jobName) return null;
  return {
    jobName: record.jobName,
    personaIds: Array.isArray(record.personaIds)
      ? record.personaIds.filter((id): id is string => typeof id === "string")
      : [],
    taskId: typeof record.taskId === "string" ? record.taskId : undefined,
  };
}

export function writeCockpitBatch(
  taskKind: HarborCockpitTaskKind,
  record: CockpitBatchRecord | null,
): void {
  const store = readStore();
  if (record?.jobName) {
    store[taskKind] = {
      jobName: record.jobName,
      personaIds: record.personaIds,
      taskId: record.taskId,
    };
  } else {
    store[taskKind] = null;
  }
  writeStore(store);
}
