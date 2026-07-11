/** Coarse Harbor trial lifecycle stages shown in batch grids. */
export type TrialLifecycleStage =
  | "queued"
  | "starting_env"
  | "agent_running"
  | "verifying";

const STAGE_LABELS: Record<TrialLifecycleStage, string> = {
  queued: "Queued",
  starting_env: "Starting env",
  agent_running: "Agent running",
  verifying: "Verifying",
};

const PHASE_TO_STAGE: Record<string, TrialLifecycleStage> = {
  harbor_starting: "starting_env",
  harbor_running: "agent_running",
  trial_running: "agent_running",
  // Legacy event phase names (pre-Harbor unify). Per Xiaoming & Yuexing: no external
  // BenchFlow branding in user-facing copy — prefer neutral stages or MatrAIx/Harbor terms.
  benchflow_starting: "starting_env",
  persona_kickoff: "agent_running",
  recommender_thinking: "agent_running",
  persona_thinking: "agent_running",
  web_simulating: "agent_running",
  survey_answering: "agent_running",
  appworld_simulating: "agent_running",
  benchflow_running: "agent_running",
  harbor_collecting_artifacts: "verifying",
  benchflow_collecting: "verifying",
  persona_feedback: "verifying",
};

export function formatTrialStageLabel(
  stage?: string | null,
  phase?: string | null,
): string | null {
  if (stage && stage in STAGE_LABELS) {
    return STAGE_LABELS[stage as TrialLifecycleStage];
  }
  const mapped = phase ? PHASE_TO_STAGE[phase] : undefined;
  if (mapped) return STAGE_LABELS[mapped];
  if (phase) return phase.replace(/^harbor_/, "").replace(/_/g, " ");
  return null;
}

export function formatBatchCellStatusLabel(
  status: "pending" | "running" | "done" | "error",
  stage?: string | null,
  phase?: string | null,
): string {
  if (status === "pending") return "Queued";
  if (status === "done") return "Done";
  if (status === "error") return "Failed";
  return formatTrialStageLabel(stage, phase) ?? "Running";
}

/** Resolve a Harbor job list row status (API field with jobResult fallback). */
export function deriveHarborJobListStatus(
  job: {
    status?: string | null;
    trialCount?: number;
    completedTrials?: number;
    jobResult?: Record<string, unknown> | null;
  },
): "running" | "success" | "failed" {
  const explicit = (job.status ?? "").toLowerCase();
  if (explicit === "success" || explicit === "failed" || explicit === "running") {
    return explicit;
  }

  const result = job.jobResult;
  if (result && typeof result === "object" && result.finished_at) {
    const stats = result.stats as { n_errored_trials?: number } | undefined;
    const errors = Number(stats?.n_errored_trials ?? 0);
    return errors > 0 ? "failed" : "success";
  }

  const trialCount = job.trialCount ?? 0;
  const completed = job.completedTrials ?? 0;
  if (trialCount > 0 && completed < trialCount) return "running";
  return "running";
}

const HARBOR_JOB_STATUS_LABEL: Record<"running" | "success" | "failed", string> = {
  running: "Running",
  success: "Success",
  failed: "Failed",
};

export function harborJobListStatusLabel(status: "running" | "success" | "failed"): string {
  return HARBOR_JOB_STATUS_LABEL[status];
}
