/**
 * TaskTypeSwitch: the application-type segmented control.
 *
 * Ports the mockup's "Application type" switch (`app-redesign-v3.html:106-112`):
 * a `.hud` micro-label above a compact `inline-flex` segmented control
 * (Chatbot / Survey / Website / AppWorld). It is a self-contained, header-embeddable block
 * (no full-width bar) so each cockpit can drop it into the top-right of its
 * "Configure a simulation" header.
 *
 * Shared primitive: Survey/Web cockpits render the same control. Props are
 * unchanged (`value` / `onChange` / `disabled`); `showLabel` + `className` are
 * optional presentation knobs.
 */
import { OS_APP_TAB_LABEL } from "@/lib/personaAgentCatalog";
import { FOCUS_RING, Sym } from "./cockpitShared";

export type PlaygroundTaskType = "chatbot" | "survey" | "web" | "os-app";

export interface TaskTypeSwitchProps {
  value: PlaygroundTaskType;
  onChange: (value: PlaygroundTaskType) => void;
  disabled?: boolean;
  /** Show the "Application type" hud label above the control. Default true. */
  showLabel?: boolean;
  className?: string;
}

const OPTIONS: ReadonlyArray<{ value: PlaygroundTaskType; label: string; icon: string; hint: string }> = [
  { value: "survey", label: "Survey", icon: "fact_check", hint: "A fixed questionnaire the user fills out." },
  { value: "chatbot", label: "Chatbot", icon: "forum", hint: "A back-and-forth conversation." },
  { value: "web", label: "Web", icon: "language", hint: "A real browser task the user completes." },
  { value: "os-app", label: OS_APP_TAB_LABEL, icon: "apps", hint: "Native apps on Linux, macOS, or iOS (computer-use simulation)." },
];

export function TaskTypeSwitch({ value, onChange, disabled, showLabel = true, className = "" }: TaskTypeSwitchProps) {
  return (
    <div className={className}>
      {showLabel && <div className="hud mb-1.5 text-[11px] text-primary">Application type</div>}
      <div className="cockpit-segment inline-flex">
        {OPTIONS.map((option) => {
          const selected = option.value === value;
          return (
            <button
              key={option.value}
              type="button"
              disabled={disabled}
              title={option.hint}
              aria-pressed={selected}
              onClick={() => onChange(option.value)}
              className={`cockpit-segment__btn flex items-center gap-1.5 px-3 py-1.5 text-[14px] transition ease-out active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100 ${FOCUS_RING} ${
                selected ? "cockpit-segment__btn--active" : ""
              }`}
            >
              <Sym name={option.icon} fill={selected ? 1 : 0} size={14} />
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default TaskTypeSwitch;
