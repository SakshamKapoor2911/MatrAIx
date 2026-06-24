import type { ConfigEnvironment } from "./types";

const configEnvironmentWithPromptOwnership: ConfigEnvironment = {
  runtime: "Harbor",
  personaAgent: "Harbor persona-claude-code",
  personaModel: "anthropic/claude-haiku-4-5",
  applicationApi: "chatbot-api sidecar",
  scorer: "Persona self-report via task controller",
  cache: "Docker image + model cache volumes",
  ranker: "application-specific ranking / tool selection",
  resources: "adapter-specific resources",
  agent: "chatbot application adapter",
  promptOwnership: {
    personaSystemPrompt: "Harbor native persona injection",
    taskPrompt: "Application-provided chatbot simulation prompt",
  },
};

void configEnvironmentWithPromptOwnership;
