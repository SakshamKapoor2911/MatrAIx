/**
 * InspectorTabs: the live-run right inspector, as a real ARIA tablist.
 *
 * Ports the mockup's inspector aside (`app-redesign-v3.html:325-336`): a header
 * bar ("Inspector"), a row of underline tabs, then the scrollable panel body.
 * The three panels are Evaluation (`Scorecard`) · Persona (`PersonaPanel`) ·
 * Prompts (`PromptPanel`).
 *
 * A proper, fully keyboard-operable tablist: `role="tablist"` over `role="tab"`
 * buttons (`aria-selected` + `aria-controls`), roving `tabIndex`, and
 * ArrowLeft/Right (+ Home/End) to move + focus. The active tab is controlled by
 * the parent so the global `1`/`2`/`3` shortcuts switch tabs too.
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
  const activeLabel = TABS.find((t) => t.id === active)?.label ?? "";

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
    <aside className="z-0 flex h-[340px] w-full flex-shrink-0 flex-col border-t border-outline bg-surface-lowest lg:h-full lg:w-[360px] lg:border-l lg:border-t-0">
      {/* Header bar */}
      <div className="flex shrink-0 items-center justify-between border-b border-outline bg-surface px-4 py-3">
        <span className="hud text-[10px] text-primary">Inspector</span>
        <span className="hud text-[9px] text-text-dim">{activeLabel}</span>
      </div>

      {/* Underline tabs */}
      <div
        role="tablist"
        aria-label="Inspector"
        aria-orientation="horizontal"
        className="flex shrink-0 items-center gap-5 border-b border-outline px-4"
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
              className={`-mb-px flex select-none items-center gap-1.5 border-b-2 py-2.5 text-[12px] font-medium transition ease-out active:opacity-70 ${FOCUS_RING} ${
                selected ? "border-primary text-primary" : "border-transparent text-text-variant hover:text-text-main"
              }`}
            >
              <Sym name={tab.icon} fill={selected ? 1 : 0} size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Panels */}
      <div className="custom-scrollbar flex-1 overflow-y-auto">
        <div role="tabpanel" id="inspector-panel-evaluation" aria-labelledby="inspector-tab-evaluation" hidden={active !== "evaluation"}>
          {active === "evaluation" && evaluation}
        </div>
        <div role="tabpanel" id="inspector-panel-persona" aria-labelledby="inspector-tab-persona" hidden={active !== "persona"}>
          {active === "persona" && persona}
        </div>
        <div role="tabpanel" id="inspector-panel-prompts" aria-labelledby="inspector-tab-prompts" hidden={active !== "prompts"}>
          {active === "prompts" && prompts}
        </div>
      </div>
    </aside>
  );
}

export default InspectorTabs;
