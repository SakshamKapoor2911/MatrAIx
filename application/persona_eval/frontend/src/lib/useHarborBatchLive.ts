import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError } from "./api";
import { applyHarborTrialEvents, type HarborCockpitLiveState } from "./harborCockpitMappers";
import type { HarborJobDetail, HarborJobLiveResponse } from "./types";

const POLL_MS = 1_000;
const STALE_BACKEND_HINT =
  "Live events API is unavailable. Restart the Playground backend (uvicorn) to enable bubble-by-bubble updates.";

function jobDetailToLive(job: HarborJobDetail): HarborJobLiveResponse {
  const trials = job.trials.map((trial) => ({
    trialName: trial.trialName,
    completed: trial.completed,
    succeeded: trial.succeeded,
    error: trial.error,
    phase: null,
  }));
  return {
    jobName: job.jobName,
    launchStatus: job.launch?.status ?? null,
    trialCount: trials.length,
    completedTrials: trials.filter((trial) => trial.completed).length,
    trials,
  };
}

async function fetchLiveSnapshot(jobName: string): Promise<HarborJobLiveResponse> {
  try {
    return await api.getHarborJobLive(jobName);
  } catch (exc) {
    if (exc instanceof ApiError && exc.status === 404) {
      const job = await api.getHarborJob(jobName);
      return jobDetailToLive(job);
    }
    throw exc;
  }
}

export function useHarborBatchLive(jobName: string | null) {
  const [live, setLive] = useState<HarborJobLiveResponse | null>(null);
  const [selectedTrial, setSelectedTrial] = useState<string | null>(null);
  const [liveByTrial, setLiveByTrial] = useState<Record<string, HarborCockpitLiveState>>({});
  const [error, setError] = useState<string | null>(null);
  const offsetsRef = useRef<Record<string, number>>({});
  const eventsApiMissingRef = useRef(false);

  const selectTrial = useCallback((trialName: string) => {
    setSelectedTrial(trialName);
  }, []);

  useEffect(() => {
    if (!jobName) {
      setLive(null);
      setSelectedTrial(null);
      setLiveByTrial({});
      offsetsRef.current = {};
      eventsApiMissingRef.current = false;
      return;
    }

    let cancelled = false;

    const tick = async () => {
      try {
        const snapshot = await fetchLiveSnapshot(jobName);
        if (cancelled) return;
        setLive(snapshot);
        if (!eventsApiMissingRef.current) setError(null);

        setSelectedTrial((current) => {
          if (current) return current;
          const active =
            snapshot.trials.find((trial) => !trial.completed) ?? snapshot.trials[0];
          return active?.trialName ?? null;
        });

        for (const trial of snapshot.trials) {
          const offset = offsetsRef.current[trial.trialName] ?? 0;
          try {
            const payload = await api.getHarborTrialEvents(jobName, trial.trialName, offset);
            offsetsRef.current[trial.trialName] = payload.offset;
            if (payload.events.length > 0) {
              setLiveByTrial((prev) => ({
                ...prev,
                [trial.trialName]: applyHarborTrialEvents(
                  payload.events,
                  prev[trial.trialName] ?? {
                    turns: [],
                    draftTurn: null,
                    phase: trial.phase ?? null,
                    prompts: null,
                  },
                ),
              }));
            } else if (trial.phase) {
              setLiveByTrial((prev) => ({
                ...prev,
                [trial.trialName]: {
                  ...(prev[trial.trialName] ?? { turns: [], prompts: null, draftTurn: null }),
                  phase: trial.phase ?? prev[trial.trialName]?.phase ?? null,
                },
              }));
            }
          } catch (exc) {
            if (exc instanceof ApiError && exc.status === 404) {
              eventsApiMissingRef.current = true;
              setError(STALE_BACKEND_HINT);
            }
            // Trial directory may not exist yet.
          }
        }
      } catch (exc) {
        if (cancelled) return;
        setError(exc instanceof Error ? exc.message : String(exc));
      }
    };

    void tick();
    const id = window.setInterval(() => void tick(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [jobName]);

  const selectedLive = selectedTrial ? liveByTrial[selectedTrial] ?? null : null;

  return {
    live,
    selectedTrial,
    selectTrial,
    selectedLive,
    liveByTrial,
    error,
    isActive:
      live?.launchStatus === "running" ||
      live?.launchStatus === "queued" ||
      (live != null && live.completedTrials < live.trialCount),
  };
}
