/**
 * InspectorTabs — the cockpit's right inspector, as a real ARIA tablist.
 *
 * Replaces the mockup's hidden-radio CSS trick with a proper, fully
 * keyboard-operable tablist (acceptance criterion):
 *   - `role="tablist"` wrapping two `role="tab"` buttons, each
 *     `aria-selected` + `aria-controls` its `role="tabpanel"`;
 *   - roving `tabIndex` (only the active tab is in the tab order);
 *   - ArrowLeft/ArrowRight (+ Home/End) move between tabs and move focus;
 *   - the active tab gets the primary underline + weight, like the mockup.
 *
 * The active tab is controlled by the parent so the global `1`/`2` shortcuts can
 * switch tabs too; selecting a tab here also moves DOM focus to it.
 */
import { useRef } from "react";

import { FOCUS_RING, Sym } from "./cockpitShared";

export type InspectorTab = "evaluation" | "persona" | "prompts";

const TABS: ReadonlyArray<{ id: InspectorTab; label: string; icon: string }> = [
  { id: "evaluation", label: "Evaluation", icon: "verified" },
  { id: "persona", label: "Persona", icon: "person" },
  { id: "prompts", label: "Prompts", icon: "terminal" },
];

export interface InspectorTabsProps {
  active: InspectorTab;
  onChange: (tab: InspectorTab) => void;
  /** Panel content keyed by tab id. */
  evaluation: React.ReactNode;
  persona: React.ReactNode;
  prompts: React.ReactNode;
}

export function InspectorTabs({ active, onChange, evaluation, persona, prompts }: InspectorTabsProps) {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  function focusTab(index: number) {
    const clamped = (index + TABS.length) % TABS.length;
    const tab = TABS[clamped];
    onChange(tab.id);
    tabRefs.current[clamped]?.focus();
  }

  function onKeyDown(e: React.KeyboardEvent, index: number) {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      focusTab(index + 1);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      focusTab(index - 1);
    } else if (e.key === "Home") {
      e.preventDefault();
      focusTab(0);
    } else if (e.key === "End") {
      e.preventDefault();
      focusTab(TABS.length - 1);
    }
  }

  return (
    <aside className="z-0 flex h-full w-[340px] flex-shrink-0 flex-col border-l border-border-soft bg-surface-container-lowest">
      {/* Tab header */}
      <div
        role="tablist"
        aria-label="Inspector"
        aria-orientation="horizontal"
        className="flex flex-shrink-0 items-center gap-lg border-b border-border-soft bg-surface px-md pt-sm"
      >
        {TABS.map((tab, i) => {
          const selected = tab.id === active;
          return (
            <button
              key={tab.id}
              ref={(el) => (tabRefs.current[i] = el)}
              role="tab"
              id={`inspector-tab-${tab.id}`}
              aria-selected={selected}
              aria-controls={`inspector-panel-${tab.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(tab.id)}
              onKeyDown={(e) => onKeyDown(e, i)}
              className={`-mb-px flex select-none items-center gap-1.5 border-b-2 pb-2.5 text-headline-sm font-headline-sm transition-colors duration-200 ${FOCUS_RING} ${
                selected
                  ? "border-primary font-bold text-primary"
                  : "border-transparent text-on-surface-variant hover:text-primary"
              }`}
            >
              <Sym name={tab.icon} fill={selected ? 1 : 0} size={18} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab panels */}
      <div className="custom-scrollbar flex-1 overflow-y-auto">
        <div
          role="tabpanel"
          id="inspector-panel-evaluation"
          aria-labelledby="inspector-tab-evaluation"
          hidden={active !== "evaluation"}
        >
          {active === "evaluation" && evaluation}
        </div>
        <div
          role="tabpanel"
          id="inspector-panel-persona"
          aria-labelledby="inspector-tab-persona"
          hidden={active !== "persona"}
        >
          {active === "persona" && persona}
        </div>
        <div
          role="tabpanel"
          id="inspector-panel-prompts"
          aria-labelledby="inspector-tab-prompts"
          hidden={active !== "prompts"}
        >
          {active === "prompts" && prompts}
        </div>
      </div>
    </aside>
  );
}

export default InspectorTabs;
