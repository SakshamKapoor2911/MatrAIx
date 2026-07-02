import { useMemo, useState } from "react";

import type { ChatbotSidecarStatus, ConfigOptionValue } from "@/lib/types";
import { FOCUS_RING, Sym } from "../cockpitShared";
import { USE_COMPUTER_URL } from "@/lib/personaAgentCatalog";
import type { PersonaEvalTaskType } from "../TaskTypeSwitch";
import { AvailabilityPill } from "./AvailabilityPill";
import { CockpitRailHeader } from "./CockpitRailHeader";
import { CockpitToggle } from "./CockpitToggle";
import { TaskDetailModal } from "./TaskDetailModal";
import { ToneChip, transportChipTone } from "./ToneChip";

export type ChatTransport = "api" | "sidecar" | "mcp";

export interface TaskCardModel {
  id: string;
  title: string;
  subtitle?: string;
  taskType: PersonaEvalTaskType;
  taskPath: string;
  transport?: ChatTransport;
  available?: boolean;
  statusLabel?: string;
  /** Survey-only: built-in questionnaire vs Harbor example-survey task. */
  surveyKind?: "instrument" | "harbor";
  /** Registry instrument id for json_survey (Harbor + built-in questionnaires). */
  surveyInstrumentId?: string;
  /** CUA task platform (linux / macos / ios / web). */
  platform?: string;
  profileMarkdown?: string;
}

const APP_ICON: Record<string, string> = {
  recai: "recommend",
  finance_openbb: "show_chart",
  medical_assistant: "stethoscope",
};

export interface TaskSelectionRailProps {
  taskType: PersonaEvalTaskType;
  chatOptions: ConfigOptionValue[];
  selectedChatAppId: string;
  onChatAppChange: (id: string) => void;
  sidecarsByApp: Record<string, ChatbotSidecarStatus>;
  sidecarsLoading: boolean;
  surveyTasks: TaskCardModel[];
  webTasks: TaskCardModel[];
  cuaTasks: TaskCardModel[];
  selectedTaskId: string;
  onSelectTask: (task: TaskCardModel) => void;
  engine: string;
  onEngineChange: (engine: string) => void;
  engineOptions: ConfigOptionValue[];
  domain: string;
  onDomainChange: (domain: string) => void;
  domainOptions: ConfigOptionValue[];
  maxTurns: number;
  onMaxTurnsChange: (turns: number) => void;
  onStartSidecar?: (applicationId: string) => void;
  sidecarStartingId?: string | null;
  sidecarActionError?: string | null;
  webPersonaAgentOptions?: Array<{ value: string; label: string; description?: string }>;
  resolveWebPersonaAgent?: (taskId: string) => string;
  onWebPersonaAgentChange?: (taskId: string, agent: string) => void;
  resolveCuaRuntime?: (taskId: string, platform?: string) => string;
  onCuaRuntimeChange?: (taskId: string, runtime: string) => void;
  cuaRuntimeOptionsForTask?: (platform?: string) => Array<{ value: string; label: string; description?: string }>;
  tasksLoading?: boolean;
  tasksError?: string | null;
  disabled?: boolean;
}

function transportLabel(transport?: ChatTransport): string {
  if (transport === "mcp") return "MCP";
  if (transport === "api") return "API";
  return "Sidecar";
}

const RAIL_TITLES: Record<PersonaEvalTaskType, { title: string; subtitle: string }> = {
  chatbot: { title: "Chat applications", subtitle: "System under test · adapter transport" },
  survey: { title: "Survey instruments", subtitle: "Fixed questionnaires to score" },
  web: { title: "Web tasks", subtitle: "Browser scenarios and traces" },
  cua: { title: "CUA tasks", subtitle: "Computer-use agent scenarios" },
};

export function TaskSelectionRail({
  taskType,
  chatOptions,
  selectedChatAppId,
  onChatAppChange,
  sidecarsByApp,
  sidecarsLoading,
  surveyTasks,
  webTasks,
  cuaTasks,
  selectedTaskId,
  onSelectTask,
  engine,
  onEngineChange,
  engineOptions,
  domain,
  onDomainChange,
  domainOptions,
  maxTurns,
  onMaxTurnsChange,
  onStartSidecar,
  sidecarStartingId,
  sidecarActionError,
  webPersonaAgentOptions = [],
  resolveWebPersonaAgent,
  onWebPersonaAgentChange,
  resolveCuaRuntime,
  onCuaRuntimeChange,
  cuaRuntimeOptionsForTask,
  tasksLoading,
  tasksError,
  disabled,
}: TaskSelectionRailProps) {
  const [settingsOpen, setSettingsOpen] = useState<string | null>(null);
  const [detailCard, setDetailCard] = useState<TaskCardModel | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const chatCards: TaskCardModel[] = chatOptions.map((opt) => {
    const sidecar = sidecarsByApp[opt.value];
    const transport: ChatTransport =
      opt.value === "finance_openbb" ? "mcp" : opt.value === "medical_assistant" ? "api" : "sidecar";
    const available = sidecarsLoading ? undefined : sidecar?.ok ?? false;
    return {
      id: opt.value,
      title: opt.label,
      subtitle: opt.description,
      taskType: "chatbot",
      taskPath: "",
      transport,
      available,
      statusLabel: sidecarsLoading ? "Checking…" : available ? "Available" : "Unavailable",
    };
  });

  const cards =
    taskType === "chatbot"
      ? chatCards
      : taskType === "survey"
        ? surveyTasks
        : taskType === "web"
          ? webTasks
          : taskType === "cua"
            ? cuaTasks
            : [];

  const filteredCards = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return cards;
    return cards.filter((card) => {
      const haystack = [card.id, card.title, card.subtitle ?? "", card.statusLabel ?? ""]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [cards, searchQuery]);

  const railMeta = RAIL_TITLES[taskType];

  return (
    <aside className="glass-panel glass-panel-rail relative flex h-full min-h-0 flex-col rounded-xl p-4">
      <CockpitRailHeader
        eyebrow="Tasks"
        title={railMeta.title}
        subtitle={railMeta.subtitle}
      />

      <label className="mb-3 flex flex-col gap-1.5">
        <span className="cockpit-field-label">Search tasks</span>
        <div className="relative">
          <Sym
            name="search"
            size={16}
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-text-dim"
          />
          <input
            type="search"
            value={searchQuery}
            disabled={disabled}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter by name or description…"
            className="h-9 w-full rounded-lg border border-outline/50 bg-surface/60 pl-9 pr-2.5 text-[12px] text-text-main placeholder:text-text-dim"
          />
        </div>
      </label>

      {tasksLoading && (
        <p className="mb-2 text-[11px] text-text-dim">Loading tasks…</p>
      )}
      {tasksError && (
        <p className="mb-2 text-[11px] text-danger">{tasksError}</p>
      )}

      <div className="custom-scrollbar min-h-0 flex-1 space-y-2.5 overflow-y-auto pr-0.5">
        {filteredCards.length === 0 && !tasksLoading && (
          <p className="rounded-lg border border-outline/35 bg-surface/25 px-3 py-4 text-center text-[11px] text-text-dim">
            {searchQuery.trim() ? "No tasks match your search." : "No tasks available."}
          </p>
        )}
        {filteredCards.map((card) => {
          const selected =
            taskType === "chatbot" ? card.id === selectedChatAppId : selectedTaskId === card.id;
          const settingsId = settingsOpen === card.id;
          const unavailable = card.available === false;
          return (
            <div
              key={card.id}
              className={`rounded-lg border transition ${
                selected
                  ? "border-primary/55 bg-primary/10 shadow-[0_0_0_1px_rgb(var(--primary)/0.2)]"
                  : unavailable
                    ? "border-outline/35 bg-surface/20 opacity-75"
                    : "border-outline/40 bg-surface/30 hover:border-primary/25"
              }`}
            >
              <div className="flex items-start gap-3 p-3">
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => {
                    if (taskType === "chatbot") onChatAppChange(card.id);
                    onSelectTask(card);
                  }}
                  className={`flex min-w-0 flex-1 items-start gap-3 text-left ${FOCUS_RING}`}
                >
                  <div
                    className={`grid h-10 w-10 shrink-0 place-items-center rounded-lg border ${
                      selected
                        ? "border-primary/45 bg-primary/15"
                        : "border-outline/40 bg-surface-high/60"
                    }`}
                  >
                    <Sym
                      name={APP_ICON[card.id] ?? (taskType === "survey" ? "quiz" : "public")}
                      size={20}
                      className={selected ? "text-primary" : "text-text-variant"}
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-display text-[14px] font-semibold leading-tight text-text-main">
                      {card.title}
                    </p>
                    {card.subtitle && (
                      <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-text-dim">
                        {card.subtitle}
                      </p>
                    )}
                    <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                      {card.transport && (
                        <ToneChip
                          tone={transportChipTone(card.transport)}
                          className="font-mono text-[9px] uppercase tracking-wide"
                        >
                          {transportLabel(card.transport)}
                        </ToneChip>
                      )}
                      {card.statusLabel && (
                        <AvailabilityPill available={card.available} label={card.statusLabel} />
                      )}
                    </div>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setDetailCard(card)}
                  className={`shrink-0 rounded-md p-1.5 text-text-dim hover:bg-surface-high hover:text-primary ${FOCUS_RING}`}
                  aria-label={`View details for ${card.title}`}
                >
                  <Sym name="info" size={16} />
                </button>
                {taskType === "chatbot" && (
                  <button
                    type="button"
                    onClick={() => setSettingsOpen(settingsId ? null : card.id)}
                    className={`shrink-0 rounded-md p-1.5 text-text-dim hover:bg-surface-high hover:text-primary ${FOCUS_RING}`}
                    aria-label="Chatbot settings"
                  >
                    <Sym name="settings" size={16} />
                  </button>
                )}
                {(taskType === "web" || taskType === "cua") && (
                  <button
                    type="button"
                    onClick={() => setSettingsOpen(settingsId ? null : card.id)}
                    className={`shrink-0 rounded-md p-1.5 text-text-dim hover:bg-surface-high hover:text-primary ${FOCUS_RING}`}
                    aria-label="Task settings"
                  >
                    <Sym name="settings" size={16} />
                  </button>
                )}
              </div>
              {settingsId && taskType === "web" && resolveWebPersonaAgent && onWebPersonaAgentChange && (
                <div className="space-y-3 border-t border-outline/30 px-3 py-3">
                  <label className="cockpit-field-label flex flex-col gap-1.5">
                    Persona agent
                    <select
                      value={resolveWebPersonaAgent(card.id)}
                      disabled={disabled}
                      onChange={(e) => onWebPersonaAgentChange(card.id, e.target.value)}
                      className="h-8 rounded-md border border-outline/50 bg-surface/60 px-2 text-[12px] font-medium text-text-main"
                    >
                      {webPersonaAgentOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    <span className="text-[10px] leading-relaxed text-text-dim">
                      {webPersonaAgentOptions.find((opt) => opt.value === resolveWebPersonaAgent(card.id))
                        ?.description ?? "Harbor driver for this web task."}
                    </span>
                  </label>
                </div>
              )}
              {settingsId && taskType === "cua" && resolveCuaRuntime && onCuaRuntimeChange && (
                <div className="space-y-3 border-t border-outline/30 px-3 py-3">
                  <label className="cockpit-field-label flex flex-col gap-1.5">
                    CUA runtime
                    <select
                      value={resolveCuaRuntime(card.id, card.platform)}
                      disabled={disabled}
                      onChange={(e) => onCuaRuntimeChange(card.id, e.target.value)}
                      className="h-8 rounded-md border border-outline/50 bg-surface/60 px-2 text-[12px] font-medium text-text-main"
                    >
                      {(cuaRuntimeOptionsForTask?.(card.platform) ?? []).map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    <span className="text-[10px] leading-relaxed text-text-dim">
                      {(cuaRuntimeOptionsForTask?.(card.platform) ?? []).find(
                        (opt) => opt.value === resolveCuaRuntime(card.id, card.platform),
                      )?.description ?? "How persona-computer-1 runs this task."}
                    </span>
                    {(card.platform === "macos" || card.platform === "ios") && (
                      <a
                        href={USE_COMPUTER_URL}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[10px] font-medium text-primary hover:underline"
                      >
                        use.computer setup →
                      </a>
                    )}
                  </label>
                </div>
              )}
              {settingsId && taskType === "chatbot" && (() => {
                const sidecar = sidecarsByApp[card.id];
                const serviceUp = sidecar?.ok ?? false;
                const starting = sidecarStartingId === card.id;
                return (
                <div className="space-y-3 border-t border-outline/30 px-3 py-3">
                  <CockpitToggle
                    checked={serviceUp}
                    onChange={(on) => {
                      if (on && !serviceUp) onStartSidecar?.(card.id);
                    }}
                    disabled={disabled || starting || sidecarsLoading || serviceUp}
                    label="Service up"
                    description={
                      starting
                        ? "Starting sidecar via docker compose…"
                        : sidecar?.detail ??
                          (serviceUp
                            ? "Chat API is reachable."
                            : "Flip on to start the local chat API sidecar.")
                    }
                  />
                  {sidecarActionError && settingsOpen === card.id && (
                    <p className="text-[10px] text-danger">{sidecarActionError}</p>
                  )}
                  <label className="cockpit-field-label flex flex-col gap-1.5">
                    Application model
                    <select
                      value={engine}
                      disabled={disabled}
                      onChange={(e) => onEngineChange(e.target.value)}
                      className="h-8 rounded-md border border-outline/50 bg-surface/60 px-2 text-[12px] font-medium text-text-main"
                    >
                      {engineOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  {domainOptions.length > 0 && (
                    <label className="cockpit-field-label flex flex-col gap-1.5">
                      Domain
                      <select
                        value={domain}
                        disabled={disabled}
                        onChange={(e) => onDomainChange(e.target.value)}
                        className="h-8 rounded-md border border-outline/50 bg-surface/60 px-2 text-[12px] font-medium text-text-main"
                      >
                        {domainOptions.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  <label className="cockpit-field-label flex flex-col gap-1.5">
                    Max turns · <span className="font-mono text-text-main">{maxTurns}</span>
                    <input
                      type="range"
                      min={2}
                      max={12}
                      value={maxTurns}
                      disabled={disabled}
                      onChange={(e) => onMaxTurnsChange(Number(e.target.value))}
                      className="accent-primary"
                    />
                  </label>
                </div>
                );
              })()}
            </div>
          );
        })}
      </div>

      <TaskDetailModal
        open={detailCard !== null}
        card={detailCard}
        onClose={() => setDetailCard(null)}
      />
    </aside>
  );
}
