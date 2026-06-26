import { FOCUS_RING, Sym } from "./cockpitShared";

export type PersonaEvalTaskType = "chatbot" | "survey" | "web";

export interface TaskTypeSwitchProps {
  value: PersonaEvalTaskType;
  onChange: (value: PersonaEvalTaskType) => void;
  disabled?: boolean;
}

const OPTIONS: ReadonlyArray<{ value: PersonaEvalTaskType; label: string; icon: string; hint: string }> = [
  { value: "chatbot", label: "Chatbot", icon: "forum", hint: "A back-and-forth conversation." },
  { value: "survey", label: "Survey", icon: "fact_check", hint: "A fixed questionnaire the user fills out." },
  { value: "web", label: "Website", icon: "language", hint: "A real browser task the user completes." },
];

export function TaskTypeSwitch({ value, onChange, disabled }: TaskTypeSwitchProps) {
  return (
    <div className="flex flex-shrink-0 items-center gap-2 border-b border-outline-dim bg-surface-lowest px-5 py-2.5">
      <span className="hud text-[10px] text-text-dim">
        What are you testing?
      </span>
      <div className="inline-flex rounded-md border border-outline bg-surface-low p-1">
        {OPTIONS.map((option) => {
          const selected = option.value === value;
          return (
            <button
              key={option.value}
              type="button"
              disabled={disabled}
              title={option.hint}
              onClick={() => onChange(option.value)}
              className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${FOCUS_RING} ${
                selected
                  ? "bg-primary text-on-primary"
                  : "text-text-variant hover:bg-surface hover:text-text-main"
              }`}
            >
              <Sym name={option.icon} fill={selected ? 1 : 0} size={16} />
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default TaskTypeSwitch;
