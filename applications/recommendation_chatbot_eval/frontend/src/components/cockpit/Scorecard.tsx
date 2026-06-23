/**
 * Scorecard — the cockpit's Evaluation inspector panel.
 *
 * Ports the mockup's evaluation card: a large overall rating beside the
 * persona's self-rating quote, per-criterion rows (constraint / preference
 * satisfaction) with threshold-coloured bars + rationale, the clarifying-
 * questions line, and a run-metrics strip.
 *
 * Honest scoring rules (acceptance criteria):
 *   - the overall number is rendered on the red→amber→green score scale, never
 *     the indigo accent, and the colour is ALWAYS paired with the number;
 *   - each criterion bar + score share the same band colour;
 *   - metrics show only what's tracked (turns / items); no tokens or cost.
 *
 * States: a skeleton while a run is in progress, and a plain teaching empty
 * state before any run / when a run finished without an evaluation.
 */
import { SCORE_BAND_CLASS, Sym, scoreBand } from "./cockpitShared";
import { GroundingChip } from "../runsShared";
import type { PersonaEvalMetricScores, PersonaEvalQuestionnaire } from "@/lib/types";
import type { PersonaEvalRunPhase } from "@/lib/usePersonaEval";

export interface ScorecardProps {
  questionnaire: PersonaEvalQuestionnaire | null;
  metrics: PersonaEvalMetricScores | null;
  phase: PersonaEvalRunPhase;
}

/** Clamp a raw score into [0, max]. */
function clamp(value: number, max: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(max, value));
}

export function Scorecard({ questionnaire, metrics, phase }: ScorecardProps) {
  const running = phase === "building" || phase === "running";

  if (running && !questionnaire) return <ScorecardSkeleton />;

  if (!questionnaire || !metrics) {
    return (
      <div className="p-md">
        <div className="rounded-xl border border-dashed border-border-soft bg-surface-container-low px-4 py-10 text-center">
          <Sym name="fact_check" size={28} className="text-outline" />
          <p className="mt-2 text-body-sm leading-relaxed text-on-surface-variant">
            {phase === "error" || phase === "timeout"
              ? "This run ended before an evaluation was produced."
              : "Run an eval to see the persona's scorecard here."}
          </p>
        </div>
      </div>
    );
  }

  const overall = clamp(questionnaire.overallRating, 10);
  const overallBand = scoreBand(overall / 10);
  const overallColor = SCORE_BAND_CLASS[overallBand];

  return (
    <div className="p-md">
      <div className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
        {/* Card header */}
        <div className="flex items-center justify-between border-b border-border-soft bg-surface-container-low px-3 py-2.5">
          <div className="flex items-center gap-2">
            <Sym name="verified" fill={1} size={18} className="text-primary" />
            <h3 className="text-headline-sm font-headline-sm uppercase tracking-wider text-on-surface">Evaluation</h3>
          </div>
          <span className="flex items-center gap-1 text-label-md font-label-md text-on-surface-variant">
            <span className="h-2 w-2 rounded-full bg-success" aria-hidden />
            Completed
          </span>
        </div>

        <div className="p-3">
          {/* Overall score + quote */}
          <div className="mb-3 flex items-start gap-3">
            <div className="flex flex-shrink-0 flex-col items-center">
              <div className="flex items-baseline gap-0.5" aria-label={`Overall rating ${overall} out of 10`}>
                <span className={`text-[40px] font-bold leading-none tracking-tight tabular-nums ${overallColor.text}`}>
                  {overall}
                </span>
                <span className="text-headline-md font-headline-md text-on-surface-variant">/ 10</span>
              </div>
              <span className="mt-1 text-center text-[10px] uppercase tracking-wider text-on-surface-variant">
                Persona self-rating
              </span>
              {/* Grounding: the self-rating measures the conversation; this says
                  whether the recommender actually returned real catalog items. */}
              <GroundingChip metrics={metrics} className="mt-1.5" />
            </div>
            {questionnaire.ratingReason && (
              <div className="flex-1 border-l border-border-soft pl-3">
                <p className="text-body-md italic leading-relaxed text-on-surface">
                  &ldquo;{questionnaire.ratingReason}&rdquo;
                </p>
              </div>
            )}
          </div>

          {/* Criterion rows */}
          <div className="mb-3 space-y-2.5">
            <CriterionRow
              label="Constraint satisfaction"
              score={questionnaire.constraintSatisfaction}
              max={5}
              rationale={questionnaire.constraintRationale}
            />
            <CriterionRow
              label="Preference satisfaction"
              score={questionnaire.preferenceSatisfaction}
              max={5}
              rationale={questionnaire.preferenceRationale}
            />
          </div>

          {/* Clarifying questions line */}
          <ClarifyingLine
            asked={questionnaire.askedUsefulClarifyingQuestions}
            notes={questionnaire.clarifyingNotes}
          />

          {/* Metrics strip — real counts only (no tokens / cost). */}
          <div className="mt-3 grid grid-cols-3 gap-2">
            <MetricTile
              value={metrics.turnsToRecommendation === null ? "—" : String(metrics.turnsToRecommendation)}
              caption="Turns to first rec"
            />
            <MetricTile value={String(metrics.numTurns)} caption="Turns" />
            <MetricTile value={String(metrics.recommendedItemCount)} caption="Items recommended" />
          </div>
        </div>
      </div>
    </div>
  );
}

/** One criterion: name + score + threshold-coloured bar + rationale. */
function CriterionRow({
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
  const passing = band === "high";

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-body-sm font-medium text-on-surface">
          <Sym
            name={passing ? "check_circle" : band === "low" ? "cancel" : "remove_circle"}
            fill={1}
            size={16}
            className={color.text}
          />
          {label}
        </span>
        <span className={`text-body-sm font-semibold tabular-nums ${color.text}`}>
          {value} / {max}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-container-high">
        <div className={`h-full rounded-full transition-[width] duration-200 ${color.bar}`} style={{ width: `${pct}%` }} />
      </div>
      {rationale && <p className="mt-1 text-body-sm leading-relaxed text-on-surface-variant">{rationale}</p>}
    </div>
  );
}

/** The clarifying-questions callout (green when useful, neutral when not). */
function ClarifyingLine({ asked, notes }: { asked: boolean; notes: string }) {
  return (
    <div
      className={`flex items-start gap-2 rounded-md border px-3 py-2 ${
        asked ? "border-success/40 bg-success-container" : "border-border-soft bg-surface-container-low"
      }`}
    >
      <Sym
        name={asked ? "help" : "help_outline"}
        fill={asked ? 1 : 0}
        size={18}
        className={`mt-0.5 ${asked ? "text-on-success-container" : "text-on-surface-variant"}`}
      />
      <span className="text-body-sm text-on-surface">
        <span className="font-semibold">Clarifying questions</span>
        {asked ? " — asked useful ones" : " — none asked"}
        {notes ? `. ${notes}` : "."}
      </span>
    </div>
  );
}

/** A compact metric tile (big value + caption). */
function MetricTile({ value, caption }: { value: string; caption: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-border-soft bg-surface-container-low py-2.5">
      <span className="text-headline-md font-headline-md tabular-nums text-on-surface">{value}</span>
      <span className="mt-0.5 text-center text-[10px] uppercase leading-tight tracking-wider text-on-surface-variant">
        {caption}
      </span>
    </div>
  );
}

/** A skeleton scorecard shown while a run is in progress. */
function ScorecardSkeleton() {
  return (
    <div className="p-md" aria-hidden>
      <div className="overflow-hidden rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft">
        <div className="border-b border-border-soft bg-surface-container-low px-3 py-2.5">
          <div className="h-4 w-28 animate-rb-pulse rounded bg-surface-container-high" />
        </div>
        <div className="space-y-3 p-3">
          <div className="flex items-center gap-3">
            <div className="h-10 w-14 animate-rb-pulse rounded bg-surface-container-high" />
            <div className="h-10 flex-1 animate-rb-pulse rounded bg-surface-container" />
          </div>
          <div className="h-8 w-full animate-rb-pulse rounded bg-surface-container" />
          <div className="h-8 w-full animate-rb-pulse rounded bg-surface-container" />
          <div className="grid grid-cols-3 gap-2">
            <div className="h-14 animate-rb-pulse rounded-lg bg-surface-container" />
            <div className="h-14 animate-rb-pulse rounded-lg bg-surface-container" />
            <div className="h-14 animate-rb-pulse rounded-lg bg-surface-container" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default Scorecard;
