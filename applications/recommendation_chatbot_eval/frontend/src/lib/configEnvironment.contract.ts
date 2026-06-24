import type { ConfigEnvironment } from "./types";

const configEnvironmentWithPromptOwnership: ConfigEnvironment = {
  runtime: "Harbor",
  personaAgent: "PersonaEval task controller",
  personaModel: "anthropic/claude-haiku-4-5",
  applicationApi: "chatbot-api sidecar",
  scorer: "PersonaEval self-report scorer",
  cache: "Docker image + model cache volumes",
  ranker: "application-specific ranking / tool selection",
  resources: "adapter-specific resources",
  agent: "chatbot application adapter",
  promptOwnership: {
    personaSystemPrompt: "Persona prompt from task runtime",
    taskPrompt: "Application-provided chatbot simulation prompt",
  },
};

void configEnvironmentWithPromptOwnership;
