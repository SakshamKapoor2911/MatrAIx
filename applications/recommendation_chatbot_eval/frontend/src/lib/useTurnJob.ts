/**
 * `useTurnJob` — drive an async recommendation turn from the UI.
 *
 * A turn is an async job (the first turn is a multi-minute cold start). This
 * hook encapsulates the full lifecycle:
 *
 *   1. `send(message)` POSTs the turn -> `{ jobId }`.
 *   2. It then polls `GET /api/jobs/{jobId}` on an interval.
 *   3. It exposes a flattened phase (`idle | building | running | done | error`)
 *      plus the resolved `TurnView` and any error message, so the Composer can
 *      show the cold-start hint and the ChatThread can render an optimistic /
 *      pending bubble.
 *   4. On `done` it invalidates the session + session-list queries so the
 *      thread and rail re-fetch the persisted turn.
 *
 * Polling is implemented with React Query's `refetchInterval`, which stops
 * automatically once the job reaches a terminal state.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryKey,
} from "@tanstack/react-query";

import { getJob, submitTurn } from "./api";
import type { JobStatus, JobView, TurnView } from "./types";

/** How often to poll a live job, in milliseconds. */
const POLL_INTERVAL_MS = 1200;

/**
 * Max wall-clock we keep polling a single turn before giving up. A turn's cold
 * start is multi-minute, so this is generous — it only catches a wedged backend
 * (job stuck `building`/`running` forever) so the UI offers a retry instead of
 * spinning indefinitely.
 */
const MAX_POLL_DURATION_MS = 5 * 60_000;

/** Query keys used by the hook and by callers that need to invalidate. */
export const sessionKeys = {
  all: ["sessions"] as const,
  list: () => ["sessions", "list"] as QueryKey,
  detail: (id: string) => ["sessions", "detail", id] as QueryKey,
};

/**
 * Flattened phase the UI renders against. `idle` = nothing in flight;
 * `timeout` = polling exceeded the max duration (a retry affordance is shown).
 */
export type TurnPhase = "idle" | JobStatus | "timeout";

export interface UseTurnJobResult {
  /** Submit a user message as a new turn. No-op while a turn is already in flight. */
  send: (message: string) => void;
  /** Current lifecycle phase. */
  phase: TurnPhase;
  /** True while a turn is submitting or polling (building or running). */
  isPending: boolean;
  /** The message currently being processed (for optimistic rendering). */
  pendingMessage: string | null;
  /** The resolved turn once the job is `done`. */
  turn: TurnView | null;
  /** Error message if submission or the job failed. */
  error: string | null;
  /** The active job id, if any. */
  jobId: string | null;
  /** True once polling exceeded the max duration (terminal `timeout` phase). */
  timedOut: boolean;
  /** Re-submit the pending message after an `error`/`timeout`. No-op otherwise. */
  retry: () => void;
  /** Clear a terminal (done/error/timeout) result so the composer resets. */
  reset: () => void;
}

/**
 * @param sessionId  The session to run the turn against. When `null` the hook
 *                   is inert (e.g. before a session is selected/created).
 * @param onDone     Optional callback fired once with the resolved `TurnView`.
 */
export function useTurnJob(
  sessionId: string | null,
  onDone?: (turn: TurnView) => void,
): UseTurnJobResult {
  const queryClient = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState(false);
  /** When the current poll started (epoch ms); null while no job is in flight. */
  const [pollStartedAt, setPollStartedAt] = useState<number | null>(null);
  /** Last message we submitted, kept for `retry` after a failure/timeout. */
  const lastMessageRef = useRef<string | null>(null);

  // --- Session-switch race fix -------------------------------------------
  // The job query is scoped to `sessionId` (its key includes it), so a switch
  // tears down the old query. We also drop any in-flight job state on switch so
  // a stale terminal transition can never resolve against the new session.
  useEffect(() => {
    setJobId(null);
    setPendingMessage(null);
    setSubmitError(null);
    setTimedOut(false);
    setPollStartedAt(null);
    lastMessageRef.current = null;
  }, [sessionId]);

  // --- 1. Submit the turn -------------------------------------------------
  const submit = useMutation({
    mutationFn: (message: string) => {
      if (!sessionId) {
        return Promise.reject(new Error("No active session"));
      }
      return submitTurn(sessionId, message);
    },
    onMutate: (message: string) => {
      setSubmitError(null);
      setTimedOut(false);
      setPendingMessage(message);
      lastMessageRef.current = message;
    },
    onSuccess: (res) => {
      setJobId(res.jobId);
      setPollStartedAt(Date.now());
    },
    onError: (err: unknown) => {
      setSubmitError(err instanceof Error ? err.message : "Failed to submit turn");
      setPendingMessage(null);
    },
  });

  // --- 2. Poll the job ----------------------------------------------------
  // The key is scoped to `sessionId` so switching sessions tears down the old
  // poll instead of letting it bleed into the new session.
  const job = useQuery<JobView>({
    queryKey: ["jobs", sessionId, jobId],
    queryFn: () => getJob(jobId as string),
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

  const jobStatus = job.data?.status;

  // --- Max-duration timeout ----------------------------------------------
  // If the poll keeps the job non-terminal past the budget, flip to a terminal
  // `timeout` state (disables the query above) with a retry affordance.
  useEffect(() => {
    if (jobId === null || pollStartedAt === null || timedOut) return;
    if (jobStatus === "done" || jobStatus === "error") return;
    const remaining = MAX_POLL_DURATION_MS - (Date.now() - pollStartedAt);
    const timer = setTimeout(() => {
      setTimedOut(true);
      setPendingMessage(null);
    }, Math.max(0, remaining));
    return () => clearTimeout(timer);
  }, [jobId, pollStartedAt, timedOut, jobStatus]);

  // --- 3. Handle terminal states -----------------------------------------
  useEffect(() => {
    if (!jobId || !jobStatus) return;

    if (jobStatus === "done") {
      const turn = job.data?.turn ?? null;
      if (turn && onDone) onDone(turn);
      // Refresh persisted session state so the thread/rail reflect the new turn.
      if (sessionId) {
        void queryClient.invalidateQueries({ queryKey: sessionKeys.detail(sessionId) });
      }
      void queryClient.invalidateQueries({ queryKey: sessionKeys.list() });
      setPendingMessage(null);
      setPollStartedAt(null);
    } else if (jobStatus === "error") {
      setSubmitError(job.data?.error ?? "The turn failed");
      setPendingMessage(null);
      setPollStartedAt(null);
    }
    // `job.data` is intentionally read inside; depending on `jobStatus` is the
    // stable trigger that flips exactly once per terminal transition.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, jobStatus, sessionId]);

  // --- Derived phase ------------------------------------------------------
  let phase: TurnPhase = "idle";
  if (timedOut) {
    phase = "timeout";
  } else if (submit.isPending) {
    phase = "building";
  } else if (jobStatus) {
    phase = jobStatus;
  }

  const isPending = phase === "building" || phase === "running";

  const reset = useCallback(() => {
    setJobId(null);
    setPendingMessage(null);
    setSubmitError(null);
    setTimedOut(false);
    setPollStartedAt(null);
    lastMessageRef.current = null;
  }, []);

  const send = useCallback(
    (message: string) => {
      const trimmed = message.trim();
      if (!trimmed || isPending || !sessionId) return;
      // Clear any prior terminal job before starting a new one.
      setJobId(null);
      setTimedOut(false);
      submit.mutate(trimmed);
    },
    [isPending, sessionId, submit],
  );

  const retry = useCallback(() => {
    const message = lastMessageRef.current;
    if (!message || isPending || !sessionId) return;
    setJobId(null);
    setTimedOut(false);
    setSubmitError(null);
    submit.mutate(message);
  }, [isPending, sessionId, submit]);

  const error =
    submitError ??
    (jobStatus === "error" ? job.data?.error ?? "The turn failed" : null) ??
    (timedOut ? "The turn is taking too long — the backend may be stuck." : null);

  return {
    send,
    phase,
    isPending,
    pendingMessage,
    turn: jobStatus === "done" ? job.data?.turn ?? null : null,
    error,
    jobId,
    timedOut,
    retry,
    reset,
  };
}
