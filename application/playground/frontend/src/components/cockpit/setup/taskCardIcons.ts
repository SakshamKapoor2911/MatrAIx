/** Icon mapping for Harbor metadata.type values. */

import type { PlaygroundTaskType } from "../TaskTypeSwitch";
import type { TaskCardModel } from "./TaskSelectionRail";

export function cuaOsIcon(os?: string): string {
  const key = (os ?? "").trim().toLowerCase();
  if (key === "macos") return "laptop_mac";
  if (key === "ios") return "phone_iphone";
  if (key === "linux") return "desktop_windows";
  return "desktop_windows";
}

export function taskMetaTypeIcon(metaType?: string): string {
  const type = (metaType ?? "").trim().toLowerCase();
  if (type === "os-app" || type === "cua") return "apps";
  if (type === "web") return "language";
  if (type === "survey") return "fact_check";
  if (type === "chatbot" || type === "chat") return "forum";
  if (type === "desktop") return "terminal";
  if (type === "mobile") return "phone_iphone";
  return "assignment";
}

export function taskCardIcon(taskType: PlaygroundTaskType, card: TaskCardModel): string {
  if (taskType === "os-app") {
    return cuaOsIcon(card.os ?? card.platform);
  }
  const metaType = card.metaType?.trim();
  if (metaType) {
    return taskMetaTypeIcon(metaType);
  }
  if (taskType === "chatbot") return "forum";
  if (taskType === "survey") return "fact_check";
  if (taskType === "web") return "language";
  return "assignment";
}
