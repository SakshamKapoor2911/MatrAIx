/**
 * TurnInspector — the Chat workbench right-hand analysis pane.
 *
 * Renders the selected turn's `TurnView`: the tool-plan timeline
 * (BufferStore → HardFilter → Rank → Map) with per-step status nodes, the
 * resolved recommended items with scores, and a collapsible raw native-action
 * block. Styled to the matrAIx tokens.
 *
 * A `<select>` in the header lets the operator jump between turns; when no turn
 * is selected (fresh session) the body shows a quiet teaching empty state.
 */
import { useState } from "react";

import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import type { PlanStep, RecommendedItem, TurnView } from "@/lib/types";

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
          <Sym
            name={error ? "close" : pending ? "more_horiz" : "check"}
            size={13}
          />
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
    <div className="flex items-center gap-2.5 rounded border border-outline bg-surface-low px-2.5 py-2">
      <span className="w-4 flex-none text-center font-mono text-[11px] text-text-dim">{item.rank}</span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[12px] font-medium text-text-main">{item.title ?? item.itemId}</div>
        <div className="font-mono text-[11px] text-text-dim">{item.itemId}</div>
      </div>
      {score && <span className="font-mono text-[11px] font-semibold tabular-nums text-primary">{score}</span>}
    </div>
  );
}

/** Collapsible raw native-action block. */
function NativeRaw({ raw, toolOutputs }: { raw: string | null; toolOutputs: unknown }) {
  const [open, setOpen] = useState(false);
  const hasOutputs =
    toolOutputs !== null && toolOutputs !== undefined && !(Array.isArray(toolOutputs) && toolOutputs.length === 0);

  const body = raw && raw.trim().length > 0 ? raw : "RecAI didn't emit a raw action for this turn.";

  return (
    <div className="border-t border-outline px-md py-4">
      <SectionHeader label="RecAI's raw output" />
      <div className="overflow-hidden rounded-md border border-outline">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className={`flex w-full items-center justify-between p-2 text-xs font-medium text-text-variant transition-colors ${
            open ? "border-b border-outline bg-surface-low" : "bg-surface-low hover:bg-surface-high"
          } ${FOCUS_RING}`}
        >
          <span className="flex items-center gap-2">
            <Sym name="code" size={16} />
            raw model action
          </span>
          <Sym name={open ? "expand_less" : "expand_more"} size={16} />
        </button>
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

/** Pretty-print arbitrary tool output, falling back to String() on cycles. */
function safeJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

/** Quiet teaching empty state when no turn is selected. */
function InspectorEmpty() {
  return (
    <div className="flex h-full items-center justify-center px-6">
      <div className="max-w-[260px] text-center">
        <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl border border-outline bg-surface-high">
          <Sym name="manage_search" size={24} className="text-text-variant" />
        </div>
        <p className="text-[12px] leading-relaxed text-text-variant">
          Click any RecAI reply to see how it answered — the tools it ran, the items it picked, and
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
}

export function TurnInspector({ turns, activeIndex, onSelectIndex }: TurnInspectorProps) {
  const turn = activeIndex !== null ? turns[activeIndex] ?? null : null;

  const plan: PlanStep[] = turn?.plan ?? [];
  const recs: RecommendedItem[] = turn?.recommendedItems ?? [];
  const allOk = plan.length > 0 && plan.every((s) => s.status === "ok");

  return (
    <aside className="flex min-h-0 flex-col border-l border-outline bg-surface-lowest">
      {/* Header with turn picker */}
      <div className="flex flex-shrink-0 items-center gap-2.5 border-b border-outline px-md py-3.5">
        <Sym name="manage_search" size={18} className="text-primary" />
        <span className="hud text-[10px] text-primary">Turn inspector</span>
        {turns.length > 0 && activeIndex !== null && (
          <div className="ml-auto inline-flex items-center gap-1.5 rounded-md border border-outline bg-surface-low px-2 py-1 font-mono text-[11px] text-text-dim">
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
        )}
      </div>

      {/* Body */}
      <div className="custom-scrollbar min-h-0 flex-1 overflow-auto">
        {!turn ? (
          <InspectorEmpty />
        ) : (
          <>
            {/* Tool plan */}
            <div className="border-b border-outline px-md py-4">
              <SectionHeader
                label="What RecAI did"
                count={plan.length > 0 ? `${plan.length} step${plan.length === 1 ? "" : "s"}${allOk ? " · all OK" : ""}` : undefined}
              />
              {plan.length > 0 ? (
                <div className="flex flex-col">
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

            {/* Recommended items */}
            <div className="border-b border-outline px-md py-4">
              <SectionHeader
                label="Items it recommended"
                count={recs.length > 0 ? `${recs.length} items` : undefined}
              />
              {recs.length > 0 ? (
                <div className="space-y-1.5">
                  {recs.map((item) => (
                    <RecItemRow key={item.itemId} item={item} />
                  ))}
                </div>
              ) : (
                <p className="text-[12px] leading-relaxed text-text-variant">
                  RecAI asked you a question this turn instead of recommending.
                </p>
              )}
            </div>

            {/* Native raw */}
            <NativeRaw raw={turn.nativeRaw ?? null} toolOutputs={turn.rawToolOutputs} />
          </>
        )}
      </div>
    </aside>
  );
}
