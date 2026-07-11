# Persona DAG Studio — Design

Date: 2026-07-11
Status: Approved direction (approach C: overview + drill-down, integrated into Playground)

## Problem

`persona/synthesis/visualization/full_dag_overview.html` renders all 1,308 nodes
and 6,999 edges of the Persona Full DAG on one canvas. At overview zoom it is an
unreadable hairball, interactions are limited, and the page is static: it cannot
condition the sampler, generate personas, or preview results. The user wants a
web tool deployed with Playground where they can adjust the graph/sampler,
generate personas, and preview them.

## Goals

1. Readable DAG exploration: category-level overview plus per-node drill-down
   subgraphs, replacing the full-hairball rendering as the primary view.
2. Adjustment ("调节"):
   - Pin attribute values before sampling (clamp semantics, see below).
   - Tune sampling parameters (seed, gamma, sample count).
   - Temporarily override graph parameters (edge weights, node priors) at
     request time without editing `full_dag.json`.
3. Generation + preview: sample personas and preview them as (a) grouped
   attribute cards, (b) natural-language persona text, (c) values overlaid on
   the DAG views.
4. Modern visual style consistent with the Playground design system
   (`application/playground/frontend/DESIGN.md`): dark-first, token-driven,
   Inter/Space Grotesk/JetBrains Mono, cyan primary.

## Non-Goals

- True posterior conditioning (rejection/importance sampling). Pinning is a
  do()-style intervention: the pinned node is clamped and only downstream
  nodes are affected; upstream distributions do not update. The UI labels this
  explicitly.
- Persisting graph edits back to `full_dag.json`.
- Replacing or deleting the existing static
  `full_dag_overview.html` (kept for offline review; unchanged).
- WebGL / heavy graph libraries. All views are SVG at the sizes involved
  (44 category nodes; drill-down subgraphs of tens of nodes).

## Architecture

New Playground module "Synthesis Studio":

- Backend: `application/playground/backend/service/persona_synthesis_service.py`
  plus routes registered in `backend/api/app.py`, wrapping
  `persona.synthesis.sampler.PersonaGraphSampler` and `full_dag.json`
  (loaded once per process, cached).
- Sampler extension: conditional sampling (pins) and runtime overrides in
  `persona/synthesis/sampler/sampler.py`.
- Frontend: `SynthesisStudioView` in a new
  `application/playground/frontend/src/components/synthesis/` directory,
  reachable from Playground navigation. It reuses the shared shell primitives
  in `components/studio/StudioShell.tsx` (`StudioMeshShell`, `StudioPageFrame`,
  `StudioGlassPanel`) like the other views do.

### Backend API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/synthesis/graph/overview` | 44 category nodes + aggregated category→category edges (count, weight sum). Computed once, cached. |
| `GET /api/synthesis/graph/subgraph?node=X&up=N&down=N` | Local subgraph around a node with configurable upstream/downstream hops. Returns nodes, edges, and topological layer per node for layout. |
| `GET /api/synthesis/nodes/{id}` | Node detail: value list, base prior, incident CPD/CPT/mask summaries. |
| `POST /api/synthesis/sample` | Body `{n, seed, gamma?, pins: {attr_id: value}, overrides?: {edge_weights, node_priors}}` → sampled personas (attribute maps) + echo of effective config. Synchronous; preview n is 1–100 and the vectorized sampler returns in milliseconds. |
| `POST /api/synthesis/render` | Persona attribute map → natural-language text, reusing `persona/synthesis/scripts/render_personas.py` rendering logic (refactor the reusable part into an importable function; the script keeps its CLI). |

Validation: unknown attribute ids or values in `pins`/`overrides` return 422
with the offending key. Pins on `emit:false` helper nodes are allowed (they are
graph nodes) but flagged in the response.

### Sampler extension

- `pins: dict[node_id, value]` — pinned nodes skip sampling and are clamped to
  the given value index; downstream nodes condition on them via the normal
  forward pass. Do()-intervention semantics.
- Runtime overrides — gamma, per-edge weight, per-node prior — are applied at
  plan-compile time. Compiled plans are cached keyed by a hash of the override
  payload; the no-override plan is the existing cached path.
- Backward compatibility: with no pins and no overrides, sampling output must
  remain bit-identical to current behavior for a fixed seed (guarded by test).

### Frontend

Three-pane layout: overview graph (left) → drill-down subgraph (center) →
adjust + preview rail (right).

- **Overview**: SVG. 44 category nodes sized by attribute count, edges
  weighted by inter-category edge count. Colors follow the dataviz skill
  palette rules within the Playground token system. Click category → attribute
  list; click attribute → drill-down.
- **Drill-down**: SVG layered DAG layout (nodes placed by topological layer
  from the subgraph endpoint), arrowheads, readable labels. Click any node to
  re-center; controls for hop depth.
- **Adjust rail**: pin list (add by clicking a node and choosing a value),
  seed/gamma/count inputs, Generate button (single `.glow` CTA).
- **Preview** (tabs + overlay): attribute cards grouped by category with
  search; rendered persona text; overlay mode stamping sampled values onto
  overview and drill-down nodes with pinned nodes visually distinct, showing
  value propagation along dependencies.
- Style: follow DESIGN.md — dark-first tokens, `.panel` on the two graph
  panes, `.hud` micro-labels, Material Symbols via `<Sym>`, 150–250 ms
  ease-out state motion, `prefers-reduced-motion` honored. No new heavy
  dependencies; typecheck stays green.

## Phases

Each phase lands independently usable:

1. **Graph browsing (read-only)**: overview + subgraph endpoints, node detail,
   overview + drill-down views in Playground.
2. **Adjust + generate + preview**: sampler pins + params, sample/render
   endpoints, adjust rail, three preview modes.
3. **Graph overrides**: edge-weight/prior overrides end to end, with a simple
   before/after comparison of sampled marginals for a touched node.

## Testing

- Backend pytest (existing `backend/tests/` patterns): subgraph correctness on
  known nodes; pinned attributes equal their pinned value in every sample;
  downstream marginals shift under a pin (statistical assertion with fixed
  seed); override plan-cache hit/miss; render endpoint contract.
- Sampler unit tests in `tests/`: pin semantics; no-pin/no-override output
  bit-identical to current sampler for fixed seed.
- Frontend: `npm run typecheck`; manual walkthrough.
- Acceptance: in Playground, pin `region` and `age_bracket`, generate 5
  personas, and view all three previews with value propagation visible on the
  graph.

## Decisions Log

- Approach C chosen over enhancing the static canvas page (A) or vendoring a
  graph library (B): the deploy-adjust-generate-preview goal requires a
  backend, and Playground already provides FastAPI + React infrastructure.
- Pin semantics: clamp (do-intervention), not posterior conditioning —
  accepted by user 2026-07-11.
- Static `full_dag_overview.html` retained unchanged.
