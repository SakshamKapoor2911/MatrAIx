import type { ReactNode } from "react";

export interface CockpitLiveStageProps {
  children: ReactNode;
  className?: string;
}

/** Glass-framed center stage for live run content (chat, survey, web trace, batch grid). */
export function CockpitLiveStage({ children, className = "" }: CockpitLiveStageProps) {
  return (
    <div
      className={`glass-panel flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-outline/40 ${className}`}
    >
      <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto p-4 sm:p-5">{children}</div>
    </div>
  );
}
