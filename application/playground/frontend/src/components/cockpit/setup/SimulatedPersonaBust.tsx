import { useId } from "react";

import type { SimulatedPersonaVisual } from "./simulatedPersonaVisual";

export interface SimulatedPersonaBustProps {
  visual: SimulatedPersonaVisual;
  muted?: boolean;
  className?: string;
}

function HairPath({ style, color }: { style: SimulatedPersonaVisual["hairStyle"]; color: string }) {
  if (style === 0) {
    return (
      <path
        d="M14 18 C14 10 18 6 24 6 C30 6 34 10 34 18 C34 14 30 12 24 12 C18 12 14 14 14 18 Z"
        fill={color}
      />
    );
  }
  if (style === 1) {
    return (
      <path
        d="M13 20 C12 9 17 5 24 5 C31 5 36 9 35 20 C38 24 37 30 34 32 L30 28 C32 22 31 16 24 15 C17 16 16 22 18 28 L14 32 C11 30 10 24 13 20 Z"
        fill={color}
      />
    );
  }
  if (style === 2) {
    return (
      <>
        <path
          d="M14 18 C14 9 18 5 24 5 C30 5 34 9 34 18 L36 36 C36 38 34 39 32 38 L30 24 C28 20 20 20 18 24 L16 38 C14 39 12 38 12 36 Z"
          fill={color}
        />
      </>
    );
  }
  return (
    <circle cx="24" cy="14" r="11" fill={color} />
  );
}

/** Compact illustrated bust — unique per persona seed, no stock icon. */
export function SimulatedPersonaBust({ visual, muted = false, className = "" }: SimulatedPersonaBustProps) {
  const gradientId = useId().replace(/:/g, "");
  const opacity = muted ? 0.45 : 1;
  return (
    <svg
      viewBox="0 0 48 56"
      className={`h-full w-full ${className}`}
      aria-hidden
      style={{ opacity }}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={visual.backdrop} />
          <stop offset="100%" stopColor="transparent" />
        </linearGradient>
      </defs>
      <rect x="4" y="4" width="40" height="48" rx="10" fill={`url(#${gradientId})`} />
      <ellipse cx="24" cy="46" rx="15" ry="7" fill={visual.shirt} opacity="0.92" />
      <path d="M17 38 L17 44 C17 46 20 47 24 47 C28 47 31 46 31 44 L31 38 Z" fill={visual.skin} />
      <ellipse cx="24" cy="24" rx="9.5" ry="11" fill={visual.skin} />
      <HairPath style={visual.hairStyle} color={visual.hair} />
      <ellipse cx="20" cy="24" rx="1.2" ry="1.6" fill="#2a2118" opacity="0.75" />
      <ellipse cx="28" cy="24" rx="1.2" ry="1.6" fill="#2a2118" opacity="0.75" />
      <path
        d="M20 29 Q24 32 28 29"
        fill="none"
        stroke="#9a6f55"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      {visual.accessory === 1 && (
        <>
          <circle cx="20" cy="24" r="3.2" fill="none" stroke="#3d4654" strokeWidth="1.1" opacity="0.85" />
          <circle cx="28" cy="24" r="3.2" fill="none" stroke="#3d4654" strokeWidth="1.1" opacity="0.85" />
          <path d="M23.2 24 L24.8 24" stroke="#3d4654" strokeWidth="1" />
        </>
      )}
      {visual.accessory === 2 && (
        <>
          <path d="M12 22 C10 24 10 28 12 30" stroke={visual.hair} strokeWidth="2.2" strokeLinecap="round" />
          <path d="M36 22 C38 24 38 28 36 30" stroke={visual.hair} strokeWidth="2.2" strokeLinecap="round" />
        </>
      )}
    </svg>
  );
}
