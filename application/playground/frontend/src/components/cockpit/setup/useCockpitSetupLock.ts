import type { HarborCockpitPhase } from "@/lib/useHarborCockpitRun";

/** Lock persona/task rails while a run or batch job is in flight — until Reset. */
export function useCockpitSetupLock(
  phase: HarborCockpitPhase,
  batchJobName: string | null,
  batchPersonaIds: string[],
  selectedPersonaIds: string[],
) {
  const setupLocked = phase !== "idle" || Boolean(batchJobName);
  const visiblePersonaIds =
    setupLocked && batchPersonaIds.length > 0 ? batchPersonaIds : selectedPersonaIds;
  return { setupLocked, visiblePersonaIds };
}
