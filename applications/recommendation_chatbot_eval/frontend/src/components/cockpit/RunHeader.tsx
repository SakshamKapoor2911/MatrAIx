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
  const title = persona ? personaDescriptiveTitle(context, persona.blurb, persona.source) : "No persona selected";
  const codename = persona ? personaCodename(persona.name, persona.id) : null;

  return (
    <div className="flex flex-shrink-0 items-center justify-between border-b border-border-soft bg-surface-container-lowest px-lg py-sm">
      <div className="flex min-w-0 items-center gap-3">
        <h1 className="truncate text-display font-display text-on-surface">{title}</h1>
        {codename && (
          <span className="flex-shrink-0 rounded bg-surface-container px-2 py-1 font-mono-sm text-mono-sm text-on-surface-variant">
            {codename}
          </span>
        )}
      </div>

      <div className="flex flex-shrink-0 items-center gap-3">
        <button
          type="button"
          onClick={onOpenRuns}
          className={`flex items-center gap-1.5 rounded-md px-3 py-2 text-label-md font-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-primary ${FOCUS_RING}`}
        >
          <Sym name="history" size={18} />
          Runs
        </button>
        <button
          type="button"
          onClick={onExport}
          disabled={!canExport}
          className={`flex items-center gap-2 rounded-md border border-outline-variant px-4 py-2 text-label-md font-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
        >
          <Sym name="download" size={18} />
          Export log
        </button>
        <button
          type="button"
          onClick={onRun}
          disabled={!persona || running}
          className={`flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-label-md font-label-md text-on-primary shadow-sm transition-colors hover:bg-primary-container disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
        >
          {running ? (
            <Sym name="autorenew" size={18} className="animate-rb-spin" />
          ) : (
            <Sym name="play_arrow" fill={1} size={18} />
          )}
          {running ? "Running…" : hasRun ? "Re-run eval" : "Run eval"}
        </button>
      </div>
    </div>
  );
}

export default RunHeader;
