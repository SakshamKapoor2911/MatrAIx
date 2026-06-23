import type { ConfigEnvironment } from "./types";

const configEnvironmentWithPromptOwnership: ConfigEnvironment = {
  runtime: "Harbor",
  personaAgent: "Harbor persona-claude-code",
  applicationApi: "rec-agent-api sidecar",
  cache: "Docker image + model cache volumes",
  ranker: "SASRec (native)",
  resources: "all_resources",
  agent: "InteRecAgent",
  promptOwnership: {
    personaSystemPrompt: "Harbor native persona injection",
    taskPrompt: "Application-provided recommender simulation prompt",
  },
};

void configEnvironmentWithPromptOwnership;
