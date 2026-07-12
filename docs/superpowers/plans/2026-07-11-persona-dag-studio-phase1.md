# Persona DAG Studio — Phase 1 (Read-Only Graph Browsing) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only "Synthesis Studio" module to Playground: a category-level overview of the Persona Full DAG plus per-node drill-down subgraphs and node detail, served by new FastAPI endpoints.

**Architecture:** A stdlib-only backend service (`PersonaSynthesisService`) lazily loads `persona/synthesis/graph/full_dag.json` (23 MB, loaded once per process), precomputes category aggregates and adjacency, and serves three GET endpoints. The React frontend adds a `SynthesisStudioView` (three panes: SVG category overview → SVG layered drill-down subgraph → detail rail) wired into the existing TopBar/App navigation.

**Tech Stack:** FastAPI + pydantic v2 (backend), React 18 + TypeScript + Tailwind + @tanstack/react-query (frontend), hand-rolled SVG (no new dependencies).

**Spec:** `docs/superpowers/specs/2026-07-11-persona-dag-studio-design.md` (this plan covers Phase 1 only; Phases 2–3 get their own plans after this lands).

## Global Constraints

- The backend service and `backend/api/schemas.py` must stay stdlib + pydantic only — **no numpy import** anywhere in Phase 1 (the test suite runs without numpy; see `backend/tests/conftest.py` docstring). Do not import `persona.synthesis.sampler` (its `__init__` pulls in numpy) — read the graph JSON directly with `json`.
- JSON wire format is **camelCase**, matching the existing API contract.
- Frontend styling uses Playground design tokens only (`application/playground/frontend/DESIGN.md`) — Tailwind token classes or `rgb(var(--x))` CSS vars, **never raw hex**. Dark-first; both themes must work.
- **No new frontend dependencies.** `npm run typecheck` must stay green.
- Do not color the 44 categories with 44 hues (dataviz rule: categorical palettes cap at ~8 fixed hues). Identity is carried by labels and position; nodes use neutral surface fills; hover/selection uses `primary`; magnitude uses size. No new palette is created, so no palette validation run is needed.
- `persona/synthesis/visualization/full_dag_overview.html` stays untouched.
- Backend tests live in `application/playground/backend/tests/` and must pass with `python -m pytest application/playground/backend/tests -x -q` from the repo root using the project venv (`uv run` or `.venv`).
- Commit messages: short imperative subject; end the body with:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: Backend graph service (`PersonaSynthesisService`)

**Files:**
- Create: `application/playground/backend/service/persona_synthesis_service.py`
- Test: `application/playground/backend/tests/test_persona_synthesis_service.py`

**Interfaces:**
- Consumes: `persona/synthesis/graph/full_dag.json` structure — `{"nodes": [{"id", "label", "category", "values", "prior", "description", "emit"?}], "directed_proposal_edges": [{"source", "target", "edge_weight", "relation"}], "proposal_view": {"topological_order": [ids]}}`. Nodes without `"emit"` default to emitted; `emit: false` marks latent/helper nodes.
- Produces (used by Task 2's routes):
  - `PersonaSynthesisService(graph_path: Path)` — cheap constructor, no I/O.
  - `PersonaSynthesisService.from_repo(repo_root: Path) -> PersonaSynthesisService`
  - `overview() -> dict` (camelCase payload, cached)
  - `subgraph(node_id: str, *, up: int = 1, down: int = 1) -> dict` — raises `KeyError` on unknown node.
  - `node_detail(node_id: str) -> dict` — raises `KeyError` on unknown node.

- [ ] **Step 1: Write the failing tests**

Create `application/playground/backend/tests/test_persona_synthesis_service.py`:

```python
"""Unit tests for PersonaSynthesisService over a small synthetic graph."""

from __future__ import annotations

import json

import pytest

from backend.service.persona_synthesis_service import PersonaSynthesisService

SYNTH_GRAPH = {
    "nodes": [
        {"id": "a", "label": "Age", "category": "Demographics",
         "values": ["young", "old"], "prior": [0.5, 0.5]},
        {"id": "b", "label": "Job", "category": "Demographics",
         "values": ["dev", "chef"], "prior": [0.6, 0.4]},
        {"id": "h", "label": "Latent H", "category": "Latent", "emit": False,
         "values": ["v"], "prior": [1.0]},
        {"id": "c", "label": "Condition", "category": "Health",
         "values": ["p", "q"], "prior": [0.3, 0.7],
         "description": "a health condition"},
        {"id": "d", "label": "Diet", "category": "Health",
         "values": ["m", "n"], "prior": [0.5, 0.5]},
    ],
    "directed_proposal_edges": [
        {"source": "a", "target": "b", "edge_weight": 0.8, "relation": "influences"},
        {"source": "b", "target": "c", "edge_weight": 0.5, "relation": "influences"},
        {"source": "h", "target": "c", "edge_weight": 0.2, "relation": "latent"},
        {"source": "c", "target": "d", "edge_weight": 0.9, "relation": "influences"},
    ],
    "proposal_view": {"topological_order": ["a", "h", "b", "c", "d"]},
}


@pytest.fixture()
def service(tmp_path):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(SYNTH_GRAPH), encoding="utf-8")
    return PersonaSynthesisService(graph_path)


def test_overview_categories_sorted_by_avg_topo(service):
    overview = service.overview()
    names = [cat["name"] for cat in overview["categories"]]
    # Demographics avg topo = (0+2)/2 = 1.0, Latent = 1.0, Health = (3+4)/2 = 3.5.
    # Ties break alphabetically: Demographics before Latent.
    assert names == ["Demographics", "Latent", "Health"]


def test_overview_category_counts_and_attributes(service):
    overview = service.overview()
    by_name = {cat["name"]: cat for cat in overview["categories"]}
    demo = by_name["Demographics"]
    assert demo["nodeCount"] == 2
    assert demo["attributeCount"] == 2
    assert demo["helperCount"] == 0
    assert [a["id"] for a in demo["attributes"]] == ["a", "b"]  # topo order
    latent = by_name["Latent"]
    assert latent["attributeCount"] == 0
    assert latent["helperCount"] == 1


def test_overview_category_edges_aggregate_cross_category(service):
    overview = service.overview()
    edges = {(e["source"], e["target"]): e for e in overview["edges"]}
    # b->c and h->c cross into Health; a->b is internal to Demographics.
    assert ("Demographics", "Health") in edges
    assert edges[("Demographics", "Health")]["count"] == 1
    assert edges[("Latent", "Health")]["count"] == 1
    assert ("Demographics", "Demographics") not in edges
    by_name = {cat["name"]: cat for cat in overview["categories"]}
    assert by_name["Demographics"]["internalEdgeCount"] == 1
    assert by_name["Health"]["internalEdgeCount"] == 1  # c->d


def test_overview_counts(service):
    counts = service.overview()["counts"]
    assert counts == {
        "graphNodes": 5,
        "attributes": 4,
        "helpers": 1,
        "directedEdges": 4,
        "categories": 3,
    }


def test_subgraph_layers_and_edges(service):
    result = service.subgraph("c", up=1, down=1)
    assert result["center"] == "c"
    layers = {n["id"]: n["layer"] for n in result["nodes"]}
    assert layers == {"b": -1, "h": -1, "c": 0, "d": 1}
    edge_pairs = {(e["source"], e["target"]) for e in result["edges"]}
    assert edge_pairs == {("b", "c"), ("h", "c"), ("c", "d")}
    assert result["truncated"] is False


def test_subgraph_zero_hops_is_center_only(service):
    result = service.subgraph("c", up=0, down=0)
    assert [n["id"] for n in result["nodes"]] == ["c"]
    assert result["edges"] == []


def test_subgraph_two_hops_upstream(service):
    result = service.subgraph("c", up=2, down=0)
    layers = {n["id"]: n["layer"] for n in result["nodes"]}
    assert layers == {"a": -2, "b": -1, "h": -1, "c": 0}
    # a->b is between included nodes, so it appears.
    edge_pairs = {(e["source"], e["target"]) for e in result["edges"]}
    assert ("a", "b") in edge_pairs


def test_subgraph_unknown_node_raises(service):
    with pytest.raises(KeyError):
        service.subgraph("nope")


def test_node_detail_fields(service):
    detail = service.node_detail("c")
    assert detail["id"] == "c"
    assert detail["label"] == "Condition"
    assert detail["category"] == "Health"
    assert detail["description"] == "a health condition"
    assert detail["type"] == "attribute"
    assert detail["values"] == ["p", "q"]
    assert detail["prior"] == [0.3, 0.7]
    assert detail["inDegree"] == 2
    assert detail["outDegree"] == 1
    assert {e["id"] for e in detail["inEdges"]} == {"b", "h"}
    assert [e["id"] for e in detail["outEdges"]] == ["d"]


def test_node_detail_helper_type(service):
    assert service.node_detail("h")["type"] == "latent/helper"


def test_node_detail_unknown_raises(service):
    with pytest.raises(KeyError):
        service.node_detail("nope")
```

- [ ] **Step 2: Run tests to verify they fail**

Run from repo root:
```bash
uv run python -m pytest application/playground/backend/tests/test_persona_synthesis_service.py -x -q
```
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'backend.service.persona_synthesis_service'`

- [ ] **Step 3: Implement the service**

Create `application/playground/backend/service/persona_synthesis_service.py`:

```python
"""Read-only browsing service for the Persona Full DAG (Synthesis Studio).

Loads ``persona/synthesis/graph/full_dag.json`` lazily (23 MB, once per
process) and serves camelCase view dicts for the overview, subgraph, and
node-detail endpoints. Stdlib-only on purpose: importing
``persona.synthesis.sampler`` would pull in numpy, which the backend test
suite runs without. Phase 2 (sampling) will lazy-import the sampler inside
request handlers instead.
"""

from __future__ import annotations

import json
import threading
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["PersonaSynthesisService", "DEFAULT_GRAPH_RELPATH", "MAX_SUBGRAPH_NODES_PER_DIRECTION"]

DEFAULT_GRAPH_RELPATH = Path("persona") / "synthesis" / "graph" / "full_dag.json"

#: Per-direction node cap so drill-down views stay readable (closest-first).
MAX_SUBGRAPH_NODES_PER_DIRECTION = 60

#: Cap on the per-node edge lists in node detail payloads.
MAX_DETAIL_EDGES = 20


def _category(node: Dict[str, Any]) -> str:
    return node.get("category") or "Uncategorized"


def _is_attribute(node: Dict[str, Any]) -> bool:
    return node.get("emit", True) is not False


class PersonaSynthesisService:
    """Lazy, cached, thread-safe views over the Full DAG graph JSON."""

    def __init__(self, graph_path: Path) -> None:
        self._graph_path = Path(graph_path)
        self._lock = threading.Lock()
        self._loaded = False
        self._nodes_by_id: Dict[str, Dict[str, Any]] = {}
        self._out_edges: Dict[str, List[Dict[str, Any]]] = {}
        self._in_edges: Dict[str, List[Dict[str, Any]]] = {}
        self._topo_index: Dict[str, int] = {}
        self._edge_count = 0
        self._overview: Optional[Dict[str, Any]] = None

    @classmethod
    def from_repo(cls, repo_root: Path) -> "PersonaSynthesisService":
        return cls(Path(repo_root) / DEFAULT_GRAPH_RELPATH)

    # ------------------------------------------------------------------ load
    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            graph = json.loads(self._graph_path.read_text(encoding="utf-8"))
            nodes = graph.get("nodes", [])
            edges = graph.get("directed_proposal_edges", [])
            order = graph.get("proposal_view", {}).get("topological_order", [])

            self._nodes_by_id = {node["id"]: node for node in nodes}
            self._topo_index = {node_id: i for i, node_id in enumerate(order)}
            self._out_edges = {node["id"]: [] for node in nodes}
            self._in_edges = {node["id"]: [] for node in nodes}
            kept = 0
            for edge in edges:
                source = edge.get("source")
                target = edge.get("target")
                if source in self._nodes_by_id and target in self._nodes_by_id:
                    self._out_edges[source].append(edge)
                    self._in_edges[target].append(edge)
                    kept += 1
            self._edge_count = kept
            self._overview = self._build_overview()
            self._loaded = True

    def _topo(self, node_id: str) -> int:
        return self._topo_index.get(node_id, len(self._topo_index))

    # -------------------------------------------------------------- overview
    def _build_overview(self) -> Dict[str, Any]:
        by_category: Dict[str, List[Dict[str, Any]]] = {}
        for node in self._nodes_by_id.values():
            by_category.setdefault(_category(node), []).append(node)

        cross_edges: Dict[Tuple[str, str], Dict[str, Any]] = {}
        internal_counts: Dict[str, int] = {}
        for node_id, edges in self._out_edges.items():
            source_cat = _category(self._nodes_by_id[node_id])
            for edge in edges:
                target_cat = _category(self._nodes_by_id[edge["target"]])
                weight = float(edge.get("edge_weight", 1.0))
                if source_cat == target_cat:
                    internal_counts[source_cat] = internal_counts.get(source_cat, 0) + 1
                    continue
                key = (source_cat, target_cat)
                agg = cross_edges.setdefault(
                    key, {"source": source_cat, "target": target_cat, "count": 0, "weightSum": 0.0}
                )
                agg["count"] += 1
                agg["weightSum"] += weight

        categories: List[Dict[str, Any]] = []
        for name, cat_nodes in by_category.items():
            topo_positions = [self._topo(n["id"]) for n in cat_nodes]
            avg_topo = sum(topo_positions) / len(topo_positions) if topo_positions else 0.0
            attributes = sorted(
                (n for n in cat_nodes if _is_attribute(n)),
                key=lambda n: (self._topo(n["id"]), n["id"]),
            )
            categories.append(
                {
                    "name": name,
                    "nodeCount": len(cat_nodes),
                    "attributeCount": len(attributes),
                    "helperCount": len(cat_nodes) - len(attributes),
                    "avgTopo": round(avg_topo, 2),
                    "internalEdgeCount": internal_counts.get(name, 0),
                    "attributes": [
                        {
                            "id": n["id"],
                            "label": n.get("label", n["id"]),
                            "valuesCount": len(n.get("values", [])),
                            "degree": len(self._in_edges[n["id"]]) + len(self._out_edges[n["id"]]),
                        }
                        for n in attributes
                    ],
                }
            )
        categories.sort(key=lambda cat: (cat["avgTopo"], cat["name"]))

        attribute_total = sum(cat["attributeCount"] for cat in categories)
        for agg in cross_edges.values():
            agg["weightSum"] = round(agg["weightSum"], 4)
        return {
            "categories": categories,
            "edges": sorted(
                cross_edges.values(), key=lambda e: (-e["count"], e["source"], e["target"])
            ),
            "counts": {
                "graphNodes": len(self._nodes_by_id),
                "attributes": attribute_total,
                "helpers": len(self._nodes_by_id) - attribute_total,
                "directedEdges": self._edge_count,
                "categories": len(categories),
            },
        }

    def overview(self) -> Dict[str, Any]:
        self._ensure_loaded()
        assert self._overview is not None
        return self._overview

    # -------------------------------------------------------------- subgraph
    def _walk(self, start: str, *, downstream: bool, max_hops: int) -> Tuple[Dict[str, int], bool]:
        """BFS hop distances from ``start`` (exclusive), closest-first, capped."""
        adjacency = self._out_edges if downstream else self._in_edges
        key = "target" if downstream else "source"
        distances: Dict[str, int] = {}
        truncated = False
        queue: deque[Tuple[str, int]] = deque([(start, 0)])
        seen = {start}
        while queue:
            node_id, hops = queue.popleft()
            if hops >= max_hops:
                continue
            for edge in adjacency[node_id]:
                neighbor = edge[key]
                if neighbor in seen:
                    continue
                if len(distances) >= MAX_SUBGRAPH_NODES_PER_DIRECTION:
                    truncated = True
                    return distances, truncated
                seen.add(neighbor)
                distances[neighbor] = hops + 1
                queue.append((neighbor, hops + 1))
        return distances, truncated

    def subgraph(self, node_id: str, *, up: int = 1, down: int = 1) -> Dict[str, Any]:
        self._ensure_loaded()
        if node_id not in self._nodes_by_id:
            raise KeyError(node_id)
        upstream, up_truncated = self._walk(node_id, downstream=False, max_hops=up)
        downstream, down_truncated = self._walk(node_id, downstream=True, max_hops=down)

        layer_by_id: Dict[str, int] = {node_id: 0}
        for other, hops in upstream.items():
            layer_by_id[other] = -hops
        for other, hops in downstream.items():
            # A node reachable both ways keeps its upstream (negative) layer.
            layer_by_id.setdefault(other, hops)

        included = set(layer_by_id)
        node_payload = [
            {
                "id": nid,
                "label": self._nodes_by_id[nid].get("label", nid),
                "category": _category(self._nodes_by_id[nid]),
                "layer": layer_by_id[nid],
                "valuesCount": len(self._nodes_by_id[nid].get("values", [])),
                "emit": _is_attribute(self._nodes_by_id[nid]),
                "inDegree": len(self._in_edges[nid]),
                "outDegree": len(self._out_edges[nid]),
            }
            for nid in sorted(included, key=lambda n: (layer_by_id[n], self._topo(n), n))
        ]
        edge_payload = []
        for nid in included:
            for edge in self._out_edges[nid]:
                if edge["target"] in included:
                    edge_payload.append(
                        {
                            "source": nid,
                            "target": edge["target"],
                            "weight": round(float(edge.get("edge_weight", 1.0)), 4),
                            "relation": edge.get("relation", ""),
                        }
                    )
        edge_payload.sort(key=lambda e: (e["source"], e["target"]))
        return {
            "center": node_id,
            "up": up,
            "down": down,
            "truncated": up_truncated or down_truncated,
            "nodes": node_payload,
            "edges": edge_payload,
        }

    # ----------------------------------------------------------- node detail
    def node_detail(self, node_id: str) -> Dict[str, Any]:
        self._ensure_loaded()
        node = self._nodes_by_id.get(node_id)
        if node is None:
            raise KeyError(node_id)

        def edge_view(edge: Dict[str, Any], other_key: str) -> Dict[str, Any]:
            other = self._nodes_by_id[edge[other_key]]
            return {
                "id": other["id"],
                "label": other.get("label", other["id"]),
                "relation": edge.get("relation", ""),
                "weight": round(float(edge.get("edge_weight", 1.0)), 4),
            }

        in_edges = sorted(
            self._in_edges[node_id],
            key=lambda e: -float(e.get("edge_weight", 1.0)),
        )
        out_edges = sorted(
            self._out_edges[node_id],
            key=lambda e: -float(e.get("edge_weight", 1.0)),
        )
        prior = node.get("prior") or []
        return {
            "id": node_id,
            "label": node.get("label", node_id),
            "category": _category(node),
            "description": node.get("description", ""),
            "type": "attribute" if _is_attribute(node) else "latent/helper",
            "values": list(node.get("values", [])),
            "prior": [round(float(p), 4) for p in prior],
            "parents": list(node.get("parents", [])),
            "inDegree": len(self._in_edges[node_id]),
            "outDegree": len(self._out_edges[node_id]),
            "inEdges": [edge_view(e, "source") for e in in_edges[:MAX_DETAIL_EDGES]],
            "outEdges": [edge_view(e, "target") for e in out_edges[:MAX_DETAIL_EDGES]],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest application/playground/backend/tests/test_persona_synthesis_service.py -x -q
```
Expected: all 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add application/playground/backend/service/persona_synthesis_service.py \
        application/playground/backend/tests/test_persona_synthesis_service.py
git commit -m "Add PersonaSynthesisService for DAG browsing

Stdlib-only service over full_dag.json: category overview aggregates,
hop-limited subgraph extraction, and node detail views.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: API schemas, AppState wiring, and synthesis routes

**Files:**
- Modify: `application/playground/backend/api/schemas.py` (append models + `__all__` entries)
- Modify: `application/playground/backend/api/deps.py` (AppState field + build_state)
- Modify: `application/playground/backend/api/app.py` (three GET routes inside `create_app`)
- Test: `application/playground/backend/tests/test_synthesis_api.py`

**Interfaces:**
- Consumes: `PersonaSynthesisService` from Task 1 (`overview()`, `subgraph(node_id, up=, down=)`, `node_detail(node_id)`; `KeyError` on unknown node).
- Produces:
  - `AppState.persona_synthesis: PersonaSynthesisService`
  - `GET /api/synthesis/graph/overview` → `SynthesisOverviewResponse`
  - `GET /api/synthesis/graph/subgraph?node=<id>&up=<0-4>&down=<0-4>` → `SynthesisSubgraphResponse` (404 unknown node, 422 out-of-range hops)
  - `GET /api/synthesis/nodes/{node_id}` → `SynthesisNodeDetail` (404 unknown node)

- [ ] **Step 1: Write the failing API tests**

Create `application/playground/backend/tests/test_synthesis_api.py`:

```python
"""API contract tests for the /api/synthesis endpoints.

The endpoints are exercised against a small synthetic graph: the test swaps
the app's PersonaSynthesisService for one pointed at a tmp file, so the
23 MB committed graph is never loaded in the test suite.
"""

from __future__ import annotations

import json

import pytest

from backend.service.persona_synthesis_service import PersonaSynthesisService
from backend.tests.test_persona_synthesis_service import SYNTH_GRAPH


@pytest.fixture()
def synthesis_client(client, app, tmp_path):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(SYNTH_GRAPH), encoding="utf-8")
    app.state.services.persona_synthesis = PersonaSynthesisService(graph_path)
    return client


def test_overview_endpoint(synthesis_client):
    response = synthesis_client.get("/api/synthesis/graph/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["graphNodes"] == 5
    assert [cat["name"] for cat in body["categories"]] == [
        "Demographics", "Latent", "Health",
    ]
    assert body["categories"][0]["attributes"][0]["id"] == "a"


def test_subgraph_endpoint(synthesis_client):
    response = synthesis_client.get(
        "/api/synthesis/graph/subgraph", params={"node": "c", "up": 1, "down": 1}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["center"] == "c"
    assert {n["id"]: n["layer"] for n in body["nodes"]} == {
        "b": -1, "h": -1, "c": 0, "d": 1,
    }


def test_subgraph_unknown_node_is_404(synthesis_client):
    response = synthesis_client.get(
        "/api/synthesis/graph/subgraph", params={"node": "nope"}
    )
    assert response.status_code == 404


def test_subgraph_out_of_range_hops_is_422(synthesis_client):
    response = synthesis_client.get(
        "/api/synthesis/graph/subgraph", params={"node": "c", "up": 9}
    )
    assert response.status_code == 422


def test_node_detail_endpoint(synthesis_client):
    response = synthesis_client.get("/api/synthesis/nodes/c")
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "Condition"
    assert body["values"] == ["p", "q"]
    assert body["type"] == "attribute"


def test_node_detail_unknown_is_404(synthesis_client):
    response = synthesis_client.get("/api/synthesis/nodes/nope")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run python -m pytest application/playground/backend/tests/test_synthesis_api.py -x -q
```
Expected: FAIL — first with `AttributeError` (AppState has no field `persona_synthesis`) or 404s from missing routes, depending on assertion order.

- [ ] **Step 3: Add pydantic models to schemas.py**

Append to `application/playground/backend/api/schemas.py` (bottom of the file), and add the eight new names to `__all__`:

```python
# --------------------------------------------------------------------------- #
# Synthesis Studio (Persona Full DAG browsing)
# --------------------------------------------------------------------------- #
class SynthesisCategoryAttribute(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    label: str
    valuesCount: int
    degree: int


class SynthesisCategorySummary(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    nodeCount: int
    attributeCount: int
    helperCount: int
    avgTopo: float
    internalEdgeCount: int
    attributes: List[SynthesisCategoryAttribute]


class SynthesisCategoryEdge(BaseModel):
    model_config = ConfigDict(extra="allow")
    source: str
    target: str
    count: int
    weightSum: float


class SynthesisOverviewResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    categories: List[SynthesisCategorySummary]
    edges: List[SynthesisCategoryEdge]
    counts: Dict[str, int]


class SynthesisSubgraphNode(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    label: str
    category: str
    layer: int
    valuesCount: int
    emit: bool
    inDegree: int
    outDegree: int


class SynthesisSubgraphEdge(BaseModel):
    model_config = ConfigDict(extra="allow")
    source: str
    target: str
    weight: float
    relation: str


class SynthesisSubgraphResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    center: str
    up: int
    down: int
    truncated: bool
    nodes: List[SynthesisSubgraphNode]
    edges: List[SynthesisSubgraphEdge]


class SynthesisNodeEdgeView(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    label: str
    relation: str
    weight: float


class SynthesisNodeDetail(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    label: str
    category: str
    description: str
    type: str
    values: List[str]
    prior: List[float]
    parents: List[str]
    inDegree: int
    outDegree: int
    inEdges: List[SynthesisNodeEdgeView]
    outEdges: List[SynthesisNodeEdgeView]
```

Add to `__all__` (keep alphabetical grouping loose — append a synthesis block at the end):

```python
    "SynthesisCategoryAttribute",
    "SynthesisCategorySummary",
    "SynthesisCategoryEdge",
    "SynthesisOverviewResponse",
    "SynthesisSubgraphNode",
    "SynthesisSubgraphEdge",
    "SynthesisSubgraphResponse",
    "SynthesisNodeEdgeView",
    "SynthesisNodeDetail",
```

- [ ] **Step 4: Wire the service into AppState (deps.py)**

In `application/playground/backend/api/deps.py`:

1. Extend the `TYPE_CHECKING` block:

```python
if TYPE_CHECKING:  # pragma: no cover - typing only
    from backend.service.harbor_job_service import HarborJobService
    from backend.service.persona_pool_service import PersonaPoolService
    from backend.service.persona_synthesis_service import PersonaSynthesisService
```

2. Add the dataclass field (after `persona_pool`):

```python
@dataclass
class AppState:
    """Container for the process-wide service singletons."""

    config: ConfigManager
    harbor_jobs: "HarborJobService"
    persona_pool: "PersonaPoolService"
    persona_synthesis: "PersonaSynthesisService"
```

3. Construct it in `build_state` (constructor is cheap; the 23 MB JSON loads lazily on first request):

```python
    config = ConfigManager()
    from backend.service.harbor_job_service import HarborJobService
    from backend.service.persona_pool_service import PersonaPoolService
    from backend.service.persona_synthesis_service import PersonaSynthesisService

    harbor_jobs = HarborJobService.from_repo()
    persona_pool = PersonaPoolService.from_repo(repo_root=harbor_jobs.repo_root)
    persona_synthesis = PersonaSynthesisService.from_repo(harbor_jobs.repo_root)
    return AppState(
        config=config,
        harbor_jobs=harbor_jobs,
        persona_pool=persona_pool,
        persona_synthesis=persona_synthesis,
    )
```

- [ ] **Step 5: Add the routes in app.py**

Inside `create_app` in `application/playground/backend/api/app.py`, after the last existing `@app.get` route block (before the SPA mounting / `return app`), add:

```python
    # ----------------------------------------------------------------- #
    # Synthesis Studio: Persona Full DAG browsing
    # ----------------------------------------------------------------- #
    @app.get(
        "/api/synthesis/graph/overview",
        response_model=schemas.SynthesisOverviewResponse,
        tags=["synthesis"],
    )
    def synthesis_overview(services: AppState = Depends(get_services)):
        """Category-level aggregate view of the Persona Full DAG."""
        return services.persona_synthesis.overview()

    @app.get(
        "/api/synthesis/graph/subgraph",
        response_model=schemas.SynthesisSubgraphResponse,
        tags=["synthesis"],
    )
    def synthesis_subgraph(
        node: str,
        up: int = Query(1, ge=0, le=4),
        down: int = Query(1, ge=0, le=4),
        services: AppState = Depends(get_services),
    ):
        """Hop-limited local subgraph around one node, with topological layers."""
        try:
            return services.persona_synthesis.subgraph(node, up=up, down=down)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"unknown graph node: {node}")

    @app.get(
        "/api/synthesis/nodes/{node_id}",
        response_model=schemas.SynthesisNodeDetail,
        tags=["synthesis"],
    )
    def synthesis_node_detail(
        node_id: str,
        services: AppState = Depends(get_services),
    ):
        """Full detail for one graph node: values, prior, and incident edges."""
        try:
            return services.persona_synthesis.node_detail(node_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"unknown graph node: {node_id}")
```

(`Depends`, `HTTPException`, and `Query` are already imported at the top of app.py.)

- [ ] **Step 6: Run the new tests, then the full backend suite**

```bash
uv run python -m pytest application/playground/backend/tests/test_synthesis_api.py -x -q
uv run python -m pytest application/playground/backend/tests -q
```
Expected: new tests PASS; full suite PASSES (no regressions — the AppState dataclass gained a required field, and `build_state` is its only constructor site plus any tests constructing AppState directly; if a test constructs `AppState(...)` by hand, add `persona_synthesis=PersonaSynthesisService(tmp_path / "missing.json")` there — search with `grep -rn "AppState(" application/playground/backend/tests`).

- [ ] **Step 7: Commit**

```bash
git add application/playground/backend/api/schemas.py \
        application/playground/backend/api/deps.py \
        application/playground/backend/api/app.py \
        application/playground/backend/tests/test_synthesis_api.py
git commit -m "Add /api/synthesis graph browsing endpoints

Overview, subgraph, and node-detail routes backed by
PersonaSynthesisService wired into AppState.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Frontend types and API client functions

**Files:**
- Modify: `application/playground/frontend/src/lib/types.ts` (append interfaces)
- Modify: `application/playground/frontend/src/lib/api.ts` (import types, add three functions to the `api` object)

**Interfaces:**
- Consumes: the wire shapes produced by Task 2.
- Produces (used by Tasks 4–6):
  - `api.getSynthesisOverview(): Promise<SynthesisOverviewResponse>`
  - `api.getSynthesisSubgraph(node: string, up: number, down: number): Promise<SynthesisSubgraphResponse>`
  - `api.getSynthesisNode(id: string): Promise<SynthesisNodeDetail>`
  - Exported types: `SynthesisOverviewResponse`, `SynthesisCategorySummary`, `SynthesisCategoryEdge`, `SynthesisSubgraphResponse`, `SynthesisSubgraphNode`, `SynthesisSubgraphEdge`, `SynthesisNodeDetail`

- [ ] **Step 1: Append types to `src/lib/types.ts`**

```ts
// ---------------------------------------------------------------------------
// Synthesis Studio (Persona Full DAG browsing)
// ---------------------------------------------------------------------------
export interface SynthesisCategoryAttribute {
  id: string;
  label: string;
  valuesCount: number;
  degree: number;
}

export interface SynthesisCategorySummary {
  name: string;
  nodeCount: number;
  attributeCount: number;
  helperCount: number;
  avgTopo: number;
  internalEdgeCount: number;
  attributes: SynthesisCategoryAttribute[];
}

export interface SynthesisCategoryEdge {
  source: string;
  target: string;
  count: number;
  weightSum: number;
}

export interface SynthesisOverviewResponse {
  categories: SynthesisCategorySummary[];
  edges: SynthesisCategoryEdge[];
  counts: Record<string, number>;
}

export interface SynthesisSubgraphNode {
  id: string;
  label: string;
  category: string;
  layer: number;
  valuesCount: number;
  emit: boolean;
  inDegree: number;
  outDegree: number;
}

export interface SynthesisSubgraphEdge {
  source: string;
  target: string;
  weight: number;
  relation: string;
}

export interface SynthesisSubgraphResponse {
  center: string;
  up: number;
  down: number;
  truncated: boolean;
  nodes: SynthesisSubgraphNode[];
  edges: SynthesisSubgraphEdge[];
}

export interface SynthesisNodeEdgeView {
  id: string;
  label: string;
  relation: string;
  weight: number;
}

export interface SynthesisNodeDetail {
  id: string;
  label: string;
  category: string;
  description: string;
  type: string;
  values: string[];
  prior: number[];
  parents: string[];
  inDegree: number;
  outDegree: number;
  inEdges: SynthesisNodeEdgeView[];
  outEdges: SynthesisNodeEdgeView[];
}
```

- [ ] **Step 2: Add client functions to `src/lib/api.ts`**

Add to the type-only import block at the top:

```ts
import type {
  // ... existing names ...
  SynthesisNodeDetail,
  SynthesisOverviewResponse,
  SynthesisSubgraphResponse,
} from "./types";
```

Add inside the `export const api = { ... }` object (the file's `qs` helper already exists):

```ts
  getSynthesisOverview: () =>
    request<SynthesisOverviewResponse>("/api/synthesis/graph/overview"),
  getSynthesisSubgraph: (node: string, up: number, down: number) =>
    request<SynthesisSubgraphResponse>(
      `/api/synthesis/graph/subgraph${qs({ node, up, down })}`,
    ),
  getSynthesisNode: (id: string) =>
    request<SynthesisNodeDetail>(`/api/synthesis/nodes/${encodeURIComponent(id)}`),
```

- [ ] **Step 3: Typecheck**

```bash
cd application/playground/frontend && npm run typecheck
```
Expected: PASS (no errors).

- [ ] **Step 4: Commit**

```bash
git add application/playground/frontend/src/lib/types.ts \
        application/playground/frontend/src/lib/api.ts
git commit -m "Add synthesis API types and client functions

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Navigation wiring and SynthesisStudioView shell

**Files:**
- Create: `application/playground/frontend/src/components/synthesis/SynthesisStudioView.tsx`
- Modify: `application/playground/frontend/src/components/TopBar.tsx` (new nav entry + props)
- Modify: `application/playground/frontend/src/App.tsx` (view branch + callbacks)

**Interfaces:**
- Consumes: `api.getSynthesisOverview` (Task 3); `StudioMeshShell`, `StudioPageFrame`, `StudioPageHeader`, `StudioGlassPanel` from `./studio/StudioShell`.
- Produces: `SynthesisStudioView` component (no props); TopBar gains `synthesisActive: boolean` and `onOpenSynthesis: () => void`; the URL state `view=synthesis` routes to the new view. Tasks 5–6 replace the placeholder pane contents and add the selection state (`selectedCategory`, `centerNode`, `selectedNode`) — the Task 4 shell deliberately has no selection state yet, so `npm run typecheck` (noUnusedLocals) stays green at this checkpoint.

- [ ] **Step 1: Create the view shell**

Create `application/playground/frontend/src/components/synthesis/SynthesisStudioView.tsx`:

```tsx
/**
 * Synthesis Studio: read-only browsing of the Persona Full DAG.
 *
 * Three panes: category overview graph → drill-down subgraph → detail rail.
 * Phase 1 of docs/superpowers/specs/2026-07-11-persona-dag-studio-design.md.
 */
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SynthesisOverviewResponse } from "@/lib/types";
import {
  StudioGlassPanel,
  StudioMeshShell,
  StudioPageFrame,
  StudioPageHeader,
} from "../studio/StudioShell";

export function SynthesisStudioView() {
  const overviewQuery = useQuery<SynthesisOverviewResponse>({
    queryKey: ["synthesis", "overview"],
    queryFn: api.getSynthesisOverview,
    staleTime: Infinity,
  });
  const overview = overviewQuery.data ?? null;

  return (
    <StudioMeshShell>
      <StudioPageFrame>
        <StudioPageHeader
          eyebrow="MatrAIx · Synthesis"
          title="Persona DAG Studio"
          subtitle={
            overview
              ? `${overview.counts.graphNodes.toLocaleString()} nodes · ${overview.counts.directedEdges.toLocaleString()} directed edges · ${overview.counts.categories} categories`
              : "Loading the Persona Full DAG…"
          }
        />
        <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,4fr)_minmax(0,3fr)]">
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            <div className="grid h-full place-items-center text-sm text-text-dim">
              {overviewQuery.isError
                ? "Failed to load the graph overview."
                : "Category overview (Task 5)"}
            </div>
          </StudioGlassPanel>
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            <div className="grid h-full place-items-center text-sm text-text-dim">
              Drill-down subgraph (Task 6)
            </div>
          </StudioGlassPanel>
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            <div className="grid h-full place-items-center text-sm text-text-dim">
              Details
            </div>
          </StudioGlassPanel>
        </div>
      </StudioPageFrame>
    </StudioMeshShell>
  );
}

export default SynthesisStudioView;
```

Note: check `StudioGlassPanel`'s actual props in `studio/StudioShell.tsx` before using `className` — if it doesn't accept `className`, wrap it in a `div` with those classes instead. Adjust to whatever the shell primitives actually accept; the layout intent is a responsive 5/4/3 three-column grid.

- [ ] **Step 2: Extend TopBar**

In `application/playground/frontend/src/components/TopBar.tsx`:

1. Extend `TopBarProps` and the destructured params:

```ts
export interface TopBarProps {
  mode: StudioMode;
  onModeChange: (mode: StudioMode) => void;
  runsActive: boolean;
  storeActive: boolean;
  synthesisActive: boolean;
  onOpenHome: () => void;
  onOpenRuns: () => void;
  onOpenPersonaStore: () => void;
  onOpenSynthesis: () => void;
}
```

2. Update the two mode-based nav entries so they aren't active while the synthesis view is open, and add the new entry after "Persona World":

```ts
  const nav: Array<{ key: string; label: string; active: boolean; onClick: () => void }> = [
    {
      key: "home",
      label: "Home",
      active: mode === "home" && !runsActive && !storeActive && !synthesisActive,
      onClick: onOpenHome,
    },
    {
      key: "playground",
      label: "Playground",
      active: mode === "playground" && !runsActive && !storeActive && !synthesisActive,
      onClick: () => onModeChange("playground"),
    },
    { key: "runs", label: "Runs", active: runsActive, onClick: onOpenRuns },
    { key: "store", label: "Persona World", active: storeActive, onClick: onOpenPersonaStore },
    { key: "synthesis", label: "Synthesis", active: synthesisActive, onClick: onOpenSynthesis },
  ];
```

Also update the file's doc comment nav list to `Home · Playground · Runs · Persona World · Synthesis`.

- [ ] **Step 3: Route the view in App.tsx**

In `application/playground/frontend/src/App.tsx`:

1. Import the view:

```ts
import { SynthesisStudioView } from "@/components/synthesis/SynthesisStudioView";
```

2. Add the active flag next to `storeViewActive`:

```ts
  const synthesisViewActive = urlState.view === "synthesis";
```

3. Add the open callback next to `openPersonaStore`:

```ts
  const openSynthesis = useCallback(() => {
    setUrlState({ view: "synthesis", harborJob: null, harborTrial: null });
  }, [setUrlState]);
```

4. Extend the footer context chain:

```ts
  const shellFooterContext = storeViewActive
    ? "persona world"
    : synthesisViewActive
      ? "synthesis"
      : runsViewActive
        ? "runs"
        : mode === "playground"
          ? playgroundFooter
          : "home";
```

5. Pass the new TopBar props:

```tsx
  const topBar = (
    <TopBar
      mode={mode}
      onModeChange={setMode}
      runsActive={runsViewActive}
      storeActive={storeViewActive}
      synthesisActive={synthesisViewActive}
      onOpenHome={openHome}
      onOpenRuns={openRunsList}
      onOpenPersonaStore={openPersonaStore}
      onOpenSynthesis={openSynthesis}
    />
  );
```

6. Add the view branch immediately before the `if (storeViewActive)` branch:

```tsx
  if (synthesisViewActive) {
    return (
      <div className="flex h-screen flex-col">
        {topBar}
        <SynthesisStudioView />
        <AppFooter context={shellFooterContext} />
      </div>
    );
  }
```

Also update App.tsx's doc comment route list to include Synthesis.

- [ ] **Step 4: Typecheck and smoke-run**

```bash
cd application/playground/frontend && npm run typecheck
```
Expected: PASS.

Smoke-run (two terminals from repo root):
```bash
bash application/playground/backend/run_dev.sh
cd application/playground/frontend && npm run dev
```
Open `http://localhost:5173/?view=synthesis` — expect the header with real node/edge counts (proves the overview endpoint round-trips) and three placeholder panes. The first overview request takes ~1–2 s (lazy 23 MB graph load), then is instant.

- [ ] **Step 5: Commit**

```bash
git add application/playground/frontend/src/components/synthesis/SynthesisStudioView.tsx \
        application/playground/frontend/src/components/TopBar.tsx \
        application/playground/frontend/src/App.tsx
git commit -m "Add Synthesis Studio view shell and navigation

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Category overview graph (SVG) + category attribute rail

**Files:**
- Create: `application/playground/frontend/src/components/synthesis/CategoryOverviewGraph.tsx`
- Create: `application/playground/frontend/src/components/synthesis/CategoryAttributeList.tsx`
- Modify: `application/playground/frontend/src/components/synthesis/SynthesisStudioView.tsx` (mount both)

**Interfaces:**
- Consumes: `SynthesisOverviewResponse` / `SynthesisCategorySummary` types (Task 3); view state from Task 4.
- Produces:
  - `CategoryOverviewGraph({ overview, selectedCategory, onSelectCategory }: { overview: SynthesisOverviewResponse; selectedCategory: string | null; onSelectCategory: (name: string | null) => void })`
  - `CategoryAttributeList({ category, onSelectAttribute }: { category: SynthesisCategorySummary; onSelectAttribute: (id: string) => void })`

Design (per spec + dataviz): circular layout of the 44 categories sorted by average topological order (so dependency flow reads clockwise from the top); node radius encodes attribute count; aggregated cross-category edges are quadratic curves pulled toward the center, width/opacity by edge count; neutral fills, `primary` for hover/selection; labels always visible (identity is never color-alone).

- [ ] **Step 1: Create CategoryOverviewGraph**

Create `application/playground/frontend/src/components/synthesis/CategoryOverviewGraph.tsx`:

```tsx
/**
 * Circular category-level overview of the Persona Full DAG.
 *
 * Categories are placed clockwise from the top by average topological order,
 * so proposal flow reads roughly clockwise. Node size encodes attribute
 * count; aggregated cross-category edges curve through the middle with
 * width/opacity by edge count. Identity is carried by the always-on labels;
 * color is reserved for hover/selection (design-token primary).
 */
import { useMemo, useState } from "react";

import type { SynthesisCategoryEdge, SynthesisOverviewResponse } from "@/lib/types";

const SIZE = 720;
const CENTER = SIZE / 2;
const RING_RADIUS = SIZE / 2 - 120;
const MIN_NODE_R = 7;
const MAX_NODE_R = 22;
const LABEL_GAP = 10;
const LABEL_MAX_CHARS = 20;

interface PlacedCategory {
  name: string;
  x: number;
  y: number;
  r: number;
  angle: number;
  attributeCount: number;
  nodeCount: number;
}

function truncate(text: string): string {
  return text.length > LABEL_MAX_CHARS ? `${text.slice(0, LABEL_MAX_CHARS - 1)}…` : text;
}

export function CategoryOverviewGraph({
  overview,
  selectedCategory,
  onSelectCategory,
}: {
  overview: SynthesisOverviewResponse;
  selectedCategory: string | null;
  onSelectCategory: (name: string | null) => void;
}) {
  const [hovered, setHovered] = useState<string | null>(null);

  const placed = useMemo(() => {
    const categories = overview.categories;
    const maxAttr = Math.max(1, ...categories.map((c) => c.attributeCount));
    const byName = new Map<string, PlacedCategory>();
    categories.forEach((cat, i) => {
      const angle = -Math.PI / 2 + (i / categories.length) * Math.PI * 2;
      byName.set(cat.name, {
        name: cat.name,
        x: CENTER + RING_RADIUS * Math.cos(angle),
        y: CENTER + RING_RADIUS * Math.sin(angle),
        r: MIN_NODE_R + (MAX_NODE_R - MIN_NODE_R) * Math.sqrt(cat.attributeCount / maxAttr),
        angle,
        attributeCount: cat.attributeCount,
        nodeCount: cat.nodeCount,
      });
    });
    return byName;
  }, [overview]);

  const maxEdgeCount = useMemo(
    () => Math.max(1, ...overview.edges.map((e) => e.count)),
    [overview],
  );

  const focus = hovered ?? selectedCategory;

  function edgePath(edge: SynthesisCategoryEdge): string {
    const s = placed.get(edge.source);
    const t = placed.get(edge.target);
    if (!s || !t) return "";
    const midX = (s.x + t.x) / 2;
    const midY = (s.y + t.y) / 2;
    // Pull the control point 45% of the way toward the ring center so
    // long-range edges arc through the middle instead of hugging the rim.
    const cx = midX + (CENTER - midX) * 0.45;
    const cy = midY + (CENTER - midY) * 0.45;
    return `M ${s.x} ${s.y} Q ${cx} ${cy} ${t.x} ${t.y}`;
  }

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      className="h-full w-full"
      role="img"
      aria-label="Persona DAG category overview"
      onClick={() => onSelectCategory(null)}
    >
      {/* Edges under nodes. Non-focused edges are recessive. */}
      <g fill="none">
        {overview.edges.map((edge) => {
          const active =
            focus !== null && (edge.source === focus || edge.target === focus);
          const width = 0.8 + 2.4 * Math.sqrt(edge.count / maxEdgeCount);
          return (
            <path
              key={`${edge.source}->${edge.target}`}
              d={edgePath(edge)}
              style={{
                stroke: active ? "rgb(var(--primary))" : "rgb(var(--outline))",
                strokeOpacity: focus === null ? 0.28 : active ? 0.85 : 0.08,
                strokeWidth: active ? width + 0.6 : width,
                transition: "stroke-opacity 150ms ease-out",
              }}
            />
          );
        })}
      </g>
      {/* Category nodes + labels. */}
      {[...placed.values()].map((cat) => {
        const isFocus = focus === cat.name;
        const isSelected = selectedCategory === cat.name;
        const rightSide = Math.cos(cat.angle) >= 0;
        const labelX = cat.x + (cat.r + LABEL_GAP) * Math.cos(cat.angle);
        const labelY = cat.y + (cat.r + LABEL_GAP) * Math.sin(cat.angle);
        return (
          <g
            key={cat.name}
            className="cursor-pointer"
            onMouseEnter={() => setHovered(cat.name)}
            onMouseLeave={() => setHovered(null)}
            onClick={(event) => {
              event.stopPropagation();
              onSelectCategory(isSelected ? null : cat.name);
            }}
          >
            <title>{`${cat.name} — ${cat.attributeCount} attributes / ${cat.nodeCount} nodes`}</title>
            <circle
              cx={cat.x}
              cy={cat.y}
              r={cat.r}
              style={{
                fill: isFocus ? "rgb(var(--primary) / 0.18)" : "rgb(var(--surface-high))",
                stroke: isFocus || isSelected ? "rgb(var(--primary))" : "rgb(var(--outline))",
                strokeWidth: isSelected ? 2 : 1.2,
                transition: "fill 150ms ease-out, stroke 150ms ease-out",
              }}
            />
            <text
              x={labelX}
              y={labelY}
              textAnchor={rightSide ? "start" : "end"}
              dominantBaseline="middle"
              className="font-mono"
              style={{
                fontSize: 10.5,
                fill: isFocus || isSelected ? "rgb(var(--text-main))" : "rgb(var(--text-dim))",
              }}
            >
              {truncate(cat.name)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
```

Token note: the CSS custom properties (`--primary`, `--outline`, `--surface-high`, `--text-main`, `--text-dim`) are defined in `src/index.css` as RGB triples (that's how `tailwind.config.ts` maps them). Verify the exact variable names in `index.css` before writing — if a name differs (e.g. `--color-primary`), use the actual name consistently in Tasks 5 and 6.

- [ ] **Step 2: Create CategoryAttributeList**

Create `application/playground/frontend/src/components/synthesis/CategoryAttributeList.tsx`:

```tsx
/**
 * Attribute list for one selected category, with client-side search.
 * Clicking an attribute drives the drill-down pane.
 */
import { useMemo, useState } from "react";

import { FOCUS_RING } from "../cockpit/cockpitShared";
import type { SynthesisCategorySummary } from "@/lib/types";

export function CategoryAttributeList({
  category,
  onSelectAttribute,
}: {
  category: SynthesisCategorySummary;
  onSelectAttribute: (id: string) => void;
}) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return category.attributes;
    return category.attributes.filter(
      (a) => a.id.toLowerCase().includes(q) || a.label.toLowerCase().includes(q),
    );
  }, [category, query]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4">
      <div>
        <div className="hud text-text-dim">Category</div>
        <h3 className="font-display text-base text-text-main">{category.name}</h3>
        <p className="text-xs text-text-dim">
          {category.attributeCount} attributes · {category.helperCount} helper nodes ·{" "}
          {category.internalEdgeCount} internal edges
        </p>
      </div>
      <input
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Filter attributes…"
        className={`h-9 rounded-md border border-outline bg-field px-3 text-sm text-text-main placeholder:text-text-dim ${FOCUS_RING}`}
      />
      <ul className="custom-scrollbar min-h-0 flex-1 space-y-1 overflow-y-auto">
        {filtered.map((attr) => (
          <li key={attr.id}>
            <button
              type="button"
              onClick={() => onSelectAttribute(attr.id)}
              className={`flex w-full items-baseline justify-between gap-2 rounded-md px-2.5 py-1.5 text-left transition-colors hover:bg-surface-low ${FOCUS_RING}`}
            >
              <span className="min-w-0 truncate text-sm text-text-variant">{attr.label}</span>
              <span className="flex-none font-mono text-[11px] text-text-dim">
                deg {attr.degree}
              </span>
            </button>
          </li>
        ))}
        {filtered.length === 0 ? (
          <li className="px-2.5 py-2 text-sm text-text-dim">No attributes match.</li>
        ) : null}
      </ul>
    </div>
  );
}
```

(`.hud` and `.custom-scrollbar` are existing utilities from `index.css`; `FOCUS_RING` is the shared focus-ring class from `cockpit/cockpitShared.tsx`.)

- [ ] **Step 3: Mount both in SynthesisStudioView**

First add the selection state to `SynthesisStudioView` (top of the component, with `useState` added to the react import). `selectedNode` comes in Task 6 — adding it now would trip noUnusedLocals:

```tsx
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [centerNode, setCenterNode] = useState<string | null>(null);
```

`centerNode` drives the Task 6 drill-down; until Task 6 lands, show it in the middle placeholder so the value is used and typecheck stays green:

```tsx
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            <div className="grid h-full place-items-center text-sm text-text-dim">
              {centerNode ? `Drill-down: ${centerNode} (Task 6)` : "Drill-down subgraph (Task 6)"}
            </div>
          </StudioGlassPanel>
```

Then replace the first placeholder pane with the overview graph and make the third pane show `CategoryAttributeList` when a category is selected (node detail arrives in Task 6):

```tsx
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            {overview ? (
              <CategoryOverviewGraph
                overview={overview}
                selectedCategory={selectedCategory}
                onSelectCategory={setSelectedCategory}
              />
            ) : (
              <div className="grid h-full place-items-center text-sm text-text-dim">
                {overviewQuery.isError ? "Failed to load the graph overview." : "Loading…"}
              </div>
            )}
          </StudioGlassPanel>
```

Third pane:

```tsx
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            {selectedCategoryData ? (
              <CategoryAttributeList
                category={selectedCategoryData}
                onSelectAttribute={setCenterNode}
              />
            ) : (
              <div className="grid h-full place-items-center px-6 text-center text-sm text-text-dim">
                Click a category to list its attributes.
              </div>
            )}
          </StudioGlassPanel>
```

with, above the return:

```tsx
  const selectedCategoryData =
    overview?.categories.find((cat) => cat.name === selectedCategory) ?? null;
```

and imports:

```tsx
import { CategoryOverviewGraph } from "./CategoryOverviewGraph";
import { CategoryAttributeList } from "./CategoryAttributeList";
```

- [ ] **Step 4: Typecheck + visual check**

```bash
cd application/playground/frontend && npm run typecheck
```
Expected: PASS.

With both dev servers running, open `http://localhost:5173/?view=synthesis` and verify: the ring of 44 labeled categories renders without label collisions; hover highlights a category's edges; click selects and the attribute list fills the right pane; click empty space deselects; both themes look right (toggle in TopBar). Fix any label overlap by increasing `SIZE`/`RING_RADIUS` or shrinking the font before committing.

- [ ] **Step 5: Commit**

```bash
git add application/playground/frontend/src/components/synthesis/
git commit -m "Add category overview graph and attribute list

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Drill-down subgraph (layered SVG) + node detail rail

**Files:**
- Create: `application/playground/frontend/src/components/synthesis/DrilldownGraph.tsx`
- Create: `application/playground/frontend/src/components/synthesis/NodeDetailRail.tsx`
- Modify: `application/playground/frontend/src/components/synthesis/SynthesisStudioView.tsx` (mount both; hop controls)

**Interfaces:**
- Consumes: `api.getSynthesisSubgraph`, `api.getSynthesisNode` (Task 3); state from Task 4.
- Produces:
  - `DrilldownGraph({ subgraph, selectedNode, onSelectNode, onRecenter }: { subgraph: SynthesisSubgraphResponse; selectedNode: string | null; onSelectNode: (id: string) => void; onRecenter: (id: string) => void })` — single click selects (drives detail rail), double click re-centers.
  - `NodeDetailRail({ nodeId, onJumpToNode }: { nodeId: string; onJumpToNode: (id: string) => void })` — fetches its own detail via react-query.

- [ ] **Step 1: Create DrilldownGraph**

Create `application/playground/frontend/src/components/synthesis/DrilldownGraph.tsx`:

```tsx
/**
 * Layered drill-down subgraph: columns are hop layers (upstream left of the
 * center node, downstream right), so proposal direction always reads
 * left-to-right. Nodes are labeled boxes; edges are cubic curves with
 * arrowheads. Click selects, double-click re-centers.
 */
import { useMemo, useState } from "react";

import type { SynthesisSubgraphResponse } from "@/lib/types";

const COL_WIDTH = 230;
const NODE_W = 176;
const NODE_H = 40;
const ROW_GAP = 14;
const PADDING = 24;
const LABEL_MAX_CHARS = 24;

function truncate(text: string): string {
  return text.length > LABEL_MAX_CHARS ? `${text.slice(0, LABEL_MAX_CHARS - 1)}…` : text;
}

export function DrilldownGraph({
  subgraph,
  selectedNode,
  onSelectNode,
  onRecenter,
}: {
  subgraph: SynthesisSubgraphResponse;
  selectedNode: string | null;
  onSelectNode: (id: string) => void;
  onRecenter: (id: string) => void;
}) {
  const [hovered, setHovered] = useState<string | null>(null);

  const layout = useMemo(() => {
    const layers = new Map<number, string[]>();
    for (const node of subgraph.nodes) {
      const bucket = layers.get(node.layer) ?? [];
      bucket.push(node.id);
      layers.set(node.layer, bucket);
    }
    const layerKeys = [...layers.keys()].sort((a, b) => a - b);
    const minLayer = layerKeys[0] ?? 0;
    const positions = new Map<string, { x: number; y: number }>();
    let maxRows = 1;
    for (const layer of layerKeys) {
      const ids = layers.get(layer) ?? [];
      maxRows = Math.max(maxRows, ids.length);
      ids.forEach((id, row) => {
        positions.set(id, {
          x: PADDING + (layer - minLayer) * COL_WIDTH,
          y: PADDING + row * (NODE_H + ROW_GAP),
        });
      });
    }
    return {
      positions,
      width: PADDING * 2 + (layerKeys.length - 1) * COL_WIDTH + NODE_W,
      height: PADDING * 2 + maxRows * (NODE_H + ROW_GAP) - ROW_GAP,
    };
  }, [subgraph]);

  const nodesById = useMemo(
    () => new Map(subgraph.nodes.map((n) => [n.id, n])),
    [subgraph],
  );
  const focus = hovered ?? selectedNode;
  const neighborIds = useMemo(() => {
    if (!focus) return new Set<string>();
    const ids = new Set<string>([focus]);
    for (const edge of subgraph.edges) {
      if (edge.source === focus) ids.add(edge.target);
      if (edge.target === focus) ids.add(edge.source);
    }
    return ids;
  }, [focus, subgraph]);

  return (
    <div className="custom-scrollbar h-full w-full overflow-auto">
      <svg
        width={layout.width}
        height={layout.height}
        role="img"
        aria-label={`Dependency subgraph around ${subgraph.center}`}
      >
        <defs>
          <marker
            id="synthesis-arrow"
            viewBox="0 0 8 8"
            refX="7"
            refY="4"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 8 4 L 0 8 z" style={{ fill: "rgb(var(--text-dim))" }} />
          </marker>
        </defs>
        <g fill="none">
          {subgraph.edges.map((edge) => {
            const s = layout.positions.get(edge.source);
            const t = layout.positions.get(edge.target);
            if (!s || !t) return null;
            const x1 = s.x + NODE_W;
            const y1 = s.y + NODE_H / 2;
            const x2 = t.x;
            const y2 = t.y + NODE_H / 2;
            const midX = (x1 + x2) / 2;
            const active =
              focus !== null && (edge.source === focus || edge.target === focus);
            return (
              <path
                key={`${edge.source}->${edge.target}`}
                d={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
                markerEnd="url(#synthesis-arrow)"
                style={{
                  stroke: active ? "rgb(var(--primary))" : "rgb(var(--outline))",
                  strokeOpacity: focus === null ? 0.55 : active ? 0.95 : 0.18,
                  strokeWidth: active ? 1.8 : 1.1,
                  transition: "stroke-opacity 150ms ease-out",
                }}
              >
                <title>{`${edge.source} → ${edge.target} (${edge.relation}, w=${edge.weight})`}</title>
              </path>
            );
          })}
        </g>
        {subgraph.nodes.map((node) => {
          const pos = layout.positions.get(node.id);
          if (!pos) return null;
          const isCenter = node.id === subgraph.center;
          const isSelected = node.id === selectedNode;
          const dimmed = focus !== null && !neighborIds.has(node.id);
          return (
            <g
              key={node.id}
              className="cursor-pointer"
              opacity={dimmed ? 0.35 : 1}
              onMouseEnter={() => setHovered(node.id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => onSelectNode(node.id)}
              onDoubleClick={() => onRecenter(node.id)}
              style={{ transition: "opacity 150ms ease-out" }}
            >
              <title>{`${node.label} (${node.category}) — in ${node.inDegree} / out ${node.outDegree}${node.emit ? "" : " · latent/helper"}`}</title>
              <rect
                x={pos.x}
                y={pos.y}
                width={NODE_W}
                height={NODE_H}
                rx={8}
                style={{
                  fill: isCenter ? "rgb(var(--primary) / 0.14)" : "rgb(var(--surface-high))",
                  stroke:
                    isSelected || isCenter ? "rgb(var(--primary))" : "rgb(var(--outline))",
                  strokeWidth: isSelected ? 2 : 1.2,
                  strokeDasharray: node.emit ? undefined : "4 3",
                }}
              />
              <text
                x={pos.x + 10}
                y={pos.y + 17}
                style={{ fontSize: 11.5, fill: "rgb(var(--text-main))" }}
              >
                {truncate(node.label)}
              </text>
              <text
                x={pos.x + 10}
                y={pos.y + 31}
                className="font-mono"
                style={{ fontSize: 9.5, fill: "rgb(var(--text-dim))" }}
              >
                {truncate(node.id)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
```

(Latent/helper nodes get a dashed border — a non-color encoding, per the dataviz rules. Same CSS-variable naming caveat as Task 5.)

- [ ] **Step 2: Create NodeDetailRail**

Create `application/playground/frontend/src/components/synthesis/NodeDetailRail.tsx`:

```tsx
/**
 * Detail rail for one graph node: values with prior bars, and the
 * strongest incoming/outgoing edges (click to jump).
 */
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { FOCUS_RING } from "../cockpit/cockpitShared";
import type { SynthesisNodeDetail, SynthesisNodeEdgeView } from "@/lib/types";

function EdgeList({
  title,
  edges,
  onJumpToNode,
}: {
  title: string;
  edges: SynthesisNodeEdgeView[];
  onJumpToNode: (id: string) => void;
}) {
  if (edges.length === 0) return null;
  return (
    <div>
      <div className="hud mb-1 text-text-dim">{title}</div>
      <ul className="space-y-0.5">
        {edges.map((edge) => (
          <li key={edge.id}>
            <button
              type="button"
              onClick={() => onJumpToNode(edge.id)}
              className={`flex w-full items-baseline justify-between gap-2 rounded px-2 py-1 text-left transition-colors hover:bg-surface-low ${FOCUS_RING}`}
            >
              <span className="min-w-0 truncate text-xs text-text-variant">{edge.label}</span>
              <span className="flex-none font-mono text-[10px] text-text-dim">
                w {edge.weight}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function NodeDetailRail({
  nodeId,
  onJumpToNode,
}: {
  nodeId: string;
  onJumpToNode: (id: string) => void;
}) {
  const detailQuery = useQuery<SynthesisNodeDetail>({
    queryKey: ["synthesis", "node", nodeId],
    queryFn: () => api.getSynthesisNode(nodeId),
    staleTime: Infinity,
  });
  const detail = detailQuery.data ?? null;

  if (detailQuery.isError) {
    return (
      <div className="grid h-full place-items-center text-sm text-danger">
        Failed to load node detail.
      </div>
    );
  }
  if (!detail) {
    return <div className="grid h-full place-items-center text-sm text-text-dim">Loading…</div>;
  }

  const maxPrior = Math.max(0.0001, ...detail.prior);
  return (
    <div className="custom-scrollbar flex h-full min-h-0 flex-col gap-4 overflow-y-auto p-4">
      <div>
        <div className="hud text-text-dim">{detail.type}</div>
        <h3 className="font-display text-base text-text-main">{detail.label}</h3>
        <p className="font-mono text-[11px] text-text-dim">{detail.id}</p>
        <p className="mt-1 text-xs text-text-dim">
          {detail.category} · in {detail.inDegree} / out {detail.outDegree}
        </p>
        {detail.description ? (
          <p className="mt-2 text-xs leading-relaxed text-text-variant">{detail.description}</p>
        ) : null}
      </div>
      {detail.values.length > 0 ? (
        <div>
          <div className="hud mb-1 text-text-dim">Base prior</div>
          <ul className="space-y-1">
            {detail.values.map((value, i) => {
              const p = detail.prior[i] ?? 0;
              return (
                <li key={value} className="flex items-center gap-2">
                  <span className="w-28 flex-none truncate text-xs text-text-variant" title={value}>
                    {value}
                  </span>
                  <span className="h-2 min-w-0 flex-1 rounded-sm bg-surface-high">
                    <span
                      className="block h-full rounded-sm"
                      style={{
                        width: `${Math.round((p / maxPrior) * 100)}%`,
                        background: "rgb(var(--primary) / 0.55)",
                      }}
                    />
                  </span>
                  <span className="w-12 flex-none text-right font-mono text-[10px] text-text-dim">
                    {(p * 100).toFixed(1)}%
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
      <EdgeList title="Strongest incoming" edges={detail.inEdges} onJumpToNode={onJumpToNode} />
      <EdgeList title="Strongest outgoing" edges={detail.outEdges} onJumpToNode={onJumpToNode} />
    </div>
  );
}
```

(The prior bars encode one magnitude in one hue — sequential use of the primary token at fixed alpha, values labeled in mono text tokens.)

- [ ] **Step 3: Mount in SynthesisStudioView with hop controls**

In `SynthesisStudioView.tsx`:

1. Add state + query below the existing state (`selectedNode` first appears here):

```tsx
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hops, setHops] = useState<{ up: number; down: number }>({ up: 1, down: 1 });

  const subgraphQuery = useQuery<SynthesisSubgraphResponse>({
    queryKey: ["synthesis", "subgraph", centerNode, hops.up, hops.down],
    queryFn: () => api.getSynthesisSubgraph(centerNode as string, hops.up, hops.down),
    enabled: centerNode !== null,
    staleTime: Infinity,
  });
```

with `SynthesisSubgraphResponse` added to the type import and `DrilldownGraph` / `NodeDetailRail` imported.

2. Replace the middle placeholder pane:

```tsx
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            {centerNode === null ? (
              <div className="grid h-full place-items-center px-6 text-center text-sm text-text-dim">
                Pick a category, then an attribute, to see its dependency neighborhood.
              </div>
            ) : (
              <div className="flex h-full min-h-0 flex-col">
                <div className="flex flex-none items-center gap-3 border-b border-outline-dim px-3 py-2">
                  <span className="hud text-text-dim">Hops</span>
                  {(["up", "down"] as const).map((dir) => (
                    <label key={dir} className="flex items-center gap-1.5 text-xs text-text-variant">
                      {dir}
                      <select
                        value={hops[dir]}
                        onChange={(event) =>
                          setHops((prev) => ({ ...prev, [dir]: Number(event.target.value) }))
                        }
                        className="h-7 rounded border border-outline bg-field px-1.5 text-xs text-text-main"
                      >
                        {[0, 1, 2, 3, 4].map((n) => (
                          <option key={n} value={n}>{n}</option>
                        ))}
                      </select>
                    </label>
                  ))}
                  {subgraphQuery.data?.truncated ? (
                    <span className="text-[11px] text-warn">truncated to nearest 60/direction</span>
                  ) : null}
                </div>
                <div className="min-h-0 flex-1">
                  {subgraphQuery.data ? (
                    <DrilldownGraph
                      subgraph={subgraphQuery.data}
                      selectedNode={selectedNode}
                      onSelectNode={setSelectedNode}
                      onRecenter={(id) => {
                        setCenterNode(id);
                        setSelectedNode(id);
                      }}
                    />
                  ) : (
                    <div className="grid h-full place-items-center text-sm text-text-dim">
                      {subgraphQuery.isError ? "Failed to load subgraph." : "Loading…"}
                    </div>
                  )}
                </div>
              </div>
            )}
          </StudioGlassPanel>
```

3. Make the third pane prefer node detail over the category list:

```tsx
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            {selectedNode ? (
              <NodeDetailRail
                nodeId={selectedNode}
                onJumpToNode={(id) => {
                  setCenterNode(id);
                  setSelectedNode(id);
                }}
              />
            ) : selectedCategoryData ? (
              <CategoryAttributeList
                category={selectedCategoryData}
                onSelectAttribute={(id) => {
                  setCenterNode(id);
                  setSelectedNode(id);
                }}
              />
            ) : (
              <div className="grid h-full place-items-center px-6 text-center text-sm text-text-dim">
                Click a category to list its attributes.
              </div>
            )}
          </StudioGlassPanel>
```

Wrap `NodeDetailRail` with a "back to category" affordance (import `FOCUS_RING` from `../cockpit/cockpitShared`):

```tsx
              <div className="flex h-full min-h-0 flex-col">
                <button
                  type="button"
                  onClick={() => setSelectedNode(null)}
                  className={`flex-none px-4 pt-3 text-left text-[11px] text-text-dim transition-colors hover:text-text-main ${FOCUS_RING}`}
                >
                  ← back to category list
                </button>
                <div className="min-h-0 flex-1">
                  <NodeDetailRail
                    nodeId={selectedNode}
                    onJumpToNode={(id) => {
                      setCenterNode(id);
                      setSelectedNode(id);
                    }}
                  />
                </div>
              </div>
```

4. Update the overview pane's callback so picking a different category clears any stale node selection (otherwise the third pane keeps showing the old node's detail):

```tsx
                onSelectCategory={(name) => {
                  setSelectedCategory(name);
                  setSelectedNode(null);
                }}
```

- [ ] **Step 4: Typecheck + visual check**

```bash
cd application/playground/frontend && npm run typecheck
```
Expected: PASS.

In the browser: category → attribute → drill-down renders layered left-to-right with arrowheads; hover dims non-neighbors; single click fills the detail rail (values + prior bars + edge lists); double-click re-centers; hop selectors refetch; a high-degree node (e.g. `region` if present) shows the truncation notice at hops 2+. Check both themes.

- [ ] **Step 5: Commit**

```bash
git add application/playground/frontend/src/components/synthesis/
git commit -m "Add drill-down subgraph and node detail rail

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Full verification pass

**Files:** none new — verification only.

- [ ] **Step 1: Backend suite**

```bash
uv run python -m pytest application/playground/backend/tests -q
```
Expected: PASS, no regressions.

- [ ] **Step 2: Frontend build-level check**

```bash
cd application/playground/frontend && npm run typecheck && npm run build
```
Expected: both PASS (build catches issues typecheck misses, e.g. bad imports in vite config paths).

- [ ] **Step 3: End-to-end walkthrough against the real graph**

With `bash application/playground/backend/run_dev.sh` and `npm run dev` running, walk the acceptance path on `http://localhost:5173/?view=synthesis`:

1. Header shows 1,308 nodes / 6,999 edges / 44 categories.
2. Ring overview renders all 44 categories, labels legible, hover highlights.
3. Select a category → attribute list; filter box narrows it.
4. Click an attribute → drill-down subgraph at 1/1 hops; raise to 2/2 and confirm layout stays readable (or truncation notice appears).
5. Node detail: values, prior bars, incoming/outgoing lists; jump via an edge entry re-centers.
6. Toggle light theme — both graphs and rails stay legible.
7. `curl -s localhost:8765/api/synthesis/graph/overview | head -c 300` returns camelCase JSON.

- [ ] **Step 4: Update the module README pointer**

Append a short section to `persona/synthesis/visualization/README.md` noting the interactive successor (do not modify the HTML):

```markdown
## Interactive Studio

An interactive browsing UI for this graph (category overview + per-node
drill-down) lives in the Playground app: open the "Synthesis" tab, or
`/?view=synthesis`, backed by `/api/synthesis/*`. This static HTML remains
the offline, dependency-free snapshot.
```

- [ ] **Step 5: Commit**

```bash
git add persona/synthesis/visualization/README.md
git commit -m "Point visualization README at the Synthesis Studio

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
