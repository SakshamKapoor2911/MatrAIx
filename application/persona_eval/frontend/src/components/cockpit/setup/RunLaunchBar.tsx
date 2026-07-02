import { FOCUS_RING, Sym } from "../cockpitShared";

export type RunLaunchPhase = "idle" | "launching" | "running" | "done" | "error";

export interface RunLaunchBarProps {
  canRun: boolean;
  isBatch: boolean;
  personaCount: number;
  parallelTrials: number;
  onParallelTrialsChange: (value: number) => void;
  isRunning: boolean;
  onRun: () => void;
  error?: string | null;
  /** When set, replaces the run button with a progress bar. */
  runPhase?: RunLaunchPhase;
  progressPct?: number;
  progressLabel?: string;
  progressSublabel?: string;
  onNewRun?: () => void;
  onViewJob?: () => void;
  onDownload?: () => void;
  canDownload?: boolean;
}

export function RunLaunchBar({
  canRun,
  isBatch,
  personaCount,
  parallelTrials,
  onParallelTrialsChange,
  isRunning,
  onRun,
  error,
  runPhase = "idle",
  progressPct = 0,
  progressLabel,
  progressSublabel,
  onNewRun,
  onViewJob,
  onDownload,
  canDownload = false,
}: RunLaunchBarProps) {
  const active = runPhase !== "idle";
  const failed = runPhase === "error";
  const done = runPhase === "done";
  const pct = Math.max(0, Math.min(100, progressPct));

  return (
    <div className="glass-panel-strong w-full shrink-0 rounded-xl border border-primary/20 px-4 py-3 sm:px-5">
      {error && (
        <p className="mb-2 w-full rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-[11px] text-danger">
          {error}
        </p>
      )}

      {active ? (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            {failed ? (
              <Sym name="error" fill={1} size={18} className="shrink-0 text-danger" />
            ) : done ? (
              <Sym name="check_circle" fill={1} size={18} className="shrink-0 text-secondary" />
            ) : (
              <Sym name="autorenew" size={18} className="shrink-0 animate-rb-spin text-primary" />
            )}
            <span className="min-w-0 flex-1 text-[12px] text-text-variant">
              {progressLabel ?? (isBatch ? "Harbor batch job" : "Running simulation")}
            </span>
            {onDownload && (done || failed) && (
              <button
                type="button"
                onClick={onDownload}
                disabled={!canDownload}
                className={`shrink-0 rounded-md border border-outline bg-surface-low px-3 py-1.5 text-[11px] font-medium text-text-variant transition hover:border-primary disabled:opacity-50 ${FOCUS_RING}`}
              >
                Download
              </button>
            )}
            {onViewJob && done && (
              <button
                type="button"
                onClick={onViewJob}
                className={`shrink-0 rounded-md border border-primary/40 bg-primary/10 px-3 py-1.5 text-[11px] font-medium text-primary transition hover:bg-primary/20 ${FOCUS_RING}`}
              >
                View job
              </button>
            )}
            {onNewRun && (done || failed) && (
              <button
                type="button"
                onClick={onNewRun}
                className={`shrink-0 rounded-md border border-outline bg-surface-low px-3 py-1.5 text-[11px] font-medium text-text-variant transition hover:border-primary hover:text-text-main ${FOCUS_RING}`}
              >
                Reset
              </button>
            )}
          </div>
          {progressSublabel && <p className="text-[10px] text-text-dim">{progressSublabel}</p>}
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-field">
            <div
              className={`h-full rounded-full transition-[width] duration-500 ${
                failed ? "bg-danger" : done ? "bg-secondary" : "bg-primary"
              } ${runPhase === "launching" ? "animate-pulse" : ""}`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      ) : (
        <>
          <div className="flex w-full flex-wrap items-center justify-center gap-3">
            <button
              type="button"
              disabled={!canRun || isRunning}
              onClick={onRun}
              className={`glow inline-flex min-w-[200px] items-center justify-center gap-2 rounded-lg bg-primary px-6 py-3.5 font-display text-[16px] font-bold text-on-primary transition hover:bg-primary-dim disabled:cursor-not-allowed disabled:opacity-50 ${FOCUS_RING}`}
            >
              <Sym name={isBatch ? "rocket_launch" : "play_arrow"} fill={1} size={22} />
              {isRunning ? "Launching…" : isBatch ? `Run batch (${personaCount})` : "Run simulation"}
            </button>
            {isBatch && (
              <label className="flex min-w-[180px] flex-col gap-1.5 text-[10px] text-text-variant">
                <div className="flex items-center justify-between">
                  <span>Parallel trials</span>
                  <span className="font-mono text-[11px] text-text-main">{parallelTrials}</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={Math.min(8, personaCount)}
                  value={parallelTrials}
                  onChange={(e) => onParallelTrialsChange(Number(e.target.value))}
                  className="accent-primary"
                />
              </label>
            )}
          </div>
          <p className="mt-2 text-center text-[10px] text-text-dim">
            {isBatch
              ? "Trials appear in the center — status lights update as each finishes."
              : "Live updates appear in the center frame."}
          </p>
        </>
      )}
    </div>
  );
}
