/**
 * TopBar — the fixed application header.
 *
 * Carries the matrAIx wordmark + ⌘K search on the left, the two top-level
 * surfaces (`Chat | PersonaEval`) as a primary-underlined tab row in the middle,
 * and a right-aligned cluster (the readiness chip, the light/dark theme toggle,
 * and — in Chat — the Export / Save / New-chat actions).
 *
 * There are exactly two surfaces: the separate "Runs" top-mode is gone — Runs
 * history + Compare now live INSIDE PersonaEval. The Chat config knobs live in
 * a dedicated bar below the header (see `ChatConfigBar`), not in this row, so the
 * nav stays clean at every width.
 */
import { PreflightChip } from "./PreflightChip";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { useTheme } from "@/hooks/useTheme";

/** The two top-level surfaces. Runs live inside PersonaEval, not up here. */
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
  /** Active surface (Chat vs. PersonaEval). */
  mode: StudioMode;
  /** Switch the surface. */
  onModeChange: (mode: StudioMode) => void;
  /** Open the catalog search (the ⌘K palette). */
  onOpenSearch: () => void;
}

/** The two surfaces, with labels for the nav row. */
const MODES: ReadonlyArray<{ value: StudioMode; label: string }> = [
  { value: "normal", label: "Chat" },
  { value: "persona-eval", label: "PersonaEval" },
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
  // The session actions belong to Chat only. PersonaEval owns its own actions
  // inside the cockpit.
  const showSessionTools = mode === "normal";
  const { theme, toggle } = useTheme();
  const nextIsLight = theme === "dark";

  return (
    <header className="relative z-20 flex h-auto min-h-14 flex-shrink-0 flex-wrap items-center gap-x-lg gap-y-2 border-b border-outline bg-surface-lowest px-md py-2 sm:h-14 sm:flex-nowrap sm:px-lg sm:py-0">
      {/* Brand + ⌘K search */}
      <div className="flex flex-shrink-0 items-center gap-md">
        <span className="whitespace-nowrap font-display text-[19px] font-bold tracking-tight text-text-main">
          matr<span className="text-primary">AI</span>x
        </span>
        <button
          type="button"
          onClick={onOpenSearch}
          aria-label="Search the catalog of personas and items — press Command-K"
          className={`hidden items-center gap-2 rounded-md border border-outline bg-surface-low py-1.5 pl-4 pr-3 text-[12px] text-text-dim transition-colors hover:border-primary hover:text-text-variant xl:flex ${FOCUS_RING}`}
        >
          <Sym name="search" size={16} className="text-text-dim" />
          <span className="whitespace-nowrap text-text-variant">Search personas &amp; items</span>
          <kbd className="ml-2 rounded border border-outline bg-surface px-1.5 py-px font-mono text-[10px] text-text-variant">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Two surfaces: Chat | PersonaEval (primary-underlined tabs) */}
      <nav className="flex h-full flex-shrink-0 items-end gap-lg" aria-label="Application surface">
        {MODES.map(({ value, label }) => {
          const active = value === mode;
          return (
            <button
              key={value}
              type="button"
              aria-current={active ? "page" : undefined}
              onClick={() => !active && onModeChange(value)}
              className={`-mb-px whitespace-nowrap border-b-2 pb-[18px] pt-5 text-[13px] font-medium transition-colors duration-200 ${FOCUS_RING} ${
                active
                  ? "border-primary font-bold text-primary"
                  : "border-transparent text-text-variant hover:text-text-main"
              }`}
            >
              {label}
            </button>
          );
        })}
      </nav>

      {/* Right cluster: readiness + theme toggle + (Chat only) session actions */}
      <div className="ml-auto flex flex-shrink-0 items-center gap-sm">
        <PreflightChip />

        <button
          type="button"
          onClick={toggle}
          aria-label={nextIsLight ? "Switch to light theme" : "Switch to dark theme"}
          title={nextIsLight ? "Switch to light theme" : "Switch to dark theme"}
          className={`grid h-9 w-9 flex-none place-items-center rounded-md border border-outline text-text-variant transition-colors hover:border-primary hover:text-text-main ${FOCUS_RING}`}
        >
          <Sym name={nextIsLight ? "light_mode" : "dark_mode"} size={18} />
        </button>

        {showSessionTools && (
          <>
            <button
              type="button"
              onClick={onExport}
              disabled={!hasSession}
              title="Download this chat as a file"
              className={`flex items-center gap-1.5 rounded-md border border-outline px-3 py-1.5 text-xs font-medium text-text-variant transition-colors hover:bg-surface-low hover:text-text-main disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              <Sym name="download" size={16} />
              Export
            </button>
            <button
              type="button"
              onClick={onSave}
              disabled={!hasSession || saving}
              title="Save this chat to the server"
              className={`rounded-md border border-outline px-3 py-1.5 text-xs font-medium text-text-variant transition-colors hover:bg-surface-low hover:text-text-main disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
            >
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              onClick={onNew}
              className={`flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-on-primary transition-colors hover:bg-primary-dim ${FOCUS_RING}`}
            >
              <Sym name="add" size={16} />
              New chat
            </button>
          </>
        )}
      </div>
    </header>
  );
}
