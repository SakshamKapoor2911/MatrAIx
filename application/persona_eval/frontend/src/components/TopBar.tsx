/**
 * TopBar: the fixed application header (mockup `app-redesign-v3.html:62-91`).
 *
 * Left: the PersonaEval wordmark + a 4-item nav (Chat ·
 * PersonaEval · Runs · Catalog) with the active surface primary-underlined.
 * Right: the ⌘K "Search catalog" pill, the readiness chip, the light/dark theme
 * toggle, and a context primary button (New chat in Chat / New run in
 * PersonaEval). Export / Save appear only on the Chat surface.
 *
 * Nav routing is delegated to the parent (`App` owns `useUrlState`): Chat /
 * PersonaEval switch the surface, Runs opens the PersonaEval Runs sub-view, and
 * Catalog opens the ⌘K catalog drawer.
 */
import { PreflightChip } from "./PreflightChip";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { useTheme } from "@/hooks/useTheme";

/** The two top-level surfaces. Runs is a sub-view inside PersonaEval. */
export type StudioMode = "normal" | "persona-eval";

export interface TopBarProps {
  /** Trigger a session export (download). Disabled when no session is active. */
  onExport: () => void;
  /** Persist the active session to disk. Disabled when no session is active. */
  onSave: () => void;
  /** Create a new session (Chat): the context primary button. */
  onNew: () => void;
  /** True while a save request is in flight (Save button busy state). */
  saving?: boolean;
  /** Whether session-scoped actions (Export/Save) are available. */
  hasSession: boolean;
  /** Active surface (Chat vs. PersonaEval). */
  mode: StudioMode;
  /** Switch the surface. */
  onModeChange: (mode: StudioMode) => void;
  /** True when the PersonaEval Runs sub-view is showing (drives the Runs tab). */
  runsActive: boolean;
  /** Open the PersonaEval Runs history sub-view. */
  onOpenRuns: () => void;
  /** Open the catalog search (the ⌘K palette / Catalog nav item). */
  onOpenSearch: () => void;
}

export function TopBar({
  onExport,
  onSave,
  onNew,
  saving,
  hasSession,
  mode,
  onModeChange,
  runsActive,
  onOpenRuns,
  onOpenSearch,
}: TopBarProps) {
  const showSessionTools = mode === "normal";
  const { theme, toggle } = useTheme();
  const nextIsLight = theme === "dark";

  // The four nav surfaces, with their active rule + handler.
  const nav: Array<{ key: string; label: string; active: boolean; onClick: () => void }> = [
    { key: "chat", label: "Chat", active: mode === "normal", onClick: () => onModeChange("normal") },
    {
      key: "peval",
      label: "PersonaEval",
      active: mode === "persona-eval" && !runsActive,
      onClick: () => onModeChange("persona-eval"),
    },
    { key: "runs", label: "Runs", active: mode === "persona-eval" && runsActive, onClick: onOpenRuns },
    { key: "catalog", label: "Catalog", active: false, onClick: onOpenSearch },
  ];

  return (
    <header className="relative z-20 flex-shrink-0 border-b border-outline bg-surface-lowest">
      <div className="flex h-14 items-center justify-between gap-4 px-5">
        {/* Brand + nav */}
        <div className="flex min-w-0 items-center gap-8">
          <button
            type="button"
            onClick={() => onModeChange("normal")}
            aria-label="PersonaEval home"
            className={`whitespace-nowrap font-display text-[19px] font-bold tracking-tight text-text-main transition hover:opacity-90 active:scale-[0.97] ${FOCUS_RING}`}
          >
            Persona<span className="text-primary">Eval</span>
          </button>
          <nav className="hidden h-14 items-stretch gap-7 text-[13px] font-medium md:flex" aria-label="Application surface">
            {nav.map(({ key, label, active, onClick }) => (
              <button
                key={key}
                type="button"
                onClick={onClick}
                aria-current={active ? "page" : undefined}
                className={`flex h-14 items-center border-b-2 transition-colors ${FOCUS_RING} ${
                  active
                    ? "border-primary text-primary"
                    : "border-transparent text-text-variant hover:text-text-main"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>

        {/* Right cluster */}
        <div className="flex flex-shrink-0 items-center gap-2.5">
          <button
            type="button"
            onClick={onOpenSearch}
            aria-label="Search the catalog of personas and items. Press Command-K"
            className={`hidden h-9 items-center gap-2 rounded-md border border-outline bg-surface-low pl-3 pr-2 text-[12px] text-text-variant transition hover:border-primary hover:text-text-main active:scale-[0.98] lg:flex ${FOCUS_RING}`}
          >
            <Sym name="search" size={14} className="text-text-dim" />
            <span className="whitespace-nowrap">Search catalog</span>
            <kbd className="ml-1 rounded border border-outline bg-surface px-1.5 py-px font-mono text-[10px] text-text-variant">
              ⌘K
            </kbd>
          </button>

          <PreflightChip />

          <button
            type="button"
            onClick={toggle}
            aria-label={nextIsLight ? "Switch to light theme" : "Switch to dark theme"}
            title="Toggle light / dark"
            className={`grid h-9 w-9 flex-none place-items-center rounded-md border border-outline text-text-variant transition hover:border-primary hover:text-text-main active:scale-95 ${FOCUS_RING}`}
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
                className={`hidden h-9 items-center gap-2 rounded-md border border-outline px-3 text-xs font-medium text-text-variant transition hover:bg-surface-low hover:text-text-main active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-55 sm:flex ${FOCUS_RING}`}
              >
                <Sym name="download" size={16} />
                Export
              </button>
              <button
                type="button"
                onClick={onSave}
                disabled={!hasSession || saving}
                title="Save this chat to the server"
                className={`hidden h-9 items-center rounded-md border border-outline px-3 text-xs font-medium text-text-variant transition hover:bg-surface-low hover:text-text-main active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-55 sm:flex ${FOCUS_RING}`}
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </>
          )}

          {/* Context primary button: New chat (Chat) / New run (PersonaEval) */}
          {showSessionTools ? (
            <button
              type="button"
              onClick={onNew}
              className={`flex items-center gap-2 rounded-md bg-primary h-9 px-3.5 text-[12px] font-semibold text-on-primary transition hover:bg-primary-dim active:scale-[0.98] ${FOCUS_RING}`}
            >
              <Sym name="add" size={16} />
              <span className="hidden sm:inline">New chat</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onModeChange("persona-eval")}
              title="Configure and launch a new evaluation run"
              className={`flex items-center gap-2 rounded-md bg-primary h-9 px-3.5 text-[12px] font-semibold text-on-primary transition hover:bg-primary-dim active:scale-[0.98] ${FOCUS_RING}`}
            >
              <Sym name="play_arrow" fill={1} size={16} />
              <span className="hidden sm:inline">New run</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
