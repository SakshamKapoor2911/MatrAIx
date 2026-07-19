import type { ChatbotEvalTask, ChatbotSidecarStatus } from "@/lib/types";

/** Merge live sidecar probes into summary chatbot task rows. */
export function mergeChatbotTaskAvailability(
  task: ChatbotEvalTask,
  sidecars: ChatbotSidecarStatus[],
): ChatbotEvalTask {
  const appId = task.applicationId?.trim();
  if (!appId) {
    return task;
  }
  const sidecar = sidecars.find((entry) => entry.applicationId === appId);
  if (!sidecar) {
    return task;
  }
  return {
    ...task,
    available: sidecar.ok,
    canStart: sidecar.canStart,
    healthUrl: sidecar.healthUrl || task.healthUrl,
    statusDetail: sidecar.detail,
  };
}
