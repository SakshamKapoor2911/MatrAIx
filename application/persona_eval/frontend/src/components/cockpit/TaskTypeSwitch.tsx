/**
 * TaskTypeSwitch: the application-type segmented control.
 *
 * Ports the mockup's "Application type" switch (`app-redesign-v3.html:106-112`):
 * a `.hud` micro-label above a compact `inline-flex` segmented control
 * (Chatbot / Survey / Website). It is a self-contained, header-embeddable block
 * (no full-width bar) so each cockpit can drop it into the top-right of its
 * "Configure a simulation" header.
 *
 * Shared primitive: Survey/Web cockpits render the same control. Props are
 * unchanged (`value` / `onChange` / `disabled`); `showLabel` + `className` are
 * optional presentation knobs.
 */
import { FOCUS_RING, Sym } from "./cockpitShared";

export type PersonaEvalTaskType = "chatbot" | "survey" | "web";

export interface TaskTypeSwitchProps {
  value: PersonaEvalTaskType;
  onChange: (value: PersonaEvalTaskType) => void;
  disabled?: boolean;
  /** Show the "Application type" hud label above the control. Default true. */
  showLabel?: boolean;
  className?: string;
}

const OPTIONS: ReadonlyArray<{ value: PersonaEvalTaskType; label: string; icon: string; hint: string }> = [
  { value: "chatbot", label: "Chatbot", icon: "forum", hint: "A back-and-forth conversation." },
  { value: "survey", label: "Survey", icon: "fact_check", hint: "A fixed questionnaire the user fills out." },
  { value: "web", label: "Web", icon: "language", hint: "A real browser task the user completes." },
];

export function TaskTypeSwitch({ value, onChange, disabled, showLabel = true, className = "" }: TaskTypeSwitchProps) {
  return (
    <div className={className}>
      {showLabel && <div className="hud mb-1.5 text-[9px] text-text-dim">Application type</div>}
      <div className="inline-flex rounded-md border border-outline bg-surface-low p-1">
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
              className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-[12px] font-medium transition ease-out active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100 ${FOCUS_RING} ${
                selected
                  ? "bg-primary text-on-primary"
                  : "text-text-variant hover:bg-surface hover:text-text-main"
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
