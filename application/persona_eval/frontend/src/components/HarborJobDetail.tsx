/**
 * Harbor batch job detail — reads ``jobs/<job>/<trial>/`` via the API.
 */
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { api, ApiError } from "@/lib/api";
import type { HarborJobDetail } from "@/lib/types";
import { HarborBatchMonitor } from "./HarborBatchMonitor";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";

export interface HarborJobDetailProps {
  jobName: string;
  onBack: () => void;
  onOpenTrial?: (trialName: string) => void;
  taskKind?: "chat" | "survey" | "web";
}

function trialStatusText(trial: HarborJobDetail["trials"][number]): string {
  if (trial.error) return "failed";
  if (trial.completed === false) return "running";
  if (trial.succeeded === false) return "failed";
  if (trial.completed) return "done";
  return "pending";
}

export function HarborJobDetail({
  jobName,
  onBack,
  onOpenTrial,
  taskKind = "chat",
}: HarborJobDetailProps) {
  const query = useQuery<HarborJobDetail>({
    queryKey: ["harbor-job", jobName],
    queryFn: () => api.getHarborJob(jobName),
    refetchInterval: (ctx) => {
      const launch = ctx.state.data?.launch;
      const trials = ctx.state.data?.trials ?? [];
      const pending = trials.some((trial) => !trial.completed);
      if (launch?.status === "running" || launch?.status === "queued" || pending) return 3000;
      return false;
    },
  });

  const job = query.data;
  const launch = job?.launch;
  const trials = job?.trials ?? [];
  const resolvedTaskKind = useMemo(() => {
    const config = job?.config as { task?: { path?: string }; tasks?: Array<{ path?: string }> } | null;
    const path = config?.task?.path ?? config?.tasks?.[0]?.path ?? "";
    const normalized = path.toLowerCase();
    if (normalized.includes("survey")) return "survey" as const;
    if (normalized.includes("web") || normalized.includes("browser")) return "web" as const;
    return taskKind;
  }, [job?.config, taskKind]);
  const showMonitor =
    launch?.status === "running" ||
    launch?.status === "queued" ||
    trials.some((trial) => !trial.completed) ||
    trials.length > 1;

  return (
    <div className="min-h-0 flex-1 overflow-auto bg-surface-dim custom-scrollbar">
      <div className="mx-auto w-full max-w-[1180px] px-6 py-7">
        <button
          type="button"
          onClick={onBack}
          className={`mb-4 flex items-center gap-1.5 rounded-md border border-outline bg-surface-low h-9 px-3 text-[12px] text-text-variant transition ease-out hover:border-primary hover:bg-surface hover:text-text-main ${FOCUS_RING}`}
        >
          <Sym name="arrow_back" size={16} />
          All jobs
        </button>

        <div className="mb-5 flex flex-wrap items-center gap-3">
          <div>
            <span className="hud text-[10px] text-primary">Harbor job</span>
            <h1 className="font-display text-[22px] font-bold tracking-tight text-text-main">
              {jobName}
            </h1>
          </div>
          {launch?.status && (
            <span className="rounded-md border border-outline bg-surface-low px-2.5 py-1 font-mono text-[11px] text-text-variant">
              {launch.status}
              {launch.exitCode != null ? ` · exit ${launch.exitCode}` : ""}
            </span>
          )}
          <button
            type="button"
            onClick={() => query.refetch()}
            disabled={query.isFetching}
            className={`ml-auto flex items-center gap-1.5 rounded-md border border-outline bg-surface-low h-9 px-3 text-[12px] text-text-variant ${FOCUS_RING}`}
          >
            <Sym name="refresh" size={16} className={query.isFetching ? "animate-rb-spin" : ""} />
            Refresh
          </button>
        </div>

        {query.isLoading ? (
          <p className="text-[13px] text-text-variant">Loading job…</p>
        ) : query.isError ? (
          <p className="text-[13px] text-danger">
            {query.error instanceof ApiError ? query.error.message : "Failed to load job."}
          </p>
        ) : (
          <>
            {launch?.error && (
              <div className="mb-4 rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-[13px] text-danger">
                {launch.error}
              </div>
            )}
            {launch?.configPath && (
              <p className="mb-4 font-mono text-[11px] text-text-variant">
                Config: {launch.configPath}
              </p>
            )}

            {showMonitor && (
              <div className="mb-6">
                <HarborBatchMonitor jobName={jobName} taskKind={resolvedTaskKind} />
              </div>
            )}

            <p className="mb-3 text-[13px] text-text-variant">
              {trials.length} trial{trials.length === 1 ? "" : "s"} in{" "}
              <span className="font-mono">{job?.jobsDir ?? "jobs/"}</span>
            </p>
            <div className="panel overflow-hidden rounded-md border border-outline bg-surface">
              <ul className="divide-y divide-outline-dim">
                {trials.length === 0 ? (
                  <li className="px-4 py-8 text-center text-[13px] text-text-variant">
                    {launch?.status === "running" || launch?.status === "queued"
                      ? "Harbor is running — trials will appear here as they start."
                      : "No trials yet."}
                  </li>
                ) : (
                  trials.map((trial) => (
                    <li key={trial.trialName}>
                      <button
                        type="button"
                        disabled={!onOpenTrial}
                        onClick={() => onOpenTrial?.(trial.trialName)}
                        className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-[13px] ${
                          onOpenTrial ? "hover:bg-surface-low" : ""
                        } ${FOCUS_RING}`}
                      >
                        <span className="font-mono text-text-main">{trial.trialName}</span>
                        <span
                          className={
                            trial.error || trial.succeeded === false
                              ? "text-danger"
                              : "text-text-variant"
                          }
                        >
                          {trialStatusText(trial)}
                        </span>
                      </button>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default HarborJobDetail;
