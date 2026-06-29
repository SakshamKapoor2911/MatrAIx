# PersonaBench Viewer

Web UI for browsing and inspecting PersonaBench simulation jobs, trials, and trajectories.

## Development

Use Node.js 20.19.0 or newer. The checked-in `.node-version` and `.nvmrc`
files pin the tested local runtime, and CI typechecks the viewer with the same
version.

Install dependencies from the npm lockfile:

```bash
npm ci
```

Start the frontend dev server with hot reloading:

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`.

For full development with the backend API, use the CLI from the repository root:

```bash
harbor view ./jobs --dev
```

This starts both the backend API server and the frontend dev server with proper configuration.

## Building

Build the production bundle:

```bash
npm run build
```

Typecheck the viewer before opening a PR:

```bash
npm run typecheck
```

Output is written to `build/client/` with static assets ready to be served.

### Deploying changes to `harbor view`

`harbor view` serves static files from `environment/runtime/harbor/viewer/static/`, **not** directly from `apps/viewer/build/client/`. After editing frontend code, you need to both build and copy the output. The easiest way:

```bash
# Option 1: Let harbor do it (recommended)
harbor view ./jobs --build

# Option 2: Manual build + copy
cd apps/viewer
npm run build
rm -rf ../../environment/runtime/harbor/viewer/static
cp -r build/client ../../environment/runtime/harbor/viewer/static
```

After either option, restart the `harbor view` server for changes to take effect.

## Stack

- React 19 with React Router 7
- TanStack Query for data fetching
- TanStack Table for sortable tables
- Tailwind CSS v4 for styling
- shadcn/ui components
- Shiki for syntax highlighting
