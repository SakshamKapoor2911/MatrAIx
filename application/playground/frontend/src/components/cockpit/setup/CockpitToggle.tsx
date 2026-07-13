import { FOCUS_RING } from "../cockpitShared";

export interface CockpitToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
}

export function CockpitToggle({
  checked,
  onChange,
  label,
  description,
  disabled,
}: CockpitToggleProps) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="min-w-0">
        <p className="text-[14px] font-semibold text-text-main">{label}</p>
        {description && (
          <p className="mt-0.5 text-[12px] leading-snug text-text-dim">{description}</p>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative h-6 w-11 shrink-0 rounded-full transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50 ${FOCUS_RING} ${
          checked ? "bg-primary" : "bg-outline/55"
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-[left] duration-200 ${
            checked ? "left-[1.35rem]" : "left-0.5"
          }`}
        />
      </button>
    </div>
  );
}
