import type { Config } from "tailwindcss";

/**
 * Tailwind theme for Playground — the "Playground" design system.
 *
 * Dark-first; tokens live in src/index.css as "R G B" triplets and are consumed
 * via rgb(var(--x)/<alpha-value>) so opacity utilities (bg-primary/10,
 * border-secondary/25) work for every color. Two faces only: font-sans /
 * font-display (Inter — same as the public MatrAIx site), font-mono
 * (JetBrains Mono, data + the uppercase `.hud` micro-label).
 *
 * Use the names directly in JSX, e.g. `bg-surface border border-outline
 * rounded-md text-text-variant font-mono`. The score-low/mid/high colors are
 * for evaluation scores ONLY (never use the primary accent to express a score).
 *
 * Font sizes are bumped ~1–2px vs Tailwind defaults for cockpit readability.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontSize: {
        // Was 12/14/16… — nudge the whole UI ladder up without touching every class.
        xs: ["0.875rem", { lineHeight: "1.25rem" }], // 14px
        sm: ["1rem", { lineHeight: "1.5rem" }], // 16px
        base: ["1.0625rem", { lineHeight: "1.625rem" }], // 17px
        lg: ["1.1875rem", { lineHeight: "1.75rem" }], // 19px
        xl: ["1.3125rem", { lineHeight: "1.875rem" }], // 21px
        "2xl": ["1.5rem", { lineHeight: "2rem" }], // 24px
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }], // 30px
      },
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
        accent: "rgb(var(--accent) / <alpha-value>)",
        "accent-dim": "rgb(var(--accent-dim) / <alpha-value>)",

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
        display: ["Inter", "system-ui", "sans-serif"],
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
      keyframes: {
        "cockpit-indeterminate": {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(350%)" },
        },
      },
      animation: {
        "cockpit-indeterminate": "cockpit-indeterminate 1.1s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
