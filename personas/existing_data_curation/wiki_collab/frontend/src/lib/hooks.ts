/**
 * React Query wiring for the cockpit.
 *
 * `useAppState` is the single source of truth for the GET /api/state payload;
 * every workflow mutation invalidates ["state"] on success so the lineage rail,
 * control strip, dossier and inspectors all refresh from one fetch.
 *
 * `useDimensions` is the static 1339-dim catalog. It may 404 on older backends
 * that predate GET /api/dimensions — React Query surfaces that as `isError`,
 * which the DimensionsPanel renders as an explanatory empty state rather than
 * crashing.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UseMutationResult } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  AppState,
  AssignmentRequest,
  AssignmentResponse,
  AuditResponse,
  DimensionCatalog,
  MergeResponse,
  ReturnResponse,
  RunRequest,
  RunResponse,
} from "@/lib/types";

export const STATE_KEY = ["state"] as const;
export const DIMENSIONS_KEY = ["dimensions"] as const;

/** The GET /api/state query — drives almost every panel. */
export function useAppState() {
  return useQuery<AppState>({
    queryKey: STATE_KEY,
    queryFn: api.getState,
  });
}

/** The static dimension catalog; tolerates a 404 (surfaced as `isError`). */
export function useDimensions() {
  return useQuery<DimensionCatalog>({
    queryKey: DIMENSIONS_KEY,
    queryFn: api.getDimensions,
    staleTime: Infinity,
    retry: false,
  });
}

/** The set of workflow actions a button can trigger. */
export type ActionKey = "package" | "run" | "return" | "audit" | "merge" | "reset";

export interface ActionBundle {
  package: UseMutationResult<AssignmentResponse, unknown, AssignmentRequest>;
  run: UseMutationResult<RunResponse, unknown, RunRequest>;
  return: UseMutationResult<ReturnResponse, unknown, void>;
  audit: UseMutationResult<AuditResponse, unknown, void>;
  merge: UseMutationResult<MergeResponse, unknown, void>;
  reset: UseMutationResult<{ ok: boolean }, unknown, void>;
  /** Which action (if any) is currently in flight. */
  pendingKey: ActionKey | null;
}

/**
 * Per-action mutations. Each invalidates ["state"] on success so the whole
 * cockpit re-derives from one refetch. `pendingKey` lets a button show its own
 * spinner while every other button stays idle.
 */
export function useAction(): ActionBundle {
  const qc = useQueryClient();
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: STATE_KEY });
  };

  const pkg = useMutation<AssignmentResponse, unknown, AssignmentRequest>({
    mutationFn: (body) => api.createAssignment(body),
    onSuccess: invalidate,
  });
  const run = useMutation<RunResponse, unknown, RunRequest>({
    mutationFn: (body) => api.runAssignment(body),
    onSuccess: invalidate,
  });
  const ret = useMutation<ReturnResponse, unknown, void>({
    mutationFn: () => api.returnArchive(),
    onSuccess: invalidate,
  });
  const audit = useMutation<AuditResponse, unknown, void>({
    mutationFn: () => api.auditArchives(),
    onSuccess: invalidate,
  });
  const merge = useMutation<MergeResponse, unknown, void>({
    mutationFn: () => api.mergeArchives(),
    onSuccess: invalidate,
  });
  const reset = useMutation<{ ok: boolean }, unknown, void>({
    mutationFn: () => api.resetOutputs(),
    onSuccess: invalidate,
  });

  const entries: Array<[ActionKey, { isPending: boolean }]> = [
    ["package", pkg],
    ["run", run],
    ["return", ret],
    ["audit", audit],
    ["merge", merge],
    ["reset", reset],
  ];
  const pendingKey = entries.find(([, m]) => m.isPending)?.[0] ?? null;

  return {
    package: pkg,
    run,
    return: ret,
    audit,
    merge,
    reset,
    pendingKey,
  };
}
