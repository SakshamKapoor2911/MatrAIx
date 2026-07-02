import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { Markdown } from "@/components/Markdown";
import { api, ApiError } from "@/lib/api";
import { HARBOR_CHAT_TASKS } from "@/lib/types";
import { AvailabilityPill } from "./AvailabilityPill";
import { RailInsetModal } from "./RailInsetModal";
import type { TaskCardModel } from "./TaskSelectionRail";
import { ToneChip, transportChipTone } from "./ToneChip";

function transportLabel(transport?: TaskCardModel["transport"]): string {
  if (transport === "mcp") return "MCP";
  if (transport === "api") return "API";
  if (transport === "sidecar") return "Sidecar";
  return "—";
}

function resolveTaskPath(card: TaskCardModel): string {
  if (card.taskPath?.trim()) return card.taskPath.trim();
  if (card.taskType === "chatbot") return HARBOR_CHAT_TASKS[card.id] ?? "";
  return "";
}

export interface TaskDetailModalProps {
  open: boolean;
  card: TaskCardModel | null;
  onClose: () => void;
}

export function TaskDetailModal({ open, card, onClose }: TaskDetailModalProps) {
  const taskPath = card ? resolveTaskPath(card) : "";
  const embeddedMarkdown = card?.profileMarkdown?.trim() ?? "";

  const detailQuery = useQuery({
    queryKey: ["task-detail", taskPath],
    queryFn: () => api.getTaskDetail(taskPath),
    enabled: open && Boolean(taskPath) && !embeddedMarkdown,
    staleTime: 300_000,
    retry: 1,
  });

  const markdown = useMemo(() => {
    if (embeddedMarkdown) return embeddedMarkdown;
    return detailQuery.data?.profileMarkdown?.trim() ?? "";
  }, [detailQuery.data?.profileMarkdown, embeddedMarkdown]);

  const loading = Boolean(taskPath) && !embeddedMarkdown && detailQuery.isLoading;
  const failed = Boolean(taskPath) && !embeddedMarkdown && detailQuery.isError;

  return (
    <RailInsetModal
      open={open && Boolean(card)}
      title={detailQuery.data?.title ?? card?.title ?? "Task"}
      subtitle={card?.taskType ? `${card.taskType} task` : "Task"}
      onClose={onClose}
    >
      {card && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-1.5">
            {card.transport && (
              <ToneChip tone={transportChipTone(card.transport)} className="font-mono text-[9px] uppercase">
                {transportLabel(card.transport)}
              </ToneChip>
            )}
            {card.statusLabel && <AvailabilityPill available={card.available} label={card.statusLabel} />}
          </div>

          {!taskPath && (
            <p className="text-[12px] text-danger">This task has no Harbor path — no instruction document to show.</p>
          )}
          {loading && <p className="text-[12px] text-text-dim">Loading task instructions…</p>}
          {failed && (
            <p className="text-[12px] text-danger">
              {detailQuery.error instanceof ApiError
                ? detailQuery.error.message
                : "Could not load task instructions."}
            </p>
          )}
          {markdown && (
            <Markdown className="text-[12px] leading-relaxed text-text-variant">{markdown}</Markdown>
          )}
        </div>
      )}
    </RailInsetModal>
  );
}
