/**
 * TaskEvalScorecard: Evaluation inspector panels for Survey, Web, and CUA runs.
 *
 * Mirrors the chat Scorecard layout (overall score + quote + criterion rows +
 * Harbor verifier strip) using each task type's debrief payload.
 */
import type { ReactNode } from "react";
import { SCORE_BAND_CLASS, Sym, scoreBand } from "./cockpitShared";
import type { HarborCockpitPhase } from "@/lib/useHarborCockpitRun";
import type { OsAppResult, SurveyResult, VerifierSummary, WebResult } from "@/lib/types";

export type TaskEvalPhase = HarborCockpitPhase;

function clamp(value: number, max: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(max, value));
}

function runningPhase(phase: TaskEvalPhase): boolean {
  return phase === "launching" || phase === "running";
}

function failedPhase(phase: TaskEvalPhase): boolean {
  return phase === "error" || phase === "timeout";
}

function ScorecardShell({
  scored,
  children,
}: {
  scored: boolean;
  children: ReactNode;
}) {
  return (
    <div className="p-md">
      <div className="panel rise-in overflow-hidden rounded-md border border-outline bg-surface-lowest">
        <div className="flex items-center justify-between border-b border-outline bg-surface-low px-3 py-2.5">
          <div className="flex items-center gap-2">
            <Sym name="verified" fill={1} size={18} className="text-primary" />
            <h3 className="hud text-[11px] text-primary">Scorecard</h3>
          </div>
          {scored ? (
            <span className="flex items-center gap-1 hud text-[10px] text-text-dim">
              <span className="h-2 w-2 rounded-full bg-secondary" aria-hidden />
              Scored
            </span>
          ) : null}
        </div>
        <div className="p-3">{children}</div>
      </div>
    </div>
  );
}

function ScorecardSkeleton() {
  return (
    <div className="p-md" aria-hidden>
      <div className="rise-in overflow-hidden rounded-md border border-outline bg-surface-lowest">
        <div className="border-b border-outline bg-surface-low px-3 py-2.5">
          <div className="h-4 w-28 animate-rb-pulse rounded bg-surface-high" />
        </div>
        <div className="space-y-3 p-3">
          <div className="flex items-center gap-3">
            <div className="h-10 w-14 animate-rb-pulse rounded bg-surface-high" />
            <div className="h-10 flex-1 animate-rb-pulse rounded bg-surface-high" />
          </div>
          <div className="h-8 w-full animate-rb-pulse rounded bg-surface-high" />
          <div className="h-8 w-full animate-rb-pulse rounded bg-surface-high" />
        </div>
      </div>
    </div>
  );
}

function EmptyScorecard({ phase }: { phase: TaskEvalPhase }) {
  return (
    <div className="p-md">
      <div className="rise-in rounded-md border border-dashed border-outline-dim bg-surface-low px-4 py-10 text-center">
        <Sym name="fact_check" size={28} className="text-text-dim" />
        <p className="mt-2 text-[13px] leading-relaxed text-text-variant">
          {failedPhase(phase)
            ? "This run stopped before it could be scored."
            : "Run a simulation and the scores will appear here."}
        </p>
      </div>
    </div>
  );
}

function CriterionRow({
  label,
  score,
  max,
  rationale,
}: {
  label: string;
  score: number;
  max: number;
  rationale?: string | null;
}) {
  const value = clamp(score, max);
  const band = scoreBand(value / max);
  const color = SCORE_BAND_CLASS[band];
  const pct = (value / max) * 100;
  const passing = band === "high";

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-[12px] font-medium text-text-main">
          <Sym
            name={passing ? "check_circle" : band === "low" ? "cancel" : "remove_circle"}
            fill={1}
            size={16}
            className={color.text}
          />
          {label}
        </span>
        <span className={`font-mono text-[12px] font-bold tabular-nums ${color.text}`}>
          {value} / {max}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-field">
        <div className={`h-full rounded-full transition-[width] duration-200 ${color.bar}`} style={{ width: `${pct}%` }} />
      </div>
      {rationale ? <p className="mt-1 text-[11px] leading-snug text-text-variant">{rationale}</p> : null}
    </div>
  );
}

export function VerifierStrip({ verifier }: { verifier: VerifierSummary }) {
  const passed = verifier.passed;
  return (
    <div
      className={`mt-3 rounded-md border px-3 py-2 ${
        passed ? "border-secondary/40 bg-secondary/10" : "border-danger/40 bg-danger/10"
      }`}
    >
      <div className="flex items-center gap-2">
        <Sym name={passed ? "task_alt" : "error"} fill={1} size={18} className={passed ? "text-secondary" : "text-danger"} />
        <span className="text-[12px] font-semibold text-text-main">
          Verifier · {passed ? "Passed" : "Failed"}
        </span>
        <span className="ml-auto font-mono text-[11px] tabular-nums text-text-variant">
          reward {verifier.reward}
        </span>
      </div>
      {verifier.detail ? (
        <pre className="custom-scrollbar mt-2 max-h-28 overflow-auto whitespace-pre-wrap font-mono text-[10px] leading-snug text-text-variant">
          {verifier.detail}
        </pre>
      ) : null}
    </div>
  );
}

function MetricTile({ value, caption }: { value: string; caption: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-outline bg-surface py-2.5">
      <span className="font-display text-[22px] font-bold tabular-nums text-text-main">{value}</span>
      <span className="mt-0.5 text-center hud text-[10px] leading-tight text-text-dim">{caption}</span>
    </div>
  );
}

export interface WebEvalScorecardProps {
  webResult: WebResult | null;
  verifier?: VerifierSummary | null;
  phase: TaskEvalPhase;
}

export function WebEvalScorecard({ webResult, verifier, phase }: WebEvalScorecardProps) {
  if (runningPhase(phase) && !webResult) return <ScorecardSkeleton />;
  if (!webResult) return <EmptyScorecard phase={phase} />;

  const overall = clamp(webResult.overallExperienceRating, 10);
  const overallBand = scoreBand(overall / 10);
  const overallColor = SCORE_BAND_CLASS[overallBand];
  const overallBorder =
    overallBand === "high"
      ? "border-l-score-high"
      : overallBand === "mid"
        ? "border-l-score-mid"
        : overallBand === "low"
          ? "border-l-score-low"
          : "border-l-outline";

  return (
    <ScorecardShell scored>
      <div className="mb-3 flex items-start gap-3">
        <div className="flex flex-shrink-0 flex-col items-center">
          <div className="flex items-baseline gap-0.5" aria-label={`Overall UX ${overall} out of 10`}>
            <span className={`font-display text-[44px] font-bold leading-none tracking-tight tabular-nums ${overallColor.text}`}>
              {overall}
            </span>
            <span className="text-[13px] text-text-dim">/ 10</span>
          </div>
          <span className="mt-1 text-center hud text-[10px] text-text-dim">How the user rated it</span>
        </div>
        {webResult.reason ? (
          <div className={`flex-1 border-l-2 pl-3 ${overallBorder}`}>
            <p className="text-[12px] italic leading-relaxed text-text-variant">&ldquo;{webResult.reason}&rdquo;</p>
          </div>
        ) : null}
      </div>

      <div className="mb-3 space-y-2.5">
        <CriterionRow
          label="Did it meet their need?"
          score={webResult.needSatisfaction}
          max={10}
          rationale={webResult.reason}
        />
        <CriterionRow label="Was it easy to use?" score={webResult.easeOfUse} max={10} />
      </div>

      <div className="flex items-start gap-3 rounded-md border border-outline bg-surface px-3 py-2.5">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded border border-outline bg-surface-high">
          <Sym name="inventory_2" size={20} className="text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[13px] font-semibold text-text-main">{webResult.selectedProductName}</span>
            <span
              className={`hud rounded border px-1.5 py-0.5 text-[8px] ${
                webResult.valid
                  ? "border-secondary/30 bg-secondary/10 text-secondary"
                  : "border-danger/30 bg-danger/10 text-danger"
              }`}
            >
              {webResult.valid ? "Complete" : "Incomplete"}
            </span>
          </div>
          <div className="mt-0.5 truncate font-mono text-[10px] text-text-variant">{webResult.selectedProductId}</div>
        </div>
      </div>

      {verifier ? <VerifierStrip verifier={verifier} /> : null}

      <p className="mt-3 text-[10px] leading-relaxed text-text-dim">
        Scores read <span className="text-secondary">green</span> when the app did well,{" "}
        <span className="text-warn">amber</span> when so-so, <span className="text-danger">red</span> when it missed.
      </p>
    </ScorecardShell>
  );
}

export interface SurveyEvalScorecardProps {
  surveyResult: SurveyResult | null;
  verifier?: VerifierSummary | null;
  phase: TaskEvalPhase;
}

export function SurveyEvalScorecard({ surveyResult, verifier, phase }: SurveyEvalScorecardProps) {
  if (runningPhase(phase) && !surveyResult) return <ScorecardSkeleton />;
  if (!surveyResult?.completion) return <EmptyScorecard phase={phase} />;

  const { completion } = surveyResult;
  const total = completion.numQuestions || completion.total || 0;
  const answered = completion.numAnswered || completion.answered || surveyResult.answers.length;
  const pct = total > 0 ? Math.round((answered / total) * 100) : 0;
  const meanLikert = completion.meanLikert;
  const mainScore = meanLikert != null ? clamp(meanLikert, 5) : pct;
  const mainMax = meanLikert != null ? 5 : 100;
  const mainBand = scoreBand(mainScore / mainMax);
  const mainColor = SCORE_BAND_CLASS[mainBand];

  return (
    <ScorecardShell scored={phase === "done"}>
      <div className="mb-3 flex items-start gap-3">
        <div className="flex flex-shrink-0 flex-col items-center">
          <div className="flex items-baseline gap-0.5">
            <span className={`font-display text-[44px] font-bold leading-none tracking-tight tabular-nums ${mainColor.text}`}>
              {meanLikert != null ? mainScore.toFixed(1) : `${pct}`}
            </span>
            <span className="text-[13px] text-text-dim">/ {mainMax}</span>
          </div>
          <span className="mt-1 text-center hud text-[10px] text-text-dim">
            {meanLikert != null ? "Mean Likert rating" : "Completion"}
          </span>
        </div>
        <div className="flex-1 border-l-2 border-l-outline pl-3">
          <p className="text-[12px] leading-relaxed text-text-variant">
            {answered} of {total} questions answered
            {completion.valid ? " · responses passed validation" : " · validation flagged issues"}
          </p>
        </div>
      </div>

      <div className="mb-3 space-y-2.5">
        <CriterionRow
          label="Did they finish the questionnaire?"
          score={total > 0 ? (answered / total) * 5 : 0}
          max={5}
        />
        <CriterionRow
          label="Were answers valid?"
          score={completion.valid ? 5 : 1}
          max={5}
        />
      </div>

      <div className="grid grid-cols-3 gap-2">
        <MetricTile value={`${answered}/${total}`} caption="Answered" />
        <MetricTile value={completion.valid ? "Yes" : "No"} caption="Valid" />
        <MetricTile
          value={meanLikert == null ? "n/a" : meanLikert.toFixed(1)}
          caption="Mean Likert"
        />
      </div>

      {verifier ? <VerifierStrip verifier={verifier} /> : null}
    </ScorecardShell>
  );
}

export interface OsAppEvalScorecardProps {
  osAppResult: OsAppResult | null;
  verifier?: VerifierSummary | null;
  traceStepCount?: number;
  phase: TaskEvalPhase;
}

export function OsAppEvalScorecard({ osAppResult, verifier, traceStepCount = 0, phase }: OsAppEvalScorecardProps) {
  if (runningPhase(phase) && !osAppResult) return <ScorecardSkeleton />;
  if (!osAppResult) return <EmptyScorecard phase={phase} />;

  const reward = osAppResult.score ?? (osAppResult.success ? 1 : 0);
  const passed = osAppResult.success;
  const band = passed ? "high" : "low";
  const color = SCORE_BAND_CLASS[band];
  const displayReward = reward >= 0 && reward <= 1 ? `${Math.round(reward * 100)}%` : String(reward);

  return (
    <ScorecardShell scored>
      <div className="mb-3 flex items-start gap-3">
        <div className="flex flex-shrink-0 flex-col items-center">
          <div className="flex items-baseline gap-0.5">
            <span className={`font-display text-[44px] font-bold leading-none tracking-tight tabular-nums ${color.text}`}>
              {displayReward}
            </span>
          </div>
          <span className="mt-1 text-center hud text-[10px] text-text-dim">Verifier reward</span>
        </div>
        <div className={`flex-1 border-l-2 pl-3 ${passed ? "border-l-score-high" : "border-l-score-low"}`}>
          <p className="text-[12px] leading-relaxed text-text-variant">
            {passed
              ? "The automated verifier accepted the desktop agent's output."
              : "The verifier did not accept the output — check the trace and artifact in the center panel."}
          </p>
        </div>
      </div>

      <div className="mb-3 space-y-2.5">
        <CriterionRow label="Task succeeded?" score={passed ? 5 : 0} max={5} />
        <CriterionRow
          label="Reward score"
          score={reward <= 1 ? reward * 5 : clamp(reward, 5)}
          max={5}
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <MetricTile value={passed ? "Pass" : "Fail"} caption="Verifier" />
        <MetricTile value={String(traceStepCount)} caption="Trace steps" />
      </div>

      {osAppResult.artifactName ? (
        <div className="mt-3 flex items-center gap-2 rounded-md border border-outline bg-surface px-3 py-2 text-[11px] text-text-variant">
          <Sym name="description" size={16} className="text-primary" />
          Output artifact · <span className="font-mono text-text-main">{osAppResult.artifactName}</span>
        </div>
      ) : null}

      {verifier?.detail ? <VerifierStrip verifier={verifier} /> : null}
    </ScorecardShell>
  );
}
