import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Markdown } from "@/components/Markdown";
import { api, ApiError } from "@/lib/api";
import { FOCUS_RING, Sym } from "../cockpitShared";
import { RailInsetModal } from "./RailInsetModal";
import type { TaskCardModel } from "./TaskSelectionRail";
import { ToneChip, transportChipTone } from "./ToneChip";
import { CHIP_TEXT_CLASS, formatChipLabel } from "./taskCardLabels";
import { buildTaskDocSections, type TaskDocSection, type TaskDocTabId } from "./taskDetailSections";

function transportLabel(transport?: TaskCardModel["transport"]): string {
  if (transport === "mcp") return "MCP";
  if (transport === "api") return "API";
  if (transport === "sidecar") return "Sidecar";
  return "—";
}

function TaskDocTabBar({
  sections,
  active,
  onChange,
}: {
  sections: TaskDocSection[];
  active: TaskDocTabId;
  onChange: (tab: TaskDocTabId) => void;
}) {
  if (sections.length <= 1) return null;

  return (
    <div
      role="tablist"
      aria-label="Task documents"
      className="flex flex-wrap items-center gap-x-1 gap-y-1 border-b border-outline/40"
    >
      {sections.map((section) => {
        const selected = section.id === active;
        return (
          <button
            key={section.id}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(section.id)}
            className={`-mb-px flex items-center gap-1 border-b-2 px-2 py-2 text-[10px] font-medium transition ${FOCUS_RING} ${
              selected
                ? "border-primary text-primary"
                : "border-transparent text-text-variant hover:text-text-main"
            }`}
          >
            <Sym name={section.icon} fill={selected ? 1 : 0} size={14} />
            {section.label}
          </button>
        );
      })}
    </div>
  );
}

export interface TaskDetailModalProps {
  open: boolean;
  card: TaskCardModel | null;
  onClose: () => void;
}

export function TaskDetailModal({ open, card, onClose }: TaskDetailModalProps) {
  const taskPath = card?.taskPath?.trim() ?? "";

  const detailQuery = useQuery({
    queryKey: ["task-detail", taskPath],
    queryFn: () => api.getTaskDetail(taskPath),
    enabled: open && Boolean(taskPath),
    staleTime: 300_000,
    retry: 1,
  });

  const sections = useMemo(
    () =>
      buildTaskDocSections({
        instructionMarkdown: detailQuery.data?.instructionMarkdown ?? card?.instructionMarkdown,
        contextMarkdown: detailQuery.data?.contextMarkdown,
        questionnaireMarkdown: detailQuery.data?.questionnaireMarkdown,
        outputSchemaMarkdown: detailQuery.data?.outputSchemaMarkdown,
        selfReportMarkdown: detailQuery.data?.selfReportMarkdown,
      }),
    [card?.instructionMarkdown, detailQuery.data],
  );

  const [activeTab, setActiveTab] = useState<TaskDocTabId>("instruction");

  useEffect(() => {
    if (!open || sections.length === 0) return;
    setActiveTab((current) =>
      sections.some((section) => section.id === current) ? current : sections[0].id,
    );
  }, [open, card?.id, sections]);

  const activeSection = sections.find((section) => section.id === activeTab) ?? sections[0] ?? null;
  const loading = Boolean(taskPath) && detailQuery.isLoading && sections.length === 0;
  const failed = Boolean(taskPath) && detailQuery.isError && sections.length === 0;

  return (
    <RailInsetModal
      open={open && Boolean(card)}
      title={detailQuery.data?.title ?? card?.title ?? "Task"}
      subtitle={card?.taskType ? `${card.taskType} task documents` : "Task documents"}
      onClose={onClose}
    >
      {card && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-1.5">
            {card.transport && (
              <ToneChip tone={transportChipTone(card.transport)} className={CHIP_TEXT_CLASS}>
                {transportLabel(card.transport)}
              </ToneChip>
            )}
            {(card.tags ??
              (card.tagLabels?.map((label) => ({ label, tone: "secondary" as const })) ??
                [])).map((tag) => (
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

          {!taskPath && (
            <p className="text-[12px] text-danger">This task has no task path — no instruction document to show.</p>
          )}
          {loading && <p className="text-[12px] text-text-dim">Loading task documents…</p>}
          {failed && (
            <p className="text-[12px] text-danger">
              {detailQuery.error instanceof ApiError
                ? detailQuery.error.message
                : "Could not load task documents."}
            </p>
          )}

          {sections.length > 0 ? (
            <>
              <TaskDocTabBar sections={sections} active={activeTab} onChange={setActiveTab} />
              {activeSection ? (
                <div role="tabpanel" className="pt-1">
                  <Markdown className="text-[12px] leading-relaxed text-text-variant">
                    {activeSection.markdown}
                  </Markdown>
                </div>
              ) : null}
            </>
          ) : null}

          {!loading && !failed && taskPath && sections.length === 0 ? (
            <p className="text-[12px] text-text-dim">No task documents are available for this task.</p>
          ) : null}
        </div>
      )}
    </RailInsetModal>
  );
}
