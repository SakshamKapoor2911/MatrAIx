import type { OsAppEvalTask, SurveyHarborTask, WebEvalTask } from "@/lib/types";
import { suggestedWebPersonaAgent, webPersonaAgentLabel } from "@/lib/personaAgentCatalog";
import type { TaskCardModel } from "./TaskSelectionRail";
import { resolveTaskKind, taskCardTags, osChipLabel, osChipTone, type TaskCardTag } from "./taskCardLabels";

function availabilityRank(available?: boolean | null): number {
  if (available === true) return 0;
  if (available === false) return 2;
  return 1;
}

/** Available tasks first, then unknown status, then unavailable; stable title order within each group. */
export function sortByAvailability<T extends { available?: boolean | null; title?: string; id?: string }>(
  tasks: T[],
): T[] {
  return [...tasks].sort((a, b) => {
    const byAvailability = availabilityRank(a.available) - availabilityRank(b.available);
    if (byAvailability !== 0) return byAvailability;
    return (a.title ?? a.id ?? "").localeCompare(b.title ?? b.id ?? "");
  });
}

function withExtraTags(tags: TaskCardTag[], ...extra: TaskCardTag[]): TaskCardTag[] {
  return [...tags, ...extra];
}

function harborTaskTags(
  item: { taskPath?: string; taskKind?: string; domain?: string; difficulty?: string },
): TaskCardTag[] {
  return taskCardTags({
    taskPath: item.taskPath,
    taskKind: item.taskKind,
    domain: item.domain,
    difficulty: item.difficulty,
  });
}

export function surveyHarborTaskCards(tasks: SurveyHarborTask[]): TaskCardModel[] {
  return tasks.map((item) => {
    const taskKind = resolveTaskKind(item.taskPath, item.taskKind);
    return {
      id: item.id,
      title: item.title,
      subtitle: item.description,
      taskType: "survey",
      taskPath: item.taskPath,
      available: true,
      metaType: item.metaType ?? "survey",
      domain: item.domain,
      difficulty: item.difficulty,
      taskKind,
      tags: harborTaskTags(item),
      profileMarkdown: item.profileMarkdown,
      instructionMarkdown: item.instructionMarkdown,
    };
  });
}

export function webEvalTaskCards(tasks: WebEvalTask[]): TaskCardModel[] {
  return tasks.map((item) => {
    const taskKind = resolveTaskKind(item.taskPath, item.taskKind);
    return {
      id: item.id,
      title: item.title,
      subtitle: item.description ?? item.siteName,
      taskType: "web",
      taskPath: item.taskPath ?? "",
      available: true,
      metaType: item.metaType ?? "web",
      domain: item.domain,
      difficulty: item.difficulty,
      taskKind,
      tags: withExtraTags(harborTaskTags(item), {
        label: webPersonaAgentLabel(suggestedWebPersonaAgent(item.id)),
        tone: "warn",
      }),
      profileMarkdown: item.profileMarkdown,
      instructionMarkdown: item.instructionMarkdown,
    };
  });
}

export function osAppTaskCards(tasks: OsAppEvalTask[]): TaskCardModel[] {
  return tasks.map((item) => {
    const taskKind = resolveTaskKind(item.taskPath, item.taskKind);
    const os = item.os ?? item.platform;
    const metaType = item.metaType?.trim() || "os-app";
    const enriched = {
      ...item,
      metaType,
      domain: item.domain,
      difficulty: item.difficulty,
      taskKind,
    };
    const osLabel = osChipLabel(os);
    return {
      id: item.id,
      title: item.title,
      subtitle: item.description ?? item.environmentLabel,
      taskType: "os-app",
      taskPath: item.taskPath,
      platform: item.platform,
      os,
      available: true,
      metaType,
      domain: item.domain,
      difficulty: item.difficulty,
      taskKind,
      tags: osLabel
        ? withExtraTags(harborTaskTags(enriched), { label: osLabel, tone: osChipTone(os) })
        : harborTaskTags(enriched),
      profileMarkdown: item.profileMarkdown,
      instructionMarkdown: item.instructionMarkdown,
    };
  });
}
