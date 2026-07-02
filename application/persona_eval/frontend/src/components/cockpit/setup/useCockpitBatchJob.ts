import { useCallback, useMemo, useState } from "react";

import { useHarborBatchLive } from "@/lib/useHarborBatchLive";
import type { HarborCockpitPhase } from "@/lib/useHarborCockpitRun";

import { buildBatchGridCells } from "./BatchTrialGrid";
import type { RunLaunchPhase } from "./RunLaunchBar";

export function useCockpitBatchJob(selectedPersonaIds: string[], parallelTrials = 1) {
  const [batchJobName, setBatchJobName] = useState<string | null>(null);
  const batchLive = useHarborBatchLive(batchJobName);

  const clearBatch = useCallback(() => setBatchJobName(null), []);

  const expectedTrialCount = selectedPersonaIds.length;
  const isBatchActive = Boolean(batchJobName && batchLive.isActive);
  const batchComplete =
    Boolean(batchJobName) &&
    (batchLive.live?.completedTrials ?? 0) >= expectedTrialCount &&
    expectedTrialCount > 0;

  const batchGridCells = useMemo(
    () =>
      buildBatchGridCells(selectedPersonaIds, batchLive.live?.trials, {
        jobStarted: Boolean(batchJobName),
        parallelTrials,
      }),
    [selectedPersonaIds, batchLive.live?.trials, batchJobName, parallelTrials],
  );

  return {
    batchJobName,
    setBatchJobName,
    batchLive,
    clearBatch,
    isBatchActive,
    batchComplete,
    batchGridCells,
    expectedTrialCount,
  };
}

export function resolveRunLaunchPhase(
  batchJobName: string | null,
  batchComplete: boolean,
  batchError: string | null,
  phase: HarborCockpitPhase,
): RunLaunchPhase {
  if (batchJobName) {
    if (batchComplete) return "done";
    if (batchError) return "error";
    return "running";
  }
  if (phase === "launching") return "launching";
  if (phase === "running") return "running";
  if (phase === "done") return "done";
  if (phase === "error" || phase === "timeout") return "error";
  return "idle";
}

export function batchProgressPct(
  batchJobName: string | null,
  completedTrials: number | undefined,
  expectedTrialCount: number,
): number {
  if (!batchJobName || expectedTrialCount <= 0) return 0;
  return Math.round(((completedTrials ?? 0) / expectedTrialCount) * 100);
}
