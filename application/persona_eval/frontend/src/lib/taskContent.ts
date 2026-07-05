const LEGACY_QUESTIONNAIRE_COPY =
  "Use exact `questionId` and valid choice ids. The platform owns the output schema and standardized trajectory generation.";
const LEGACY_TRAJECTORY_COPY =
  "Do not include `trajectory`; the backend/runtime appends the standardized survey trajectory.";
const LEGACY_TRAJECTORY_INSTRUCTION_COPY =
  "Do not include `trajectory`; the backend/runtime appends it separately.";
const LEGACY_RESPONSE_COPY =
  "Do not mention file paths, runtime artifacts, or platform internals inside the JSON response.";

function trimPreservingEmpty(text: string): string {
  return text
    .split("\n")
    .map((line) => line.replace(/\s+$/g, ""))
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function normalizeTaskInstructionMarkdown(markdown?: string | null): string {
  const trimmed = (markdown ?? "").trim();
  if (!trimmed) return "";
  return trimPreservingEmpty(
    trimmed
      .replace(LEGACY_TRAJECTORY_INSTRUCTION_COPY, "")
      .replace("- Do not include `trajectory`.", "")
      .replace(LEGACY_RESPONSE_COPY, "Return only the JSON object."),
  );
}

export function normalizeQuestionnaireMarkdown(markdown?: string | null): string {
  const trimmed = (markdown ?? "").trim();
  if (!trimmed) return "";
  return trimPreservingEmpty(trimmed.replace(LEGACY_QUESTIONNAIRE_COPY, "Use exact `questionId` and valid choice ids."));
}

export function normalizeOutputSchemaMarkdown(markdown?: string | null): string {
  const trimmed = (markdown ?? "").trim();
  if (!trimmed) return "";
  return trimPreservingEmpty(
    trimmed
      .replace("Write strict JSON to `/app/output/survey_result.json`.", "Return strict JSON matching this shape.")
      .replace(LEGACY_TRAJECTORY_COPY, "")
      .replace("- Do not include `trajectory`.", ""),
  );
}

const LEGACY_SELF_REPORT_PLATFORM_COPY =
  "Platform-managed harness artifacts are documented in `application/task-spec/chatbot/eval_artifacts.md`.";

export function normalizeSelfReportMarkdown(markdown?: string | null): string {
  const trimmed = (markdown ?? "").trim();
  if (!trimmed) return "";
  return trimPreservingEmpty(
    trimmed
      .replace(LEGACY_SELF_REPORT_PLATFORM_COPY, "")
      .replace(/^Persona self-report artifact: `user_feedback\.json`\s*/m, ""),
  );
}

export function hasMeaningfulTaskContext(markdown?: string | null): boolean {
  const trimmed = (markdown ?? "").trim();
  if (!trimmed) return false;

  const nonEmptyLines = trimmed
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (trimmed.length >= 120) return true;
  if (nonEmptyLines.length >= 3) return true;
  if (/^[-*]\s/m.test(trimmed)) return true;
  if (/^\d+\.\s/m.test(trimmed)) return true;

  return false;
}
