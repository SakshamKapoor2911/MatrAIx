import type { CockpitSelectOption } from "@/components/cockpit/setup/CockpitSelect";

/** Control surface from light (script-only) → full (desktop pixels). */
export type AgentCapabilityTier = "light" | "standard" | "extended" | "full";

export interface PersonaAgentOption {
  value: string;
  label: string;
  capability: string;
  tier: AgentCapabilityTier;
  summary: string;
}

/** Harbor web agents — increasing control surface. */
export const WEB_PERSONA_AGENTS: PersonaAgentOption[] = [
  {
    value: "persona-openhands-sdk",
    label: "OpenHands SDK",
    capability: "Playwright + DOM",
    tier: "light",
    summary: "the agent writes playwright scripts in a terminal — page structure only, no packaged browser product.",
  },
  {
    value: "persona-browser-use",
    label: "Browser-use",
    capability: "Browser + DOM + Vision",
    tier: "standard",
    summary: "a ready-made website agent — browse and save output inside one chromium loop, no shell.",
  },
  {
    value: "persona-cocoa",
    label: "CocoaAgent",
    capability: "Browser API (incl. vision) + DOM + File + Code",
    tier: "extended",
    summary:
      "browse plus dom tools, files, shell, and code in one sandbox — still inside browser apis, not full-desktop clicks.",
  },
  {
    value: "persona-computer-1",
    label: "Computer-use",
    capability: "Pixel Click full Desktop",
    tier: "full",
    summary: "sees the whole desktop and clicks screen coordinates — for native apps, not structured page apis.",
  },
];

/** persona-computer-1 runtime backends for CUA tasks. */
export const CUA_RUNTIME_OPTIONS: PersonaAgentOption[] = [
  {
    value: "docker",
    label: "Docker desktop",
    capability: "Linux Xvfb",
    tier: "standard",
    summary: "linux desktop in docker with xvfb — default for desktop tasks.",
  },
  {
    value: "macos",
    label: "use.computer macOS",
    capability: "Native macOS",
    tier: "full",
    summary: "real macos desktop via use.computer.",
  },
  {
    value: "ios",
    label: "use.computer iOS",
    capability: "iOS Simulator",
    tier: "full",
    summary: "ios simulator via use.computer.",
  },
];

export const USE_COMPUTER_URL = "https://use.computer";

export const WEB_TASK_SUGGESTED_AGENT: Record<string, string> = {
  "web-playwright-quote-choice": "persona-openhands-sdk",
  "web-browser-use-laptop-choice": "persona-browser-use",
  "web-cocoa-plan-choice": "persona-cocoa",
  "web-cua-bookshop-choice": "persona-computer-1",
  "web-ecommerce-platform_product-discovery": "persona-openhands-sdk",
};

export function webPersonaAgentSelectOptions(): CockpitSelectOption[] {
  return WEB_PERSONA_AGENTS.map((opt) => ({
    value: opt.value,
    label: opt.label,
    meta: `${opt.tier} · ${opt.capability}`,
    summary: opt.summary,
  }));
}

export function cuaRuntimeSelectOptions(platform: string): CockpitSelectOption[] {
  return cuaRuntimeOptionsForPlatform(platform).map((opt) => ({
    value: opt.value,
    label: opt.label,
    meta: opt.capability,
    summary: opt.summary,
  }));
}

export function suggestedWebPersonaAgent(taskId: string): string {
  return WEB_TASK_SUGGESTED_AGENT[taskId] ?? "persona-openhands-sdk";
}

export function resolveWebPersonaAgent(taskId: string, overrides: Record<string, string>): string {
  return overrides[taskId] ?? suggestedWebPersonaAgent(taskId);
}

export function suggestedCuaBackend(platform: string): string {
  if (platform === "macos") return "macos";
  if (platform === "ios") return "ios";
  return "docker";
}

export function resolveCuaBackend(
  taskId: string,
  platform: string,
  overrides: Record<string, string>,
): string {
  return overrides[taskId] ?? suggestedCuaBackend(platform);
}

export function cuaRuntimeOptionsForPlatform(platform: string): PersonaAgentOption[] {
  if (platform === "macos") {
    return CUA_RUNTIME_OPTIONS.filter((opt) => opt.value === "macos");
  }
  if (platform === "ios") {
    return CUA_RUNTIME_OPTIONS.filter((opt) => opt.value === "ios");
  }
  return CUA_RUNTIME_OPTIONS.filter((opt) => opt.value === "docker");
}

export function findWebPersonaAgent(agentId: string): PersonaAgentOption | undefined {
  return WEB_PERSONA_AGENTS.find((opt) => opt.value === agentId);
}

export function webPersonaAgentLabel(agentId: string): string {
  return findWebPersonaAgent(agentId)?.label ?? agentId;
}

export function webPersonaAgentMode(agentId: string): string {
  return webPersonaAgentLabel(agentId);
}

export function webPersonaAgentCapabilityLabel(agentId: string): string {
  const opt = findWebPersonaAgent(agentId);
  if (!opt) return agentId;
  return `${opt.label} (${opt.capability})`;
}

const CAPABILITY_TIER_LABELS: Record<AgentCapabilityTier, string> = {
  light: "Light",
  standard: "Standard",
  extended: "Extended",
  full: "Full",
};

/** Capability tier for the web pipeline (no agent naming). */
export function webCapabilityTierLabel(agentId: string): string {
  const tier = findWebPersonaAgent(agentId)?.tier;
  return tier ? CAPABILITY_TIER_LABELS[tier] : "Per task";
}

/** Short control-surface summary for the web pipeline node detail. */
export function webCapabilitySurfaceLabel(agentId: string): string {
  return findWebPersonaAgent(agentId)?.capability ?? "per task";
}

export function webCapabilityTierIcon(agentId: string): string {
  const tier = findWebPersonaAgent(agentId)?.tier;
  return webCapabilityTierIconForTier(tier);
}

export function webCapabilityTierIconForTier(tier?: AgentCapabilityTier | string | null): string {
  switch (tier) {
    case "light":
      return "code";
    case "standard":
      return "language";
    case "extended":
      return "extension";
    case "full":
      return "desktop_windows";
    default:
      return "tune";
  }
}

export interface PipelinePathOption {
  id: string;
  label: string;
  icon: string;
  hint?: string;
}

/** Web access paths — vertical fork before the Website node. */
export const WEB_ACCESS_PIPELINE_PATHS: PipelinePathOption[] = WEB_PERSONA_AGENTS.map((agent) => ({
  id: agent.tier,
  label: CAPABILITY_TIER_LABELS[agent.tier],
  icon: webCapabilityTierIconForTier(agent.tier),
  hint: agent.capability,
}));

/** Chatbot adapter paths — vertical fork before the Chatbot node. */
export const CHAT_ACCESS_PIPELINE_PATHS: PipelinePathOption[] = [
  { id: "sidecar", label: "Sidecar", icon: "dns" },
  { id: "api", label: "API", icon: "http" },
  { id: "mcp", label: "MCP", icon: "hub" },
];

export function personaAgentSelectLabel(opt: PersonaAgentOption): string {
  return `${opt.label} (${opt.capability})`;
}

export const OS_APP_TAB_LABEL = "OS app";

/** OS platform paths — vertical fork before the OS app node. */
export const OS_PLATFORM_PIPELINE_PATHS: PipelinePathOption[] = [
  { id: "linux", label: "Linux", icon: "desktop_windows", hint: "Docker · Xvfb" },
  { id: "macos", label: "macOS", icon: "laptop_mac", hint: "use.computer" },
  { id: "ios", label: "iOS", icon: "phone_iphone", hint: "Simulator" },
];

export function cuaRuntimeLabel(backend: string): string {
  const opt = CUA_RUNTIME_OPTIONS.find((o) => o.value === backend);
  return opt ? `${opt.label} (${opt.capability})` : backend;
}

/** Default LLM for OS app Harbor runs (persona-computer-1 ``model_name``). */
export const DEFAULT_CUA_AGENT_MODEL = "anthropic/claude-sonnet-4-6";

/** Platform-aware agent model list for the Persona rail (macOS/iOS → Anthropic only). */
export function cuaPersonaModelSelectOptions(
  platform: string | undefined,
  options: CockpitSelectOption[],
): CockpitSelectOption[] {
  const normalized = (platform ?? "linux").toLowerCase();
  if (normalized === "macos" || normalized === "ios") {
    return options
      .filter((opt) => opt.value.startsWith("anthropic/"))
      .map((opt) => ({
        ...opt,
        summary:
          opt.summary ??
          "Anthropic computer-use — required for use.computer on macOS and iOS.",
      }));
  }
  return options;
}

/** Short pipeline subtitle for the Persona node (mirrors the Persona model selector). */
export function personaModelPipelineLabel(
  modelId: string | undefined,
  options: Pick<CockpitSelectOption, "value" | "label">[],
): string {
  if (!modelId) return "Base model";
  const match = options.find((opt) => opt.value === modelId);
  if (match) return match.label;
  const slash = modelId.lastIndexOf("/");
  return slash >= 0 ? modelId.slice(slash + 1) : modelId;
}
