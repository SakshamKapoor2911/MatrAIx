import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Vite config for the Persona Curation Cockpit.
 *
 * - React plugin (Fast Refresh + JSX).
 * - `@` path alias -> `src/` (mirrors tsconfig `paths`).
 * - Dev proxy: `/api/*` is forwarded to the demo_app.py http.server, which
 *   defaults to 127.0.0.1:8765 (see demo_app.parse_args). Override with the
 *   `VITE_API_TARGET` env var. So the browser talks to a single origin in dev.
 * - `build.outDir` is `dist`; demo_app.py serves that directory when it exists,
 *   so the built SPA ships from the same origin with no extra server — a
 *   collaborator still just runs `python demo_app.py`.
 */
const API_TARGET = process.env.VITE_API_TARGET ?? "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5174,
    strictPort: false,
    proxy: {
      "/api": { target: API_TARGET, changeOrigin: true },
      "/files": { target: API_TARGET, changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    // dist/ is committed (so collaborators run `python demo_app.py` with no
    // build step); keep it lean by not shipping sourcemaps.
    sourcemap: false,
  },
});
