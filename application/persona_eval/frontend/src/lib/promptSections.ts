import type { PersonaEvalPrompts } from "@/lib/types";

const SCENARIO_MARKER = "## Your scenario";
const PERSONA_MARKER = "## Persona";
const GUIDELINES_HEADER = "# User simulator guidelines";

/** Default sim guidelines are injected at runtime — strip from display-only persona text. */
export function stripDefaultSimGuidelines(text: string): string {
  const trimmed = text.trim();
  if (!trimmed.startsWith(GUIDELINES_HEADER)) {
    return trimmed;
  }
  const personaIndex = trimmed.indexOf(PERSONA_MARKER);
  if (personaIndex > 0) {
    return trimmed.slice(personaIndex).trim();
  }
  return trimmed;
}

/** Split stored prompts into persona profile vs task instruction for debrief rails. */
export function resolvePromptSections(prompts: PersonaEvalPrompts): {
  persona: string;
  task: string;
} {
  const personaPrompt = (prompts.personaPrompt ?? "").trim();
  const harborPrompt = stripDefaultSimGuidelines((prompts.harborPrompt ?? "").trim());
  const personaSource =
    personaPrompt.includes(SCENARIO_MARKER) || !harborPrompt.includes(SCENARIO_MARKER)
      ? stripDefaultSimGuidelines(personaPrompt || harborPrompt)
      : harborPrompt;
  const taskRaw = (prompts.taskPrompt ?? "").trim();

  if (taskRaw.includes(SCENARIO_MARKER) || taskRaw.includes("## Application kickoff")) {
    const scenarioInPersona = personaSource.indexOf(SCENARIO_MARKER);
    const persona =
      scenarioInPersona > 0 ? personaSource.slice(0, scenarioInPersona).trim() : personaSource;
    return { persona, task: taskRaw };
  }

  const markerIndex = personaSource.indexOf(SCENARIO_MARKER);
  if (markerIndex > 0 && taskRaw.length < 120) {
    return {
      persona: personaSource.slice(0, markerIndex).trim(),
      task: [personaSource.slice(markerIndex).trim(), taskRaw].filter(Boolean).join("\n\n"),
    };
  }

  return { persona: personaSource, task: taskRaw };
}

/** Ignore placeholder persona stubs when deciding whether a rail has content. */
export function isMeaningfulPromptBody(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) {
    return false;
  }
  if (trimmed.includes("You are a simulated user with predefined persona attributes")) {
    return false;
  }
  let body = trimmed;
  if (body.startsWith(PERSONA_MARKER)) {
    body = body.slice(PERSONA_MARKER.length).trim();
  }
  if (!body) {
    return false;
  }
  if (/^Persona\s+\S+$/i.test(body)) {
    return false;
  }
  if (/^Persona:\s*persona-\S+$/im.test(body) && body.split("\n").length <= 4) {
    return false;
  }
  return body.length >= 40 || body.includes("\n");
}
