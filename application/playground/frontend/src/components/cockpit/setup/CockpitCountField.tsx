import { FOCUS_RING } from "../cockpitShared";

export interface CockpitCountFieldProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max: number;
  disabled?: boolean;
  presets?: number[];
  hint?: string;
}

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, Math.round(value)));
}

/** Numeric field with optional quick presets — for sample sizes and similar knobs. */
export function CockpitCountField({
  label,
  value,
  onChange,
  min = 1,
  max,
  disabled,
  presets,
  hint,
}: CockpitCountFieldProps) {
  const presetOptions = (presets ?? []).filter((n) => n >= min && n <= max);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[13px] font-medium text-text-variant">{label}</span>
        {hint ? <span className="text-[12px] text-text-dim">{hint}</span> : null}
      </div>
      <input
        type="number"
        inputMode="numeric"
        min={min}
        max={max}
        step={1}
        value={value}
        disabled={disabled}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") return;
          onChange(clamp(Number(raw), min, max));
        }}
        onBlur={(e) => onChange(clamp(Number(e.target.value), min, max))}
        className={`h-9 w-full rounded-lg border border-outline/50 bg-surface/60 px-2.5 font-mono text-[15px] text-text-main backdrop-blur disabled:opacity-50 ${FOCUS_RING}`}
      />
      {presetOptions.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {presetOptions.map((preset) => (
            <button
              key={preset}
              type="button"
              disabled={disabled}
              onClick={() => onChange(preset)}
              className={`rounded-md border px-2 py-0.5 font-mono text-[12px] transition ${FOCUS_RING} ${
                value === preset
                  ? "border-primary/50 bg-primary/15 text-primary"
                  : "border-outline/40 text-text-dim hover:border-primary/35 hover:text-text-variant"
              }`}
            >
              {preset}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** Compact label + number input for toolbars (e.g. parallel trials). */
export function CockpitInlineCount({
  label,
  value,
  onChange,
  min = 1,
  max,
  disabled,
  hint,
}: Omit<CockpitCountFieldProps, "presets">) {
  return (
    <label className="inline-flex items-center gap-2 rounded-lg border border-outline/35 bg-surface/40 px-2.5 py-1.5">
      <span className="whitespace-nowrap text-[13px] text-text-variant">{label}</span>
      <input
        type="number"
        inputMode="numeric"
        min={min}
        max={max}
        step={1}
        value={value}
        disabled={disabled}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") return;
          onChange(clamp(Number(raw), min, max));
        }}
        onBlur={(e) => onChange(clamp(Number(e.target.value), min, max))}
        className={`h-7 min-w-[3.25rem] w-20 rounded-md border border-outline/40 bg-surface/80 px-1.5 text-center font-mono text-[14px] text-text-main disabled:opacity-50 ${FOCUS_RING}`}
      />
      {hint ? <span className="text-[12px] text-text-dim">{hint}</span> : null}
    </label>
  );
}

export interface CockpitChipCountProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  options: number[];
  disabled?: boolean;
}

/** Compact chip picker for small bounded counts (e.g. parallel trials). */
export function CockpitChipCount({ label, value, onChange, options, disabled }: CockpitChipCountProps) {
  const choices = options.length > 0 ? options : [value];

  return (
    <div className="inline-flex items-center gap-2.5 rounded-lg border border-outline/35 bg-surface/40 px-3 py-2">
      <span className="whitespace-nowrap text-[13px] text-text-variant">{label}</span>
      <div className="flex gap-1">
        {choices.map((option) => (
          <button
            key={option}
            type="button"
            disabled={disabled}
            onClick={() => onChange(option)}
            className={`min-w-[2rem] rounded-md px-2 py-1 font-mono text-[13px] transition ${FOCUS_RING} ${
              value === option
                ? "bg-primary text-on-primary shadow-sm"
                : "text-text-variant hover:bg-surface-high hover:text-text-main"
            }`}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}
