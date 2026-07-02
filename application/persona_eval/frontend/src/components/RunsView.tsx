/**
 * RunsView: Harbor job history inside PersonaEval.
 */
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { RunDetail } from "./RunDetail";
import { HarborJobDetail } from "./HarborJobDetail";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { fmtRunDate } from "./runsShared";
import { api, ApiError } from "@/lib/api";
import {
  deriveHarborJobListStatus,
  harborJobListStatusLabel,
} from "@/lib/trialStatus";
import type { HarborJobListStatus, HarborJobSummary } from "@/lib/types";

export interface RunsViewProps {
  harborJobId: string | null;
  harborTrialId: string | null;
  openHarborJob: (jobName: string) => void;
  openHarborTrial: (jobName: string, trialName: string) => void;
  backToList: () => void;
  backToHarborJob: () => void;
  onClose: () => void;
}

export function RunsView({
  harborJobId,
  harborTrialId,
  openHarborJob,
  openHarborTrial,
  backToList,
  backToHarborJob,
  onClose,
}: RunsViewProps) {
  if (harborJobId && harborTrialId) {
    return (
      <RunDetail
        harborTrial={{ jobName: harborJobId, trialName: harborTrialId }}
        onBack={backToHarborJob}
      />
    );
  }
  if (harborJobId) {
    return (
      <HarborJobDetail
        jobName={harborJobId}
        onBack={backToList}
        onOpenTrial={(trialName) => openHarborTrial(harborJobId, trialName)}
      />
    );
  }
  return <HarborJobsList openHarborJob={openHarborJob} onClose={onClose} />;
}

interface HarborJobsListProps {
  openHarborJob: (jobName: string) => void;
  onClose: () => void;
}

function sortHarborJobs(jobs: HarborJobSummary[]): HarborJobSummary[] {
  return [...jobs].sort((a, b) => {
    const ta = Date.parse(a.startedAt ?? a.updatedAt ?? "") || 0;
    const tb = Date.parse(b.startedAt ?? b.updatedAt ?? "") || 0;
    return tb - ta;
  });
}

function formatJobTimeFull(iso: string | null | undefined): string {
  if (!iso) return "";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return iso;
  return new Date(t).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

const JOB_STATUS_STYLES: Record<
  HarborJobListStatus,
  { className: string; icon: string; fill?: 0 | 1 }
> = {
  running: {
    className: "border-warn/40 bg-warn/10 text-warn",
    icon: "autorenew",
  },
  success: {
    className: "border-secondary/40 bg-secondary/10 text-secondary",
    icon: "check_circle",
    fill: 1,
  },
  failed: {
    className: "border-danger/40 bg-danger/10 text-danger",
    icon: "error",
    fill: 1,
  },
};

function HarborJobStatusBadge({ job }: { job: HarborJobSummary }) {
  const status = deriveHarborJobListStatus(job);
  const style = JOB_STATUS_STYLES[status];
  const label = harborJobListStatusLabel(status);
  const detail =
    status === "failed" && (job.failedTrials ?? 0) > 0
      ? `${label} · ${job.failedTrials} trial${job.failedTrials === 1 ? "" : "s"} failed`
      : label;

  return (
    <span
      className={`inline-flex max-w-full items-center gap-1 truncate rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide ${style.className}`}
      title={detail}
    >
      <Sym
        name={style.icon}
        size={12}
        fill={style.fill}
        className={status === "running" ? "shrink-0 animate-rb-spin" : "shrink-0"}
      />
      <span className="truncate">{label}</span>
    </span>
  );
}

function HarborJobsList({ openHarborJob, onClose }: HarborJobsListProps) {
  const queryClient = useQueryClient();
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const harborQuery = useQuery({
    queryKey: ["harbor-jobs"],
    queryFn: api.listHarborJobs,
    refetchInterval: 5000,
  });
  const harborJobs = useMemo(
    () => sortHarborJobs(harborQuery.data?.jobs ?? []),
    [harborQuery.data],
  );

  const deleteMutation = useMutation({
    mutationFn: (jobName: string) => api.deleteHarborJob(jobName),
    onSuccess: () => {
      setDeleteError(null);
      void queryClient.invalidateQueries({ queryKey: ["harbor-jobs"] });
    },
    onError: (error) => {
      setDeleteError(error instanceof ApiError ? error.message : "Could not delete job.");
    },
  });

  const handleDelete = (job: HarborJobSummary) => {
    const ok = window.confirm(
      `Delete "${job.jobName}"?\n\nThis removes the job folder under jobs/ and cannot be undone.`,
    );
    if (!ok) return;
    deleteMutation.mutate(job.jobName);
  };

  return (
    <div className="min-h-0 flex-1 overflow-auto bg-surface-dim custom-scrollbar">
      <div className="mx-auto w-full max-w-[1180px] px-6 py-7">
        <div className="mb-5 flex flex-wrap items-center gap-x-3 gap-y-2">
          <button
            type="button"
            onClick={onClose}
            className={`flex items-center gap-1.5 rounded-md border border-outline bg-surface-low h-9 px-3 text-[12px] text-text-variant transition ease-out hover:border-primary hover:bg-surface hover:text-text-main active:scale-[0.97] ${FOCUS_RING}`}
          >
            <Sym name="arrow_back" size={16} />
            Back to cockpit
          </button>
          <div className="flex flex-col">
            <span className="hud text-[10px] text-primary">PersonaEval · Runs</span>
            <h1 className="font-display text-[22px] font-bold tracking-tight text-text-main">Harbor jobs</h1>
          </div>
          {!harborQuery.isLoading && !harborQuery.isError && (
            <span className="font-mono text-[11px] text-text-variant">
              {harborJobs.length} job{harborJobs.length === 1 ? "" : "s"}
            </span>
          )}
          <button
            type="button"
            onClick={() => harborQuery.refetch()}
            disabled={harborQuery.isFetching}
            className={`ml-auto flex items-center gap-1.5 rounded-md border border-outline bg-surface-low h-9 px-3 text-[12px] text-text-variant transition ease-out hover:border-primary hover:bg-surface hover:text-text-main active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
          >
            <Sym name="refresh" size={16} className={harborQuery.isFetching ? "animate-rb-spin" : ""} />
            {harborQuery.isFetching ? "Refreshing…" : "Refresh"}
          </button>
          <p className="w-full max-w-2xl text-[13px] leading-relaxed text-text-variant">
            Batch runs and sign-off artifacts live under <span className="font-mono">jobs/</span>.
            Launch a job from the cockpit, then open a trial for the debrief.
          </p>
          {deleteError && (
            <p className="w-full text-[12px] text-danger" role="alert">
              {deleteError}
            </p>
          )}
        </div>

        {harborQuery.isLoading ? (
          <ListLoading />
        ) : harborQuery.isError ? (
          <ListError error={harborQuery.error} onRetry={() => harborQuery.refetch()} />
        ) : harborJobs.length === 0 ? (
          <ListEmpty onClose={onClose} />
        ) : (
          <HarborJobsTable
            jobs={harborJobs}
            onOpen={openHarborJob}
            onDelete={handleDelete}
            deletingJobName={deleteMutation.isPending ? deleteMutation.variables : null}
          />
        )}
      </div>
    </div>
  );
}

function HarborJobsTable({
  jobs,
  onOpen,
  onDelete,
  deletingJobName,
}: {
  jobs: HarborJobSummary[];
  onOpen: (jobName: string) => void;
  onDelete: (job: HarborJobSummary) => void;
  deletingJobName: string | null | undefined;
}) {
  return (
    <div className="panel overflow-hidden rounded-md border border-outline bg-surface rise-in">
      <div className="grid grid-cols-[minmax(0,1fr)_5.75rem_7rem_5.5rem_2.5rem] gap-3 border-b border-outline-dim px-3.5 py-2 text-[10px] uppercase tracking-wide text-text-dim">
        <span>Job</span>
        <span>Status</span>
        <span>Started</span>
        <span className="text-right">Trials</span>
        <span className="sr-only">Actions</span>
      </div>
      <ul className="divide-y divide-outline-dim">
        {jobs.map((job) => {
          const timeIso = job.startedAt ?? job.updatedAt;
          const deleting = deletingJobName === job.jobName;
          return (
            <li key={job.jobName} className="group">
              <div className="grid grid-cols-[minmax(0,1fr)_5.75rem_7rem_5.5rem_2.5rem] items-center gap-3 px-3.5 py-2.5">
                <button
                  type="button"
                  onClick={() => onOpen(job.jobName)}
                  className={`min-w-0 truncate text-left font-mono text-[13px] text-text-main hover:text-primary ${FOCUS_RING}`}
                >
                  {job.jobName}
                </button>
                <div className="min-w-0">
                  <HarborJobStatusBadge job={job} />
                </div>
                <button
                  type="button"
                  onClick={() => onOpen(job.jobName)}
                  title={formatJobTimeFull(timeIso)}
                  className={`text-left font-mono text-[11px] text-text-variant hover:text-text-main ${FOCUS_RING}`}
                >
                  {fmtRunDate(timeIso)}
                </button>
                <button
                  type="button"
                  onClick={() => onOpen(job.jobName)}
                  className={`text-right font-mono text-[11px] text-text-variant hover:text-text-main ${FOCUS_RING}`}
                >
                  {job.completedTrials ?? job.trialCount}/{job.trialCount}
                </button>
                <button
                  type="button"
                  aria-label={`Delete ${job.jobName}`}
                  disabled={deleting}
                  onClick={() => onDelete(job)}
                  className={`grid h-8 w-8 place-items-center rounded-md text-text-dim opacity-0 transition hover:bg-danger/10 hover:text-danger group-hover:opacity-100 disabled:opacity-40 ${FOCUS_RING}`}
                >
                  <Sym
                    name={deleting ? "autorenew" : "delete"}
                    size={16}
                    className={deleting ? "animate-rb-spin" : ""}
                  />
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function ListLoading() {
  return (
    <div className="overflow-hidden rounded-md border border-outline bg-surface" aria-hidden>
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="grid grid-cols-[minmax(0,1fr)_5.75rem_7rem_5.5rem_2.5rem] gap-3 border-b border-outline-dim px-3.5 py-3.5 last:border-b-0"
        >
          <div className="h-3.5 animate-rb-pulse rounded bg-surface-high" />
          <div className="h-3.5 animate-rb-pulse rounded bg-surface-high" />
          <div className="h-3.5 animate-rb-pulse rounded bg-surface-high" />
          <div className="ml-auto h-3.5 w-10 animate-rb-pulse rounded bg-surface-high" />
        </div>
      ))}
    </div>
  );
}

function ListEmpty({ onClose }: { onClose: () => void }) {
  return (
    <div className="rounded-md border border-dashed border-outline bg-surface px-6 py-14 text-center rise-in">
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-md border border-dashed border-outline bg-surface-high">
        <Sym name="history" size={26} className="text-text-dim" />
      </div>
      <h2 className="font-display text-[15px] font-semibold text-text-main">No Harbor jobs yet</h2>
      <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-text-variant">
        Launch a Harbor job from the cockpit to run personas in batch. Results appear here under{" "}
        <span className="font-mono">jobs/</span>.
      </p>
      <button
        type="button"
        onClick={onClose}
        className={`mt-4 inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-[12px] text-on-primary glow transition ease-out hover:bg-primary-dim active:scale-[0.97] ${FOCUS_RING}`}
      >
        <Sym name="play_arrow" fill={1} size={16} />
        Back to cockpit
      </button>
    </div>
  );
}

function ListError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message =
    error instanceof ApiError
      ? error.message
      : "Something went wrong loading Harbor jobs.";
  return (
    <div className="rounded-md border border-outline border-l-4 border-l-danger bg-surface px-5 py-8 text-center rise-in">
      <h2 className="font-display text-[15px] font-semibold text-text-main">Couldn&apos;t load jobs</h2>
      <p className="mx-auto mt-1.5 max-w-md break-words text-[13px] leading-relaxed text-text-variant">
        {message}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className={`mt-4 inline-flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-4 py-2 text-[12px] text-danger ${FOCUS_RING}`}
      >
        <Sym name="refresh" size={16} />
        Try again
      </button>
    </div>
  );
}

export default RunsView;
