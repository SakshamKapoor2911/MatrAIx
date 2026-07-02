import { Sym } from "../cockpitShared";
import { formatBatchCellStatusLabel } from "@/lib/trialStatus";

export type BatchTrialStatus = "pending" | "running" | "done" | "error";

export interface BatchTrialCell {
  id: string;
  label: string;
  status: BatchTrialStatus;
  statusLabel?: string;
}

const STATUS_STYLES: Record<BatchTrialStatus, { ring: string; dot: string; glow?: string }> = {
  pending: { ring: "border-outline/50 bg-surface/40", dot: "bg-text-dim/40" },
  running: {
    ring: "border-amber-400/60 bg-amber-400/10",
    dot: "bg-amber-400 animate-pulse",
    glow: "shadow-[0_0_12px_-2px_rgb(251_191_36/0.55)]",
  },
  done: {
    ring: "border-secondary/50 bg-secondary/10",
    dot: "bg-secondary",
    glow: "shadow-[0_0_12px_-2px_rgb(var(--secondary)/0.45)]",
  },
  error: {
    ring: "border-danger/50 bg-danger/10",
    dot: "bg-danger",
    glow: "shadow-[0_0_12px_-2px_rgb(var(--danger)/0.45)]",
  },
};

export interface BatchTrialGridProps {
  trials: BatchTrialCell[];
  jobLabel?: string;
  className?: string;
}

function gridColumns(count: number): number {
  if (count <= 1) return 1;
  if (count <= 4) return 2;
  if (count <= 9) return 3;
  return Math.ceil(Math.sqrt(count));
}

/** Evenly distributed trial status lights for Harbor batch jobs. */
export function BatchTrialGrid({ trials, jobLabel, className = "" }: BatchTrialGridProps) {
  const done = trials.filter((t) => t.status === "done").length;
  const running = trials.filter((t) => t.status === "running").length;
  const pending = trials.filter((t) => t.status === "pending").length;
  const failed = trials.filter((t) => t.status === "error").length;
  const runningLabels = [
    ...new Set(
      trials
        .filter((t) => t.status === "running")
        .map((t) => t.statusLabel ?? "Running"),
    ),
  ];
  const cols = gridColumns(trials.length);

  return (
    <div className={`flex h-full min-h-0 flex-col ${className}`}>
      <div className="mb-3 flex shrink-0 items-center justify-between gap-2">
        <div>
          <p className="hud text-[10px] text-primary">Harbor batch</p>
          <h2 className="font-display text-[18px] font-bold tracking-tight text-text-main">
            {jobLabel ?? `${trials.length} trials`}
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[10px] text-text-dim">
          {pending > 0 && (
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-text-dim/50" />
              {pending} queued
            </span>
          )}
          {running > 0 && (
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
              {running} running
              {runningLabels.length > 0 && (
                <span className="text-text-dim">· {runningLabels.join(", ")}</span>
              )}
            </span>
          )}
          {done > 0 && (
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-secondary" />
              {done} done
            </span>
          )}
          {failed > 0 && (
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-danger" />
              {failed} failed
            </span>
          )}
        </div>
      </div>

      <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto">
        <div
          className="grid gap-3"
          style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
        >
          {trials.map((trial, index) => {
            const style = STATUS_STYLES[trial.status];
            return (
              <div
                key={trial.id}
                className={`rise-in flex aspect-square min-h-[88px] flex-col items-center justify-center gap-2 rounded-xl border px-2 py-3 text-center transition-all duration-500 ${style.ring} ${style.glow ?? ""}`}
                style={{ animationDelay: `${Math.min(index, 12) * 40}ms` }}
              >
                <span className={`h-3 w-3 rounded-full ${style.dot}`} />
                <span className="max-w-full truncate font-mono text-[10px] text-text-variant" title={trial.label}>
                  {trial.label}
                </span>
                <span
                  className={`text-[9px] uppercase tracking-wide ${
                    trial.status === "done"
                      ? "text-secondary"
                      : trial.status === "error"
                        ? "text-danger"
                        : trial.status === "running"
                          ? "text-amber-500"
                          : "text-text-dim"
                  }`}
                >
                  {trial.statusLabel ??
                    (trial.status === "pending"
                      ? "Queued"
                      : trial.status === "done"
                        ? "Done"
                        : trial.status === "error"
                          ? "Failed"
                          : "Running")}
                </span>
                {trial.status === "running" && (
                  <Sym name="autorenew" size={14} className="animate-rb-spin text-amber-400" />
                )}
                {trial.status === "done" && (
                  <Sym name="check_circle" size={14} className="text-secondary" fill={1} />
                )}
                {trial.status === "error" && <Sym name="error" size={14} className="text-danger" fill={1} />}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

type HarborTrialRow = {
  trialName: string;
  completed?: boolean;
  succeeded?: boolean | null;
  error?: string | null;
  phase?: string | null;
  stage?: string | null;
};

/** One grid cell per persona — all slots visible from job start. */
export function buildBatchGridCells(
  personaIds: string[],
  harborTrials: HarborTrialRow[] | undefined,
  opts: { jobStarted?: boolean; parallelTrials?: number } = {},
): BatchTrialCell[] {
  const { jobStarted = false, parallelTrials = 1 } = opts;
  if (personaIds.length === 0) return [];

  const completedCount = harborTrials?.filter((trial) => trial.completed).length ?? 0;

  return personaIds.map((personaId, index) => {
    const trial = harborTrials?.[index];
    let status: BatchTrialStatus = "pending";

    if (trial?.completed) {
      status = trial.succeeded === false || trial.error ? "error" : "done";
    } else if (!jobStarted) {
      status = "pending";
    } else if (index >= completedCount && index < completedCount + parallelTrials) {
      status = "running";
    }

    return {
      id: trial?.trialName ?? `persona-${personaId}`,
      label: `persona-${personaId}`,
      status,
      statusLabel: formatBatchCellStatusLabel(
        status,
        trial?.stage ?? (status === "running" ? "starting_env" : null),
        trial?.phase,
      ),
    };
  });
}

/** @deprecated Use buildBatchGridCells — keeps old call sites working. */
export function harborTrialsToGridCells(
  trials: HarborTrialRow[],
  personaIds?: string[],
  jobStarted = true,
): BatchTrialCell[] {
  const ids =
    personaIds && personaIds.length >= trials.length
      ? personaIds
      : trials.map((trial, index) => personaIds?.[index] ?? trial.trialName);
  return buildBatchGridCells(ids, trials, { jobStarted, parallelTrials: trials.length });
}
