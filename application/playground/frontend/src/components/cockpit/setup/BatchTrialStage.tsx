import type { ReactNode } from "react";

/** Dedicated full-bleed stage for batch grids — no inner scroll, strict height chain. */
export function BatchTrialStage({ children }: { children: ReactNode }) {
  return (
    <div className="glass-panel flex h-0 min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-outline/40">
      <div className="box-border flex h-full min-h-0 w-full flex-col overflow-hidden p-2 sm:p-3">
        {children}
      </div>
    </div>
  );
}
