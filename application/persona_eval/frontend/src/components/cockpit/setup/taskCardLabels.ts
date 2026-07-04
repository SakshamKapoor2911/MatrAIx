import type { ToneChipTone } from "./ToneChip";

export function taskKindLabel(taskKind: "example" | "task"): string {
  return taskKind === "example" ? "Example" : "Task";
}

/** Example tasks live under ``application/tasks/example-*`` folders. */
export function inferTaskKindFromPath(taskPath?: string): "example" | "task" {
  const folder = taskPath?.split("/").filter(Boolean).pop() ?? "";
  return folder.startsWith("example-") ? "example" : "task";
}

export function resolveTaskKind(taskPath?: string, taskKind?: string): "example" | "task" {
  if (taskKind === "example" || taskKind === "task") {
    return taskKind;
  }
  return inferTaskKindFromPath(taskPath);
}

export interface TaskCardTag {
  label: string;
  tone: ToneChipTone;
}

export interface TaskCardTagInput {
  taskPath?: string;
  taskKind?: string;
  domain?: string;
  difficulty?: string;
}

export function osChipLabel(os?: string | null): string {
  const key = (os ?? "").trim().toLowerCase();
  if (key === "macos") return "macOS";
  if (key === "ios") return "iOS";
  if (key === "linux") return "Linux";
  if (!key) return "";
  return formatChipLabel(key);
}

/** Sentence-case chip text — only the first letter capitalized unless already mixed case. */
export function formatChipLabel(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return "";
  if (/[a-z]/.test(trimmed) && /[A-Z]/.test(trimmed)) {
    return trimmed;
  }
  return trimmed.charAt(0).toUpperCase() + trimmed.slice(1).toLowerCase();
}

/** Persona dimension chips use the same tone order as task metadata chips. */
const PERSONA_DIM_TONE: Record<string, ToneChipTone> = {
  age_bracket: "primary",
  region: "accent",
  domain: "secondary",
  intent: "warn",
  life_stage: "warn",
  source: "secondary",
};

const PERSONA_DIM_FALLBACK_TONES: ToneChipTone[] = ["primary", "accent", "secondary", "warn"];

export function personaDimChipTone(dimensionKey: string, index: number): ToneChipTone {
  return PERSONA_DIM_TONE[dimensionKey] ?? PERSONA_DIM_FALLBACK_TONES[index % PERSONA_DIM_FALLBACK_TONES.length];
}

/** Shared chip typography (task rail + persona cards). */
export const CHIP_TEXT_CLASS = "text-[9px]";

/** OS chips use a distinct tone so they do not collide with difficulty (secondary). */
export function osChipTone(os?: string | null): ToneChipTone {
  const key = (os ?? "").trim().toLowerCase();
  if (key === "macos") return "warn";
  if (key === "ios") return "warn";
  if (key === "linux") return "warn";
  return "warn";
}

export function taskCardTags({ taskPath, taskKind, domain, difficulty }: TaskCardTagInput): TaskCardTag[] {
  const kind = resolveTaskKind(taskPath, taskKind);
  const tags: TaskCardTag[] = [
    {
      label: taskKindLabel(kind),
      tone: kind === "example" ? "primary" : "warn",
    },
  ];

  const domainLabel = domain?.trim();
  if (domainLabel) {
    tags.push({ label: formatChipLabel(domainLabel), tone: "accent" });
  }

  const difficultyLabel = difficulty?.trim();
  if (difficultyLabel) {
    tags.push({ label: formatChipLabel(difficultyLabel), tone: "secondary" });
  }

  return tags;
}
