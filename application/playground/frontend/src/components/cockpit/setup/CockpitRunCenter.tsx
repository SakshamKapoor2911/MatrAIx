import type { ReactNode } from "react";

import { BatchTrialGrid, harborTrialsToGridCells, type BatchTrialCell } from "./BatchTrialGrid";
import { BatchTrialStage } from "./BatchTrialStage";
import { CockpitLiveStage } from "./CockpitLiveStage";
import { RunLaunchBar, type RunLaunchPhase } from "./RunLaunchBar";

export interface CockpitRunCenterProps {
  showLive: boolean;
  pipeline: ReactNode;
  liveContent: ReactNode;
  batchJobName: string | null;
  batchCells: BatchTrialCell[];
  runLaunchPhase: RunLaunchPhase;
  progressPct: number;
  progressLabel?: string;
  progressSublabel?: string;
  canRun: boolean;
  isBatch: boolean;
  personaCount: number;
  parallelTrials: number;
  onParallelTrialsChange: (value: number) => void;
  runBusy: boolean;
  onRun: () => void;
  error?: string | null;
  onNewRun?: () => void;
  onViewJob?: () => void;
  onCancelRun?: () => void;
  cancelRunBusy?: boolean;
  onDownload?: () => void;
  canDownload?: boolean;
}

/** Center column: pipeline (idle) → live stage or batch grid (running) + progress launch bar. */
export function CockpitRunCenter({
  showLive,
  pipeline,
  liveContent,
  batchJobName,
  batchCells,
  runLaunchPhase,
  progressPct,
  progressLabel,
  progressSublabel,
  canRun,
  isBatch,
  personaCount,
  parallelTrials,
  onParallelTrialsChange,
  runBusy,
  onRun,
  error,
  onNewRun,
  onViewJob,
  onCancelRun,
  cancelRunBusy,
  onDownload,
  canDownload,
}: CockpitRunCenterProps) {
  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-2 overflow-hidden">
      {showLive ? (
        batchJobName ? (
          <BatchTrialStage>
            <BatchTrialGrid trials={batchCells} jobLabel={batchJobName} />
          </BatchTrialStage>
        ) : (
          <CockpitLiveStage className="h-0 min-h-0 flex-1">{liveContent}</CockpitLiveStage>
        )
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">{pipeline}</div>
      )}
      <RunLaunchBar
        canRun={canRun}
        isBatch={isBatch}
        personaCount={personaCount}
        parallelTrials={parallelTrials}
        onParallelTrialsChange={onParallelTrialsChange}
        isRunning={runBusy}
        onRun={onRun}
        error={error}
        runPhase={runLaunchPhase}
        progressPct={progressPct}
        progressLabel={progressLabel}
        progressSublabel={progressSublabel}
        onNewRun={onNewRun}
        onViewJob={onViewJob}
        onCancelRun={onCancelRun}
        cancelRunBusy={cancelRunBusy}
        onDownload={onDownload}
        canDownload={canDownload}
      />
    </div>
  );
}

export { harborTrialsToGridCells };
