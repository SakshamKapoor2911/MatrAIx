export interface CockpitRailHeaderProps {
  label: string;
}

/** Compact rail title — single label, minimal vertical footprint for card lists below. */
export function CockpitRailHeader({ label }: CockpitRailHeaderProps) {
  return (
    <div className="mb-2.5 shrink-0 border-b border-outline/20 pb-2">
      <div className="flex items-center gap-2">
        <span className="h-4 w-0.5 rounded-full bg-primary" aria-hidden />
        <h2 className="font-display text-[15px] font-semibold leading-none tracking-tight text-text-main">
          {label}
        </h2>
      </div>
    </div>
  );
}
