/**
 * RunsView: Harbor job history inside PersonaEval.
 */
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { RunDetail } from "./RunDetail";
import { HarborJobDetail } from "./HarborJobDetail";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { AppTypeTag } from "./runsShared";
import {
  StudioGlassPanel,
  StudioMeshShell,
  StudioPageFrame,
  StudioPageHeader,
  StudioToolbarButton,
} from "./studio/StudioShell";
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
  backLabel?: string;
}

export function RunsView({
  harborJobId,
  harborTrialId,
  openHarborJob,
  openHarborTrial,
  backToList,
  backToHarborJob,
  onClose,
  backLabel = "Back",
}: RunsViewProps) {
  if (harborJobId && harborTrialId) {
    return (
      <StudioMeshShell>
        <RunDetail
          harborTrial={{ jobName: harborJobId, trialName: harborTrialId }}
          onBack={backToHarborJob}
        />
      </StudioMeshShell>
    );
  }
  if (harborJobId) {
    return (
      <StudioMeshShell>
        <HarborJobDetail
          jobName={harborJobId}
          onBack={backToList}
          onOpenTrial={(trialName) => openHarborTrial(harborJobId, trialName)}
        />
      </StudioMeshShell>
    );
  }
  return <HarborJobsList openHarborJob={openHarborJob} onClose={onClose} backLabel={backLabel} />;
}

interface HarborJobsListProps {
  openHarborJob: (jobName: string) => void;
  onClose: () => void;
  backLabel: string;
}

function sortHarborJobs(jobs: HarborJobSummary[]): HarborJobSummary[] {
  return [...jobs].sort((a, b) => {
    const ta = Date.parse(a.startedAt ?? a.updatedAt ?? "") || 0;
    const tb = Date.parse(b.startedAt ?? b.updatedAt ?? "") || 0;
    return tb - ta;
  });
}

function formatJobTimeFull(iso: string | null | undefined): string {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return iso;
  const date = new Date(t);
  const y = date.getFullYear();
  const mo = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  const h = String(date.getHours()).padStart(2, "0");
  const mi = String(date.getMinutes()).padStart(2, "0");
  const s = String(date.getSeconds()).padStart(2, "0");
  return `${y}-${mo}-${d} ${h}:${mi}:${s}`;
}

function harborJobAppType(job: HarborJobSummary): string {
  const explicit = (job.applicationType ?? "").toString().toLowerCase();
  if (explicit && explicit !== "unknown") return explicit;
  const name = job.jobName.toLowerCase();
  if (name.includes("survey")) return "survey";
  if (name.includes("web") || name.includes("playwright") || name.includes("cocoa")) return "web";
  if (name.includes("computer-use") || name.includes("os-app") || name.includes("cua")) return "os-app";
  if (name.includes("appworld")) return "os-app";
  return "chatbot";
}

/** Shared column template for the Harbor jobs table (header + rows + skeleton). */
const HARBOR_JOBS_GRID =
  "grid grid-cols-[minmax(0,1fr)_5.75rem_9.75rem_3.75rem_minmax(5.5rem,6.25rem)_2.25rem] items-center gap-x-5";

type AppTypeFilter = "all" | "chatbot" | "survey" | "web" | "os-app";
type StatusFilter = "all" | HarborJobListStatus;

const APP_TYPE_FILTER_OPTIONS: { value: Exclude<AppTypeFilter, "all">; label: string }[] = [
  { value: "chatbot", label: "Chatbot" },
  { value: "survey", label: "Survey" },
  { value: "web", label: "Web" },
  { value: "os-app", label: "OS app" },
];

const STATUS_FILTER_OPTIONS: { value: Exclude<StatusFilter, "all">; label: string }[] = [
  { value: "running", label: "Running" },
  { value: "success", label: "Success" },
  { value: "failed", label: "Failed" },
];

function harborJobSearchHaystack(job: HarborJobSummary): string {
  const status = deriveHarborJobListStatus(job);
  const timeIso = job.startedAt ?? job.updatedAt;
  return [
    job.jobName,
    harborJobAppType(job),
    harborJobListStatusLabel(status),
    formatJobTimeFull(timeIso),
    `${job.completedTrials ?? job.trialCount}/${job.trialCount}`,
  ]
    .join(" ")
    .toLowerCase();
}

function filterHarborJobs(
  jobs: HarborJobSummary[],
  {
    searchQuery,
    appTypeFilter,
    statusFilter,
  }: {
    searchQuery: string;
    appTypeFilter: AppTypeFilter;
    statusFilter: StatusFilter;
  },
): HarborJobSummary[] {
  const q = searchQuery.trim().toLowerCase();
  return jobs.filter((job) => {
    if (appTypeFilter !== "all" && harborJobAppType(job) !== appTypeFilter) return false;
    if (statusFilter !== "all" && deriveHarborJobListStatus(job) !== statusFilter) return false;
    if (!q) return true;
    return harborJobSearchHaystack(job).includes(q);
  });
}

function runsFiltersActive(
  searchQuery: string,
  appTypeFilter: AppTypeFilter,
  statusFilter: StatusFilter,
): boolean {
  return searchQuery.trim() !== "" || appTypeFilter !== "all" || statusFilter !== "all";
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

function HarborJobsList({ openHarborJob, onClose, backLabel }: HarborJobsListProps) {
  const queryClient = useQueryClient();
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [appTypeFilter, setAppTypeFilter] = useState<AppTypeFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const harborQuery = useQuery({
    queryKey: ["harbor-jobs"],
    queryFn: api.listHarborJobs,
    refetchInterval: 5000,
  });
  const harborJobs = useMemo(
    () => sortHarborJobs(harborQuery.data?.jobs ?? []),
    [harborQuery.data],
  );
  const filteredJobs = useMemo(
    () =>
      filterHarborJobs(harborJobs, {
        searchQuery,
        appTypeFilter,
        statusFilter,
      }),
    [harborJobs, searchQuery, appTypeFilter, statusFilter],
  );
  const filtersActive = runsFiltersActive(searchQuery, appTypeFilter, statusFilter);

  const clearFilters = () => {
    setSearchQuery("");
    setAppTypeFilter("all");
    setStatusFilter("all");
  };

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
    <StudioMeshShell>
      <StudioPageFrame>
        <StudioPageHeader
          compact
          eyebrow="MatrAIx · Runs"
          title="Runs"
          subtitle={
            <>
              Harbor jobs in <span className="font-mono">jobs/</span> — launch from PersonaEval, debrief
              trials here.
            </>
          }
          meta={
            !harborQuery.isLoading && !harborQuery.isError ? (
              <span className="font-mono text-[11px] text-text-variant">
                {filtersActive
                  ? `${filteredJobs.length} of ${harborJobs.length}`
                  : harborJobs.length}{" "}
                job{harborJobs.length === 1 ? "" : "s"}
              </span>
            ) : null
          }
          actions={
            <>
              <StudioToolbarButton icon="arrow_back" onClick={onClose}>
                {backLabel}
              </StudioToolbarButton>
              <StudioToolbarButton
                icon="refresh"
                onClick={() => harborQuery.refetch()}
                disabled={harborQuery.isFetching}
              >
                {harborQuery.isFetching ? "Refreshing…" : "Refresh"}
              </StudioToolbarButton>
            </>
          }
        />
        {deleteError && (
          <p className="mb-4 text-[12px] text-danger" role="alert">
            {deleteError}
          </p>
        )}

        {harborQuery.isLoading ? (
          <ListLoading />
        ) : harborQuery.isError ? (
          <ListError error={harborQuery.error} onRetry={() => harborQuery.refetch()} />
        ) : harborJobs.length === 0 ? (
          <ListEmpty onClose={onClose} />
        ) : (
          <>
            <HarborJobsFilterBar
              searchQuery={searchQuery}
              onSearchQueryChange={setSearchQuery}
              appTypeFilter={appTypeFilter}
              onAppTypeFilterChange={setAppTypeFilter}
              statusFilter={statusFilter}
              onStatusFilterChange={setStatusFilter}
              onClearFilters={clearFilters}
              filtersActive={filtersActive}
            />
            {filteredJobs.length === 0 ? (
              <ListFilterEmpty onClearFilters={clearFilters} />
            ) : (
              <HarborJobsTable
                jobs={filteredJobs}
                onOpen={openHarborJob}
                onDelete={handleDelete}
                deletingJobName={deleteMutation.isPending ? deleteMutation.variables : null}
              />
            )}
          </>
        )}
      </StudioPageFrame>
    </StudioMeshShell>
  );
}

function HarborJobsFilterBar({
  searchQuery,
  onSearchQueryChange,
  appTypeFilter,
  onAppTypeFilterChange,
  statusFilter,
  onStatusFilterChange,
  onClearFilters,
  filtersActive,
}: {
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  appTypeFilter: AppTypeFilter;
  onAppTypeFilterChange: (value: AppTypeFilter) => void;
  statusFilter: StatusFilter;
  onStatusFilterChange: (value: StatusFilter) => void;
  onClearFilters: () => void;
  filtersActive: boolean;
}) {
  return (
    <StudioGlassPanel className="mb-3 p-3">
      <div className="flex h-8 min-w-0 items-center rounded-lg border border-outline/50 bg-surface/60 backdrop-blur transition-colors focus-within:border-primary/50">
        <Sym name="search" size={16} className="ml-3 flex-none text-text-dim" />
        <input
          type="search"
          value={searchQuery}
          onChange={(e) => onSearchQueryChange(e.target.value)}
          placeholder="Search by job name, app type, or status…"
          aria-label="Search runs"
          className="h-full w-full min-w-0 bg-transparent px-3 text-[13px] text-text-main outline-none placeholder:text-text-variant"
        />
        {searchQuery && (
          <button
            type="button"
            onClick={() => onSearchQueryChange("")}
            aria-label="Clear search"
            className={`mr-2 flex-none rounded p-1 text-text-dim transition-colors hover:bg-surface-high hover:text-text-main ${FOCUS_RING}`}
          >
            <Sym name="close" size={16} />
          </button>
        )}
      </div>

      <div className="mt-2.5 flex flex-col gap-2 border-t border-outline/20 pt-2.5 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3">
          <span className="cockpit-field-label shrink-0 text-[10px] text-text-dim">App type</span>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by app type">
            <RunsFilterChip
              label="All"
              active={appTypeFilter === "all"}
              onClick={() => onAppTypeFilterChange("all")}
            />
            {APP_TYPE_FILTER_OPTIONS.map((option) => (
              <RunsFilterChip
                key={option.value}
                label={option.label}
                active={appTypeFilter === option.value}
                onClick={() => onAppTypeFilterChange(option.value)}
              />
            ))}
          </div>
        </div>

        <div className="flex min-w-0 flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3 lg:pl-4">
          <span className="hidden h-6 w-px bg-outline/30 sm:block" aria-hidden />
          <span className="cockpit-field-label shrink-0 text-[10px] text-text-dim">Status</span>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by status">
            <RunsFilterChip
              label="All"
              active={statusFilter === "all"}
              onClick={() => onStatusFilterChange("all")}
            />
            {STATUS_FILTER_OPTIONS.map((option) => (
              <RunsFilterChip
                key={option.value}
                label={option.label}
                active={statusFilter === option.value}
                onClick={() => onStatusFilterChange(option.value)}
              />
            ))}
          </div>
        </div>
      </div>

      {filtersActive && (
        <div className="mt-3 flex justify-end border-t border-outline/20 pt-3">
          <button
            type="button"
            onClick={onClearFilters}
            className={`inline-flex h-8 items-center gap-1.5 rounded-md border border-outline/50 bg-surface/50 px-3 text-[11px] font-medium text-text-variant transition-colors hover:border-primary/40 hover:text-text-main ${FOCUS_RING}`}
          >
            <Sym name="filter_alt_off" size={15} />
            Clear filters
          </button>
        </div>
      )}
    </StudioGlassPanel>
  );
}

function RunsFilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`inline-flex h-8 items-center rounded-full border px-2.5 text-[11px] font-medium transition-colors ${FOCUS_RING} ${
        active
          ? "border-primary bg-primary text-on-primary active:bg-primary-dim"
          : "border-outline bg-surface text-text-variant hover:border-primary hover:bg-surface-low hover:text-text-main active:bg-surface-high"
      }`}
    >
      {label}
    </button>
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
    <StudioGlassPanel className="rounded-xl">
      <div
        className={`${HARBOR_JOBS_GRID} border-b border-outline/40 px-4 py-2.5 text-[10px] uppercase tracking-wide text-text-dim`}
      >
        <span>Job</span>
        <span>App type</span>
        <span>Started</span>
        <span className="text-right">Trials</span>
        <span className="justify-self-end">Status</span>
        <span className="sr-only">Actions</span>
      </div>
      <ul className="divide-y divide-outline-dim">
        {jobs.map((job) => {
          const timeIso = job.startedAt ?? job.updatedAt;
          const deleting = deletingJobName === job.jobName;
          return (
            <li key={job.jobName} className="group">
              <div className={`${HARBOR_JOBS_GRID} px-4 py-3`}>
                <button
                  type="button"
                  onClick={() => onOpen(job.jobName)}
                  className={`min-w-0 truncate text-left font-mono text-[13px] text-text-main hover:text-primary ${FOCUS_RING}`}
                  title={job.jobName}
                >
                  {job.jobName}
                </button>
                <div className="min-w-0">
                  <AppTypeTag type={harborJobAppType(job)} />
                </div>
                <button
                  type="button"
                  onClick={() => onOpen(job.jobName)}
                  title={timeIso ?? undefined}
                  className={`whitespace-nowrap text-left font-mono text-[11px] tabular-nums text-text-variant hover:text-text-main ${FOCUS_RING}`}
                >
                  {formatJobTimeFull(timeIso)}
                </button>
                <button
                  type="button"
                  onClick={() => onOpen(job.jobName)}
                  className={`text-right font-mono text-[11px] tabular-nums text-text-variant hover:text-text-main ${FOCUS_RING}`}
                >
                  {job.completedTrials ?? job.trialCount}/{job.trialCount}
                </button>
                <div className="min-w-0 justify-self-end">
                  <HarborJobStatusBadge job={job} />
                </div>
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
    </StudioGlassPanel>
  );
}

function ListLoading() {
  return (
    <StudioGlassPanel className="rounded-xl" aria-hidden>
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className={`${HARBOR_JOBS_GRID} border-b border-outline-dim px-4 py-3.5 last:border-b-0`}
        >
          <div className="h-3.5 animate-rb-pulse rounded bg-surface-high" />
          <div className="h-3.5 w-14 animate-rb-pulse rounded bg-surface-high" />
          <div className="h-3.5 animate-rb-pulse rounded bg-surface-high" />
          <div className="ml-auto h-3.5 w-8 animate-rb-pulse rounded bg-surface-high" />
          <div className="ml-auto h-3.5 w-16 animate-rb-pulse rounded bg-surface-high" />
        </div>
      ))}
    </StudioGlassPanel>
  );
}

function ListFilterEmpty({ onClearFilters }: { onClearFilters: () => void }) {
  return (
    <StudioGlassPanel className="px-6 py-12 text-center rise-in">
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-md border border-dashed border-outline bg-surface-high">
        <Sym name="search_off" size={24} className="text-text-dim" />
      </div>
      <h2 className="font-display text-[15px] font-semibold text-text-main">No matching runs</h2>
      <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-text-variant">
        Try a different search term or clear the app type and status filters.
      </p>
      <button
        type="button"
        onClick={onClearFilters}
        className={`mt-4 inline-flex items-center gap-1.5 rounded-md border border-outline/50 bg-surface/60 px-4 py-2 text-[12px] text-text-variant transition hover:border-primary/40 hover:text-text-main ${FOCUS_RING}`}
      >
        <Sym name="filter_alt_off" size={16} />
        Clear filters
      </button>
    </StudioGlassPanel>
  );
}

function ListEmpty({ onClose }: { onClose: () => void }) {
  return (
    <StudioGlassPanel className="px-6 py-14 text-center rise-in">
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-md border border-dashed border-outline bg-surface-high">
        <Sym name="history" size={26} className="text-text-dim" />
      </div>
      <h2 className="font-display text-[15px] font-semibold text-text-main">No runs yet</h2>
      <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-text-variant">
        Launch a batch from PersonaEval to run personas at scale. Results appear here under{" "}
        <span className="font-mono">jobs/</span>.
      </p>
      <button
        type="button"
        onClick={onClose}
        className={`mt-4 inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-[12px] text-on-primary glow transition ease-out hover:bg-primary-dim active:scale-[0.97] ${FOCUS_RING}`}
      >
        <Sym name="play_arrow" fill={1} size={16} />
        Back to home
      </button>
    </StudioGlassPanel>
  );
}

function ListError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message =
    error instanceof ApiError
      ? error.message
      : "Something went wrong loading runs.";
  return (
    <StudioGlassPanel className="border-l-4 border-l-danger px-5 py-8 text-center rise-in">
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
    </StudioGlassPanel>
  );
}

export default RunsView;
