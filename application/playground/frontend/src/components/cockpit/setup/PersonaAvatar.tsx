import { SimulatedPersonaBust } from "./SimulatedPersonaBust";
import { personaSeedFromCell, simulatedPersonaVisual } from "./simulatedPersonaVisual";

export type PersonaAvatarSize = "sm" | "md" | "lg";

const SIZE_CLASS: Record<PersonaAvatarSize, string> = {
  sm: "h-9 w-8 px-0.5 pt-0.5",
  md: "h-11 w-9 px-0.5 pt-0.5",
  lg: "h-16 w-14 px-1 pt-1",
};

export interface PersonaAvatarProps {
  personaId: string;
  dimensions?: Record<string, string>;
  size?: PersonaAvatarSize;
  muted?: boolean;
  className?: string;
}

export function PersonaAvatar({
  personaId,
  dimensions = {},
  size = "md",
  muted = false,
  className = "",
}: PersonaAvatarProps) {
  const seed = personaSeedFromCell(personaId, `persona-${personaId}`);
  const visual = simulatedPersonaVisual(seed, dimensions);

  return (
    <div
      className={`flex shrink-0 items-end justify-center overflow-hidden rounded-2xl bg-surface/60 ring-1 ring-inset ring-outline/15 ${SIZE_CLASS[size]} ${className}`}
      style={{ backgroundColor: visual.backdrop }}
      aria-hidden
    >
      <SimulatedPersonaBust visual={visual} muted={muted} className="h-full w-full" />
    </div>
  );
}
