/**
 * Shared helpers + precise types for the Runs monitoring surface.
 *
 * `src/lib/types.ts` declares the persisted-run shapes loosely (`transcript:
 * TurnView[]`, `recommendedItemIds: Record<string, unknown>`) to stay tolerant
 * of legacy artifacts. The live backend returns a richer, more specific shape
 * (verified against the running API), so the Runs views narrow it here, at the
 * read boundary, into the fields they actually render, rather than threading
 * `unknown` through the components.
 */
import type { ReactNode } from "react";

import { SCORE_BAND_CLASS, Sym, type ScoreBand } from "./cockpit/cockpitShared";
import type {
  Domain,
  PersonaEvalMetricScores,
  PersonaEvalResult,
  SurveyResult,
  WebResult,
  WebTrace,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Narrowed run-detail shapes (what RunDetail / RunCompare actually read)
// ---------------------------------------------------------------------------

/** One recommended item as the transcript carries it (id + resolved title). */
export interface RunRecItem {
  id: string;
  title: string | null;
}

/** The persona's terminal stance on a turn. */
export type RunDecision = "continue" | "satisfied" | "give_up";

/** One turn of a persisted run's transcript (the verified backend shape). */
export interface RunTranscriptTurn {
  turnIndex: number;
  userMessage: string;
  assistantMessage: string;
  recommendedItems: RunRecItem[];
  decision: RunDecision | string;
  durationSeconds: number | null;
}

/** The run config block we surface (domain / engine / goal context, etc.). */
export interface RunConfig {
  domain?: Domain | string | null;
  engine?: string | null;
  rankerMode?: string | null;
  resourceMode?: string | null;
  maxTurns?: number | null;
  goalContextId?: string | null;
  /** Which chatbot adapter was under test (`recai` / `finance_openbb` / …). */
  applicationId?: string | null;
}

/**
 * Which kind of app a run exercised. The debrief picks its shape from this.
 * Today the runs endpoints only persist chatbot (`PersonaEvalResult`) runs, so
 * `runApplicationType` resolves to `"chatbot"`; the survey/web branches activate
 * only if the loaded artifact carries the matching result object (see below).
 */
export type RunApplicationType = "chatbot" | "survey" | "web";

/** The persona block we surface in headers. */
export interface RunPersona {
  id?: string | null;
  name?: string | null;
  source?: string | null;
  context?: string | null;
}

/**
 * The full persisted run, narrowed for the Runs views. We re-type the loosely
 * declared members of `PersonaEvalResult` to the verified concrete shapes and add
 * the top-level fields the API injects at persist time.
 */
export type RunDetailView = Omit<
  PersonaEvalResult,
  "config" | "persona" | "transcript" | "recommendedItemIds"
> & {
  config: RunConfig;
  persona: RunPersona;
  transcript: RunTranscriptTurn[];
  recommendedItemIds: { perTurn?: unknown; final?: string[] | null } & Record<string, unknown>;
  // ---------------------------------------------------------------------------
  // Option-aware fields the data layer MAY hand over (render-what-we-get).
  // TODO: the runs list/detail endpoints (`api.listPersonaEvalRuns` /
  // `api.getPersonaEvalRun`) currently only persist chatbot runs, so these are
  // absent today and the debrief renders the chatbot shape. The survey/web
  // bodies read the `SurveyResult` / `WebResult` / `WebTrace` shapes already
  // declared in `types.ts`; they light up unchanged once those run kinds persist.
  // ---------------------------------------------------------------------------
  /** Discriminator the artifact may carry; absent → resolved from the payload. */
  applicationType?: RunApplicationType | string | null;
  /** Survey artifact, present only on a persisted survey run. */
  surveyResult?: SurveyResult | null;
  /** Web result + browser trace, present only on a persisted web run. */
  webResult?: WebResult | null;
  webTrace?: WebTrace | null;
  trace?: WebTrace | null;
  /** Human labels a survey/web artifact may carry for the run-meta line. */
  instrumentTitle?: string | null;
  taskTitle?: string | null;
  siteName?: string | null;
};

/** Narrow a raw `PersonaEvalResult` into the richer `RunDetailView` shape. */
export function asRunDetail(raw: PersonaEvalResult): RunDetailView {
  return raw as unknown as RunDetailView;
}

/**
 * Resolve which debrief shape a loaded run should render. Prefers an explicit
 * `applicationType` discriminator, then falls back to sniffing which result
 * object the artifact carries. Defaults to `"chatbot"` (the only kind the runs
 * data layer persists today).
 */
export function runApplicationType(run: RunDetailView): RunApplicationType {
  const explicit = (run.applicationType ?? "").toString().toLowerCase();
  if (explicit === "survey" || explicit === "web" || explicit === "chatbot") {
    return explicit;
  }
  if (run.webResult || run.webTrace || run.trace) return "web";
  if (run.surveyResult) return "survey";
  return "chatbot";
}

/** The browser trace, wherever the artifact stashed it. */
export function runWebTrace(run: RunDetailView): WebTrace | null {
  return run.webTrace ?? run.trace ?? null;
}

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

/** The sentinel the backend uses for a failed/empty agent turn. */
export const AGENT_ERROR_TEXT = "Something went wrong, please retry.";

/** True when an assistant message reads as an error / empty hiccup. */
export function isAgentHiccup(message: string | null | undefined): boolean {
  if (message === null || message === undefined) return true;
  const trimmed = message.trim();
  return trimmed === "" || trimmed === AGENT_ERROR_TEXT;
}

/** A short absolute date like `Jun 21, 14:03` (locale-aware, no year clutter). */
function shortAbsolute(d: Date): string {
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/**
 * A compact relative-or-short date for mono columns. Recent timestamps read as
 * `3m`, `5h`, `2d`; anything older falls back to the short absolute date. An
 * unparseable / missing value renders as a dash.
 */
export function fmtRunDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "-";
  const date = new Date(t);
  const diffMs = Date.now() - t;
  const sec = Math.round(diffMs / 1000);
  if (sec < 0) return shortAbsolute(date); // clock skew: just show the date
  if (sec < 45) return "just now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h`;
  const day = Math.round(hr / 24);
  if (day < 7) return `${day}d`;
  return shortAbsolute(date);
}

/** Title-case a snake/lower domain token for a pill (`beauty_product` → `Beauty product`). */
export function fmtDomain(domain: string | null | undefined): string {
  if (!domain) return "-";
  const spaced = domain.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** Render a persona `source`, falling back to "curated" when absent. */
export function fmtSource(source: string | null | undefined): string {
  if (source === null || source === undefined || source === "") return "curated";
  return source;
}

/**
 * Friendly label for a goal-context id (the conversation style). `scenario_default`
 * ("Realistic scenario") is the only current option; `gradual_reveal` is retained
 * only so older runs that used it still render a name. Unknown ids are humanized; a
 * missing id reads as a dash.
 */
const GOAL_CONTEXT_LABELS: Record<string, string> = {
  scenario_default: "Realistic scenario",
  gradual_reveal: "Gradual reveal",
};

export function fmtGoalContext(id: string | null | undefined): string {
  if (!id) return "-";
  if (GOAL_CONTEXT_LABELS[id]) return GOAL_CONTEXT_LABELS[id];
  const spaced = id.replace(/_/g, " ").trim();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

// ---------------------------------------------------------------------------
// Small shared presentational atoms
// ---------------------------------------------------------------------------

/** A quiet domain pill (reused across list / detail / compare headers). */
export function DomainPill({ domain }: { domain: string | null | undefined }) {
  return (
    <span className="inline-flex items-center rounded border border-outline bg-surface-high px-2 py-0.5 text-[11px] font-medium text-text-variant">
      {fmtDomain(domain)}
    </span>
  );
}

/** A small muted source tag next to a persona name. */
export function SourceTag({ source }: { source: string | null | undefined }) {
  return (
    <span className="inline-flex shrink-0 items-center rounded bg-surface-high px-1.5 py-px font-mono text-[10px] text-text-variant">
      {fmtSource(source)}
    </span>
  );
}

/**
 * Grounding indicator: did the recommender actually return real catalog items,
 * or did the agent answer from base knowledge? A run can read smoothly (and even
 * self-score highly) while recommending nothing real, so we surface this plainly:
 * `N from the real catalog` (mint) when the corpus was used, `Nothing from the
 * catalog` (amber) when zero catalog items were recommended.
 */
export function GroundingChip({
  metrics,
  className = "",
}: {
  metrics: PersonaEvalMetricScores | null | undefined;
  className?: string;
}) {
  const count = metrics?.recommendedItemCount ?? 0;
  const grounded = count > 0;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-medium ${
        grounded
          ? "border-secondary/30 bg-secondary/10 text-secondary"
          : "border-warn/30 bg-warn/10 text-warn"
      } ${className}`}
      title={
        grounded
          ? `${count} suggestion${count === 1 ? "" : "s"} came from the real product catalog.`
          : "The app suggested items but none came from the real product catalog. They're from the model's own knowledge, so treat them with care."
      }
    >
      <Sym name={grounded ? "inventory_2" : "warning"} size={13} />
      {grounded ? `${count} from the real catalog` : "Nothing from the catalog"}
    </span>
  );
}

/** A compact recommended-item chip (mono id + title) for trajectories. */
export function RecChip({ item }: { item: RunRecItem }) {
  return (
    <span
      className="inline-flex max-w-full items-center gap-1.5 rounded border border-outline bg-surface-low px-2 py-1 text-[11px]"
      title={item.title ?? undefined}
    >
      <span className="font-mono text-[10px] text-text-dim">{item.id}</span>
      {item.title && <span className="truncate text-text-variant">{item.title}</span>}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Option-aware helpers + tiles (chatbot / survey / web debrief shapes)
// ---------------------------------------------------------------------------

/** Friendly display name for the chatbot adapter that was under test. */
const APP_DISPLAY_NAMES: Record<string, string> = {
  recai: "RecAI",
  finance_openbb: "OpenBB",
  medical_assistant: "Medical assistant",
};

/** The app's real name for the transcript label + meta line (defaults to RecAI). */
export function appName(applicationId: string | null | undefined): string {
  if (!applicationId) return "RecAI";
  return APP_DISPLAY_NAMES[applicationId] ?? fmtDomain(applicationId);
}

/** Per-kind glyph + label for the list "Kind" tag (Material Symbols, like the cockpit switch). */
const APP_TYPE_META: Record<RunApplicationType, { icon: string; label: string }> = {
  chatbot: { icon: "forum", label: "Chatbot" },
  survey: { icon: "fact_check", label: "Survey" },
  web: { icon: "language", label: "Web" },
};

/**
 * A small app-type tag for the runs list, so a (future) mixed list reads at a
 * glance. Renders from whatever type the summary carries; absent → chatbot.
 */
export function AppTypeTag({ type }: { type?: string | null }) {
  const key: RunApplicationType = type === "survey" || type === "web" ? type : "chatbot";
  const meta = APP_TYPE_META[key];
  return (
    <span
      className="inline-flex items-center gap-1 rounded border border-outline bg-surface-high px-1.5 py-0.5 text-[11px] text-text-variant"
      title="Which kind of app was tested: a chatbot, a survey, or a website."
    >
      <Sym name={meta.icon} size={13} />
      {meta.label}
    </span>
  );
}

/** Read a run summary's app type defensively (the summary may not carry one). */
export function runSummaryAppType(summary: unknown): RunApplicationType {
  const t = ((summary as { applicationType?: string | null } | null)?.applicationType ?? "").toString().toLowerCase();
  if (t === "survey" || t === "web") return t;
  return "chatbot";
}

/** Map a score band to its left-rule accent class (mirrors the cockpit Scorecard). */
export function bandBorderL(band: ScoreBand): string {
  switch (band) {
    case "high":
      return "border-l-score-high";
    case "mid":
      return "border-l-score-mid";
    case "low":
      return "border-l-score-low";
    default:
      return "border-l-outline";
  }
}

/**
 * A debrief headline tile: HUD caption + a big `font-display` value (+ optional
 * unit). When `band` is supplied the value is score-coloured via
 * `SCORE_BAND_CLASS`; `lead` adds the mockup's `border-l-4` accent (band-tinted,
 * or mint when the tile carries no score).
 */
export function StatTile({
  caption,
  value,
  unit,
  band,
  lead = false,
}: {
  caption: string;
  value: ReactNode;
  unit?: string;
  band?: ScoreBand;
  lead?: boolean;
}) {
  const color = band ? SCORE_BAND_CLASS[band] : null;
  const leadBorder = lead ? `border-l-4 ${band ? bandBorderL(band) : "border-l-secondary"}` : "";
  const captionTone = lead ? (color ? color.text : "text-secondary") : "text-text-dim";
  return (
    <div className={`flex flex-col justify-center rounded-md border border-outline bg-surface p-4 ${leadBorder}`}>
      <span className={`hud text-[9px] ${captionTone}`}>{caption}</span>
      <div className="mt-1.5 flex items-baseline gap-1">
        <span
          className={`font-display text-[26px] font-bold leading-none tabular-nums ${color ? color.text : "text-text-main"}`}
        >
          {value}
        </span>
        {unit && <span className="font-sans text-[13px] text-text-dim">{unit}</span>}
      </div>
    </div>
  );
}
