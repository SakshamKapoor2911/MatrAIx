export interface CockpitRailHeaderProps {
  eyebrow: string;
  title: string;
  subtitle?: string;
}

/** Shared section header for cockpit side rails — clear typographic hierarchy. */
export function CockpitRailHeader({ eyebrow, title, subtitle }: CockpitRailHeaderProps) {
  return (
    <div className="mb-4 shrink-0 border-b border-outline/25 pb-3">
      <div className="mb-2 flex items-center gap-2">
        <span className="h-3.5 w-0.5 rounded-full bg-primary" aria-hidden />
        <p className="hud text-[9px] text-primary">{eyebrow}</p>
      </div>
      <h2 className="font-display text-[16px] font-semibold leading-snug tracking-tight text-text-main">
        {title}
      </h2>
      {subtitle && (
        <p className="mt-1 text-[11px] leading-relaxed text-text-dim">{subtitle}</p>
      )}
    </div>
  );
}
