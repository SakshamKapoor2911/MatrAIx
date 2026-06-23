/**
 * TopBar — the fixed application header.
 *
 * Ports the approved cockpit nav (`cockpit-stitch-v2.html`): the "RecBot Studio"
 * brand lockup + ⌘K search on the left, the two top-level surfaces
 * (`Chat | Persona Eval`) as a primary-underlined tab row in the middle, and a
 * right-aligned cluster (the readiness chip + — in Chat — the Export / Save /
 * New-session actions).
 *
 * There are exactly two surfaces: the separate "Runs" top-mode is gone — Runs
 * history + Compare now live INSIDE Persona Eval. The Chat config knobs live in
 * a dedicated bar below the header (see `ChatConfigBar`), not in this row, so the
 * nav stays clean at every width.
 */
import { PreflightChip } from "./PreflightChip";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";

/** The two top-level surfaces. Runs live inside Persona Eval, not up here. */
export type StudioMode = "normal" | "persona-eval";

export interface TopBarProps {
  /** Trigger a session export (download). Disabled when no session is active. */
  onExport: () => void;
  /** Persist the active session to disk. Disabled when no session is active. */
  onSave: () => void;
  /** Create a new session. */
  onNew: () => void;
  /** True while a save request is in flight (Save button busy state). */
  saving?: boolean;
  /** Whether session-scoped actions (Export/Save) are available. */
  hasSession: boolean;
  /** Active surface (Chat vs. Persona Eval). */
  mode: StudioMode;
  /** Switch the surface. */
  onModeChange: (mode: StudioMode) => void;
  /** Open the catalog search (the ⌘K palette). */
  onOpenSearch: () => void;
}

/** The two surfaces, with labels for the nav row. */
const MODES: ReadonlyArray<{ value: StudioMode; label: string }> = [
  { value: "normal", label: "Chat" },
  { value: "persona-eval", label: "Persona Eval" },
];

export function TopBar({
  onExport,
  onSave,
  onNew,
  saving,
  hasSession,
  mode,
  onModeChange,
  onOpenSearch,
}: TopBarProps) {
  // The session actions belong to Chat only. Persona Eval owns its own actions
  // inside the cockpit.
  const showSessionTools = mode === "normal";

  return (
    <header className="relative z-20 flex h-16 flex-shrink-0 items-center gap-lg border-b border-border-soft bg-surface-container-lowest px-lg">
      {/* Brand + ⌘K search */}
      <div className="flex flex-shrink-0 items-center gap-md">
        <span className="whitespace-nowrap text-headline-md font-headline-md font-bold tracking-[-0.01em] text-primary">
          RecBot Studio
        </span>
        <button
          type="button"
          onClick={onOpenSearch}
          aria-label="Search the catalog (⌘K)"
          className={`hidden items-center gap-2 rounded-full border border-outline-variant bg-surface-container-low py-1.5 pl-4 pr-3 text-body-sm text-outline transition-colors hover:border-primary hover:text-on-surface-variant xl:flex ${FOCUS_RING}`}
        >
          <Sym name="search" size={16} className="text-outline" />
          <span className="whitespace-nowrap text-on-surface-variant">Search catalog</span>
          <kbd className="ml-2 rounded border border-outline-variant bg-surface-container px-1.5 py-px font-mono-sm text-[11px] text-on-surface-variant">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Two surfaces: Chat | Persona Eval (primary-underlined tabs) */}
      <nav className="flex h-full flex-shrink-0 items-end gap-lg" aria-label="Studio surface">
        {MODES.map(({ value, label }) => {
          const active = value === mode;
          return (
            <button
              key={value}
              type="button"
              aria-current={active ? "page" : undefined}
              onClick={() => !active && onModeChange(value)}
              className={`-mb-px whitespace-nowrap border-b-2 pb-[18px] pt-5 text-body-md transition-colors duration-200 ${FOCUS_RING} ${
                active
                  ? "border-primary font-bold text-primary"
                  : "border-transparent text-on-surface-variant hover:text-primary"
              }`}
            >
              {label}
            </button>
          );
        })}
      </nav>

      {/* Right cluster: readiness + (Chat only) session actions */}
      <div className="ml-auto flex flex-shrink-0 items-center gap-sm">
        <PreflightChip />

        {showSessionTools && (
          <>
            <button
              type="button"
              onClick={onExport}
              disabled={!hasSession}
              className={`flex items-center gap-1.5 rounded-md border border-outline-variant px-3 py-1.5 text-label-md font-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              <Sym name="download" size={16} />
              Export
            </button>
            <button
              type="button"
              onClick={onSave}
              disabled={!hasSession || saving}
              className={`rounded-md border border-outline-variant px-3 py-1.5 text-label-md font-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              onClick={onNew}
              className={`flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-label-md font-label-md text-on-primary shadow-sm transition-colors hover:bg-primary-container ${FOCUS_RING}`}
            >
              <Sym name="add" size={16} />
              New session
            </button>
          </>
        )}
      </div>
    </header>
  );
}
