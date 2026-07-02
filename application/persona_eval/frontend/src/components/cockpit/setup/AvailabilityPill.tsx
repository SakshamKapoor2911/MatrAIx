import { ToneChip } from "./ToneChip";

export interface AvailabilityPillProps {
  available?: boolean;
  label?: string;
}

/** Availability badge — green when ready, red when not. */
export function AvailabilityPill({ available, label }: AvailabilityPillProps) {
  if (available === undefined) {
    return (
      <ToneChip tone="warn" showDot pulseDot>
        {label ?? "Checking…"}
      </ToneChip>
    );
  }

  if (available) {
    return (
      <ToneChip tone="secondary" showDot>
        {label ?? "Available"}
      </ToneChip>
    );
  }

  return (
    <ToneChip tone="danger" showDot>
      {label ?? "Unavailable"}
    </ToneChip>
  );
}
