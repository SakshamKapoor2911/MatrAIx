/**
 * KnobSelect — one editable config knob in the cockpit's run-config bar.
 *
 * A minimalist dropdown (label + current value + chevron) matching the mockup's
 * knobs: the *border* turns primary when the knob is "active" (the highlighted
 * conversation-style knob), never the background fill. Opening reveals a small
 * menu of `{value,label,description}` options; selecting one calls `onChange`.
 *
 * Implemented as a button + a positioned menu (not a native `<select>`) so the
 * option descriptions from the config metadata can be shown. The menu is a
 * keyboard-operable listbox: Up/Down move, Enter/Space select, Escape closes,
 * and arrow/typeahead focus is managed via roving `tabIndex`.
 */
import { useEffect, useId, useRef, useState } from "react";

import { FOCUS_RING, Sym } from "./cockpitShared";

/** One selectable option (mirrors the backend `ConfigOptionValue`). */
export interface KnobOption {
  value: string;
  label: string;
  description?: string;
}

export interface KnobSelectProps {
  /** Uppercase knob label ("Model", "Domain", …). */
  label: string;
  /** Currently selected value. */
  value: string;
  options: KnobOption[];
  onChange: (value: string) => void;
  /** Render with the primary border (the highlighted knob in the mockup). */
  accent?: boolean;
  disabled?: boolean;
}

export function KnobSelect({ label, value, options, onChange, accent, disabled }: KnobSelectProps) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  const selected = options.find((o) => o.value === value) ?? null;
  const currentLabel = selected?.label ?? value;

  // Close on outside click + Escape.
  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  // When opening, focus the selected option.
  useEffect(() => {
    if (open) {
      const idx = options.findIndex((o) => o.value === value);
      setActiveIndex(idx >= 0 ? idx : 0);
    }
  }, [open, options, value]);

  function commit(idx: number) {
    const opt = options[idx];
    if (opt) onChange(opt.value);
    setOpen(false);
  }

  function onButtonKey(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setOpen(true);
    }
  }

  function onMenuKey(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(options.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(0, i - 1));
    } else if (e.key === "Home") {
      e.preventDefault();
      setActiveIndex(0);
    } else if (e.key === "End") {
      e.preventDefault();
      setActiveIndex(options.length - 1);
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      commit(activeIndex);
    } else if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
    }
  }

  return (
    <div ref={rootRef} className="flex flex-shrink-0 items-center gap-2">
      <span className="text-label-md font-label-md uppercase tracking-wider text-on-surface-variant">{label}</span>
      <div className="relative">
        <button
          type="button"
          disabled={disabled}
          onClick={() => !disabled && setOpen((v) => !v)}
          onKeyDown={onButtonKey}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-label={`${label}: ${currentLabel}`}
          className={`flex items-center gap-2 rounded border px-3 py-1.5 text-body-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING} ${
            accent
              ? "border-primary bg-primary/5 text-primary hover:bg-primary/10"
              : "border-outline-variant bg-surface text-on-surface hover:border-primary"
          }`}
        >
          {currentLabel}
          <Sym name="expand_more" size={16} className={accent ? "" : "text-outline"} />
        </button>

        {open && (
          <ul
            id={menuId}
            role="listbox"
            aria-label={label}
            tabIndex={-1}
            onKeyDown={onMenuKey}
            ref={(el) => el?.focus()}
            className="absolute left-0 top-full z-30 mt-1 max-h-72 w-64 overflow-auto rounded-lg border border-border-soft bg-surface-container-lowest p-1 shadow-pop outline-none"
          >
            {options.map((opt, idx) => {
              const isSelected = opt.value === value;
              const isActive = idx === activeIndex;
              return (
                <li
                  key={opt.value}
                  role="option"
                  aria-selected={isSelected}
                  onMouseEnter={() => setActiveIndex(idx)}
                  onClick={() => commit(idx)}
                  className={`cursor-pointer rounded-md px-2.5 py-2 transition-colors ${
                    isActive ? "bg-surface-container" : ""
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-body-sm font-medium ${isSelected ? "text-primary" : "text-on-surface"}`}>
                      {opt.label}
                    </span>
                    {isSelected && <Sym name="check" size={16} className="text-primary" />}
                  </div>
                  {opt.description && (
                    <p className="mt-0.5 text-[11px] leading-relaxed text-on-surface-variant">{opt.description}</p>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

export default KnobSelect;
