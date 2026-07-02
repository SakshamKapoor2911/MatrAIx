import type { ReactNode } from "react";

export interface CockpitSetupShellProps {
  header: ReactNode;
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
}

/** Full-viewport three-column cockpit — side rails scroll internally; no page scroll. */
export function CockpitSetupShell({ header, left, center, right }: CockpitSetupShellProps) {
  return (
    <div className="cockpit-mesh-bg flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-outline/30 bg-surface-lowest/70 px-5 py-3 backdrop-blur-md">
        {header}
      </div>
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-hidden px-3 py-3 xl:grid-cols-12 xl:gap-4 xl:px-5 xl:py-4">
        <div className="flex h-full min-h-0 flex-col overflow-hidden xl:col-span-3">{left}</div>
        <div className="flex h-full min-h-0 flex-col overflow-hidden xl:col-span-6">{center}</div>
        <div className="flex h-full min-h-0 flex-col overflow-hidden xl:col-span-3">{right}</div>
      </div>
    </div>
  );
}
