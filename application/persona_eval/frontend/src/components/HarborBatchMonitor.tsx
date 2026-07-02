/**
 * Batch Harbor job monitor — persona cards (left), live events (center), task card (right).
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useHarborBatchLive } from "@/lib/useHarborBatchLive";
import { formatTrialStageLabel } from "@/lib/trialStatus";
import type { HarborJobLiveTrial } from "@/lib/types";
import { Trajectory } from "./cockpit/Trajectory";
import { Markdown } from "./Markdown";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { buildSurveyInstructionMarkdown } from "@/lib/surveyInstruction";
import type { SurveyInstrument } from "@/lib/types";

export interface HarborBatchMonitorProps {
  jobName: string;
  taskKind?: "chat" | "survey" | "web";
  surveyInstrument?: SurveyInstrument | null;
  sutLabel?: string;
  sutDescription?: string | null;
}

function trialStatusLabel(trial: HarborJobLiveTrial): string {
  if (trial.error) return "Failed";
  if (trial.completed && trial.succeeded === false) return "Failed";
  if (trial.completed) return "Done";
  return formatTrialStageLabel(trial.stage, trial.phase) ?? "Running";
}

function trialTone(trial: HarborJobLiveTrial, selected: boolean): string {
  if (selected) return "border-primary bg-primary/10";
  if (trial.error || trial.succeeded === false) return "border-danger/40 bg-danger/5";
  if (trial.completed) return "border-secondary/30 bg-secondary/5";
  return "border-outline bg-surface-low hover:border-primary/40";
}

export function HarborBatchMonitor({
  jobName,
  taskKind = "chat",
  surveyInstrument = null,
  sutLabel = "Application",
  sutDescription = null,
}: HarborBatchMonitorProps) {
  const { live, selectedTrial, selectTrial, selectedLive, error, isActive } =
    useHarborBatchLive(jobName);

  const instructionMarkdown = useMemo(() => {
    if (selectedLive?.instructionMarkdown) return selectedLive.instructionMarkdown;
    if (taskKind === "survey" && surveyInstrument) {
      return buildSurveyInstructionMarkdown(surveyInstrument);
    }
    return null;
  }, [selectedLive?.instructionMarkdown, surveyInstrument, taskKind]);

  const debriefQuery = useQuery({
    queryKey: ["harbor-trial-debrief", jobName, selectedTrial],
    queryFn: () => api.getHarborTrialDebrief(jobName, selectedTrial!),
    enabled: Boolean(
      selectedTrial && live?.trials.find((t) => t.trialName === selectedTrial)?.completed,
    ),
    staleTime: 30_000,
  });

  const turns = selectedLive?.turns ?? [];
  const surveyAnswers =
    (debriefQuery.data?.surveyResult as { answers?: unknown[] } | undefined)?.answers ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <span className="hud text-[10px] text-primary">Live monitor</span>
          <p className="text-[13px] text-text-variant">
            {live?.completedTrials ?? 0}/{live?.trialCount ?? 0} trials finished
            {isActive ? " · polling events" : ""}
          </p>
        </div>
        {live?.launchStatus && (
          <span className="rounded-md border border-outline bg-surface-low px-2 py-1 font-mono text-[11px] text-text-variant">
            {live.launchStatus}
          </span>
        )}
      </div>

      {error && (
        <div className="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-[13px] text-danger">
          {error}
        </div>
      )}

      <div className="grid min-h-[420px] grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Left: persona / trial cards */}
        <div className="space-y-2 lg:col-span-3">
          <p className="hud text-[9px] text-text-dim">Personas</p>
          {(live?.trials ?? []).length === 0 ? (
            <p className="text-[12px] text-text-variant">Waiting for trials to start…</p>
          ) : (
            live?.trials.map((trial) => (
              <button
                key={trial.trialName}
                type="button"
                onClick={() => selectTrial(trial.trialName)}
                className={`w-full rounded-md border px-3 py-3 text-left transition ${trialTone(
                  trial,
                  selectedTrial === trial.trialName,
                )} ${FOCUS_RING}`}
              >
                <p className="text-[13px] font-semibold text-text-main">
                  {trial.personaName ?? trial.personaId ?? trial.trialName}
                </p>
                <p className="mt-0.5 font-mono text-[10px] text-text-dim">{trial.trialName}</p>
                <p className="mt-1 text-[11px] text-text-variant">{trialStatusLabel(trial)}</p>
              </button>
            ))
          )}
        </div>

        {/* Center: live stream */}
        <div className="flex min-h-[360px] flex-col overflow-hidden rounded-md border border-outline bg-surface-lowest lg:col-span-6">
          {taskKind === "chat" ? (
            <Trajectory
              turns={turns}
              draftTurn={selectedLive?.draftTurn ?? null}
              livePhase={selectedLive?.phase ?? null}
              domain="movie"
              appName={sutLabel}
              sutDescription={sutDescription}
              goalContext={null}
              phase={isActive ? "running" : "done"}
              liveStatus={
                selectedLive?.phase
                  ? `Phase: ${selectedLive.phase.replace(/_/g, " ")}`
                  : isActive
                    ? "Waiting for turns…"
                    : null
              }
              error={
                (selectedTrial &&
                  live?.trials.find((t) => t.trialName === selectedTrial)?.error) ??
                null
              }
              expandedTurns={new Set(turns.map((_, i) => i))}
              onToggleTurn={() => undefined}
              focusedTurnIndex={turns.length > 0 ? turns.length - 1 : null}
              registerTurnRef={() => undefined}
              onRetry={() => undefined}
            />
          ) : taskKind === "survey" ? (
            <div className="custom-scrollbar flex-1 overflow-y-auto p-5">
              {surveyAnswers.length > 0 ? (
                <div className="space-y-3">
                  <p className="text-[12px] font-semibold text-text-main">Answers</p>
                  {surveyAnswers.map((answer, index) => (
                    <div
                      key={index}
                      className="rounded-md border border-outline bg-surface-low px-3 py-2 text-[12px]"
                    >
                      <pre className="whitespace-pre-wrap text-text-variant">
                        {JSON.stringify(answer, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              ) : instructionMarkdown ? (
                <div className="prose-sm max-w-none text-[13px] text-text-main">
                  <Markdown>{instructionMarkdown}</Markdown>
                </div>
              ) : (
                <p className="text-[13px] text-text-variant">Select a trial to review the questionnaire.</p>
              )}
            </div>
          ) : (
            <div className="flex flex-1 items-center justify-center p-6 text-[13px] text-text-variant">
              Live events for this task type are not wired yet.
            </div>
          )}
        </div>

        {/* Right: SUT / survey card */}
        <div className="space-y-3 lg:col-span-3">
          <p className="hud text-[9px] text-text-dim">{taskKind === "survey" ? "Survey" : "SUT"}</p>
          <div className="rounded-md border border-outline bg-surface-low p-4">
            <p className="text-[14px] font-semibold text-text-main">
              {taskKind === "survey"
                ? surveyInstrument?.title ?? "Questionnaire"
                : sutLabel}
            </p>
            <p className="mt-2 text-[12px] leading-relaxed text-text-variant">
              {taskKind === "survey"
                ? surveyInstrument?.description ??
                  `${surveyInstrument?.questions.length ?? 0} questions`
                : sutDescription ?? "System under test for this Harbor batch."}
            </p>
            {taskKind === "survey" && surveyInstrument && (
              <ul className="mt-3 space-y-1 text-[11px] text-text-dim">
                {surveyInstrument.questions.slice(0, 4).map((q) => (
                  <li key={q.id} className="truncate">
                    · {q.prompt}
                  </li>
                ))}
                {surveyInstrument.questions.length > 4 && (
                  <li>· +{surveyInstrument.questions.length - 4} more</li>
                )}
              </ul>
            )}
          </div>
          {selectedTrial && (
            <div className="rounded-md border border-outline-dim bg-surface-high px-3 py-2 text-[11px] text-text-variant">
              <Sym name="visibility" size={14} className="mr-1 inline text-primary" />
              Watching <span className="font-mono">{selectedTrial}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default HarborBatchMonitor;
