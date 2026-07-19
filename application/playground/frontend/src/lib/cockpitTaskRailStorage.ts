import type { PlaygroundTaskType } from "../components/cockpit/TaskTypeSwitch";

const RECENT_KEY = "playground.taskRail.recent";
const PINNED_KEY = "playground.taskRail.pinned";
const MAX_RECENT = 12;

type TaskRailStorage = Record<string, string[]>;

function readMap(key: string): TaskRailStorage {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    return parsed as TaskRailStorage;
  } catch {
    return {};
  }
}

function writeMap(key: string, value: TaskRailStorage): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore quota / privacy mode errors.
  }
}

function listForTaskType(map: TaskRailStorage, taskType: PlaygroundTaskType): string[] {
  const values = map[taskType];
  return Array.isArray(values) ? values.filter((item) => typeof item === "string") : [];
}

export function readRecentTaskIds(taskType: PlaygroundTaskType): string[] {
  return listForTaskType(readMap(RECENT_KEY), taskType);
}

export function readPinnedTaskIds(taskType: PlaygroundTaskType): string[] {
  return listForTaskType(readMap(PINNED_KEY), taskType);
}

export function recordRecentTaskSelection(taskType: PlaygroundTaskType, taskId: string): void {
  const trimmed = taskId.trim();
  if (!trimmed) return;
  const map = readMap(RECENT_KEY);
  const current = listForTaskType(map, taskType).filter((item) => item !== trimmed);
  map[taskType] = [trimmed, ...current].slice(0, MAX_RECENT);
  writeMap(RECENT_KEY, map);
}

export function togglePinnedTask(taskType: PlaygroundTaskType, taskId: string): string[] {
  const trimmed = taskId.trim();
  const map = readMap(PINNED_KEY);
  const current = listForTaskType(map, taskType);
  const next = current.includes(trimmed)
    ? current.filter((item) => item !== trimmed)
    : [...current, trimmed];
  map[taskType] = next;
  writeMap(PINNED_KEY, map);
  return next;
}

export function isPinnedTask(taskType: PlaygroundTaskType, taskId: string): boolean {
  return readPinnedTaskIds(taskType).includes(taskId);
}
