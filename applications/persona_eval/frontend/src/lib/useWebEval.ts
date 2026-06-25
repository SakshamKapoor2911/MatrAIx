import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { getWebEvalJob, startWebEval } from "./api";
import type { JobStatus, PersonaModel, WebEvalJobView } from "./types";

const POLL_INTERVAL_MS = 1200;
const MAX_POLL_DURATION_MS = 15 * 60_000;

export interface RunWebEvalInput {
  personaId: string;
  taskId?: string;
  personaModel?: PersonaModel;
}

export type WebEvalRunPhase = JobStatus | "idle" | "timeout";

export interface UseWebEvalResult {
  run: (input: RunWebEvalInput) => void;
  job: WebEvalJobView | null;
  phase: WebEvalRunPhase;
  isRunning: boolean;
  error: string | null;
  timedOut: boolean;
  retry: () => void;
  reset: () => void;
}

export function useWebEval(): UseWebEvalResult {
  const [jobId, setJobId] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState(false);
  const [pollStartedAt, setPollStartedAt] = useState<number | null>(null);
  const lastInputRef = useRef<RunWebEvalInput | null>(null);

  const mutation = useMutation({
    mutationFn: (input: RunWebEvalInput) => startWebEval(input),
    onMutate: (input: RunWebEvalInput) => {
      setStartError(null);
      setTimedOut(false);
      lastInputRef.current = input;
    },
    onSuccess: (res) => {
      setJobId(res.jobId);
      setPollStartedAt(Date.now());
    },
    onError: (err: unknown) => {
      setStartError(err instanceof Error ? err.message : "Failed to start website test");
    },
  });

  const query = useQuery<WebEvalJobView>({
    queryKey: ["web-eval", jobId],
    queryFn: () => getWebEvalJob(jobId as string),
    enabled: jobId !== null && !timedOut,
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

  const job = jobId !== null ? query.data ?? null : null;
  const jobStatus = job?.status;

  useEffect(() => {
    if (jobId === null || pollStartedAt === null || timedOut) return;
    if (jobStatus === "done" || jobStatus === "error") return;
    const remaining = MAX_POLL_DURATION_MS - (Date.now() - pollStartedAt);
    const timer = setTimeout(() => setTimedOut(true), Math.max(0, remaining));
    return () => clearTimeout(timer);
  }, [jobId, pollStartedAt, timedOut, jobStatus]);

  useEffect(() => {
    if (jobStatus === "done" || jobStatus === "error") setPollStartedAt(null);
  }, [jobStatus]);

  let phase: WebEvalRunPhase = "idle";
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
    (timedOut ? "The website test is taking too long — the backend may be stuck." : null);

  const run = useCallback(
    (input: RunWebEvalInput) => {
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
