from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, Iterable, List

import numpy as np


def _is_normalized(dist: Iterable[float], tol: float = 1e-6) -> bool:
    arr = np.asarray(list(dist), dtype=float)
    return np.isfinite(arr).all() and (arr >= -tol).all() and abs(float(arr.sum()) - 1.0) <= tol


def _node_values(graph: Dict[str, Any]) -> Dict[str, List[str]]:
    return {n["id"]: list(n.get("values", [])) for n in graph.get("nodes", [])}


def validate_graph(graph: Dict[str, Any], *, tol: float = 1e-6) -> Dict[str, Any]:
    """Static graph validator for Persona Full DAG releases.

    It intentionally computes counts from actual arrays rather than trusting metadata.
    """
    nodes = graph.get("nodes", [])
    edges = graph.get("directed_proposal_edges", [])
    cpts = graph.get("full_cpts", [])
    masks = graph.get("conditional_masks", [])
    node_ids = [n.get("id") for n in nodes]
    node_set = set(node_ids)
    values = _node_values(graph)

    duplicate_node_ids = len(node_ids) - len(node_set)
    duplicate_pairs = len(edges) - len({(e.get("source"), e.get("target")) for e in edges})

    missing_refs = []
    for e in edges:
        if e.get("source") not in node_set or e.get("target") not in node_set:
            missing_refs.append({"type": "edge", "id": e.get("edge_id"), "source": e.get("source"), "target": e.get("target")})
    for c in cpts:
        if c.get("target") not in node_set:
            missing_refs.append({"type": "full_cpt", "id": c.get("cpt_id"), "target": c.get("target")})
        for p in c.get("parents", []):
            if p not in node_set:
                missing_refs.append({"type": "full_cpt_parent", "id": c.get("cpt_id"), "parent": p})
    for m in masks:
        if m.get("target") not in node_set:
            missing_refs.append({"type": "mask", "id": m.get("mask_id"), "target": m.get("target")})
        for p in m.get("condition", {}):
            if p not in node_set:
                missing_refs.append({"type": "mask_parent", "id": m.get("mask_id"), "parent": p})

    prior_bad = []
    for n in nodes:
        vals = values[n["id"]]
        prior = n.get("prior", {})
        if isinstance(prior, dict):
            dist = [prior.get(v, 0.0) for v in vals]
        else:
            dist = prior
        if not _is_normalized(dist, tol=tol):
            prior_bad.append(n["id"])

    edge_bad_rows = 0
    edge_exact_zero_cells = 0
    edge_exact_one_cells = 0
    raw_backed_edges = 0
    raw_backed_affected = 0
    raw_backed_low_entropy_rows_gt_0_98 = 0
    for e in edges:
        cpd = e.get("cpd", {})
        if cpd.get("type") != "pairwise_conditional_matrix":
            continue
        is_raw = e.get("evidence_level") == "raw_direct" or "raw_backed" in str(cpd.get("model", ""))
        if is_raw:
            raw_backed_edges += 1
        affected = False
        for row in cpd.get("P_target_given_source", []):
            arr = np.asarray(row, dtype=float)
            if not _is_normalized(arr, tol=tol):
                edge_bad_rows += 1
            z = int((arr == 0).sum())
            o = int((arr == 1).sum())
            edge_exact_zero_cells += z
            edge_exact_one_cells += o
            if is_raw and (z or o):
                affected = True
            if is_raw and len(arr) and float(arr.max()) > 0.98:
                raw_backed_low_entropy_rows_gt_0_98 += 1
        if affected:
            raw_backed_affected += 1

    full_cpt_bad_rows = 0
    full_cpt_exact_zero_cells = 0
    full_cpt_deterministic_rows = 0
    for c in cpts:
        target = c.get("target")
        vals = values.get(target, [])
        for row in c.get("rows", []):
            dist_obj = row.get("distribution", {})
            if isinstance(dist_obj, dict):
                dist = [dist_obj.get(v, 0.0) for v in vals]
            else:
                dist = dist_obj
            arr = np.asarray(dist, dtype=float)
            if not _is_normalized(arr, tol=tol):
                full_cpt_bad_rows += 1
            full_cpt_exact_zero_cells += int((arr == 0).sum())
            if len(arr) and float(arr.max()) == 1.0:
                full_cpt_deterministic_rows += 1

    # DAG check on directed edges + full-CPT dependencies + mask dependencies.
    graph_adj = defaultdict(list)
    indeg = defaultdict(int)
    for nid in node_set:
        indeg[nid] = 0
    def add_dep(s: str, t: str) -> None:
        if s in node_set and t in node_set:
            graph_adj[s].append(t)
            indeg[t] += 1
    for e in edges:
        add_dep(e.get("source"), e.get("target"))
    for c in cpts:
        for p in c.get("parents", []):
            add_dep(p, c.get("target"))
    for m in masks:
        for p in m.get("condition", {}):
            add_dep(p, m.get("target"))

    q = deque([nid for nid in node_set if indeg[nid] == 0])
    seen = 0
    while q:
        u = q.popleft()
        seen += 1
        for v in graph_adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    cycle_free = seen == len(node_set)

    topo = graph.get("proposal_view", {}).get("topological_order", [])
    pos = {nid: i for i, nid in enumerate(topo)}
    topo_violations = []
    for s, outs in graph_adj.items():
        for t in outs:
            if s in pos and t in pos and pos[s] >= pos[t]:
                topo_violations.append((s, t))

    external = [n for n in nodes if n.get("category") == "External: Datasets" or str(n.get("id", "")).startswith(("wiki_", "wildchat_", "nemotron_"))]
    hard_zero_mask_values = 0
    for m in masks:
        if float(m.get("bad_value_multiplier", 1.0)) == 0.0:
            hard_zero_mask_values += len(m.get("bad_values", []))

    validation_passed = (
        duplicate_node_ids == 0
        and duplicate_pairs == 0
        and len(missing_refs) == 0
        and len(prior_bad) == 0
        and edge_bad_rows == 0
        and full_cpt_bad_rows == 0
        and cycle_free
        and len(topo_violations) == 0
    )
    return {
        "node_count": len(nodes),
        "directed_edge_count": len(edges),
        "full_cpt_count": len(cpts),
        "full_cpt_row_count": sum(len(c.get("rows", [])) for c in cpts),
        "conditional_mask_count": len(masks),
        "duplicate_node_ids": duplicate_node_ids,
        "duplicate_directed_pairs": duplicate_pairs,
        "missing_refs": missing_refs,
        "bad_prior_nodes": prior_bad,
        "edge_bad_rows": edge_bad_rows,
        "edge_exact_zero_cells": edge_exact_zero_cells,
        "edge_exact_one_cells": edge_exact_one_cells,
        "raw_backed_edge_count": raw_backed_edges,
        "raw_backed_edges_affected_by_exact_zero_or_one": raw_backed_affected,
        "raw_backed_low_entropy_rows_gt_0_98": raw_backed_low_entropy_rows_gt_0_98,
        "full_cpt_bad_rows": full_cpt_bad_rows,
        "full_cpt_exact_zero_cells": full_cpt_exact_zero_cells,
        "full_cpt_deterministic_rows": full_cpt_deterministic_rows,
        "hard_zero_mask_values": hard_zero_mask_values,
        "cycle_free": cycle_free,
        "topological_dependency_violations": len(topo_violations),
        "topological_dependency_violation_examples": topo_violations[:20],
        "external_or_proxy_nodes": len(external),
        "external_or_proxy_emit_false": sum(1 for n in external if n.get("emit", True) is False),
        "validation_passed": validation_passed,
    }
