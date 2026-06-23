/**
 * TurnBubble — one conversational bubble in the cockpit trajectory.
 *
 * Ports the mockup's two bubble styles:
 *   - persona (the simulated user): right-aligned, indigo fill, white text;
 *   - RecBot (the agent under test): left-aligned, neutral white + border,
 *     carrying its recommended-item card and the "Tool plan / raw action" fold.
 *
 * A RecBot turn that produced no reply text (a backend hiccup) is rendered
 * honestly — the failure shows as an italic error line rather than passing as a
 * normal reply. Per-turn metadata shows ONLY the real wall-clock latency
 * (`durationSeconds`); tokens/cost are not tracked, so they are never shown.
 *
 * Presentational: the parent owns the fold's open state + the turn data.
 */
import { type ReactNode } from "react";

import { RecommendedItems } from "./RecommendedItems";
import { ToolPlanFold } from "./ToolPlanFold";
import { Sym, fmtLatency } from "./cockpitShared";
import { Markdown } from "../Markdown";
import type { Domain, TurnView } from "@/lib/types";

/** Sentinel the backend uses for a failed/empty agent turn. */
const AGENT_ERROR_TEXT = "Something went wrong, please retry.";

function isHiccup(message: string | null | undefined): boolean {
  if (message == null) return true;
  const t = message.trim();
  return t === "" || t === AGENT_ERROR_TEXT;
}

/** Avatar + name header for a bubble. */
function BubbleHeader({
  side,
  personaName,
}: {
  side: "persona" | "recbot";
  personaName: string;
}) {
  if (side === "persona") {
    return (
      <div className="mb-1 flex items-center gap-2">
        <span className="text-label-md font-label-md font-medium text-on-surface-variant">{personaName} · Persona</span>
        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10" aria-hidden>
          <Sym name="face" fill={1} size={14} className="text-primary" />
        </div>
      </div>
    );
  }
  return (
    <div className="mb-1 flex items-center gap-2">
      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-surface-container-highest" aria-hidden>
        <Sym name="smart_toy" fill={1} size={14} className="text-on-surface-variant" />
      </div>
      <span className="text-label-md font-label-md font-medium text-on-surface-variant">RecBot</span>
    </div>
  );
}

export interface PersonaBubbleProps {
  message: string;
  personaName: string;
}

/** The persona's message (right-aligned, indigo). */
export function PersonaBubble({ message, personaName }: PersonaBubbleProps) {
  return (
    <div className="flex w-full flex-col items-end gap-1 pl-12">
      <BubbleHeader side="persona" personaName={personaName} />
      <div className="rounded-2xl rounded-tr-sm bg-primary p-md text-on-primary shadow-soft">
        <p className="text-body-md leading-relaxed">
          {message?.trim() ? message : <span className="italic opacity-80">(no message)</span>}
        </p>
      </div>
    </div>
  );
}

export interface RecBotBubbleProps {
  turn: TurnView;
  domain: Domain;
  /** Domain-aware header label for the recommended-items card. */
  recommendedTitle?: string;
  recommendedIcon?: string;
  /** Tool-plan fold open state (controlled by the parent for expand-all). */
  foldOpen: boolean;
  onToggleFold: () => void;
}

/** The RecBot reply (left-aligned, neutral) with items + tool-plan fold. */
export function RecBotBubble({
  turn,
  domain,
  recommendedTitle,
  recommendedIcon,
  foldOpen,
  onToggleFold,
}: RecBotBubbleProps) {
  const hiccup = isHiccup(turn.assistantMessage);
  const latency = fmtLatency(turn.durationSeconds);
  const items = turn.recommendedItems ?? [];

  return (
    <div className="mt-3 flex w-full flex-col items-start gap-1 pr-12">
      <BubbleHeader side="recbot" personaName="" />
      <div className="w-full rounded-2xl rounded-tl-sm border border-border-soft bg-surface-container-lowest p-md shadow-soft">
        {hiccup ? (
          <p className="text-body-md italic leading-relaxed text-error">
            RecBot did not return a reply for this turn.
          </p>
        ) : (
          <Markdown className="mb-3 text-body-md text-on-surface">{turn.assistantMessage ?? ""}</Markdown>
        )}

        {items.length > 0 && (
          <RecommendedItems items={items} domain={domain} title={recommendedTitle} icon={recommendedIcon} />
        )}

        <ToolPlanFold
          plan={turn.plan ?? []}
          items={items}
          nativeRaw={turn.nativeRaw ?? null}
          open={foldOpen}
          onToggle={onToggleFold}
        />
      </div>

      {/* Per-turn metadata — REAL latency only (tokens/cost are not tracked). */}
      {latency && (
        <div className="ml-2 mt-1 flex items-center gap-3">
          <span className="flex items-center gap-1 font-mono-sm text-mono-sm text-on-surface-variant">
            <Sym name="timer" size={12} />
            {latency}
          </span>
        </div>
      )}
    </div>
  );
}

/** A turn divider ("Turn N") matching the mockup's marker rule. */
export function TurnMarker({ label, children }: { label: string; children?: ReactNode }) {
  return (
    <div className="my-1 flex w-full items-center">
      <div className="flex-1 border-t border-border-soft" />
      <span className="flex items-center gap-1 bg-background px-3 text-label-md font-label-md uppercase tracking-widest text-on-surface-variant">
        {children}
        {label}
      </span>
      <div className="flex-1 border-t border-border-soft" />
    </div>
  );
}
