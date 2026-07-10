import type { ReactNode } from "react";

export interface CockpitLiveStageProps {
  children: ReactNode;
  className?: string;
  /** When true, children fill the stage without an inner scroll region (batch grid). */
  fillContent?: boolean;
}

/** Glass-framed center stage for live run content (chat, survey, web trace, batch grid). */
export function CockpitLiveStage({ children, className = "", fillContent = false }: CockpitLiveStageProps) {
  return (
    <div
      className={`glass-panel flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-outline/40 ${className}`}
    >
      <div
        className={
          fillContent
            ? "flex min-h-0 flex-1 flex-col overflow-hidden p-2 sm:p-3"
            : "custom-scrollbar min-h-0 flex-1 overflow-y-auto p-4 sm:p-5"
        }
      >
        {fillContent ? (
          <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">{children}</div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
