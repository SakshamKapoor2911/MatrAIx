/**
 * TurnBubble: one conversational turn in the live-run thread.
 *
 * Ports the mockup's two bubble styles (`app-redesign-v3.html:488-511`):
 *   - persona (the simulated user): left-aligned, `.hud` "Persona" label over a
 *     bordered `bg-surface` bubble with a top-left notch;
 *   - app reply (the agent under test): right-aligned, a `smart_toy` + app-name
 *     label over a bordered bubble carrying the reply, task-configured structured
 *     exposure cards, the "How the app decided" fold, and a meta chip row.
 */
import { type ReactNode } from "react";

import { ChatbotChatAvatar, PersonaChatAvatar } from "./ChatBubbleAvatar";
import { PersonaExposurePanel, exposureItemLists } from "./PersonaExposurePanel";
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
  personaId?: string | null;
  personaDimensions?: Record<string, string>;
}

/** The persona's message: left-aligned, on a bordered surface. */
export function PersonaBubble({ message, personaId, personaDimensions }: PersonaBubbleProps) {
  return (
    <div className="flex w-full items-start gap-2.5 pr-10">
      <PersonaChatAvatar personaId={personaId} dimensions={personaDimensions} />
      <div className="flex min-w-0 flex-1 flex-col items-start">
        <div className="hud mb-1.5 text-[9px] text-text-dim">Persona</div>
        <div className="w-full break-words rounded-md rounded-tl-sm border border-outline bg-surface px-4 py-3 text-[13px] leading-relaxed text-text-main">
          {message?.trim() ? message : <span className="italic text-text-dim">(the user said nothing)</span>}
        </div>
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

/** The app reply: right-aligned, with exposure + tool-plan fold + meta chips. */
export function RecBotBubble({ turn, domain, appName, foldOpen, onToggleFold }: RecBotBubbleProps) {
  void domain;
  const exposure = turn.personaExposure ?? [];
  const items = exposureItemLists(exposure);
  const hiccup = isHiccup(turn.assistantMessage);
  const textlessStructured = hiccup && (items.length > 0 || exposure.length > 0);
  const latency = fmtLatency(turn.durationSeconds);
  const plan = turn.plan ?? [];
  const hasPlan = plan.length > 0;
  const planFailed = plan.some((s) => s.status === "error");

  return (
    <div className="flex w-full justify-end pl-10">
      <div className="flex max-w-full items-start gap-2.5">
        <div className="flex min-w-0 flex-col items-end">
          <div className="hud mb-1.5 text-[9px] text-primary">{appName}</div>
          <div className="max-w-full rounded-md rounded-tr-sm border border-outline bg-surface px-4 py-4">
            {!hiccup ? (
              <Markdown
                className={`text-[13px] leading-relaxed text-text-main ${exposure.length > 0 ? "mb-4 border-b border-outline pb-4" : ""}`}
              >
                {turn.assistantMessage ?? ""}
              </Markdown>
            ) : textlessStructured ? (
              <p className="mb-4 border-b border-outline pb-4 text-[13px] italic leading-relaxed text-text-dim">
                The app returned structured details, but no reply text was captured for this turn.
              </p>
            ) : (
              <p className="text-[13px] italic leading-relaxed text-danger">The app didn&apos;t reply on this turn.</p>
            )}

            {exposure.length > 0 && <PersonaExposurePanel exposure={exposure} />}

            <div className={exposure.length > 0 || !hiccup ? "mt-3" : ""}>
              <ToolPlanFold plan={plan} items={items} nativeRaw={turn.nativeRaw ?? null} open={foldOpen} onToggle={onToggleFold} />
            </div>
          </div>

          {(hasPlan || latency) && (
            <div className="mt-2.5 flex items-center gap-2">
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
        <ChatbotChatAvatar appName={appName} />
      </div>
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
