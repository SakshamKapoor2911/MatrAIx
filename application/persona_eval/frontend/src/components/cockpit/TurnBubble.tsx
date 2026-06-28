/**
 * TurnBubble: one conversational turn in the live-run thread.
 *
 * Ports the mockup's two bubble styles (`app-redesign-v3.html:488-511`):
 *   - persona (the simulated user): right-aligned, `.hud` "Persona" label over a
 *     bordered `bg-surface` bubble with a top-right notch;
 *   - app reply (the agent under test): left-aligned, a `smart_toy` + app-name
 *     label over a full-width bordered bubble carrying the reply, the
 *     recommended-item cards (divided from the reply), the "How the app decided"
 *     fold, and a meta chip row (tool-call status + real latency).
 *
 * An app turn with no reply text (a backend hiccup) is rendered honestly as an
 * italic danger line. Meta shows ONLY the real wall-clock latency
 * (`durationSeconds`): tokens / cost are not tracked, so never shown.
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

export interface PersonaBubbleProps {
  message: string;
}

/** The persona's message: right-aligned, on a bordered surface. */
export function PersonaBubble({ message }: PersonaBubbleProps) {
  return (
    <div className="flex w-full flex-col items-end pl-10">
      <div className="hud mb-1.5 mr-1 text-[9px] text-text-dim">Persona</div>
      <div className="max-w-full break-words rounded-md rounded-tr-sm border border-outline bg-surface px-4 py-3 text-[13px] leading-relaxed text-text-main">
        {message?.trim() ? message : <span className="italic text-text-dim">(the user said nothing)</span>}
      </div>
    </div>
  );
}

export interface RecBotBubbleProps {
  turn: TurnView;
  domain: Domain;
  /** App display name (RecAI / OpenBB / Medical Assistant). */
  appName: string;
  /** Tool-plan fold open state (controlled by the parent for expand-all). */
  foldOpen: boolean;
  onToggleFold: () => void;
}

/** The app reply: left-aligned, with items + tool-plan fold + meta chips. */
export function RecBotBubble({ turn, domain, appName, foldOpen, onToggleFold }: RecBotBubbleProps) {
  const hiccup = isHiccup(turn.assistantMessage);
  const latency = fmtLatency(turn.durationSeconds);
  const items = turn.recommendedItems ?? [];
  const plan = turn.plan ?? [];
  const hasPlan = plan.length > 0;
  const planFailed = plan.some((s) => s.status === "error");

  return (
    <div className="flex w-full flex-col items-start pr-10">
      <div className="hud mb-1.5 ml-1 flex items-center gap-2 text-[9px] text-primary">
        <Sym name="smart_toy" fill={1} size={14} />
        {appName}
      </div>
      <div className="w-full rounded-md rounded-tl-sm border border-outline bg-surface px-4 py-4">
        {hiccup ? (
          <p className="text-[13px] italic leading-relaxed text-danger">The app didn&apos;t reply on this turn.</p>
        ) : (
          <Markdown
            className={`text-[13px] leading-relaxed text-text-main ${items.length > 0 ? "mb-4 border-b border-outline pb-4" : ""}`}
          >
            {turn.assistantMessage ?? ""}
          </Markdown>
        )}

        {items.length > 0 && <RecommendedItems items={items} domain={domain} />}

        <div className={items.length > 0 || !hiccup ? "mt-3" : ""}>
          <ToolPlanFold plan={plan} items={items} nativeRaw={turn.nativeRaw ?? null} open={foldOpen} onToggle={onToggleFold} />
        </div>
      </div>

      {/* Meta chip row: tool-call status + REAL latency only. */}
      {(hasPlan || latency) && (
        <div className="ml-1 mt-2.5 flex items-center gap-2">
          {hasPlan && (
            <span
              className={`hud rounded border px-2 py-1 text-[8px] ${
                planFailed
                  ? "border-danger/25 bg-danger/10 text-danger"
                  : "border-secondary/25 bg-secondary/10 text-secondary"
              }`}
            >
              {planFailed ? "Tool call failed" : "Tool call OK"}
            </span>
          )}
          {latency && (
            <span className="hud flex items-center gap-1 rounded border border-outline px-2 py-1 text-[8px] text-text-dim">
              <Sym name="timer" size={11} />
              {latency}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/** A turn divider ("Turn N"): retained for callers that group turns. */
export function TurnMarker({ label, children }: { label: string; children?: ReactNode }) {
  return (
    <div className="my-1 flex w-full items-center">
      <div className="flex-1 border-t border-outline-dim" />
      <span className="hud flex items-center gap-1 bg-surface-dim px-3 text-[10px] text-text-dim">
        {children}
        {label}
      </span>
      <div className="flex-1 border-t border-outline-dim" />
    </div>
  );
}
