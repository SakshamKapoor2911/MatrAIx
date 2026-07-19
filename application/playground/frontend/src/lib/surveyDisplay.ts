import type { SurveyQuestion, SurveyTrajectoryEvent } from "@/lib/types";

const TYPE_LABELS: Record<string, string> = {
  likert: "Likert",
  single_choice: "Single choice",
  multi_choice: "Multi choice",
  free_text: "Free text",
  boolean: "Yes / no",
  bool: "Yes / no",
};

/**
 * Question-type chip tones.
 *
 * Mint (`secondary`) is reserved for pass/valid status — never use it here,
 * or type chips collide with the Valid badge in the same stats row.
 *
 *   single_choice → primary (blue)
 *   likert        → accent (violet)
 *   multi_choice  → warn (amber)
 *   free_text     → neutral outline
 */
const TYPE_TONE: Record<string, "primary" | "accent" | "warn" | "neutral"> = {
  single_choice: "primary",
  likert: "accent",
  multi_choice: "warn",
  free_text: "neutral",
  boolean: "primary",
  bool: "primary",
};

const TYPE_CHIP_CLASS: Record<"primary" | "accent" | "warn" | "neutral", string> = {
  primary: "border-primary/40 bg-primary/10 text-primary",
  accent: "border-accent/40 bg-accent/10 text-accent",
  warn: "border-warn/40 bg-warn/10 text-warn",
  neutral: "border-outline/50 bg-surface-high text-text-variant",
};

export type SurveyQuestionTypeCount = {
  type: string;
  label: string;
  count: number;
};

/** Count instrument questions by type for debrief / scorecard tiles. */
export function countSurveyQuestionTypes(
  questions: ReadonlyArray<SurveyQuestion> | null | undefined,
): SurveyQuestionTypeCount[] {
  const counts = new Map<string, number>();
  for (const question of questions ?? []) {
    const key = (question.type || "unknown").trim() || "unknown";
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([type, count]) => ({
      type,
      label: TYPE_LABELS[type] ?? type.replace(/_/g, " "),
      count,
    }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
}

export function surveyQuestionTypeLabel(type: string | null | undefined): string {
  const key = (type ?? "").trim();
  if (!key) return "Question";
  return TYPE_LABELS[key] ?? key.replace(/_/g, " ");
}

/** Border / fill / text classes for a question-type chip (never mint/secondary). */
export function surveyQuestionTypeChipClass(type: string | null | undefined): string {
  const key = (type ?? "").trim();
  const tone = TYPE_TONE[key] ?? "neutral";
  return TYPE_CHIP_CLASS[tone];
}

export type SurveyTrajectoryGroup =
  | { kind: "qa"; ask: SurveyTrajectoryEvent; answer: SurveyTrajectoryEvent }
  | { kind: "event"; event: SurveyTrajectoryEvent };

/** Pair ask_question + answer_question into Q&A steps for a readable timeline. */
export function groupSurveyTrajectory(
  events: ReadonlyArray<SurveyTrajectoryEvent>,
): SurveyTrajectoryGroup[] {
  const groups: SurveyTrajectoryGroup[] = [];
  for (let i = 0; i < events.length; i += 1) {
    const event = events[i];
    const next = events[i + 1];
    if (
      event.action === "ask_question" &&
      next &&
      next.action === "answer_question"
    ) {
      groups.push({ kind: "qa", ask: event, answer: next });
      i += 1;
      continue;
    }
    groups.push({ kind: "event", event });
  }
  return groups;
}

export function surveyTrajectoryPrompt(event: SurveyTrajectoryEvent): string {
  const prompt = event.outcome?.prompt;
  return typeof prompt === "string" ? prompt.trim() : "";
}

export function surveyTrajectoryQuestionIndex(event: SurveyTrajectoryEvent): number | null {
  const raw = event.context?.questionIndex;
  return typeof raw === "number" && Number.isFinite(raw) ? raw : null;
}

export function surveyTrajectoryQuestionType(event: SurveyTrajectoryEvent): string {
  const raw = event.context?.questionType;
  return typeof raw === "string" ? raw : "";
}

export function formatSurveyTrajectoryValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => String(item)).join(", ");
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
