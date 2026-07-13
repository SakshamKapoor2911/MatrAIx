/**
 * TopBar: MatrAIx application header.
 *
 * Nav: Home · Playground · Runs · Persona World.
 */
import { PreflightChip } from "./PreflightChip";
import { FOCUS_RING, Sym } from "./cockpit/cockpitShared";
import { MatrAIxLogo } from "./studio/MatrAIxLogo";
import { useTheme } from "@/hooks/useTheme";

export type StudioMode = "home" | "playground";

export interface TopBarProps {
  mode: StudioMode;
  onModeChange: (mode: StudioMode) => void;
  runsActive: boolean;
  storeActive: boolean;
  onOpenHome: () => void;
  onOpenRuns: () => void;
  onOpenPersonaStore: () => void;
}

export function TopBar({
  mode,
  onModeChange,
  runsActive,
  storeActive,
  onOpenHome,
  onOpenRuns,
  onOpenPersonaStore,
}: TopBarProps) {
  const { theme, toggle } = useTheme();
  const nextIsLight = theme === "dark";

  const nav: Array<{ key: string; label: string; active: boolean; onClick: () => void }> = [
    { key: "home", label: "Home", active: mode === "home" && !runsActive && !storeActive, onClick: onOpenHome },
    {
      key: "playground",
      label: "Playground",
      active: mode === "playground" && !runsActive && !storeActive,
      onClick: () => onModeChange("playground"),
    },
    { key: "runs", label: "Runs", active: runsActive, onClick: onOpenRuns },
    { key: "store", label: "Persona World", active: storeActive, onClick: onOpenPersonaStore },
  ];

  return (
    <header className="relative z-20 flex-shrink-0 border-b border-outline bg-surface-lowest">
      <div className="flex h-14 items-center justify-between gap-4 px-5">
        <div className="flex min-w-0 items-center gap-8">
          <MatrAIxLogo size="md" onClick={onOpenHome} />
          <nav className="hidden h-14 items-stretch gap-7 text-[15px] font-medium md:flex" aria-label="Application">
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

        <div className="flex flex-shrink-0 items-center gap-2.5">
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
        </div>
      </div>
    </header>
  );
}
