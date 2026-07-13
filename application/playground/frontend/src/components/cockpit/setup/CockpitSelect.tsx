import { useEffect, useId, useRef, useState } from "react";

import { FOCUS_RING, Sym } from "../cockpitShared";

export interface CockpitSelectOption {
  value: string;
  label: string;
  /** Secondary line in the menu, e.g. "light · Playwright + DOM". */
  meta?: string;
  /** Shown below the field when this option is selected (normal case). */
  summary?: string;
}

export interface CockpitSelectProps {
  label: string;
  value: string;
  options: CockpitSelectOption[];
  onChange: (value: string) => void;
  disabled?: boolean;
  /** Fallback hint when the selected option has no summary. */
  hint?: string;
}

export function CockpitSelect({ label, value, options, onChange, disabled, hint }: CockpitSelectProps) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  const selected = options.find((o) => o.value === value) ?? null;

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

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
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      commit(activeIndex);
    } else if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
    }
  }

  const footer = selected?.summary ?? hint;

  return (
    <div ref={rootRef} className="flex flex-col gap-1.5">
      <span className="text-[13px] font-medium text-text-dim normal-case tracking-normal">{label}</span>
      <div className="relative">
        <button
          type="button"
          disabled={disabled}
          onClick={() => !disabled && setOpen((v) => !v)}
          onKeyDown={onButtonKey}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-label={`${label}: ${selected?.label ?? value}`}
          className={`flex w-full items-center justify-between gap-2 rounded-lg border border-outline/50 bg-surface/60 px-2.5 py-2 text-left backdrop-blur transition ease-out hover:border-primary/40 hover:bg-surface/75 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55 disabled:active:scale-100 ${FOCUS_RING}`}
        >
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[15px] font-medium text-text-main">
              {selected?.label ?? value}
            </span>
            {selected?.meta ? (
              <span className="block truncate text-[12px] text-text-dim">{selected.meta}</span>
            ) : null}
          </span>
          <Sym
            name="expand_more"
            size={18}
            className={`shrink-0 text-text-dim transition-transform duration-150 ${open ? "rotate-180" : ""}`}
          />
        </button>
        {open && (
          <ul
            id={menuId}
            role="listbox"
            aria-label={label}
            tabIndex={-1}
            onKeyDown={onMenuKey}
            ref={(el) => el?.focus()}
            className="pop-in custom-scrollbar absolute left-0 top-full z-40 mt-1 max-h-72 w-full overflow-auto rounded-lg border border-outline/60 bg-surface-lowest p-1 shadow-2xl outline-none"
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
                    isActive ? "bg-surface-high" : ""
                  } ${isSelected ? "bg-primary/8" : ""}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <span
                        className={`block truncate text-[15px] font-medium ${
                          isSelected ? "text-primary" : "text-text-main"
                        }`}
                      >
                        {opt.label}
                      </span>
                      {opt.meta ? (
                        <span className="mt-0.5 block text-[12px] leading-snug text-text-dim">{opt.meta}</span>
                      ) : null}
                    </div>
                    {isSelected ? <Sym name="check" size={16} className="mt-0.5 shrink-0 text-primary" /> : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
      {footer ? (
        <p className="text-[12px] leading-relaxed text-text-dim normal-case">{footer}</p>
      ) : null}
    </div>
  );
}
