import type { PlaygroundTaskType } from "@/components/cockpit/TaskTypeSwitch";
import { readPinnedTaskIds, readRecentTaskIds } from "@/lib/cockpitTaskRailStorage";
import type { TaskCardModel } from "@/components/cockpit/setup/TaskSelectionRail";

function normalizeDomain(value?: string): string {
  return (value ?? "").trim().toLowerCase();
}

export function domainOptionsForTaskCards(cards: TaskCardModel[]): string[] {
  const domains = new Set<string>();
  for (const card of cards) {
    const domain = normalizeDomain(card.domain);
    if (domain) domains.add(domain);
  }
  return [...domains].sort((a, b) => a.localeCompare(b));
}

export function orderTaskCards(
  cards: TaskCardModel[],
  taskType: PlaygroundTaskType,
  domainFilter: string | null,
): TaskCardModel[] {
  const domainKey = normalizeDomain(domainFilter ?? undefined);
  const filtered = domainKey
    ? cards.filter((card) => normalizeDomain(card.domain) === domainKey)
    : cards;

  const pinned = readPinnedTaskIds(taskType);
  const recent = readRecentTaskIds(taskType);

  const rank = (taskId: string): number => {
    const pinnedIndex = pinned.indexOf(taskId);
    if (pinnedIndex >= 0) return pinnedIndex;
    const recentIndex = recent.indexOf(taskId);
    if (recentIndex >= 0) return pinned.length + recentIndex;
    return pinned.length + recent.length + 1_000;
  };

  return [...filtered].sort((left, right) => {
    const byRank = rank(left.id) - rank(right.id);
    if (byRank !== 0) return byRank;
    return left.title.localeCompare(right.title);
  });
}
