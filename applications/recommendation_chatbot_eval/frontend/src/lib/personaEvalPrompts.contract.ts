import type { PersonaEvalJobView, PersonaEvalResult, PersonaEvalPrompts } from "./types";

const prompts: PersonaEvalPrompts = {
  harborPrompt: "Harbor persona system prompt",
  taskPrompt: "Application task prompt",
};

const liveJobPrompts: Pick<PersonaEvalJobView, "prompts"> = {
  prompts,
};

const persistedRunPrompts: Pick<PersonaEvalResult, "prompts"> = {
  prompts,
};

void liveJobPrompts;
void persistedRunPrompts;
