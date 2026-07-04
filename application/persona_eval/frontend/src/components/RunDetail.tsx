/**
 * RunDetail: one persisted run, rebuilt as the mockup's "Run debrief".
 *
 * Shape mirrors `data-view="runs"` (app-redesign-v3.html:340-429): a back link +
 * "Run debrief" H1 with a run-type reflection on the right, a one-line run-meta
 * breadcrumb, a headline score band + metric tiles, then the body.
 *
 * Option-aware, honestly scoped (spec §05): the debrief renders the stored
 * application artifact shape: chatbot, survey, web, or OS app.
 */
import { useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  StatTile,
  AppTypeTag,
  appName,
  asRunDetail,
  fmtDomain,
  fmtRunDate,
  runApplicationType,
  runWebTrace,
  type RunApplicationType,
  type RunDetailView,
} from "./runsShared";
import { ChatTrialDebriefBody } from "./ChatTrialDebrief";
import { TrialDebriefRails } from "./TrialDebriefRails";
import { HarborTraceReplay } from "./cockpit/HarborTraceReplay";
import { OsAppEvalScorecard } from "./cockpit/TaskEvalScorecard";
import {
  StudioGlassPanel,
  StudioPageFrame,
  StudioPageHeader,
  StudioToolbarButton,
} from "./studio/StudioShell";
import { FOCUS_RING, SCORE_BAND_CLASS, Sym, humanizeToken, scoreBand } from "./cockpit/cockpitShared";
import { api, ApiError } from "@/lib/api";
import type {
  PersonaEvalResult,
  OsAppResult,
  SurveyAnswer,
  SurveyQuestion,
  SurveyTrajectoryEvent,
  UserFeedbackArtifact,
} from "@/lib/types";

export interface RunDetailProps {
  harborTrial: { jobName: string; trialName: string };
  onBack: () => void;
}

function runDebriefMetaLine(run: RunDetailView, appType: RunApplicationType): string {
  const persona = run.persona?.name ? `persona “${run.persona.name}”` : "";
  const personaPart = persona ? ` · ${persona}` : "";
  const when = fmtRunDate(
    run.surveyResult?.createdAt ??
      run.webResult?.createdAt ??
      run.createdAt,
  );
  if (appType === "survey" && run.surveyResult) {
    const label =
      run.surveyResult.instrument.title || run.instrumentTitle || run.surveyResult.instrument.id;
    return `${label}${personaPart} · ${when}`;
  }
  if (appType === "web" && run.webResult) {
    const task = run.taskTitle || run.siteName || "website task";
    const site = run.siteName ? ` on ${run.siteName}` : "";
    return `${task}${site}${personaPart} · ${when}`;
  }
  if (appType === "os-app") {
    const task = run.taskTitle || "OS app task";
    return `${task}${personaPart} · ${when}`;
  }
  const app = appName(run.config?.applicationId);
  const domain = run.config?.domain ? ` · ${fmtDomain(run.config.domain)} catalog` : "";
  return `${app}${domain}${personaPart} · ${when}`;
}

export function RunDetail({ harborTrial, onBack }: RunDetailProps) {
  const query = useQuery<PersonaEvalResult>({
    queryKey: ["harbor-trial-debrief", harborTrial.jobName, harborTrial.trialName],
    queryFn: () => api.getHarborTrialDebrief(harborTrial.jobName, harborTrial.trialName),
  });

  const run = useMemo(() => (query.data ? asRunDetail(query.data) : null), [query.data]);
  const appType: RunApplicationType = run ? runApplicationType(run) : "chatbot";
  const metaLine = run ? runDebriefMetaLine(run, appType) : null;
  const subtitleText = metaLine ? `Job ${harborTrial.jobName} · ${metaLine}` : `Job ${harborTrial.jobName}`;

  return (
    <StudioPageFrame>
      <StudioPageHeader
        compact
        eyebrow="MatrAIx · Runs"
        title={harborTrial.trialName}
        subtitle={
          <span className="font-mono text-[11px] text-text-variant" title={subtitleText}>
            {subtitleText}
          </span>
        }
        meta={run ? <AppTypeTag type={appType} /> : null}
        actions={
          <>
            <StudioToolbarButton icon="arrow_back" onClick={onBack}>
              Back to job
            </StudioToolbarButton>
            <StudioToolbarButton
              icon="refresh"
              onClick={() => query.refetch()}
              disabled={query.isFetching}
            >
              Refresh
            </StudioToolbarButton>
          </>
        }
      />

      {query.isLoading ? (
        <DetailLoading />
      ) : query.isError ? (
        <DetailError error={query.error} onRetry={() => query.refetch()} />
      ) : !run ? (
        <DetailNotFound />
      ) : (
        <>
          {appType === "survey" ? (
            <SurveyDebrief run={run} />
          ) : appType === "web" ? (
            <WebDebrief run={run} />
          ) : appType === "os-app" ? (
            <OsAppDebrief run={run} />
          ) : (
            <ChatbotDebrief run={run} />
          )}
        </>
      )}
    </StudioPageFrame>
  );
}

// ---------------------------------------------------------------------------
// Shared chrome
// ---------------------------------------------------------------------------

function DebriefPanel({
  title,
  icon,
  children,
  className = "",
  bodyClassName = "",
}: {
  title?: string;
  icon?: string;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <StudioGlassPanel className={`overflow-hidden ${className}`}>
      {title ? (
        <div className="flex items-center gap-2 border-b border-outline/40 px-4 py-2.5 text-[10px] font-medium uppercase tracking-wide text-text-dim">
          {icon ? <Sym name={icon} size={14} className="text-primary" /> : null}
          {title}
        </div>
      ) : null}
      <div className={bodyClassName}>{children}</div>
    </StudioGlassPanel>
  );
}

function TrialDebriefChrome({
  prompts,
  persona,
  instructionMarkdown,
  contextMarkdown,
  questionnaireMarkdown,
  outputSchemaMarkdown,
  children,
}: {
  prompts?: RunDetailView["prompts"];
  persona?: RunDetailView["persona"];
  instructionMarkdown?: RunDetailView["instructionMarkdown"];
  contextMarkdown?: RunDetailView["contextMarkdown"];
  questionnaireMarkdown?: RunDetailView["questionnaireMarkdown"];
  outputSchemaMarkdown?: RunDetailView["outputSchemaMarkdown"];
  children: ReactNode;
}) {
  const rails = (
    <TrialDebriefRails
      prompts={prompts}
      persona={persona ?? null}
      instructionMarkdown={instructionMarkdown ?? null}
      contextMarkdown={contextMarkdown ?? null}
      questionnaireMarkdown={questionnaireMarkdown ?? null}
      outputSchemaMarkdown={outputSchemaMarkdown ?? null}
    />
  );

  return (
    <div className="space-y-5">
      {rails ? (
        <StudioGlassPanel className="divide-y divide-outline/40 overflow-hidden">{rails}</StudioGlassPanel>
      ) : null}
      {children}
    </div>
  );
}

/** A quiet dashed "nothing here" note, reused by empty bodies. */
function DashedNote({ children }: { children: ReactNode }) {
  return (
    <div className="px-4 py-10 text-center text-[13px] text-text-variant">{children}</div>
  );
}

/** A mint/danger validity badge (survey "Valid"/web "Valid pick"). */
function ValidityBadge({
  valid,
  validLabel,
  invalidLabel,
}: {
  valid: boolean;
  validLabel: string;
  invalidLabel: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-1 hud text-[9px] ${
        valid
          ? "border-secondary/30 bg-secondary/10 text-secondary"
          : "border-danger/30 bg-danger/10 text-danger"
      }`}
    >
      {valid ? validLabel : invalidLabel}
    </span>
  );
}

function humanizeFeedbackKey(key: string): string {
  const snake = key.replace(/([a-z0-9])([A-Z])/g, "$1_$2");
  return humanizeToken(snake);
}

function feedbackDisplayValue(value: unknown): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value;
  return "-";
}

function feedbackNumericValue(
  feedback: UserFeedbackArtifact | null | undefined,
  key: string,
): number | null {
  const value = feedback?.[key];
  return typeof value === "number" ? value : null;
}

function feedbackTextValue(
  feedback: UserFeedbackArtifact | null | undefined,
  key: string,
): string {
  const value = feedback?.[key];
  return typeof value === "string" ? value : "";
}

function feedbackBooleanValue(
  feedback: UserFeedbackArtifact | null | undefined,
  key: string,
): boolean | null {
  const value = feedback?.[key];
  return typeof value === "boolean" ? value : null;
}

function trialEvaluationFeedback(run: RunDetailView): UserFeedbackArtifact | null {
  const context =
    run.trialEvaluation?.contexts.find(
      (item) => item.contextType === "user_feedback" || item.contextType === "feedback",
    ) ?? null;
  if (!context) return null;
  const payload: UserFeedbackArtifact = {};
  for (const facet of context.facets) {
    const value = facet.value;
    if (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean" ||
      value === null
    ) {
      payload[facet.key] = value;
    }
  }
  return Object.keys(payload).length > 0 ? payload : null;
}

function resolveUserFeedback(run: RunDetailView): UserFeedbackArtifact | null {
  return run.userFeedback ?? trialEvaluationFeedback(run);
}

function UserFeedbackPanel({
  feedback,
}: {
  feedback: UserFeedbackArtifact | null | undefined;
}) {
  const overall = feedbackNumericValue(feedback, "overallExperienceRating");
  const trust = feedbackNumericValue(feedback, "trustLevel");
  const effort = feedbackNumericValue(feedback, "effortRating");
  const clarity = feedbackNumericValue(feedback, "clarityOfNextStep");
  const feltUnderstood = feedbackBooleanValue(feedback, "feltUnderstood");
  const reason = feedbackTextValue(feedback, "reason");
  const extraEntries = Object.entries(feedback ?? {})
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .filter(
      ([key]) =>
        ![
          "overallExperienceRating",
          "trustLevel",
          "effortRating",
          "clarityOfNextStep",
          "feltUnderstood",
          "reason",
        ].includes(key),
    );

  return (
    <DebriefPanel title="Persona self-report" icon="rate_review" bodyClassName="p-4">
      {!feedback || Object.keys(feedback).length === 0 ? (
        <DashedNote>
          No post-run self-report was recorded. This section appears when the task writes{" "}
          <span className="font-mono text-[11px]">user_feedback.json</span>.
        </DashedNote>
      ) : (
        <div className="space-y-4">
          <p className="text-[11px] leading-relaxed text-text-variant">
            Subjective reflection captured after task completion from{" "}
            <span className="font-mono">user_feedback.json</span>.
          </p>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {overall != null ? (
              <StatTile
                lead
                caption="Overall experience"
                value={overall}
                unit="/10"
                band={scoreBand(overall / 10)}
              />
            ) : null}
            {trust != null ? <StatTile caption="Trust" value={trust} unit="/10" /> : null}
            {effort != null ? <StatTile caption="Effort" value={effort} /> : null}
            {clarity != null ? <StatTile caption="Next step clarity" value={clarity} /> : null}
            {feltUnderstood != null ? (
              <div className="flex flex-col justify-center rounded-lg border border-outline/40 bg-surface/40 p-4 backdrop-blur-sm">
                <span className="hud text-[9px] text-text-dim">Felt understood</span>
                <div className="mt-1.5">
                  <ValidityBadge
                    valid={feltUnderstood}
                    validLabel="Yes"
                    invalidLabel="Not really"
                  />
                </div>
              </div>
            ) : null}
          </div>

          {reason ? (
            <div className="rounded-lg border border-outline/40 bg-surface/40 p-4 text-[12px] leading-relaxed text-text-variant">
              <span className="font-medium text-text-main">Why:</span> {reason}
            </div>
          ) : null}

          {extraEntries.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {extraEntries.map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-lg border border-outline/40 bg-surface/40 p-3 backdrop-blur-sm"
                >
                  <div className="text-[10px] uppercase tracking-wide text-text-dim">
                    {humanizeFeedbackKey(key)}
                  </div>
                  <div className="mt-1.5 text-[13px] leading-relaxed text-text-main">
                    {feedbackDisplayValue(value)}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </DebriefPanel>
  );
}

// ===========================================================================
// Chatbot debrief
// ===========================================================================

function ChatbotDebrief({ run }: { run: RunDetailView }) {
  const persona = run.persona ?? {};
  const config = run.config ?? {};

  return (
    <TrialDebriefChrome
      prompts={run.prompts}
      persona={persona}
      instructionMarkdown={run.instructionMarkdown}
      contextMarkdown={run.contextMarkdown}
      questionnaireMarkdown={run.questionnaireMarkdown}
      outputSchemaMarkdown={run.outputSchemaMarkdown}
    >
      <ChatTrialDebriefBody
        config={config}
        transcript={run.transcript ?? []}
        persona={run.persona}
        questionnaire={run.questionnaire}
        metricScores={run.metricScores}
        verifier={run.verifier}
        trialEvaluation={run.trialEvaluation}
      />
    </TrialDebriefChrome>
  );
}

// ===========================================================================
// Survey debrief: reads `SurveyResult` (types.ts)
// ===========================================================================

function SurveyDebrief({ run }: { run: RunDetailView }) {
  const survey = run.surveyResult;
  const persona = run.persona ?? {};
  if (!survey) {
    return (
      <TrialDebriefChrome
        prompts={run.prompts}
        persona={persona}
        instructionMarkdown={run.instructionMarkdown}
        contextMarkdown={run.contextMarkdown}
        questionnaireMarkdown={run.questionnaireMarkdown}
        outputSchemaMarkdown={run.outputSchemaMarkdown}
      >
        <DashedNote>No survey results were recorded for this run.</DashedNote>
      </TrialDebriefChrome>
    );
  }

  const c = survey.completion;
  const questionsById = new Map<string, SurveyQuestion>(
    survey.instrument.questions.map((qq) => [qq.id, qq]),
  );
  const freeTextCount = survey.answers.filter((a) => {
    const q = questionsById.get(a.questionId);
    return q?.type === "free_text";
  }).length;
  const likertQuestionCount = survey.instrument.questions.filter((q) => q.type === "likert").length;
  const meanBand = c.meanLikert == null ? undefined : scoreBand(c.meanLikert / 5);

  return (
    <TrialDebriefChrome
      prompts={run.prompts}
      persona={persona}
      instructionMarkdown={run.instructionMarkdown}
      contextMarkdown={run.contextMarkdown}
      questionnaireMarkdown={run.questionnaireMarkdown}
      outputSchemaMarkdown={run.outputSchemaMarkdown}
    >
      <DebriefPanel bodyClassName="p-4">
        <div
          className={`grid gap-4 ${
            likertQuestionCount > 0 ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-2 sm:grid-cols-3"
          }`}
        >
          <StatTile lead caption="Questions answered" value={`${c.numAnswered}/${c.numQuestions}`} />
          <div className="flex flex-col justify-center rounded-lg border border-outline/40 bg-surface/40 p-4 backdrop-blur-sm">
            <span className="hud text-[9px] text-text-dim">Answers look valid</span>
            <div className="mt-1.5">
              <ValidityBadge valid={c.valid} validLabel="Valid" invalidLabel="Needs review" />
            </div>
          </div>
          {likertQuestionCount > 0 ? (
            <StatTile
              caption="Mean Likert score"
              value={c.meanLikert == null ? "n/a" : c.meanLikert.toFixed(1)}
              unit="/5"
              band={meanBand}
            />
          ) : null}
          <StatTile caption="Written answers" value={freeTextCount} />
        </div>
      </DebriefPanel>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <DebriefPanel title="Answers" icon="fact_check" className="lg:col-span-7">
          {survey.answers.length === 0 ? (
            <DashedNote>No answers were recorded for this survey run.</DashedNote>
          ) : (
            <ul className="divide-y divide-outline-dim">
              {survey.answers.map((a, i) => (
                <SurveyAnswerRow
                  key={a.questionId}
                  answer={a}
                  question={questionsById.get(a.questionId)}
                  index={i}
                />
              ))}
            </ul>
          )}
        </DebriefPanel>

        <DebriefPanel title="Trajectory" icon="route" className="lg:col-span-5">
          {survey.trajectory.length === 0 ? (
            <DashedNote>No trajectory was recorded for this run.</DashedNote>
          ) : (
            <div className="custom-scrollbar max-h-[min(70vh,520px)] space-y-2 overflow-y-auto p-4 font-mono text-[11px] leading-relaxed">
              {survey.trajectory.map((e, i) => (
                <SurveyTrajectoryRow key={`${e.timestamp}-${i}`} event={e} />
              ))}
            </div>
          )}
        </DebriefPanel>
      </div>
    </TrialDebriefChrome>
  );
}

/** One survey answer row: prompt + a type-aware value + rationale/confidence. */
function SurveyAnswerRow({
  answer,
  question,
  index,
}: {
  answer: SurveyAnswer;
  question: SurveyQuestion | undefined;
  index: number;
}) {
  const type = question?.type;
  const prompt = question?.prompt ?? answer.questionId;
  const conf = answer.confidence;
  const valueText = fmtAnswerValue(answer.value, question);
  const freeText = type === "free_text";
  const likert = type === "likert";
  const singleChoice = type === "single_choice";
  const max = question?.maxValue ?? 5;
  const numeric = Number(answer.value);
  const band = likert && Number.isFinite(numeric) ? scoreBand(numeric / (max || 5)) : "none";
  const color = SCORE_BAND_CLASS[band];

  return (
    <li
      className="px-4 py-3.5 rise-in hover:bg-surface/30"
      style={{ animationDelay: `${Math.min(index, 6) * 30}ms`, animationFillMode: "backwards" }}
    >
      <div className="mb-1.5 flex items-start justify-between gap-3">
        <span className="text-[12px] font-medium leading-snug text-text-main">
          Q{index + 1} · {prompt}
        </span>
        {freeText ? (
          <span className="shrink-0 hud text-[8px] text-text-dim">Free text</span>
        ) : likert ? (
          <span className={`shrink-0 font-mono text-[12px] font-bold tabular-nums ${color.text}`}>
            {valueText} / {max}
          </span>
        ) : (
          <span className="shrink-0 max-w-[45%] truncate rounded border border-outline/40 bg-surface/60 px-2 py-0.5 text-right font-mono text-[10px] text-text-variant">
            {valueText}
          </span>
        )}
      </div>
      {freeText ? (
        <p className="text-[11px] leading-relaxed text-text-variant">&ldquo;{valueText}&rdquo;</p>
      ) : answer.rationale ? (
        <p className="rounded-lg border border-outline/30 bg-surface/35 px-3 py-2 text-[11px] leading-relaxed text-text-variant">
          {singleChoice || likert ? "Why: " : ""}
          {answer.rationale}
          {conf != null && (
            <span className="text-text-dim"> · How sure: {(conf * 100).toFixed(0)}%</span>
          )}
        </p>
      ) : conf != null ? (
        <p className="text-[11px] text-text-variant">How sure: {(conf * 100).toFixed(0)}%</p>
      ) : null}
    </li>
  );
}

/** One survey trajectory event: time · action · actor (submit highlighted). */
function SurveyTrajectoryRow({ event }: { event: SurveyTrajectoryEvent }) {
  const submit = event.action.toLowerCase().includes("submit");
  return (
    <div className="flex gap-2.5">
      <span className="shrink-0 text-text-dim">{event.timestamp}</span>
      <span className={submit ? "font-bold text-secondary" : "text-primary"}>{event.action}</span>
      <span className="truncate text-text-variant">{trajectoryActor(event.actor)}</span>
    </div>
  );
}

function fmtAnswerValue(value: unknown, question?: SurveyQuestion): string {
  const optionLabel = (raw: unknown): string => {
    const id = String(raw);
    const detail = question?.optionDetails?.find((option) => option.id === id);
    return detail?.label ? `${detail.label} (${id})` : id;
  };
  if (question?.type === "single_choice") return optionLabel(value);
  if (question?.type === "multi_choice" && Array.isArray(value)) return value.map(optionLabel).join(", ");
  if (Array.isArray(value)) return value.map((item) => String(item)).join(", ");
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function trajectoryActor(actor: string): string {
  const value = actor.toLowerCase();
  if (value === "agent") return "Simulated user";
  if (value === "system") return "System";
  if (value === "scorer") return "Scorer";
  return humanizeToken(actor);
}

// ===========================================================================
// Web debrief: reads `WebResult` + `WebTrace` (types.ts)
// ===========================================================================

function WebDebrief({ run }: { run: RunDetailView }) {
  const result = run.webResult;
  const persona = run.persona ?? {};
  const trace = runWebTrace(run);
  const events = trace?.events ?? [];
  const feedback = resolveUserFeedback(run);

  if (!result) {
    return (
      <TrialDebriefChrome
        prompts={run.prompts}
        persona={persona}
        instructionMarkdown={run.instructionMarkdown}
        contextMarkdown={run.contextMarkdown}
        questionnaireMarkdown={run.questionnaireMarkdown}
        outputSchemaMarkdown={run.outputSchemaMarkdown}
      >
        <DebriefPanel>
          <DashedNote>No web result was recorded for this run.</DashedNote>
        </DebriefPanel>
      </TrialDebriefChrome>
    );
  }

  return (
    <TrialDebriefChrome
      prompts={run.prompts}
      persona={persona}
      instructionMarkdown={run.instructionMarkdown}
      contextMarkdown={run.contextMarkdown}
      questionnaireMarkdown={run.questionnaireMarkdown}
      outputSchemaMarkdown={run.outputSchemaMarkdown}
    >
      <DebriefPanel bodyClassName="p-4">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:col-span-5">
            <StatTile
              lead
              caption="Met the persona's need"
              value={result.needSatisfaction}
              unit="/10"
              band={scoreBand(result.needSatisfaction / 10)}
            />
            <StatTile
              caption="Ease of use"
              value={result.easeOfUse}
              unit="/10"
              band={scoreBand(result.easeOfUse / 10)}
            />
            <StatTile
              caption="Overall experience"
              value={result.overallExperienceRating}
              unit="/10"
              band={scoreBand(result.overallExperienceRating / 10)}
            />
          </div>

          <div className="flex items-center gap-4 rounded-lg border border-outline/40 bg-surface/40 p-4 backdrop-blur-sm lg:col-span-7">
            <div
              className="grid h-12 w-12 shrink-0 place-items-center rounded-lg border border-outline/40 bg-surface-high/80"
              aria-hidden
            >
              <Sym name="inventory_2" size={22} className="text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[14px] font-semibold text-text-main">
                  {result.selectedProductName || "(no product chosen)"}
                </span>
                <ValidityBadge valid={result.valid} validLabel="Valid pick" invalidLabel="Invalid pick" />
              </div>
              {result.selectedProductId && (
                <div className="mt-0.5 font-mono text-[10px] text-text-dim">{result.selectedProductId}</div>
              )}
              {result.reason && (
                <p className="mt-1 text-[11px] leading-snug text-text-variant">
                  Why this one: {result.reason}
                </p>
              )}
            </div>
          </div>
        </div>
      </DebriefPanel>

      <UserFeedbackPanel feedback={feedback} />

      <DebriefPanel
        title={`Browser trace · ${events.length} step${events.length === 1 ? "" : "s"}`}
        icon="route"
      >
        {!trace || events.length === 0 ? (
          <DashedNote>No browser steps were captured for this run.</DashedNote>
        ) : (
          <div className="p-4">
            <HarborTraceReplay trace={trace} />
          </div>
        )}
      </DebriefPanel>
    </TrialDebriefChrome>
  );
}

// ===========================================================================
// OS app debrief
// ===========================================================================

function OsAppDebrief({ run }: { run: RunDetailView }) {
  const runRecord = run as Record<string, unknown>;
  const osAppResult = (runRecord.osAppResult as OsAppResult | null | undefined) ?? null;
  const trace = runRecord.osAppTrace as { events?: unknown[] } | null | undefined;
  const feedback = resolveUserFeedback(run);

  return (
    <TrialDebriefChrome
      prompts={run.prompts}
      persona={run.persona}
      instructionMarkdown={run.instructionMarkdown}
      contextMarkdown={run.contextMarkdown}
      questionnaireMarkdown={run.questionnaireMarkdown}
      outputSchemaMarkdown={run.outputSchemaMarkdown}
    >
      <DebriefPanel title="Evaluation" icon="verified" bodyClassName="p-4">
        <OsAppEvalScorecard
          osAppResult={osAppResult}
          verifier={run.verifier ?? null}
          traceStepCount={trace?.events?.length ?? 0}
          phase="done"
        />
      </DebriefPanel>
      <UserFeedbackPanel feedback={feedback} />
    </TrialDebriefChrome>
  );
}

// ===========================================================================
// States
// ===========================================================================

function DetailLoading() {
  return (
    <div className="space-y-5" aria-hidden>
      <div className="glass-panel h-14 animate-rb-pulse rounded-xl" />
      <div className="glass-panel h-28 animate-rb-pulse rounded-xl" />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div className="glass-panel h-80 animate-rb-pulse rounded-xl lg:col-span-7" />
        <div className="glass-panel h-80 animate-rb-pulse rounded-xl lg:col-span-5" />
      </div>
    </div>
  );
}

function DetailNotFound() {
  return (
    <StudioGlassPanel className="px-6 py-14 text-center rise-in">
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-md border border-dashed border-outline bg-surface-high">
        <Sym name="search_off" size={26} className="text-text-dim" />
      </div>
      <h2 className="font-display text-[15px] font-semibold text-text-main">
        We couldn&apos;t find this run
      </h2>
      <p className="mx-auto mt-2 max-w-sm text-[13px] leading-relaxed text-text-variant">
        It may have been deleted. Go back to the list to pick another.
      </p>
    </StudioGlassPanel>
  );
}

function DetailError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const notFound = error instanceof ApiError && error.status === 404;
  if (notFound) return <DetailNotFound />;
  const message =
    error instanceof ApiError
      ? error.message
      : "Something went wrong loading the details. Try again in a moment.";
  return (
    <StudioGlassPanel className="border-l-4 border-l-danger px-5 py-8 text-center rise-in">
      <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-md border border-danger/30 bg-danger/10">
        <Sym name="error" fill={1} size={22} className="text-danger" />
      </div>
      <h2 className="font-display text-[15px] font-semibold text-text-main">
        We couldn&apos;t open this run
      </h2>
      <p className="mx-auto mt-1.5 max-w-md break-words text-[13px] leading-relaxed text-text-variant">
        {message}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className={`mt-4 inline-flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-4 py-2 text-[12px] text-danger transition ease-out hover:border-danger/60 hover:bg-danger/20 active:scale-[0.97] ${FOCUS_RING}`}
      >
        <Sym name="refresh" size={16} />
        Try again
      </button>
    </StudioGlassPanel>
  );
}

export default RunDetail;
