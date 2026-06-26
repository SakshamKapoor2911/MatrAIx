/**
 * TurnBubble — one conversational bubble in the cockpit trajectory.
 *
 * Ports the mockup's two bubble styles:
 *   - persona (the simulated user): right-aligned, on a bordered surface;
 *   - app reply (the agent under test): left-aligned, neutral surface + border,
 *     carrying its recommended-item card and the "How the app decided" fold.
 *
 * An app turn that produced no reply text (a backend hiccup) is rendered
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
        <span className="hud text-[10px] text-text-dim">{personaName} · Persona</span>
        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10" aria-hidden>
          <Sym name="face" fill={1} size={14} className="text-primary" />
        </div>
      </div>
    );
  }
  return (
    <div className="mb-1 flex items-center gap-2">
      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-surface-high" aria-hidden>
        <Sym name="smart_toy" fill={1} size={14} className="text-primary" />
      </div>
      <span className="hud text-[10px] text-primary">The app</span>
    </div>
  );
}

export interface PersonaBubbleProps {
  message: string;
  personaName: string;
}

/** The persona's message (right-aligned, on a bordered surface). */
export function PersonaBubble({ message, personaName }: PersonaBubbleProps) {
  return (
    <div className="flex w-full flex-col items-end gap-1 pl-12">
      <BubbleHeader side="persona" personaName={personaName} />
      <div className="rounded-md rounded-tr-sm border border-outline bg-surface-low p-md text-text-main">
        <p className="text-[13px] leading-relaxed">
          {message?.trim() ? message : <span className="italic text-text-dim">(the user said nothing)</span>}
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

/** The app reply (left-aligned, neutral) with items + tool-plan fold. */
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
      <div className="w-full rounded-md rounded-tl-sm border border-outline bg-surface p-md">
        {hiccup ? (
          <p className="text-[13px] italic leading-relaxed text-danger">
            The app didn&apos;t reply on this turn.
          </p>
        ) : (
          <Markdown className="mb-3 text-[13px] leading-relaxed text-text-main">{turn.assistantMessage ?? ""}</Markdown>
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
          <span className="flex items-center gap-1 font-mono text-[11px] text-text-dim">
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
      <div className="flex-1 border-t border-outline-dim" />
      <span className="flex items-center gap-1 bg-surface-dim px-3 hud text-[10px] text-text-dim">
        {children}
        {label}
      </span>
      <div className="flex-1 border-t border-outline-dim" />
    </div>
  );
}
