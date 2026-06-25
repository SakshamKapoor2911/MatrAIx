import { FOCUS_RING, Sym } from "./cockpitShared";

export type PersonaEvalTaskType = "chatbot" | "survey" | "web";

export interface TaskTypeSwitchProps {
  value: PersonaEvalTaskType;
  onChange: (value: PersonaEvalTaskType) => void;
  disabled?: boolean;
}

const OPTIONS: ReadonlyArray<{ value: PersonaEvalTaskType; label: string; icon: string }> = [
  { value: "chatbot", label: "Chatbot", icon: "forum" },
  { value: "survey", label: "Survey", icon: "fact_check" },
  { value: "web", label: "Web", icon: "language" },
];

export function TaskTypeSwitch({ value, onChange, disabled }: TaskTypeSwitchProps) {
  return (
    <div className="flex flex-shrink-0 items-center gap-2 border-b border-border-soft bg-surface px-lg py-2">
      <span className="text-label-md font-label-md uppercase tracking-wider text-on-surface-variant">
        Application type
      </span>
      <div className="flex overflow-hidden rounded-md border border-border-soft bg-surface-container-low">
        {OPTIONS.map((option) => {
          const selected = option.value === value;
          return (
            <button
              key={option.value}
              type="button"
              disabled={disabled}
              onClick={() => onChange(option.value)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-label-md font-label-md transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${FOCUS_RING} ${
                selected
                  ? "bg-primary text-on-primary"
                  : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
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
