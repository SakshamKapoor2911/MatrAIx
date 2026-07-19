import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Vite config for the Playground SPA.
 *
 * - React plugin (Fast Refresh + JSX).
 * - `@` path alias -> `src/` (mirrors the `paths` entry in tsconfig.json so
 *   `import { api } from "@/lib/api"` resolves identically in the editor,
 *   the type-checker, and the Rollup bundle).
 * - Dev proxy: every `/api/*` request is forwarded to the FastAPI app on
 *   port 8765 (see `uvicorn backend.api.app:app`), so the browser talks to a
 *   single origin during development. Override the target with the
 *   `VITE_API_TARGET` env var when the backend runs on another port.
 * - `build.outDir` is `dist`; the API mounts that directory as StaticFiles
 *   when it exists, serving the built SPA from the same origin in production.
 */
const API_TARGET = process.env.VITE_API_TARGET ?? "http://localhost:8765";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      "/api": {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
