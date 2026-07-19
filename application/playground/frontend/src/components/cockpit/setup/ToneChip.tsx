import type { ReactNode } from "react";

export type ToneChipTone = "primary" | "accent" | "secondary" | "warn" | "danger";

export interface ToneChipProps {
  tone: ToneChipTone;
  /** Emphasized fill — stronger tint, text stays `text-main`. */
  solid?: boolean;
  /** Muted fill for inactive options. */
  muted?: boolean;
  showDot?: boolean;
  pulseDot?: boolean;
  className?: string;
  children: ReactNode;
}

const TONE_CLASS: Record<ToneChipTone, string> = {
  primary: "tone-chip--primary",
  accent: "tone-chip--accent",
  secondary: "tone-chip--secondary",
  warn: "tone-chip--warn",
  danger: "tone-chip--danger",
};

/** Filled pill — background is a lighter wash of the label color. */
export function ToneChip({
  tone,
  solid = false,
  muted = false,
  showDot = false,
  pulseDot = false,
  className = "",
  children,
}: ToneChipProps) {
  const toneClass = TONE_CLASS[tone];
  const variant = solid ? "tone-chip--solid" : muted ? "tone-chip--muted" : toneClass;
  return (
    <span
      className={`tone-chip ${solid ? `${toneClass} tone-chip--solid` : variant} ${showDot ? "tone-chip--with-dot" : ""} ${pulseDot ? "tone-chip--pulse-dot" : ""} ${className}`}
    >
      {showDot && <span className="tone-chip__dot" aria-hidden />}
      {children}
    </span>
  );
}

export const DIMENSION_CHIP_TONES: ToneChipTone[] = ["primary", "accent", "secondary", "warn"];

export function transportChipTone(
  transport: "api_sidecar" | "api_external" | "mcp_sidecar" | "mcp_external",
): ToneChipTone {
  if (transport === "api_external") return "accent";
  if (transport === "mcp_sidecar" || transport === "mcp_external") return "warn";
  return "primary";
}
