import type { Config } from "tailwindcss";

/**
 * Tailwind theme for PersonaEval — the "Executive Precision" design system
 * (see `DESIGN.md` for the authoritative token values, and
 * `tools/recbot-mockups/cockpit-stitch-v2.html` for the approved cockpit).
 *
 * The theme is the **Executive Precision** palette + type scale: the canonical
 * names `surface*`, `on-surface*`, `primary*`, `border-soft`, the semantic
 * `success`/`error`/`warning` container pairs, and the Inter/JetBrains-Mono
 * `display`/`headline-*`/`body-*`/`label-md`/`mono-sm` scale. These mirror the
 * mockup's `tailwind.config` exactly so the React app renders in the same
 * palette + faces. Color values are tokenized (no arbitrary hex in component
 * JSX); semantic colors carry their `-container` / `on-` pairs.
 *
 * Use the names directly in JSX, e.g. `bg-surface-container-lowest
 * border-border-soft text-on-surface-variant font-body-md rounded-lg
 * shadow-soft`.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        surface: "var(--surface)",
        "surface-dim": "var(--surface-dim)",
        "surface-bright": "var(--surface-bright)",
        "surface-container-lowest": "var(--surface-container-lowest)",
        "surface-container-low": "var(--surface-container-low)",
        "surface-container": "var(--surface-container)",
        "surface-container-high": "var(--surface-container-high)",
        "surface-container-highest": "var(--surface-container-highest)",
        "on-surface": "var(--on-surface)",
        "on-surface-variant": "var(--on-surface-variant)",
        outline: "var(--outline)",
        "outline-variant": "var(--outline-variant)",
        "border-soft": "var(--border-soft)",

        primary: {
          DEFAULT: "var(--primary)",
          container: "var(--primary-container)",
          tint: "var(--primary-tint)",
        },
        "on-primary": "var(--on-primary)",
        "on-primary-container": "var(--on-primary-container)",

        secondary: "var(--secondary)",

        // Semantic colors — tokenized with their container / on-container pairs.
        success: {
          DEFAULT: "var(--success)",
          container: "var(--success-container)",
        },
        "on-success-container": "var(--on-success-container)",
        warning: {
          DEFAULT: "var(--warning)",
          container: "var(--warning-container)",
        },
        "on-warning-container": "var(--on-warning-container)",
        error: {
          DEFAULT: "var(--error)",
          container: "var(--error-container)",
        },
        "on-error-container": "var(--on-error-container)",
      },
      fontFamily: {
        // Executive Precision: Inter for UI, JetBrains Mono for machine data.
        display: ["Inter", "system-ui", "sans-serif"],
        "headline-md": ["Inter", "system-ui", "sans-serif"],
        "headline-sm": ["Inter", "system-ui", "sans-serif"],
        "body-lg": ["Inter", "system-ui", "sans-serif"],
        "body-md": ["Inter", "system-ui", "sans-serif"],
        "body-sm": ["Inter", "system-ui", "sans-serif"],
        "label-md": ["Inter", "system-ui", "sans-serif"],
        "mono-sm": ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        // Executive Precision type scale (size + lineHeight/tracking/weight).
        display: ["24px", { lineHeight: "32px", letterSpacing: "-0.02em", fontWeight: "600" }],
        "headline-md": ["18px", { lineHeight: "24px", letterSpacing: "-0.01em", fontWeight: "600" }],
        "headline-sm": ["14px", { lineHeight: "20px", letterSpacing: "0.05em", fontWeight: "600" }],
        "body-lg": ["16px", { lineHeight: "24px", fontWeight: "400" }],
        "body-md": ["14px", { lineHeight: "20px", fontWeight: "400" }],
        "body-sm": ["13px", { lineHeight: "18px", fontWeight: "400" }],
        "label-md": ["12px", { lineHeight: "16px", fontWeight: "500" }],
        "mono-sm": ["12px", { lineHeight: "16px", fontWeight: "400" }],
      },
      borderRadius: {
        // Executive Precision radii (8px standard; 12–16px large panels; pill).
        sm: "0.25rem",
        DEFAULT: "0.5rem",
        lg: "0.75rem",
        xl: "1rem",
        full: "9999px",
      },
      spacing: {
        // Executive Precision 8px grid (4px for tight components).
        xs: "4px",
        sm: "8px",
        md: "16px",
        lg: "24px",
        xl: "32px",
        unit: "4px",
        gutter: "16px",
        "container-max": "1440px",
      },
      boxShadow: {
        // Executive Precision "Stacked Layer" elevation. `shadow-sm` keeps
        // Tailwind's built-in subtle shadow for small raised controls.
        soft: "0 4px 6px -1px rgb(0 0 0 / 0.04), 0 2px 4px -1px rgb(0 0 0 / 0.02)",
        pop: "0 12px 24px -6px rgb(0 0 0 / 0.08), 0 4px 8px -4px rgb(0 0 0 / 0.04)",
      },
      maxWidth: {
        thread: "680px",
      },
    },
  },
  plugins: [],
} satisfies Config;
