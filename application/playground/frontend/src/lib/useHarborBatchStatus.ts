import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "./api";
import type { HarborStatusCode } from "./types";

const POLL_MS = 1_000;
const TERMINAL_LAUNCH_STATUSES = new Set(["completed", "failed", "cancelled"]);

export interface BatchStatusSnapshot {
  version: number;
  trialCount: number;
  launchStatus: string | null;
  counts: { pending: number; running: number; done: number; error: number };
  codes: HarborStatusCode[];
  trialNames: string[];
  personaIds: (string | null)[];
  personaNames: (string | null)[];
}

function shouldStopPolling(snapshot: BatchStatusSnapshot): boolean {
  const { pending, running, done, error } = snapshot.counts;
  if (pending > 0 || running > 0) return false;
  const launch = (snapshot.launchStatus ?? "").toLowerCase();
  if (TERMINAL_LAUNCH_STATUSES.has(launch)) return true;
  // Disk-only completed jobs may have a null launchStatus.
  return snapshot.trialCount > 0 && done + error >= snapshot.trialCount;
}

/**
 * Lightweight cohort status feed for very large batch runs. Polls the aggregate
 * `/status` endpoint and applies incremental `[index, code]` deltas so payloads
 * stay tiny at tens-of-thousands scale. Falls back to a full refetch (since=0)
 * whenever the local snapshot can't absorb a delta (e.g. new trials appeared).
 */
export function useHarborBatchStatus(jobName: string | null, enabled: boolean) {
  const [snapshot, setSnapshot] = useState<BatchStatusSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const stateRef = useRef<BatchStatusSnapshot | null>(null);

  useEffect(() => {
    if (!jobName || !enabled) {
      setSnapshot(null);
      setError(null);
      stateRef.current = null;
      return;
    }

    let cancelled = false;
    let intervalId: number | null = null;
    stateRef.current = null;

    const stopPolling = () => {
      if (intervalId != null) {
        window.clearInterval(intervalId);
        intervalId = null;
      }
    };

    const tick = async () => {
      const since = stateRef.current?.version ?? 0;
      try {
        const res = await api.getHarborJobStatus(jobName, since);
        if (cancelled) return;
        setError(null);

        const prev = stateRef.current;
        let next: BatchStatusSnapshot;

        if (res.full || !prev) {
          next = {
            version: res.version,
            trialCount: res.trialCount,
            launchStatus: res.launchStatus ?? null,
            counts: res.counts,
            codes: res.statuses ?? [],
            trialNames: res.trialNames ?? [],
            personaIds: res.personaIds ?? [],
            personaNames: res.personaNames ?? [],
          };
        } else {
          const codes = prev.codes.slice();
          let needFull = false;
          for (const [index, code] of res.changes ?? []) {
            if (index < 0 || index >= codes.length) {
              needFull = true;
              break;
            }
            codes[index] = code;
          }
          if (needFull || res.trialCount !== codes.length) {
            // Can't reconcile locally — reset version so the next tick pulls full.
            next = { ...prev, version: 0 };
          } else {
            next = {
              ...prev,
              version: res.version,
              trialCount: res.trialCount,
              launchStatus: res.launchStatus ?? null,
              counts: res.counts,
              codes,
            };
          }
        }

        stateRef.current = next;
        setSnapshot(next);
        if (shouldStopPolling(next)) {
          stopPolling();
        }
      } catch (exc) {
        if (cancelled) return;
        setError(exc instanceof ApiError ? exc.message : exc instanceof Error ? exc.message : String(exc));
      }
    };

    void tick();
    intervalId = window.setInterval(() => void tick(), POLL_MS);
    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [jobName, enabled]);

  return { snapshot, error };
}
