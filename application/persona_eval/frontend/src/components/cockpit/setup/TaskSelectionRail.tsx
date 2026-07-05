import { useMemo, useState } from "react";

import type { ConfigOptionValue } from "@/lib/types";
import { FOCUS_RING, Sym } from "../cockpitShared";
import { USE_COMPUTER_URL, cuaRuntimeSelectOptions, webPersonaAgentSelectOptions } from "@/lib/personaAgentCatalog";
import { CockpitSelect } from "./CockpitSelect";
import type { PersonaEvalTaskType } from "../TaskTypeSwitch";
import { CockpitRailHeader } from "./CockpitRailHeader";
import { CockpitToggle } from "./CockpitToggle";
import { TaskDetailModal } from "./TaskDetailModal";
import { ToneChip, transportChipTone, type ToneChipTone } from "./ToneChip";
import { CHIP_TEXT_CLASS, formatChipLabel } from "./taskCardLabels";
import type { TaskCardTag } from "./taskCardLabels";
import { taskCardIcon } from "./taskCardIcons";

export type ChatTransport = "api" | "sidecar" | "mcp";

export interface TaskCardModel {
  id: string;
  title: string;
  subtitle?: string;
  taskType: PersonaEvalTaskType;
  taskPath: string;
  transport?: ChatTransport;
  available?: boolean | null;
  canStart?: boolean;
  statusLabel?: string;
  statusDetail?: string;
  /** CUA runtime platform (linux / macos / ios / web). */
  platform?: string;
  /** Harbor metadata.type from task.toml — display tag only. */
  metaType?: string;
  /** CUA metadata.os (linux / macos / ios). */
  os?: string;
  domain?: string;
  difficulty?: string;
  taskKind?: "example" | "task";
  tags?: TaskCardTag[];
  /** @deprecated prefer tags */
  tagLabels?: string[];
  profileMarkdown?: string;
  instructionMarkdown?: string;
}

export { taskCardIcon, taskMetaTypeIcon } from "./taskCardIcons";

export interface TaskSelectionRailProps {
  taskType: PersonaEvalTaskType;
  chatTasks: TaskCardModel[];
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
  maxTurns: number | null;
  onMaxTurnsChange: (turns: number | null) => void;
  onStartSidecar?: (taskId: string) => void;
  sidecarStartingId?: string | null;
  sidecarActionError?: string | null;
  resolveWebPersonaAgent?: (taskId: string) => string;
  onWebPersonaAgentChange?: (taskId: string, agent: string) => void;
  resolveCuaRuntime?: (taskId: string, platform?: string) => string;
  onCuaRuntimeChange?: (taskId: string, runtime: string) => void;
  tasksLoading?: boolean;
  tasksError?: string | null;
  disabled?: boolean;
}

function transportLabel(transport?: ChatTransport): string {
  if (transport === "mcp") return "MCP";
  if (transport === "api") return "API";
  return "Sidecar";
}

export function TaskSelectionRail({
  taskType,
  chatTasks,
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
  resolveWebPersonaAgent,
  onWebPersonaAgentChange,
  resolveCuaRuntime,
  onCuaRuntimeChange,
  tasksLoading,
  tasksError,
  disabled,
}: TaskSelectionRailProps) {
  const [settingsOpen, setSettingsOpen] = useState<string | null>(null);
  const [detailCard, setDetailCard] = useState<TaskCardModel | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const cards =
    taskType === "chatbot"
      ? chatTasks
      : taskType === "survey"
        ? surveyTasks
        : taskType === "web"
          ? webTasks
          : taskType === "os-app"
            ? cuaTasks
            : [];

  const filteredCards = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return cards;
    return cards.filter((card) => {
      const haystack = [
        card.id,
        card.title,
        card.subtitle ?? "",
        ...(card.tags?.map((tag) => tag.label) ?? []),
        card.statusLabel ?? "",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [cards, searchQuery]);

  return (
    <aside className="glass-panel glass-panel-rail relative flex h-full min-h-0 flex-col rounded-xl p-4">
      <CockpitRailHeader label="Task" />

      <label className="mb-2.5 flex flex-col gap-1">
        <span className="sr-only">Search tasks</span>
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
          const selected = selectedTaskId === card.id;
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
                  onClick={() => onSelectTask(card)}
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
                      name={taskCardIcon(taskType, card)}
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
                        <ToneChip tone={transportChipTone(card.transport)} className={CHIP_TEXT_CLASS}>
                          {transportLabel(card.transport)}
                        </ToneChip>
                      )}
                      {(card.tags ??
                        (card.tagLabels?.map((label) => ({ label, tone: "secondary" as ToneChipTone })) ??
                          (card.statusLabel
                            ? [{ label: card.statusLabel, tone: "secondary" as ToneChipTone }]
                            : []))).map((tag) => (
                        <ToneChip
                          key={tag.label}
                          tone={tag.tone}
                          showDot={tag.label === "Available" || tag.label === "Unavailable"}
                          className={CHIP_TEXT_CLASS}
                        >
                          {formatChipLabel(tag.label)}
                        </ToneChip>
                      ))}
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
                {(taskType === "web" || taskType === "os-app") && (
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
                <div className="border-t border-outline/30 px-3 py-3">
                  <CockpitSelect
                    label="Agent capability"
                    value={resolveWebPersonaAgent(card.id)}
                    options={webPersonaAgentSelectOptions()}
                    disabled={disabled}
                    onChange={(agentId) => onWebPersonaAgentChange(card.id, agentId)}
                  />
                </div>
              )}
              {settingsId && taskType === "os-app" && resolveCuaRuntime && onCuaRuntimeChange && (
                <div className="space-y-2 border-t border-outline/30 px-3 py-3">
                  <CockpitSelect
                    label="OS runtime"
                    value={resolveCuaRuntime(card.id, card.platform)}
                    options={cuaRuntimeSelectOptions(card.platform ?? "linux")}
                    disabled={disabled}
                    onChange={(backend) => onCuaRuntimeChange(card.id, backend)}
                  />
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
                </div>
              )}
              {settingsId && taskType === "chatbot" && (() => {
                const serviceUp = card.available ?? false;
                const canStart = card.canStart ?? false;
                const starting = sidecarStartingId === card.id;
                const showServiceToggle = card.available !== null && card.available !== undefined;
                return (
                <div className="space-y-3 border-t border-outline/30 px-3 py-3">
                  {showServiceToggle ? (
                    <CockpitToggle
                      checked={serviceUp}
                      onChange={(on) => {
                        if (on && !serviceUp && canStart) onStartSidecar?.(card.id);
                      }}
                      disabled={disabled || starting || serviceUp || !canStart}
                      label="Service up"
                      description={
                        starting
                          ? "Starting sidecar via docker compose…"
                          : card.statusDetail ??
                            (serviceUp
                              ? "Chat API is reachable."
                              : canStart
                                ? "Flip on to start the local chat API sidecar."
                                : "Configure the upstream endpoint for this task.")
                      }
                    />
                  ) : (
                    <div className="rounded-md border border-outline/35 bg-surface/30 px-3 py-2">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-dim">
                        Connection
                      </p>
                      <p className="mt-1 text-[11px] leading-relaxed text-text-variant">
                        {card.statusDetail ??
                          (card.transport === "mcp"
                            ? "MCP-backed task; no local HTTP health toggle is available."
                            : "No HTTP health check is configured for this task.")}
                      </p>
                    </div>
                  )}
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
                  <CockpitToggle
                    checked={maxTurns !== null}
                    onChange={(enabled) => onMaxTurnsChange(enabled ? maxTurns ?? 8 : null)}
                    disabled={disabled}
                    label="Turn limit"
                    description={
                      maxTurns === null
                        ? "Unlimited by default. The run stops only when the user simulator decides to end."
                        : "Stop after this many user turns."
                    }
                  />
                  {maxTurns !== null && (
                    <label className="cockpit-field-label flex flex-col gap-1.5">
                      Max turns
                      <input
                        type="number"
                        min={1}
                        step={1}
                        value={maxTurns}
                        disabled={disabled}
                        onChange={(e) => {
                          const next = e.currentTarget.valueAsNumber;
                          if (Number.isFinite(next) && next >= 1) onMaxTurnsChange(next);
                        }}
                        className="h-8 rounded-md border border-outline/50 bg-surface/60 px-2 text-[12px] font-medium text-text-main"
                      />
                    </label>
                  )}
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
