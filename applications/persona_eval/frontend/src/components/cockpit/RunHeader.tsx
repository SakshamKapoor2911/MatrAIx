/**
 * RunHeader — the cockpit centre header (above the knob bar).
 *
 * Ports the mockup's run header: the persona identity on the left (a human
 * descriptive title + the machine codename chip — the codename heading gets
 * human framing) and the run actions on the right (Runs · Export log · Run /
 * Re-run eval). The primary action relabels between "Run eval" and "Re-run
 * eval" depending on whether a run has been produced, and shows a busy state
 * while a run is in flight.
 *
 * Presentational: the parent owns the selection + the run lifecycle and passes
 * the handlers. Icon-only / compact controls carry `aria-label`s.
 */
import { FOCUS_RING, Sym, personaCodename, personaDescriptiveTitle } from "./cockpitShared";
import type { PersonaEvalPersona } from "@/lib/types";

export interface RunHeaderProps {
  persona: PersonaEvalPersona | null;
  /** Full context, when loaded (sharpens the descriptive title). */
  context: string | null;
  /** A run is in flight. */
  running: boolean;
  /** A terminal run exists (so the button reads "Re-run"). */
  hasRun: boolean;
  /** Run / re-run the eval. */
  onRun: () => void;
  /** Export the current run log (client-side JSON download). */
  onExport: () => void;
  /** Whether an export is available (there are turns to export). */
  canExport: boolean;
  /** Open the Runs surface. */
  onOpenRuns: () => void;
}

export function RunHeader({
  persona,
  context,
  running,
  hasRun,
  onRun,
  onExport,
  canExport,
  onOpenRuns,
}: RunHeaderProps) {
  const title = persona ? personaDescriptiveTitle(context, persona.blurb, persona.source) : "No persona chosen yet";
  const codename = persona ? personaCodename(persona.name, persona.id) : null;

  return (
    <div className="flex flex-shrink-0 items-center justify-between border-b border-outline-dim bg-surface-lowest px-5 py-sm">
      <div className="flex min-w-0 items-center gap-3">
        <h1 className="truncate font-display text-[20px] font-bold tracking-tight text-text-main">{title}</h1>
        {codename && (
          <span className="flex-shrink-0 rounded bg-surface-high px-2 py-1 font-mono text-[11px] text-text-dim">
            {codename}
          </span>
        )}
        {persona?.source && (
          <span className="hud flex-shrink-0 rounded border border-secondary/30 bg-secondary/10 px-1.5 py-0.5 text-[9px] text-secondary">
            {persona.source}
          </span>
        )}
      </div>

      <div className="flex flex-shrink-0 flex-col items-end gap-1">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onOpenRuns}
            className={`flex items-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium text-text-variant transition-colors hover:bg-surface hover:text-primary ${FOCUS_RING}`}
          >
            <Sym name="history" size={18} />
            Past runs
          </button>
          <button
            type="button"
            onClick={onExport}
            disabled={!canExport}
            title="Save this conversation and its scores as a JSON file."
            className={`flex items-center gap-2 rounded-md border border-outline bg-surface-low px-4 py-2 text-xs font-medium text-text-variant transition-colors hover:border-primary hover:text-text-main disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
          >
            <Sym name="download" size={18} />
            Download transcript
          </button>
          <button
            type="button"
            onClick={onRun}
            disabled={!persona || running}
            className={`glow flex items-center gap-2 rounded-md bg-primary px-4 py-2 font-display text-sm font-semibold text-on-primary transition-colors hover:bg-primary-dim disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
          >
            {running ? (
              <Sym name="autorenew" size={18} className="animate-rb-spin" />
            ) : (
              <Sym name="play_arrow" fill={1} size={18} />
            )}
            {running ? "Running…" : hasRun ? "Run again" : "Run simulation"}
          </button>
        </div>
        <p className="max-w-[22rem] text-right text-[11px] leading-relaxed text-text-dim">
          A simulated user chats with the app for a few turns, then rates how well it understood and met their needs.
        </p>
      </div>
    </div>
  );
}

export default RunHeader;
