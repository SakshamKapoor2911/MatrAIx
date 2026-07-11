/**
 * Shared chat trial debrief: persona subjective scores, objective task metrics,
 * then the conversational transcript (batch monitor + RunDetail).
 */
import type { ReactNode } from "react";

import { PersonaBubble, RecBotBubble } from "./cockpit/TurnBubble";
import { SCORE_BAND_CLASS, humanizeToken, scoreBand } from "./cockpit/cockpitShared";
import {
  StatTile,
  appName,
  bandBorderL,
  type RunConfig,
  type RunDetailView,
  type RunPersona,
  type RunTranscriptTurn,
} from "./runsShared";
import type { TurnView } from "@/lib/types";
import type { PlaygroundQuestionnaire } from "@/lib/types";
import type { TrialEvaluationArtifact, TrialEvaluationContext } from "@/lib/types";

export type ChatTrialVerifier = NonNullable<RunDetailView["verifier"]>;

export interface ChatTrialDebriefBodyProps {
  config: RunConfig;
  transcript: RunTranscriptTurn[];
  persona?: RunPersona | null;
  questionnaire?: PlaygroundQuestionnaire | null;
  metricScores?: RunDetailView["metricScores"];
  verifier?: ChatTrialVerifier | null;
  trialEvaluation?: TrialEvaluationArtifact | null;
  /** When false, hide section headings (embedded in batch monitor). */
  showSectionHeadings?: boolean;
}

function clamp(value: number, max: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(max, value));
}

function DashedNote({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-outline bg-surface-low px-4 py-8 text-center text-[13px] text-text-variant">
      {children}
    </div>
  );
}

function SectionHeading({ children }: { children: ReactNode }) {
  return <h2 className="hud text-[10px] text-primary">{children}</h2>;
}

function SubsectionHeading({ children }: { children: ReactNode }) {
  return <h3 className="text-[12px] font-semibold text-text-main">{children}</h3>;
}

function previewText(value: string | null | undefined, limit = 180): string {
  const normalized = (value ?? "").trim().replace(/\s+/g, " ");
  if (!normalized) return "";
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit - 1).trimEnd()}…`;
}

function contextOfType(
  trialEvaluation: TrialEvaluationArtifact | null | undefined,
  contextType: string,
): TrialEvaluationContext | null {
  return (
    trialEvaluation?.contexts.find((context) => context.contextType === contextType) ?? null
  );
}

function facetValue(context: TrialEvaluationContext | null, key: string): string | number | boolean | null {
  const facet = context?.facets.find((item) => item.key === key);
  return facet?.value ?? null;
}

function facetText(context: TrialEvaluationContext | null, key: string): string {
  const value = facetValue(context, key);
  return typeof value === "string" ? value : "";
}

function facetNumber(context: TrialEvaluationContext | null, key: string): number | null {
  const value = facetValue(context, key);
  return typeof value === "number" ? value : null;
}

function formatFacetToken(value: string | number | boolean | null | undefined): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return String(value);
  if (!value) return "-";
  if (value === "true") return "Yes";
  if (value === "false") return "No";
  return humanizeToken(value);
}

function SummarySignalCard({
  title,
  value,
  eyebrow,
  detail,
}: {
  title: string;
  value: ReactNode;
  eyebrow?: string | null;
  detail?: string | null;
}) {
  return (
    <div className="rounded-md border border-outline/40 bg-surface p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="hud text-[9px] text-text-dim">{title}</span>
        {eyebrow ? (
          <span className="inline-flex items-center rounded border border-outline/40 bg-surface-high px-2 py-0.5 text-[10px] text-text-variant">
            {eyebrow}
          </span>
        ) : null}
      </div>
      <div className="mt-2 text-[20px] font-semibold leading-tight text-text-main">{value}</div>
      {detail ? <p className="mt-2 text-[11px] leading-relaxed text-text-variant">{detail}</p> : null}
    </div>
  );
}

function ChatContractSummary({
  trialEvaluation,
}: {
  trialEvaluation: TrialEvaluationArtifact | null | undefined;
}) {
  const outcome = contextOfType(trialEvaluation, "task_outcome");
  const conversation = contextOfType(trialEvaluation, "conversation_summary");
  const feedback =
    contextOfType(trialEvaluation, "user_feedback") ?? contextOfType(trialEvaluation, "feedback");

  if (!outcome && !conversation && !feedback) return null;

  const outcomeStatus = formatFacetToken(facetValue(outcome, "outcome_status"));
  const resolutionBasis = facetText(outcome, "resolution_basis");
  const outcomeReason = previewText(facetText(outcome, "outcome_reason"), 140);

  const conversationPath = formatFacetToken(facetValue(conversation, "conversation_path"));
  const turnCount = facetNumber(conversation, "message_count");
  const clarificationCount = facetNumber(conversation, "clarification_question_count");
  const processNotes = previewText(facetText(conversation, "process_notes"), 140);

  const rating = facetNumber(feedback, "overall_experience_rating");
  const needSatisfaction = formatFacetToken(facetValue(feedback, "need_constraint_satisfaction"));
  const feedbackReason = previewText(facetText(feedback, "feedback_reason"), 140);

  return (
    <div className="space-y-3 rounded-md border border-outline bg-surface-low p-4">
      <div className="space-y-1">
        <SubsectionHeading>Trial summary</SubsectionHeading>
        <p className="text-[11px] leading-relaxed text-text-variant">
          Chat-specific signals from this trial: outcome, how the conversation unfolded, and the
          persona&apos;s post-chat rating.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {outcome ? (
          <SummarySignalCard
            title="Task outcome"
            value={outcomeStatus}
            eyebrow={resolutionBasis ? formatFacetToken(resolutionBasis) : null}
            detail={outcomeReason || "No outcome explanation was recorded."}
          />
        ) : null}
        {conversation ? (
          <SummarySignalCard
            title="Conversation path"
            value={conversationPath}
            eyebrow={
              turnCount != null || clarificationCount != null
                ? `${turnCount ?? "-"} msgs · ${clarificationCount ?? "-"} clarifications`
                : null
            }
            detail={processNotes || "No process summary was recorded."}
          />
        ) : null}
        {feedback ? (
          <SummarySignalCard
            title="User feedback"
            value={rating != null ? `${rating}/10` : needSatisfaction}
            eyebrow={rating != null ? needSatisfaction : null}
            detail={feedbackReason || "No feedback explanation was recorded."}
          />
        ) : null}
      </div>
    </div>
  );
}

/** Persona simulator self-report after the chat (from ``user_feedback.json``). */
export function ChatSelfReport({
  questionnaire,
}: {
  questionnaire: PlaygroundQuestionnaire | null | undefined;
}) {
  const overall = questionnaire?.overallRating ?? null;
  const band = scoreBand(overall == null ? null : overall / 10);
  const color = SCORE_BAND_CLASS[band];

  return (
    <div className="space-y-4">
      <div
        className={`rounded-md border border-outline bg-surface p-5 border-l-4 ${
          overall == null ? "border-l-outline" : bandBorderL(band)
        }`}
      >
        <span className={`hud text-[9px] ${overall == null ? "text-text-dim" : color.text}`}>
          Overall satisfaction
        </span>
        <div className="mt-1.5 flex items-baseline gap-1.5">
          <span
            className={`font-display text-[40px] font-bold leading-none tabular-nums ${
              overall == null ? "text-text-dim" : color.text
            }`}
          >
            {overall == null ? "-" : overall}
          </span>
          <span className="text-[13px] text-text-dim">/ 10</span>
        </div>
        <p className="mt-3 text-[12px] leading-relaxed text-text-variant">
          {questionnaire?.ratingReason ||
            "After the chat, the persona simulator rates how well the app understood and met their needs."}
        </p>
      </div>

      {questionnaire ? (
        <DebriefScorecard q={questionnaire} />
      ) : (
        <DashedNote>
          No persona self-report was recorded. The simulator writes{" "}
          <span className="font-mono text-[11px]">user_feedback.json</span> after the conversation ends.
        </DashedNote>
      )}
    </div>
  );
}

/** Run completeness strip — shown first so pass/fail is visible before quality insights. */
export function ChatObjectiveEvaluation({
  metrics,
  verifier,
}: {
  metrics: RunDetailView["metricScores"];
  verifier?: ChatTrialVerifier | null;
}) {
  const artifactMissing =
    verifier &&
    !verifier.passed &&
    (verifier.detail?.includes("transcript.json is missing") ||
      verifier.detail?.includes("artifacts/app/output"));

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <StatTile caption="Turns" value={metrics?.numTurns ?? "-"} />
        {verifier ? (
          <div
            className={`flex flex-col justify-center rounded-lg border px-3 py-2.5 ${
              verifier.passed
                ? "border-secondary/40 bg-secondary/10"
                : "border-danger/40 bg-danger/10"
            }`}
          >
            <span className="hud text-[9px] text-text-dim">Run complete</span>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-[13px] font-semibold text-text-main">
                {verifier.passed ? "Passed checks" : "Failed checks"}
              </span>
              <span className="font-mono text-[11px] text-text-variant">reward {verifier.reward}</span>
            </div>
          </div>
        ) : (
          <div className="flex flex-col justify-center rounded-lg border border-dashed border-outline/50 bg-surface/40 px-3 py-2.5">
            <span className="hud text-[9px] text-text-dim">Run complete</span>
            <span className="mt-1 text-[13px] text-text-variant">Checks pending</span>
          </div>
        )}
      </div>
      {artifactMissing ? (
        <p className="text-[11px] leading-relaxed text-text-variant">
          Scores above were recovered from the live event stream. Artifact checks failed because
          output files were missing on this run. Re-run the job for a clean pass.
        </p>
      ) : null}
      {verifier?.detail && !verifier.passed ? (
        <pre className="custom-scrollbar max-h-24 overflow-auto whitespace-pre-wrap rounded-md border border-outline/40 bg-surface/50 px-3 py-2 font-mono text-[10px] leading-snug text-text-variant">
          {verifier.detail}
        </pre>
      ) : null}
    </div>
  );
}

export function ChatTrialTranscript({
  transcript,
  appLabel,
  domain = "movie",
  persona,
}: {
  transcript: RunTranscriptTurn[];
  appLabel: string;
  domain?: string;
  persona?: RunPersona | null;
}) {
  if (transcript.length === 0) {
    return <DashedNote>No conversation turns were recorded for this trial.</DashedNote>;
  }
  return (
    <div className="space-y-7 rounded-md border border-outline bg-surface p-5">
      {transcript.map((turn, i) => (
        <TranscriptTurn
          key={turn.turnIndex ?? i}
          turn={turn}
          index={i}
          appLabel={appLabel}
          domain={domain}
          persona={persona}
        />
      ))}
    </div>
  );
}

/** Run checks first, then evaluation (chat summary + persona report), transcript below. */
export function ChatTrialDebriefBody({
  config,
  transcript,
  persona,
  questionnaire,
  metricScores,
  verifier,
  trialEvaluation,
  showSectionHeadings = true,
}: ChatTrialDebriefBodyProps) {
  const app = appName(config.applicationId);

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        {showSectionHeadings && <SectionHeading>Evaluation</SectionHeading>}
        <div className="space-y-2 rounded-md border border-outline/50 bg-surface/40 p-3">
          <p className="text-[11px] leading-relaxed text-text-variant">
            Run checks confirm the conversation finished and artifacts are valid — not a quality
            score.
          </p>
          <ChatObjectiveEvaluation metrics={metricScores} verifier={verifier} />
        </div>
        <ChatContractSummary trialEvaluation={trialEvaluation} />
        <div className="space-y-3 rounded-md border border-outline bg-surface-low p-4">
          {showSectionHeadings && <SubsectionHeading>Persona self-report</SubsectionHeading>}
          <p className="text-[11px] leading-relaxed text-text-variant">
            How the simulated user rated the chat after it ended.
          </p>
          <ChatSelfReport questionnaire={questionnaire} />
        </div>
      </section>

      <section className="space-y-3">
        {showSectionHeadings && <SectionHeading>Conversation</SectionHeading>}
        <ChatTrialTranscript
          transcript={transcript}
          appLabel={app}
          domain={String(config.domain ?? "movie")}
          persona={persona}
        />
      </section>
    </div>
  );
}

function TranscriptTurn({
  turn,
  index,
  appLabel,
  domain,
  persona,
}: {
  turn: RunTranscriptTurn;
  index: number;
  appLabel: string;
  domain: string;
  persona?: RunPersona | null;
}) {
  const turnView: TurnView = {
    userMessage: turn.userMessage,
    assistantMessage: turn.assistantMessage ?? "",
    personaExposure: turn.personaExposure ?? [],
    durationSeconds: turn.durationSeconds,
    plan: [],
  };

  return (
    <div
      className="space-y-7 rise-in"
      style={{ animationDelay: `${Math.min(index, 6) * 30}ms`, animationFillMode: "backwards" }}
    >
      <div className="flex items-center justify-center">
        <span className="hud text-[9px] text-text-dim">Turn {index + 1}</span>
      </div>
      <PersonaBubble
        message={turn.userMessage}
        personaId={persona?.id}
        personaDimensions={persona?.dimensions ?? undefined}
      />
      {turn.decision && turn.decision !== "continue" ? (
        <div className="flex items-start gap-2.5 pr-10">
          <div className="h-8 w-8 shrink-0" aria-hidden />
          <DecisionTag decision={turn.decision} />
        </div>
      ) : null}
      <RecBotBubble
        turn={turnView}
        domain={domain}
        appName={appLabel}
        foldOpen={false}
        onToggleFold={() => undefined}
      />
    </div>
  );
}

function DecisionTag({ decision }: { decision: string }) {
  const satisfied = decision === "satisfied";
  const cls = satisfied
    ? "text-secondary border border-secondary/30 bg-secondary/10"
    : "text-warn border border-warn/30 bg-warn/10";
  const label = satisfied ? "Got what they needed" : decision === "give_up" ? "Gave up" : humanizeToken(decision);
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-px hud text-[9px] ${cls}`}>{label}</span>
  );
}

function DebriefScorecard({ q }: { q: PlaygroundQuestionnaire }) {
  return (
    <div className="space-y-5 rounded-md border border-outline bg-surface p-4">
      <CriterionBar
        label="Stayed within my requirements"
        score={q.constraintSatisfaction}
        max={5}
        rationale={q.constraintRationale}
      />
      <CriterionBar
        label="Matched my preferences"
        score={q.preferenceSatisfaction}
        max={5}
        rationale={q.preferenceRationale}
      />
      <div className="border-t border-outline pt-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[12px] font-medium text-text-main">Asked helpful follow-up questions</span>
          <span
            className={`inline-flex items-center rounded border px-2 py-1 hud text-[9px] ${
              q.askedUsefulClarifyingQuestions
                ? "border-secondary/30 bg-secondary/10 text-secondary"
                : "border-outline bg-surface-high text-text-variant"
            }`}
          >
            {q.askedUsefulClarifyingQuestions ? "Yes" : "Not this time"}
          </span>
        </div>
        {q.clarifyingNotes && (
          <p className="mt-1.5 text-[11px] leading-snug text-text-variant">{q.clarifyingNotes}</p>
        )}
      </div>
    </div>
  );
}

function CriterionBar({
  label,
  score,
  max,
  rationale,
}: {
  label: string;
  score: number;
  max: number;
  rationale: string;
}) {
  const value = clamp(score, max);
  const band = scoreBand(value / max);
  const color = SCORE_BAND_CLASS[band];
  const pct = (value / max) * 100;
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="text-[12px] font-medium text-text-main">{label}</span>
        <span className={`font-mono text-[12px] font-bold tabular-nums ${color.text}`}>
          {value} / {max}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-field">
        <div className={`h-full ${color.bar}`} style={{ width: `${pct}%` }} />
      </div>
      {rationale && <p className="mt-1.5 text-[11px] leading-snug text-text-variant">{rationale}</p>}
    </div>
  );
}

export default ChatTrialDebriefBody;
