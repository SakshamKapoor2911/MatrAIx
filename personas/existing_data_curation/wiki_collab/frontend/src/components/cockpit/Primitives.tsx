/**
 * Small reusable presentation primitives shared across cockpit panels.
 *
 * Everything here is tokenized against the Executive Precision design system
 * (no arbitrary hex) and degrades gracefully when given empty/null inputs.
 */
import type { ReactNode } from "react";

import { Sym, scoreBand, SCORE_BAND_CLASS, FOCUS_RING } from "@/components/cockpit/cockpitShared";
import { shortSha, copyToClipboard } from "@/lib/format";

// ---------------------------------------------------------------------------
// Chip — a tokenized status pill
// ---------------------------------------------------------------------------

export type ChipTone = "neutral" | "primary" | "success" | "warning" | "error";

const CHIP_TONE: Record<ChipTone, string> = {
  neutral: "bg-surface-container-high text-on-surface-variant",
  primary: "bg-primary-tint text-on-primary-container",
  success: "bg-success-container text-on-success-container",
  warning: "bg-warning-container text-on-warning-container",
  error: "bg-error-container text-on-error-container",
};

export function Chip({
  children,
  tone = "neutral",
  title,
}: {
  children: ReactNode;
  tone?: ChipTone;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-xs rounded-full px-2 py-0.5 font-label-md ${CHIP_TONE[tone]}`}
    >
      {children}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Fingerprint — a mono short-sha chip that copies its full value on click
// ---------------------------------------------------------------------------

export function Fingerprint({
  value,
  label,
  n = 10,
}: {
  value: string | null | undefined;
  label?: string;
  n?: number;
}) {
  const full = (value ?? "").trim();
  const short = shortSha(full, n);
  const disabled = !full;
  return (
    <button
      type="button"
      disabled={disabled}
      title={disabled ? "no value" : `${full}\n(click to copy)`}
      onClick={() => full && copyToClipboard(full)}
      className={`group inline-flex items-center gap-xs rounded-md border border-border-soft bg-surface-container-low px-2 py-0.5 font-mono-sm text-on-surface-variant transition-colors hover:bg-surface-container disabled:cursor-default disabled:opacity-60 ${FOCUS_RING}`}
    >
      {label ? <span className="font-label-md text-outline">{label}</span> : null}
      <span className="tabular-nums">{short}</span>
      {!disabled ? (
        <Sym name="content_copy" size={13} className="text-outline opacity-0 transition-opacity group-hover:opacity-100" />
      ) : null}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Bar — a 0..1 confidence bar coloured by the score band
// ---------------------------------------------------------------------------

export function Bar({ value }: { value: number | null | undefined }) {
  const band = scoreBand(value);
  const cls = SCORE_BAND_CLASS[band];
  const fill = value === null || value === undefined || Number.isNaN(value) ? 0 : Math.max(0, Math.min(1, value));
  const widthPct = Math.round(fill * 100);
  return (
    <div className="flex items-center gap-xs" title={value === null || value === undefined ? "no confidence" : `${widthPct}%`}>
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-container-high">
        <div className={`h-full rounded-full ${cls.bar}`} style={{ width: `${widthPct}%` }} />
      </div>
      <span className={`font-mono-sm tabular-nums ${cls.text}`}>
        {value === null || value === undefined || Number.isNaN(value) ? "—" : fill.toFixed(2)}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// MetricTile — a compact stat card
// ---------------------------------------------------------------------------

export function MetricTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div className="flex flex-col gap-0.5 rounded-lg border border-border-soft bg-surface-container-lowest px-3 py-2 shadow-soft">
      <span className="font-label-md uppercase tracking-wide text-on-surface-variant">{label}</span>
      <span className="font-headline-md text-on-surface tabular-nums">{value}</span>
      {hint ? <span className="font-body-sm text-on-surface-variant">{hint}</span> : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty — a quiet empty-state block
// ---------------------------------------------------------------------------

export function Empty({
  icon = "inbox",
  title,
  hint,
}: {
  icon?: string;
  title: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-sm rounded-lg border border-dashed border-border-soft bg-surface-container-low px-6 py-10 text-center">
      <Sym name={icon} size={28} className="text-outline-variant" />
      <p className="font-body-md text-on-surface">{title}</p>
      {hint ? <p className="max-w-xs font-body-sm text-on-surface-variant">{hint}</p> : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SectionLabel — an uppercase headline-sm group label
// ---------------------------------------------------------------------------

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <h3 className="font-headline-sm uppercase tracking-wide text-on-surface-variant">{children}</h3>
  );
}

// ---------------------------------------------------------------------------
// Spinner — a tiny inline spinner for pending buttons
// ---------------------------------------------------------------------------

export function Spinner({ size = 16, className = "" }: { size?: number; className?: string }) {
  return (
    <span
      className={`inline-block animate-rb-spin rounded-full border-2 border-current border-r-transparent align-[-2px] ${className}`}
      style={{ width: size, height: size }}
      aria-hidden
    />
  );
}
