import type { PersonaPoolCatalog } from "./types";

export function poolSlugLabel(poolPath: string): string {
  const slug = poolPath.split("/").filter(Boolean).pop() ?? poolPath;
  return slug.replace(/-/g, " ");
}

export function personaPoolEmptyMessage(
  catalog: PersonaPoolCatalog | null | undefined,
): string {
  const pool = catalog?.pool ? poolSlugLabel(catalog.pool) : "persona pool";
  return `${pool} is empty or could not be loaded.`;
}

/** Backend / sampling errors that mean the fixture pool is too thin for filters. */
export function isPersonaPoolCoverageError(message: string | null | undefined): boolean {
  const text = message ?? "";
  return (
    text.includes("exceeds matched pool size") ||
    text.includes("No personas with stratify fields") ||
    text.includes("sample_size_per_value_group=") ||
    text.includes("generate_dev_personas.py --strategy")
  );
}

export function personaStrategyGenerateCommand(taskPath?: string | null): string {
  const cleaned = (taskPath ?? "").trim().replace(/\/+$/, "");
  const strategy = cleaned
    ? `${cleaned}/persona_strategy.json`
    : "application/tasks/<task>/persona_strategy.json";
  return `uv run python persona/scripts/generate_dev_personas.py --strategy ${strategy}`;
}

export function personaPoolCoverageHint(taskPath?: string | null): string {
  return (
    "Auto pool top-up was unavailable. Generate a local strategy pool manually, " +
    'then point persona_strategy.json "pool" at the printed _generated path:\n' +
    personaStrategyGenerateCommand(taskPath)
  );
}

/** Prefer the API message when it already includes the recovery command. */
export function formatPersonaSampleError(
  message: string,
  taskPath?: string | null,
): { summary: string; command: string | null } {
  const trimmed = message.trim();
  const commandMatch = trimmed.match(
    /uv run python persona\/scripts\/generate_dev_personas\.py --strategy \S+/,
  );
  if (commandMatch) {
    const summary = trimmed
      .replace(commandMatch[0], "")
      .replace(/\n{3,}/g, "\n\n")
      .replace(/\n\nFix:|\n\nPool coverage[\s\S]*$/i, "")
      .trim();
    return {
      summary: summary || "Pool coverage is too thin for these filters.",
      command: commandMatch[0],
    };
  }
  if (isPersonaPoolCoverageError(trimmed)) {
    return {
      summary: trimmed.split("\n")[0] || trimmed,
      command: personaStrategyGenerateCommand(taskPath),
    };
  }
  return { summary: trimmed, command: null };
}
