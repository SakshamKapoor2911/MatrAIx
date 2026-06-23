/**
 * ToolPlanFold — the expandable "Tool plan / raw action" disclosure on a
 * RecBot turn.
 *
 * Ports the mockup's fold: a header button that expands to reveal (when the
 * data is present) the parsed tool-plan steps, the ranked items with their
 * scores, and the raw native action text. Each section renders only when it has
 * content, so a turn that carried no tool plan / no raw action shows just the
 * sections it actually has — never empty scaffolding.
 *
 * Controlled disclosure: the parent owns `open` (so the "expand/collapse all"
 * keyboard shortcut can drive every fold at once) and gets `onToggle`. The
 * header is a real `aria-expanded` button targeting the panel by id.
 */
import { useId } from "react";

import { FOCUS_RING, Sym } from "./cockpitShared";
import type { PlanStep, RecommendedItem } from "@/lib/types";

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

export interface ToolPlanFoldProps {
  plan: PlanStep[];
  /** Ranked items (for the "Ranked items · scores" section). */
  items: RecommendedItem[];
  /** Raw native action text (the model's own output), if any. */
  nativeRaw: string | null;
  open: boolean;
  onToggle: () => void;
}

export function ToolPlanFold({ plan, items, nativeRaw, open, onToggle }: ToolPlanFoldProps) {
  const panelId = useId();
  const scored = items.filter((i) => i.score !== null && i.score !== undefined);
  const hasPlan = plan.length > 0;
  const hasScores = scored.length > 0;
  const hasRaw = Boolean(nativeRaw && nativeRaw.trim());
  const hasBody = hasPlan || hasScores || hasRaw;

  return (
    <div
      className={`overflow-hidden rounded-md border ${
        open ? "border-outline-variant bg-surface-container-lowest" : "border-outline-variant bg-surface-container-low"
      }`}
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={hasBody ? panelId : undefined}
        className={`flex w-full items-center justify-between p-2 text-label-md font-label-md text-on-surface-variant transition-colors ${
          open ? "border-b border-outline-variant bg-surface-container-low" : "hover:bg-surface-variant"
        } ${FOCUS_RING}`}
      >
        <span className="flex items-center gap-2">
          <Sym name="code" size={16} />
          Tool plan / raw action
        </span>
        <Sym name={open ? "expand_less" : "expand_more"} size={16} />
      </button>

      {open && (
        <div id={panelId}>
          {!hasBody && (
            <p className="p-3 text-body-sm text-on-surface-variant">
              No tool plan or raw action was recorded for this turn.
            </p>
          )}

          {hasPlan && (
            <div className="border-b border-outline-variant p-3">
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-on-surface-variant">Tool plan</p>
              <ol className="space-y-1.5">
                {plan.map((step, i) => (
                  <li key={i} className="flex items-center gap-2 text-body-sm text-on-surface">
                    <span className="w-4 font-mono-sm text-mono-sm text-on-surface-variant">{i + 1}</span>
                    <Sym name={iconForTool(step.tool)} size={15} className="text-primary" />
                    <span className="font-mono-sm font-medium">{step.tool}</span>
                    {step.detail && <span className="truncate text-on-surface-variant">{step.detail}</span>}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {hasScores && (
            <div className="border-b border-outline-variant p-3">
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-on-surface-variant">
                Ranked items · scores
              </p>
              <div className="space-y-1 font-mono-sm text-mono-sm text-on-surface-variant">
                {scored.map((item) => (
                  <div key={`${item.itemId}-${item.rank}`} className="flex items-center justify-between gap-3">
                    <span className="truncate">
                      {item.itemId}
                      {item.title ? ` · ${item.title}` : ""}
                    </span>
                    <span className="flex-shrink-0 text-on-surface">{item.score?.toFixed(3)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {hasRaw && (
            <pre className="overflow-x-auto whitespace-pre-wrap break-words bg-surface p-3 font-mono-sm text-mono-sm text-on-surface-variant">
              {nativeRaw}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

export default ToolPlanFold;
