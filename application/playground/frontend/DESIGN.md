# DESIGN.md — Playground design system

Dark-first, restrained "mission control". Authoritative tokens live in `src/index.css` (`:root` dark / `:root.light`) and are mapped in `tailwind.config.ts` as `rgb(var(--x)/<alpha-value>)` (so opacity utilities work everywhere).

## Tokens (use the Tailwind names, never hex)
- **Surfaces:** `surface-dim` (page) · `surface-lowest` (header/rails/wells) · `surface` (panels) · `surface-low` (hover) · `surface-high` (raised chips/tiles) · `field` (inputs).
- **Lines:** `outline` (default borders) · `outline-dim` (hairlines/dividers).
- **Brand:** `primary` cyan (CTAs, active nav, accents) + `primary-dim` (hover) + `on-primary` (text on fills); `secondary` mint (success / "ready" / positive) + `secondary-dim`.
- **Text:** `text-main` (headings) · `text-variant` (body) · `text-dim` (captions/placeholders).
- **Status:** `danger` · `warn`. **Scores only:** `score-low|mid|high` (red→amber→mint) via `SCORE_BAND_CLASS` in `cockpit/cockpitShared.tsx` — never use the primary accent for a score.

## Type
**Inter** for both `font-sans` (UI) and `font-display` (headings / wordmark) — same face as the public MatrAIx site ([Google Fonts](https://fonts.google.com/specimen/Inter)). **JetBrains Mono** for `font-mono` (data + uppercase `.hud` micro-labels). Base body is 16px; Tailwind `text-xs`/`text-sm`/… are bumped ~2px vs defaults for cockpit readability.

## Utilities (in `index.css`)
- `.panel` — bordered box with a top-left cyan corner bracket (signature; use on key panels, not everything).
- `.hud` — mono, uppercase, letter-spaced micro-label (pair with `text-text-dim`); labels must be real words.
- `.glow` — cyan glow, reserved for the single primary CTA per view.
- `.custom-scrollbar`, `.animate-rb-pulse`, `.animate-rb-spin`.

## Components & motion
- Icons: Material Symbols via the `<Sym>` primitive (lucide migration is a planned follow-up). Keep one icon family.
- Every interactive element needs default/hover/focus/active/disabled/loading; `:focus-visible` ring is tokenized globally (`FOCUS_RING`).
- Motion: 150–250ms, ease-out, state-conveying only (no decorative/page-load choreography). Honor `prefers-reduced-motion` (already global in `index.css`).
- Overlays (dropdowns/popovers/drawers) MUST stay within the viewport and escape clipping containers — use fixed/portaled positioning with viewport-collision handling, not `absolute` inside an overflow container.
- Theme: dark default; `useTheme` toggles `<html>.light`, persisted, set pre-paint in `index.html`.
