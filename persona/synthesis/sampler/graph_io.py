from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

Graph = Dict[str, Any]
DEFAULT_GRAPH_PATH = (
    Path(__file__).resolve().parents[1] / "graph" / "full_dag.json"
)


def load_graph(path: str | Path) -> Graph:
    """Load a persona graph JSON file."""
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj: Any, path: str | Path, *, indent: int = 2) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)


def emitted_node_ids(graph: Graph, include_hidden: bool = False) -> List[str]:
    """Return node ids emitted in default persona samples.

    The graph marks source-proxy and audit-only nodes with ``emit:false``.
    Default outputs omit those nodes. Pass ``include_hidden=True`` to return
    every graph node.
    """
    return [
        n["id"]
        for n in graph.get("nodes", [])
        if include_hidden or n.get("emit", True) is not False
    ]


def graph_summary(graph: Graph) -> Dict[str, Any]:
    """Compute a small summary directly from actual graph arrays."""
    nodes = graph.get("nodes", [])
    edges = graph.get("directed_proposal_edges", [])
    cpts = graph.get("full_cpts", [])
    masks = graph.get("conditional_masks", [])
    external = [
        n
        for n in nodes
        if n.get("category") == "External: Datasets"
        or str(n.get("id", "")).startswith(("wiki_", "wildchat_", "nemotron_"))
    ]
    return {
        "graph_version": graph.get("metadata", {}).get("graph_version")
        or graph.get("metadata", {}).get("version"),
        "target_population": graph.get("metadata", {}).get("target_population"),
        "nodes": len(nodes),
        "emitted_nodes": len(emitted_node_ids(graph)),
        "directed_edges": len(edges),
        "full_cpts": len(cpts),
        "full_cpt_rows": sum(len(c.get("rows", [])) for c in cpts),
        "conditional_masks": len(masks),
        "external_or_proxy_nodes": len(external),
        "external_or_proxy_emit_false": sum(1 for n in external if n.get("emit", True) is False),
    }
