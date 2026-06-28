import type { Config } from "tailwindcss";

/**
 * Tailwind theme for PersonaEval — the "PersonaEval" design system.
 *
 * Dark-first; tokens live in src/index.css as "R G B" triplets and are consumed
 * via rgb(var(--x)/<alpha-value>) so opacity utilities (bg-primary/10,
 * border-secondary/25) work for every color. Three faces only: font-sans
 * (Inter, default UI), font-display (Space Grotesk, headings + the PersonaEval
 * wordmark), font-mono (JetBrains Mono, data + the uppercase `.hud` micro-label).
 *
 * Use the names directly in JSX, e.g. `bg-surface border border-outline
 * rounded-md text-text-variant font-mono`. The score-low/mid/high colors are
 * for evaluation scores ONLY (never use the primary accent to express a score).
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "surface-lowest": "rgb(var(--surface-lowest) / <alpha-value>)",
        "surface-dim": "rgb(var(--surface-dim) / <alpha-value>)",
        "surface-low": "rgb(var(--surface-low) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        "surface-high": "rgb(var(--surface-high) / <alpha-value>)",
        field: "rgb(var(--field) / <alpha-value>)",

        outline: "rgb(var(--outline) / <alpha-value>)",
        "outline-dim": "rgb(var(--outline-dim) / <alpha-value>)",

        primary: "rgb(var(--primary) / <alpha-value>)",
        "primary-dim": "rgb(var(--primary-dim) / <alpha-value>)",
        "on-primary": "rgb(var(--on-primary) / <alpha-value>)",
        secondary: "rgb(var(--secondary) / <alpha-value>)",
        "secondary-dim": "rgb(var(--secondary-dim) / <alpha-value>)",

        "text-main": "rgb(var(--text-main) / <alpha-value>)",
        "text-variant": "rgb(var(--text-variant) / <alpha-value>)",
        "text-dim": "rgb(var(--text-dim) / <alpha-value>)",

        danger: "rgb(var(--danger) / <alpha-value>)",
        warn: "rgb(var(--warn) / <alpha-value>)",

        // Evaluation score ramp only (red → amber → mint).
        "score-low": "rgb(var(--score-low) / <alpha-value>)",
        "score-mid": "rgb(var(--score-mid) / <alpha-value>)",
        "score-high": "rgb(var(--score-high) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Space Grotesk", "Inter", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "4px",
        DEFAULT: "6px",
        md: "8px",
        lg: "10px",
        // `xl`, `2xl`, `full` fall through to Tailwind defaults.
      },
      // Layout-only; intentionally retained from the prior config.
      spacing: {
        xs: "4px",
        sm: "8px",
        md: "16px",
        lg: "24px",
        xl: "32px",
        unit: "4px",
        gutter: "16px",
        "container-max": "1440px",
      },
      maxWidth: { thread: "680px" },
    },
  },
  plugins: [],
} satisfies Config;
