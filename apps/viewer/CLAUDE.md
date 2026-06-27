# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

PersonaBench Viewer is a React SPA for browsing and inspecting PersonaBench simulation jobs, trials, and agent trajectories. It operates in two modes: "jobs" mode (browse evaluation results) and "tasks" mode (browse task definitions). The mode is determined by the backend API config.

## Commands

```bash
# Install dependencies
npm ci

# Dev server with hot reload (frontend only, http://localhost:5173)
npm run dev

# Full dev with backend API (from repo root)
harbor view ./jobs --dev

# Production build (output: build/client/)
npm run build

# Type checking
npm run typecheck

# Deploy to harbor view (copies build to src/harbor/viewer/static/)
harbor view ./jobs --build
```

Use Node.js 20.19.0 or newer. The checked-in `.node-version` and `.nvmrc`
files pin the tested local runtime, and `.github/workflows/viewer.yml`
typechecks this package in CI.

## Architecture

**Stack**: React 19, React Router 7 (SPA mode, no SSR), Vite, TypeScript strict, Tailwind CSS v4, shadcn/ui (new-york style, Radix primitives).

**Path alias**: `~/*` maps to `./app/*` (configured in tsconfig.json).

### Key Files

- `app/root.tsx` - App shell with providers (QueryClient, ThemeProvider, NuqsAdapter, Toaster)
- `app/routes.ts` - All route definitions
- `app/lib/api.ts` - All backend API calls (fetch-based, base URL from `VITE_API_URL` env var or relative)
- `app/lib/types.ts` - TypeScript types for jobs, trials, tasks, ATIF trajectories, filters, pagination
- `app/lib/hooks.ts` - Custom hooks (keyboard table navigation, debounce)
- `app/lib/highlighter.tsx` - Shiki syntax highlighting setup
- `app/components/ui/` - shadcn/ui component library
- `app/components/trajectory/` - Trajectory/ATIF content renderers
- `app/components/task-chat.tsx` - Streaming AI chat interface (SSE)

### Data Flow

- **Server state**: TanStack React Query for all API data fetching, caching, and mutations
- **URL state**: `nuqs` for search, filters, column visibility, and selection (persisted in query params)
- **Local state**: React useState for transient UI state; sessionStorage for chat history

### Routes

| Path | Purpose |
|------|---------|
| `/` | Jobs listing (jobs mode) or redirect to /task-definitions (tasks mode) |
| `/compare` | Multi-job comparison grid |
| `/jobs/:jobName` | Single job detail with task table |
| `/jobs/:jobName/tasks/:source/:agent/:modelProvider/:modelName/:taskName` | Task results within a job |
| `.../trials/:trialName` | Trial trajectory viewer |
| `/task-definitions` | Task definition browser |
| `/task-definitions/:taskName` | Task definition detail with AI chat |

### Adding shadcn/ui Components

Uses the shadcn CLI with config in `components.json`. Components install to `app/components/ui/`.
