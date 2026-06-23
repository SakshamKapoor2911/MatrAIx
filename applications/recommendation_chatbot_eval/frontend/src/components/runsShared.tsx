/**
 * Shared helpers + precise types for the Runs monitoring surface.
 *
 * `src/lib/types.ts` declares the persisted-run shapes loosely (`transcript:
 * TurnView[]`, `recommendedItemIds: Record<string, unknown>`) to stay tolerant
 * of legacy artifacts. The live backend returns a richer, more specific shape
 * (verified against the running API), so the Runs views narrow it here — at the
 * read boundary — into the fields they actually render, rather than threading
 * `unknown` through the components.
 */
import { Sym } from "./cockpit/cockpitShared";
import type { Domain, PersonaEvalMetricScores, PersonaEvalResult } from "@/lib/types";

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
}

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
};

/** Narrow a raw `PersonaEvalResult` into the richer `RunDetailView` shape. */
export function asRunDetail(raw: PersonaEvalResult): RunDetailView {
  return raw as unknown as RunDetailView;
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
 * unparseable / missing value renders as an em dash.
 */
export function fmtRunDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "—";
  const date = new Date(t);
  const diffMs = Date.now() - t;
  const sec = Math.round(diffMs / 1000);
  if (sec < 0) return shortAbsolute(date); // clock skew — just show the date
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
  if (!domain) return "—";
  const spaced = domain.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** Render a persona `source`, falling back to "curated" / em dash when absent. */
export function fmtSource(source: string | null | undefined): string {
  if (source === null || source === undefined || source === "") return "curated";
  return source;
}

/**
 * Friendly label for a goal-context id (the conversation style), mirroring the
 * cockpit knob copy: `scenario_default` → "Realistic scenario", `gradual_reveal`
 * → "Gradual reveal". Unknown ids are humanized; a missing id reads as an em dash.
 */
const GOAL_CONTEXT_LABELS: Record<string, string> = {
  scenario_default: "Realistic scenario",
  gradual_reveal: "Gradual reveal",
};

export function fmtGoalContext(id: string | null | undefined): string {
  if (!id) return "—";
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
    <span className="inline-flex items-center rounded-md border border-border-soft bg-surface-container px-2 py-0.5 text-label-md font-label-md font-medium text-on-surface-variant">
      {fmtDomain(domain)}
    </span>
  );
}

/** A small muted source tag next to a persona name. */
export function SourceTag({ source }: { source: string | null | undefined }) {
  return (
    <span className="inline-flex items-center rounded bg-surface-container px-1.5 py-px font-mono-sm text-[10.5px] text-on-surface-variant">
      {fmtSource(source)}
    </span>
  );
}

/**
 * Grounding indicator — did the recommender actually return real catalog items,
 * or did the agent answer from base knowledge? A run can read smoothly (and even
 * self-score highly) while recommending nothing real, so we surface this plainly:
 * `N grounded` (green) when the corpus was used, `Ungrounded` (amber) when zero
 * catalog items were recommended.
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
      className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-label-md font-label-md font-medium ${
        grounded
          ? "bg-success-container text-on-success-container"
          : "bg-warning-container text-warning"
      } ${className}`}
      title={
        grounded
          ? `${count} item${count === 1 ? "" : "s"} recommended from the real catalog`
          : "No catalog items recommended — the agent's suggestions aren't grounded in the corpus (base knowledge)"
      }
    >
      <Sym name={grounded ? "inventory_2" : "warning"} size={13} />
      {grounded ? `${count} grounded` : "Ungrounded"}
    </span>
  );
}

/** A compact recommended-item chip (mono id + title) for trajectories. */
export function RecChip({ item }: { item: RunRecItem }) {
  return (
    <span className="inline-flex max-w-full items-center gap-1.5 rounded-md border border-border-soft bg-surface-container-lowest px-2 py-1 text-label-md">
      <span className="font-mono-sm text-[10.5px] text-on-surface-variant">{item.id}</span>
      {item.title && <span className="truncate text-on-surface-variant">{item.title}</span>}
    </span>
  );
}
