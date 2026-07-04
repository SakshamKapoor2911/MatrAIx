import { SimulatedPersonaBust } from "./setup/SimulatedPersonaBust";
import {
  personaSeedFromCell,
  simulatedPersonaVisual,
} from "./setup/simulatedPersonaVisual";
import { Sym } from "./cockpitShared";

const AVATAR_FRAME =
  "flex h-8 w-8 shrink-0 overflow-hidden rounded-full border ring-1 ring-inset";

export function PersonaChatAvatar({
  personaId,
  dimensions = {},
  className = "",
}: {
  personaId?: string | null;
  dimensions?: Record<string, string>;
  className?: string;
}) {
  const seed = personaSeedFromCell(personaId ?? undefined, "persona");
  const visual = simulatedPersonaVisual(seed, dimensions);
  return (
    <div
      className={`${AVATAR_FRAME} items-end justify-center border-outline bg-surface-high ring-outline/40 ${className}`}
      style={{ backgroundColor: visual.backdrop }}
      aria-hidden
    >
      <SimulatedPersonaBust visual={visual} className="h-9 w-8" />
    </div>
  );
}

export function ChatbotChatAvatar({
  appName,
  className = "",
}: {
  appName: string;
  className?: string;
}) {
  return (
    <div
      className={`${AVATAR_FRAME} items-center justify-center border-primary/30 bg-primary/10 text-primary ring-primary/20 ${className}`}
      title={appName}
      aria-hidden
    >
      <Sym name="smart_toy" fill={1} size={16} />
    </div>
  );
}
