/// <reference types="vite/client" />

/**
 * Ambient type declarations for the Vite client environment.
 *
 * This pulls in module declarations for CSS side-effect imports
 * (`import "./index.css"`), static assets, and `import.meta.env`, so the
 * TypeScript build (`tsc --noEmit`) accepts the same imports Vite resolves at
 * bundle time.
 */
