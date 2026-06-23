/**
 * `usePersonaEval` — drive a persona-driven "Persona Eval" run from the UI.
 *
 * A persona-eval is an async job: the persona agent drives a live multi-turn
 * conversation against the real native RecAI, and the job's state grows as
 * turns stream in (and finally carries the evaluator's questionnaire +
 * metrics). This hook encapsulates the lifecycle:
 *
 *   1. `run({ domain, personaId, maxTurns? })` POSTs the run -> `{ jobId }`.
 *   2. It then polls `GET /api/persona-eval/jobs/{jobId}` on an interval.
 *   3. It exposes the growing `PersonaEvalJobView` (with its accumulating
 *      `turns`), a flattened phase (`idle | building | running | done |
 *      error`), an `isRunning` flag, and any error message.
 *
 * Polling is implemented with React Query's `refetchInterval`, which stops
 * automatically once the job reaches a terminal state — mirroring `useTurnJob`.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { getPersonaEvalJob, getPersonaEvalPersona, startPersonaEval } from "./api";
import type {
  Domain,
  Engine,
  JobStatus,
  PersonaEvalJobView,
  PersonaEvalPersonaDetail,
} from "./types";

/** How often to poll a live persona-eval job, in milliseconds. */
const POLL_INTERVAL_MS = 1200;

/**
 * Max wall-clock for a whole persona-eval run before we give up polling. A run
 * is a full multi-turn conversation plus an evaluation pass, so this is generous
 * — it only catches a wedged backend so the picker can offer a retry.
 */
const MAX_POLL_DURATION_MS = 15 * 60_000;

/** Input accepted by `run` (mirrors the `startPersonaEval` request body). */
export interface RunPersonaEvalInput {
  domain: Domain;
  personaId: string;
  maxTurns?: number;
  goalContextId?: string;
  /** Chat model driving both the recommender and the user-simulator. */
  engine?: Engine;
}

/**
 * Flattened persona-eval phase. `idle` = nothing in flight; `timeout` = polling
 * exceeded the max duration (a retry affordance is shown).
 */
export type PersonaEvalRunPhase = JobStatus | "idle" | "timeout";

export interface UsePersonaEvalResult {
  /** Start a persona-eval run. Clears any prior result first. */
  run: (input: RunPersonaEvalInput) => void;
  /** The growing job view while polling; `null` before a run is started. */
  job: PersonaEvalJobView | null;
  /** Flattened lifecycle phase. `idle` = nothing in flight. */
  phase: PersonaEvalRunPhase;
  /** True while the run is submitting or polling (building or running). */
  isRunning: boolean;
  /** Error message if the start call or the job itself failed. */
  error: string | null;
  /** True once polling exceeded the max duration (terminal `timeout` phase). */
  timedOut: boolean;
  /** Re-run the last input after an `error`/`timeout`. No-op otherwise. */
  retry: () => void;
  /** Clear a terminal (done/error/timeout) run so the picker resets. */
  reset: () => void;
}

/**
 * Fetch one persona's full humanized profile — the catalog's "full persona"
 * view. Cached by id and long-lived (curated personas are immutable for the
 * session); only runs when an id is given.
 */
export function usePersonaDetail(personaId: string | null) {
  return useQuery<PersonaEvalPersonaDetail>({
    queryKey: ["persona-eval", "persona", personaId],
    queryFn: () => getPersonaEvalPersona(personaId as string),
    enabled: personaId !== null,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  });
}

export function usePersonaEval(): UsePersonaEvalResult {
  const [jobId, setJobId] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState(false);
  /** When the current poll started (epoch ms); null while no run is in flight. */
  const [pollStartedAt, setPollStartedAt] = useState<number | null>(null);
  /** Last input we ran, kept for `retry` after a failure/timeout. */
  const lastInputRef = useRef<RunPersonaEvalInput | null>(null);

  // --- 1. Start the run ---------------------------------------------------
  const mutation = useMutation({
    mutationFn: (input: RunPersonaEvalInput) => startPersonaEval(input),
    onMutate: (input: RunPersonaEvalInput) => {
      setStartError(null);
      setTimedOut(false);
      lastInputRef.current = input;
    },
    onSuccess: (res) => {
      setJobId(res.jobId);
      setPollStartedAt(Date.now());
    },
    onError: (err: unknown) => {
      setStartError(err instanceof Error ? err.message : "Failed to start persona eval");
    },
  });

  // --- 2. Poll the job ----------------------------------------------------
  const query = useQuery<PersonaEvalJobView>({
    queryKey: ["persona-eval", jobId],
    queryFn: () => getPersonaEvalJob(jobId as string),
    enabled: jobId !== null && !timedOut,
    // Poll until the job reaches a terminal state or the max duration elapses.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "done" || status === "error") return false;
      if (pollStartedAt !== null && Date.now() - pollStartedAt > MAX_POLL_DURATION_MS) {
        return false;
      }
      return POLL_INTERVAL_MS;
    },
    refetchOnWindowFocus: false,
    gcTime: 0,
  });

  // --- Derived view -------------------------------------------------------
  const job = jobId !== null ? query.data ?? null : null;
  const jobStatus = job?.status;

  // --- Max-duration timeout ----------------------------------------------
  useEffect(() => {
    if (jobId === null || pollStartedAt === null || timedOut) return;
    if (jobStatus === "done" || jobStatus === "error") return;
    const remaining = MAX_POLL_DURATION_MS - (Date.now() - pollStartedAt);
    const timer = setTimeout(() => setTimedOut(true), Math.max(0, remaining));
    return () => clearTimeout(timer);
  }, [jobId, pollStartedAt, timedOut, jobStatus]);

  // Clear the poll clock once the run reaches a real terminal state.
  useEffect(() => {
    if (jobStatus === "done" || jobStatus === "error") setPollStartedAt(null);
  }, [jobStatus]);

  let phase: PersonaEvalRunPhase = "idle";
  if (timedOut) {
    phase = "timeout";
  } else if (mutation.isPending) {
    phase = "building";
  } else if (job) {
    phase = job.status;
  }

  const isRunning = phase === "building" || phase === "running";
  const error =
    startError ??
    job?.error ??
    (timedOut ? "The persona eval is taking too long — the backend may be stuck." : null);

  const run = useCallback(
    (input: RunPersonaEvalInput) => {
      // Clear any prior terminal run before starting a new one.
      setStartError(null);
      setTimedOut(false);
      setPollStartedAt(null);
      setJobId(null);
      mutation.mutate(input);
    },
    [mutation],
  );

  const retry = useCallback(() => {
    const input = lastInputRef.current;
    if (!input || isRunning) return;
    setStartError(null);
    setTimedOut(false);
    setPollStartedAt(null);
    setJobId(null);
    mutation.mutate(input);
  }, [isRunning, mutation]);

  const reset = useCallback(() => {
    setJobId(null);
    setStartError(null);
    setTimedOut(false);
    setPollStartedAt(null);
    lastInputRef.current = null;
  }, []);

  return useMemo(
    () => ({ run, job, phase, isRunning, error, timedOut, retry, reset }),
    [run, job, phase, isRunning, error, timedOut, retry, reset],
  );
}
