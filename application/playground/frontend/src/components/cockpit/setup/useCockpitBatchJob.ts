import { useCallback, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { PersonaPoolPersonaCard } from "@/lib/types";
import { useHarborBatchLive } from "@/lib/useHarborBatchLive";
import type { HarborCockpitPhase } from "@/lib/useHarborCockpitRun";
import type { HarborCockpitTaskKind } from "@/lib/harborCockpitMappers";
import { useUrlState } from "@/lib/useUrlState";

import { buildBatchGridCells } from "./BatchTrialGrid";
import { readCockpitBatch, writeCockpitBatch } from "./cockpitBatchStorage";
import type { RunLaunchPhase } from "./RunLaunchBar";

function initialBatchState(taskKind?: HarborCockpitTaskKind) {
  if (!taskKind) {
    return { jobName: null as string | null, personaIds: [] as string[], taskId: null as string | null };
  }
  const saved = readCockpitBatch(taskKind);
  return {
    jobName: saved?.jobName ?? null,
    personaIds: saved?.personaIds ?? [],
    taskId: saved?.taskId ?? null,
  };
}

export function useCockpitBatchJob(
  selectedPersonaIds: string[],
  parallelTrials = 1,
  taskKind?: HarborCockpitTaskKind,
) {
  const { state: urlState, setState: setUrlState } = useUrlState();
  const [initial] = useState(() => initialBatchState(taskKind));
  const [batchJobName, setBatchJobNameInternal] = useState<string | null>(initial.jobName);
  const [restoredPersonaIds, setRestoredPersonaIds] = useState<string[]>(initial.personaIds);
  const [restoredTaskId, setRestoredTaskId] = useState<string | null>(initial.taskId);
  const batchLive = useHarborBatchLive(batchJobName);

  const setBatchJobName = useCallback(
    (jobName: string | null, meta?: { taskId?: string }) => {
      setBatchJobNameInternal(jobName);
      if (!taskKind) return;

      if (jobName) {
        const personaIds = selectedPersonaIds.length > 0 ? selectedPersonaIds : restoredPersonaIds;
        const taskId = meta?.taskId ?? restoredTaskId ?? undefined;
        writeCockpitBatch(taskKind, { jobName, personaIds, taskId });
        if (selectedPersonaIds.length > 0) {
          setRestoredPersonaIds(selectedPersonaIds);
        }
        if (taskId) {
          setRestoredTaskId(taskId);
        }
        if (urlState.pgTask === taskKind) {
          setUrlState({
            cockpitBatch: jobName,
            cockpitJob: null,
            cockpitTrial: null,
            pgTask: taskKind,
          });
        }
      } else {
        writeCockpitBatch(taskKind, null);
        setRestoredPersonaIds([]);
        setRestoredTaskId(null);
        if (urlState.pgTask === taskKind) {
          setUrlState({ cockpitBatch: null });
        }
      }
    },
    [restoredPersonaIds, restoredTaskId, selectedPersonaIds, setUrlState, taskKind, urlState.pgTask],
  );

  const clearBatch = useCallback(() => setBatchJobName(null), [setBatchJobName]);
  const [cancelBusy, setCancelBusy] = useState(false);

  const cancelBatch = useCallback(async () => {
    if (!batchJobName || cancelBusy) return;
    setCancelBusy(true);
    try {
      await api.deleteHarborJob(batchJobName);
      clearBatch();
    } finally {
      setCancelBusy(false);
    }
  }, [batchJobName, cancelBusy, clearBatch]);

  // Freeze the cohort to the batch launch snapshot until the user resets.
  const effectivePersonaIds = batchJobName
    ? restoredPersonaIds.length > 0
      ? restoredPersonaIds
      : selectedPersonaIds
    : selectedPersonaIds.length > 0
      ? selectedPersonaIds
      : restoredPersonaIds;

  const personaCardsQuery = useQuery({
    queryKey: ["batch-cohort-personas", effectivePersonaIds.join(",")],
    queryFn: () =>
      api.getPersonaPoolCards({
        personaIds: effectivePersonaIds,
        limit: effectivePersonaIds.length,
      }),
    enabled: effectivePersonaIds.length > 0,
    staleTime: 300_000,
  });

  const personaById = useMemo(() => {
    const map: Record<string, PersonaPoolPersonaCard> = {};
    for (const card of personaCardsQuery.data?.personas ?? []) {
      map[card.personaId] = card;
    }
    return map;
  }, [personaCardsQuery.data?.personas]);

  const expectedTrialCount =
    effectivePersonaIds.length ||
    batchLive.live?.trialCount ||
    batchLive.live?.trials.length ||
    0;
  const isBatchActive = Boolean(batchJobName && batchLive.isActive);
  const batchComplete =
    Boolean(batchJobName) &&
    (batchLive.live?.completedTrials ?? 0) >= expectedTrialCount &&
    expectedTrialCount > 0;

  const batchGridCells = useMemo(
    () =>
      buildBatchGridCells(effectivePersonaIds, batchLive.live?.trials, {
        jobStarted: Boolean(batchJobName),
        parallelTrials,
        personaById,
      }),
    [effectivePersonaIds, batchLive.live?.trials, batchJobName, parallelTrials, personaById],
  );

  return {
    batchJobName,
    batchTaskId: restoredTaskId,
    batchPersonaIds: effectivePersonaIds,
    setBatchJobName,
    batchLive,
    clearBatch,
    cancelBatch,
    cancelBusy,
    isBatchActive,
    batchComplete,
    batchGridCells,
    expectedTrialCount,
    personaById,
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

/** Batch footer progress — counts simulated people, not job re-runs. */
export function formatBatchProgressLabel(completed: number, total: number): string {
  const done = Math.max(0, Math.min(completed, total));
  const noun = total === 1 ? "person" : "people";
  if (total <= 0) return "Batch run";
  if (done >= total) return `All ${total} ${noun} finished`;
  return `${done} of ${total} ${noun} finished`;
}

export const BATCH_RUN_COMPLETE_HINT =
  "Everyone finished — open Runs for debrief.";
