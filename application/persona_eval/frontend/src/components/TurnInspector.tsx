/**
 * TurnInspector: the Chat workbench right-hand analysis pane.
 *
 * Ports the PersonaEval tabbed inspector (mockup `app-redesign-v3.html:325-336`):
 * a header with a jump-to-turn picker, a Trace / Output / Scores tab strip, and
 * a scrolling body that renders the selected turn's `TurnView`.
 *
 *   - Trace: the tool-plan timeline (BufferStore → HardFilter → Rank → Map),
 *              one status node per `PlanStep`.
 *   - Output: the resolved recommended items + a collapsible, copyable raw
 *              native-action block.
 *   - Scores: an HONEST teaching panel. A manual chat turn isn't scored, so it
 *              surfaces the real per-turn signals we have (latency, item count,
 *              whether RecAI asked a question) and points to PersonaEval for the
 *              full Overall / Constraint / Preference scorecard.
 *
 * The active tab is local presentation state; the turn data plumbing is unchanged.
 */
import { useState } from "react";

import { FOCUS_RING, Sym, fmtLatency } from "./cockpit/cockpitShared";
import type { PlanStep, RecommendedItem, TurnView } from "@/lib/types";

type InspectorTab = "trace" | "output" | "scores";

/** A plan-step tool → a representative Material Symbol. */
const TOOL_ICON: Record<string, string> = {
  bufferstore: "database",
  buffer: "database",
  hardfilter: "filter_alt",
  softfilter: "filter_alt",
  filter: "filter_alt",
  rank: "leaderboard",
  rankingtool: "leaderboard",
  ranking: "leaderboard",
  map: "map",
  lookup: "map",
};

function iconForTool(tool: string): string {
  return TOOL_ICON[tool.toLowerCase().replace(/[^a-z]/g, "")] ?? "bolt";
}

/** Format a score for the mono badge (0.91), tolerating nullish values. */
function fmtScore(score: number | null | undefined): string | null {
  if (score === null || score === undefined || Number.isNaN(score)) return null;
  return score.toFixed(2);
}

/** An uppercase section header with an optional right-aligned count. */
function SectionHeader({ label, count }: { label: string; count?: string }) {
  return (
    <div className="mb-2 flex items-center justify-between">
      <span className="hud text-[9px] text-text-dim">{label}</span>
      {count && <span className="font-mono text-[11px] text-text-dim">{count}</span>}
    </div>
  );
}

/** A single node + connector in the tool-plan timeline. */
function PlanStepRow({ step, last }: { step: PlanStep; last: boolean }) {
  const pending = step.status === "pending";
  const error = step.status === "error";
  const nodeClass = error
    ? "border-danger/40 bg-danger/10 text-danger"
    : pending
      ? "border-outline bg-surface text-text-dim"
      : "border-secondary/40 bg-secondary/10 text-secondary";

  return (
    <div className="flex gap-3 pb-3 last:pb-0">
      <div className="flex flex-none flex-col items-center">
        <div className={`flex h-[22px] w-[22px] items-center justify-center rounded-full border ${nodeClass}`}>
          <Sym name={error ? "close" : pending ? "more_horiz" : "check"} size={13} />
        </div>
        {!last && <div className="mt-1 w-px flex-1 bg-outline" />}
      </div>
      <div className="min-w-0 pt-0.5">
        <div className="flex items-center gap-1.5">
          <Sym name={iconForTool(step.tool)} size={15} className="text-primary" />
          <span className="text-[12px] font-semibold text-text-main">{step.tool}</span>
        </div>
        {step.detail && (
          <div className="mt-0.5 break-words font-mono text-[11px] leading-relaxed text-text-variant">
            {step.detail}
          </div>
        )}
      </div>
    </div>
  );
}

/** One resolved recommended item row in the inspector. */
function RecItemRow({ item }: { item: RecommendedItem }) {
  const score = fmtScore(item.score);
  return (
    <div className="flex items-start gap-2.5 rounded border border-outline bg-surface-low px-2.5 py-2">
      <span className="w-4 flex-none text-center font-mono text-[11px] text-text-dim">{item.rank}</span>
      <div className="min-w-0 flex-1">
        <div className="break-words text-[12px] font-medium text-text-main">{item.title ?? item.itemId}</div>
        <div className="font-mono text-[11px] text-text-dim">{item.itemId}</div>
      </div>
      {score && <span className="flex-none font-mono text-[11px] font-semibold tabular-nums text-primary">{score}</span>}
    </div>
  );
}

/** Pretty-print arbitrary tool output, falling back to String() on cycles. */
function safeJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

/** Collapsible + copyable raw native-action block. */
function NativeRaw({ raw, toolOutputs }: { raw: string | null; toolOutputs: unknown }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const hasOutputs =
    toolOutputs !== null && toolOutputs !== undefined && !(Array.isArray(toolOutputs) && toolOutputs.length === 0);

  const body = raw && raw.trim().length > 0 ? raw : "No raw action was emitted for this turn.";

  const copy = () => {
    const text = hasOutputs ? `${body}\n\n# tool outputs\n${safeJson(toolOutputs)}` : body;
    void navigator.clipboard?.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    });
  };

  return (
    <div>
      <SectionHeader label="Raw output" />
      <div className="overflow-hidden rounded-md border border-outline">
        <div
          className={`flex w-full items-center justify-between text-xs font-medium text-text-variant ${
            open ? "border-b border-outline bg-surface-low" : "bg-surface-low"
          }`}
        >
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className={`flex flex-1 items-center gap-2 p-2 transition-colors hover:bg-surface-high ${FOCUS_RING}`}
          >
            <Sym name="code" size={16} />
            raw model action
            <Sym name={open ? "expand_less" : "expand_more"} size={16} className="ml-auto" />
          </button>
          <button
            type="button"
            onClick={copy}
            title="Copy raw output"
            aria-label="Copy raw output"
            className={`flex-none border-l border-outline p-2 text-text-variant transition hover:text-text-main active:scale-95 ${FOCUS_RING}`}
          >
            <Sym name={copied ? "check" : "content_copy"} size={14} />
          </button>
        </div>
        {open && (
          <>
            <pre className="panel overflow-x-auto whitespace-pre-wrap break-words bg-surface p-3 font-mono text-[10.5px] leading-relaxed text-text-variant">
              {body}
            </pre>
            {hasOutputs && (
              <pre className="overflow-x-auto whitespace-pre-wrap break-words border-t border-outline bg-surface p-3 font-mono text-[10.5px] leading-relaxed text-text-variant">
                <span className="text-text-dim"># tool outputs</span>
                {"\n"}
                {safeJson(toolOutputs)}
              </pre>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/** A compact stat card for the Scores tab. */
function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-outline bg-surface p-4">
      <div className="hud text-[9px] text-text-dim">{label}</div>
      <div className="mt-1.5 font-display text-[20px] font-bold tabular-nums text-text-main">{value}</div>
    </div>
  );
}

/** Quiet teaching empty state when no turn is selected. */
function InspectorEmpty() {
  return (
    <div className="flex h-full items-center justify-center px-6">
      <div className="max-w-[260px] text-center">
        <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-md border border-outline bg-surface-high">
          <Sym name="manage_search" size={24} className="text-text-variant" />
        </div>
        <p className="text-[12px] leading-relaxed text-text-variant">
          Click any reply to see how it answered: the tools it ran, the items it picked, and
          its raw output.
        </p>
      </div>
    </div>
  );
}

export interface TurnInspectorProps {
  /** All turns of the active session (for the turn picker). */
  turns: TurnView[];
  /** Index of the focused turn, or `null` for the empty state. */
  activeIndex: number | null;
  onSelectIndex: (index: number) => void;
  /** Jump to the PersonaEval surface (the honest "score this" link target). */
  onScoreInPersonaEval?: () => void;
}

const TABS: ReadonlyArray<{ value: InspectorTab; label: string }> = [
  { value: "trace", label: "Trace" },
  { value: "output", label: "Output" },
  { value: "scores", label: "Scores" },
];

export function TurnInspector({ turns, activeIndex, onSelectIndex, onScoreInPersonaEval }: TurnInspectorProps) {
  const [tab, setTab] = useState<InspectorTab>("trace");
  const turn = activeIndex !== null ? turns[activeIndex] ?? null : null;

  const plan: PlanStep[] = turn?.plan ?? [];
  const recs: RecommendedItem[] = turn?.recommendedItems ?? [];
  const allOk = plan.length > 0 && plan.every((s) => s.status === "ok");
  const askedQuestion = recs.length === 0;
  const latency = fmtLatency(turn?.durationSeconds);

  return (
    <aside className="hidden min-h-0 w-[360px] flex-shrink-0 flex-col border-l border-outline bg-surface-lowest xl:flex">
      {/* Header with turn picker */}
      <div className="flex flex-shrink-0 items-center justify-between gap-2.5 border-b border-outline bg-surface px-4 py-3">
        <span className="hud text-[10px] text-primary">Turn inspector</span>
        {turns.length > 0 && activeIndex !== null ? (
          <div className="inline-flex items-center gap-1.5 rounded-md border border-outline bg-surface-low px-2 py-1 font-mono text-[11px] text-text-dim transition-colors hover:border-primary/60">
            <span>turn</span>
            <div className="relative inline-flex items-center">
              <select
                value={activeIndex}
                onChange={(e) => onSelectIndex(Number(e.target.value))}
                aria-label="Select turn"
                className={`cursor-pointer appearance-none bg-transparent pr-4 font-semibold text-text-main outline-none ${FOCUS_RING}`}
              >
                {turns.map((_, i) => (
                  <option key={i} value={i}>
                    {i + 1}
                  </option>
                ))}
              </select>
              <Sym name="expand_more" size={14} className="pointer-events-none absolute right-0 text-text-dim" />
            </div>
          </div>
        ) : (
          <span className="hud text-[9px] text-text-dim">no turn</span>
        )}
      </div>

      {/* Tab strip */}
      <div className="flex flex-shrink-0 items-center gap-5 border-b border-outline px-4 text-[12px]">
        {TABS.map(({ value, label }) => {
          const active = value === tab;
          return (
            <button
              key={value}
              type="button"
              onClick={() => setTab(value)}
              aria-current={active ? "true" : undefined}
              className={`-mb-px border-b-2 py-2.5 transition-colors ${FOCUS_RING} ${
                active
                  ? "border-primary text-primary"
                  : "border-transparent text-text-variant hover:text-text-main"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Body */}
      <div className="custom-scrollbar min-h-0 flex-1 space-y-5 overflow-auto p-4">
        {!turn ? (
          <InspectorEmpty />
        ) : tab === "trace" ? (
          <div key={`trace-${activeIndex}`} className="rise-in">
            <SectionHeader
              label="Execution trace"
              count={
                plan.length > 0
                  ? `${plan.length} step${plan.length === 1 ? "" : "s"}${allOk ? " · all OK" : ""}`
                  : undefined
              }
            />
            {plan.length > 0 ? (
              <div className="flex flex-col rounded-md border border-outline bg-surface p-4">
                {plan.map((step, i) => (
                  <PlanStepRow key={i} step={step} last={i === plan.length - 1} />
                ))}
              </div>
            ) : (
              <p className="text-[12px] leading-relaxed text-text-variant">
                No tool steps were recorded for this turn.
              </p>
            )}
          </div>
        ) : tab === "output" ? (
          <div key={`output-${activeIndex}`} className="rise-in space-y-5">
            <div>
              <SectionHeader label="Items it recommended" count={recs.length > 0 ? `${recs.length} items` : undefined} />
              {recs.length > 0 ? (
                <div className="space-y-1.5">
                  {recs.map((item) => (
                    <RecItemRow key={item.itemId} item={item} />
                  ))}
                </div>
              ) : (
                <p className="text-[12px] leading-relaxed text-text-variant">
                  The assistant asked you a question this turn instead of answering.
                </p>
              )}
            </div>
            <NativeRaw raw={turn.nativeRaw ?? null} toolOutputs={turn.rawToolOutputs} />
          </div>
        ) : (
          /* Scores: honest teaching panel */
          <div key={`scores-${activeIndex}`} className="rise-in space-y-5">
            <div>
              <SectionHeader label="Per-turn signals" />
              <div className="grid grid-cols-3 gap-3">
                <StatCard label="Latency" value={latency ?? "n/a"} />
                <StatCard label="Items" value={String(recs.length)} />
                <StatCard label="Asked Q" value={askedQuestion ? "Yes" : "No"} />
              </div>
            </div>
            <p className="text-[12px] leading-relaxed text-text-variant">
              This is a manual chat, so it isn&apos;t scored. What we can show: it replied
              {latency ? ` in ${latency}` : ""}, recommended {recs.length} item{recs.length === 1 ? "" : "s"}
              {askedQuestion ? ", and asked a clarifying question" : ""}. For Overall / Constraint /
              Preference scores, run this persona in PersonaEval.
            </p>
            {onScoreInPersonaEval && (
              <button
                type="button"
                onClick={onScoreInPersonaEval}
                className={`group inline-flex items-center gap-1.5 text-[12px] font-medium text-primary transition-colors hover:text-primary-dim ${FOCUS_RING}`}
              >
                Score this persona in PersonaEval
                <Sym name="arrow_forward" size={14} className="transition-transform group-hover:translate-x-0.5" />
              </button>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
