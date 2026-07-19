from __future__ import annotations

import csv
import gzip
import json
import math
import multiprocessing as mp
import shutil
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

import numpy as np

EPS = 1e-12
_WORKER_SAMPLER: "PersonaForwardSampler | None" = None
COMPACT_CODES_FORMAT_VERSION = 2
_NIBBLE_MAX_VALUES = 16
# Fast deflate keeps per-worker compression far above disk throughput; each
# shard is an independent gzip member, so concatenation stays a valid stream.
_GZIP_LEVEL = 1
_CODES_COMPRESSIONS = {"none", "gzip"}


def _compress_payload(payload: np.ndarray, compression: str) -> bytes:
    if compression == "gzip":
        return gzip.compress(payload.reshape(-1).data, compresslevel=_GZIP_LEVEL, mtime=0)
    raise ValueError(f"Unsupported codes compression: {compression!r}")


def _normalize_compression(compress: str | None) -> str:
    compression = compress or "none"
    if compression not in _CODES_COMPRESSIONS:
        raise ValueError(f"Unsupported codes compression: {compress!r}")
    return compression


def codes_schema_path(codes_path: str | Path) -> Path:
    return Path(f"{codes_path}.schema.json")


def _normalize(x: Any) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    arr = np.where(np.isfinite(arr), arr, 0.0)
    arr = np.maximum(arr, 0.0)
    s = float(arr.sum())
    if s <= 0:
        return np.ones_like(arr, dtype=float) / len(arr)
    return arr / s


def _align_dist(dist: Any, values: List[str], source_values: Optional[List[str]] = None) -> np.ndarray:
    if isinstance(dist, Mapping):
        return _normalize([float(dist.get(v, 0.0)) for v in values])
    if source_values:
        m = {v: float(p) for v, p in zip(source_values, dist)}
        return _normalize([m.get(v, 0.0) for v in values])
    return _normalize(dist)


def _codes_dtype_for_value_counts(value_counts: List[int]) -> np.dtype:
    max_count = max(value_counts, default=0)
    if max_count <= np.iinfo(np.uint8).max + 1:
        return np.dtype("uint8")
    if max_count <= np.iinfo(np.uint16).max + 1:
        return np.dtype("uint16")
    return np.dtype("uint32")


def _pack_nibbles(matrix: np.ndarray) -> np.ndarray:
    """Pack a uint8 code matrix with values <= 15 into two codes per byte.

    Column 2i occupies the low nibble and column 2i+1 the high nibble of byte i,
    so each row stays a fixed-width block of ceil(cols / 2) bytes.
    """
    n, cols = matrix.shape
    packed = np.zeros((n, (cols + 1) // 2), dtype=np.uint8)
    even = matrix[:, 0::2]
    odd = matrix[:, 1::2]
    np.copyto(packed[:, : even.shape[1]], even)
    if odd.shape[1]:
        packed[:, : odd.shape[1]] |= odd << 4
    return packed


def _unpack_nibbles(packed: np.ndarray, cols: int) -> np.ndarray:
    n = packed.shape[0]
    out = np.empty((n, packed.shape[1] * 2), dtype=np.uint8)
    out[:, 0::2] = packed & 0x0F
    out[:, 1::2] = packed >> 4
    return out[:, :cols]


@dataclass(frozen=True)
class SamplingConfig:
    seed: int = 42
    emit_only: bool = True
    eps: float = EPS


@dataclass
class _NodePlan:
    """Precompiled per-node sampling step.

    All log-ratio tables are pre-scaled by ``gamma * weight`` and stored as
    float32 so the sampling loop only gathers and accumulates. Tables are laid
    out value-major, shape ``(k, ...)``, so per-row work in the sampling loop
    runs along the contiguous sample axis.
    """

    nid: str
    k: int
    logprior: np.ndarray  # (k, 1) float32
    cpts: List[tuple] = field(default_factory=list)  # (parents, multipliers, lut (k, code_space))
    edges: List[tuple] = field(default_factory=list)  # (source, scaled_logratio (k, k_source))
    masks: List[tuple] = field(default_factory=list)  # (conds | None, value_mult (k, 1))
    static_cdf: np.ndarray | None = None
    static_total: float = 0.0


class PersonaForwardSampler:
    """Vectorized forward sampler for the Persona Full DAG.

    The graph is interpreted as a DAG-style proposal distribution. For node i:

        q_i(v) ∝ P0_i(v) * exp(gamma_i * [pairwise log-ratio evidence + full-CPT log-ratio evidence])
                 * local mask multipliers.

    Pairwise and full-CPT contributions are represented as log-likelihood ratios against
    the target node prior. Conditional masks implement explicit local hard/soft guards.

    Compilation folds ``gamma_i`` and the per-edge/per-CPT weights into float32
    lookup tables. Sampling then draws each node with an unnormalized inverse-CDF,
    which selects values with exactly the normalized proposal probabilities while
    avoiding intermediate normalization passes.
    """

    def __init__(self, graph_path: str | Path, config: SamplingConfig | None = None):
        self.graph_path = Path(graph_path)
        self.config = config or SamplingConfig()
        with self.graph_path.open("r", encoding="utf-8") as f:
            self.graph: Dict[str, Any] = json.load(f)
        self.rng = np.random.default_rng(self.config.seed)
        self.nodes = {n["id"]: n for n in self.graph.get("nodes", [])}
        self.values = {nid: list(n.get("values", [])) for nid, n in self.nodes.items()}
        self.vtoi = {nid: {v: i for i, v in enumerate(vals)} for nid, vals in self.values.items()}
        self.prior = {nid: _align_dist(n.get("prior", {}), self.values[nid]) for nid, n in self.nodes.items()}
        self.logprior = {nid: np.log(np.maximum(self.prior[nid], self.config.eps)) for nid in self.nodes}
        self.topological_order = self.graph.get("proposal_view", {}).get("topological_order") or list(self.nodes)
        self.emit_nodes = [nid for nid, n in self.nodes.items() if (not self.config.emit_only or n.get("emit", True) is not False)]

        self.in_edges = self._compile_pairwise_edges()
        self.full_cpts = self._compile_full_cpts()
        self.masks = self._compile_masks()
        self.replaced_parents, self.gamma = self._compile_node_shrinkage()
        self.required_nodes = self._compile_required_nodes()
        self._compile_plan()

    def _compile_pairwise_edges(self) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for e in self.graph.get("directed_proposal_edges", []):
            s, t = e.get("source"), e.get("target")
            if s not in self.nodes or t not in self.nodes:
                continue
            cpd = e.get("cpd", {})
            if cpd.get("type") != "pairwise_conditional_matrix":
                continue
            svals = cpd.get("source_values", [])
            tvals = cpd.get("target_values", [])
            matrix = cpd.get("P_target_given_source", [])
            rows = {sv: _align_dist(row, self.values[t], tvals) for sv, row in zip(svals, matrix)}
            rowmat = np.vstack([rows.get(sv, self.prior[t]) for sv in self.values[s]])
            out[t].append(
                {
                    "source": s,
                    "weight": float(e.get("edge_weight", 1.0)),
                    "logratio": np.log(np.maximum(rowmat, self.config.eps)) - self.logprior[t][None, :],
                }
            )
        return out

    def _compile_full_cpts(self) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for cpt in self.graph.get("full_cpts", []):
            target = cpt.get("target")
            if target not in self.nodes:
                continue
            parents = [p for p in cpt.get("parents", []) if p in self.nodes]
            multipliers: List[int] = []
            m = 1
            for p in parents:
                multipliers.append(m)
                m *= len(self.values[p])
            lookup: Dict[int, np.ndarray] = {}
            for row in cpt.get("rows", []):
                assn = row.get("parent_assignment", {})
                try:
                    code = sum(self.vtoi[p][assn[p]] * multipliers[j] for j, p in enumerate(parents))
                except Exception:
                    continue
                dist = _align_dist(row.get("distribution", {}), self.values[target])
                lookup[int(code)] = np.log(np.maximum(dist, self.config.eps)) - self.logprior[target]
            out[target].append(
                {
                    "parents": parents,
                    "multipliers": np.array(multipliers, dtype=np.int64),
                    "code_space": m,
                    "weight": float(cpt.get("cpt_weight", 1.0)),
                    "replace": bool(cpt.get("replace_pairwise_parent_edges", False)),
                    "lookup": lookup,
                }
            )
        return out

    def _compile_masks(self) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for mask in self.graph.get("conditional_masks", []):
            target = mask.get("target")
            if target not in self.nodes:
                continue
            cond = []
            ok = True
            for p, allowed in mask.get("condition", {}).items():
                if p not in self.nodes:
                    ok = False
                    break
                allowed_ids = np.array([self.vtoi[p][v] for v in allowed if v in self.vtoi[p]], dtype=np.int16)
                cond.append((p, allowed_ids))
            if not ok:
                continue
            value_mult = np.ones(len(self.values[target]), dtype=float)
            for v in mask.get("bad_values", []):
                if v in self.vtoi[target]:
                    value_mult[self.vtoi[target][v]] *= float(mask.get("bad_value_multiplier", 0.0))
            for v, w in mask.get("downweight_values", {}).items():
                if v in self.vtoi[target]:
                    value_mult[self.vtoi[target][v]] *= float(w)
            preferred = set(mask.get("preferred_values", []))
            if mask.get("penalize_values_outside_preferred_set", False) and preferred:
                outside = float(mask.get("outside_preferred_multiplier", 1.0))
                for v in self.values[target]:
                    if v not in preferred:
                        value_mult[self.vtoi[target][v]] *= outside
            out[target].append({"condition": cond, "value_mult": value_mult})
        return out

    def _compile_node_shrinkage(self) -> tuple[Dict[str, set[str]], Dict[str, float]]:
        replaced: Dict[str, set[str]] = defaultdict(set)
        gamma: Dict[str, float] = defaultdict(lambda: 1.0)
        for nid in self.nodes:
            weights: List[float] = []
            repl: set[str] = set()
            for cpt in self.full_cpts.get(nid, []):
                weights.append(cpt["weight"])
                if cpt["replace"]:
                    repl.update(cpt["parents"])
            for edge in self.in_edges.get(nid, []):
                if edge["source"] not in repl:
                    weights.append(edge["weight"])
            replaced[nid] = repl
            gamma[nid] = 1.0 / max(1.0, math.sqrt(max(sum(w * w for w in weights), self.config.eps)))
        return replaced, gamma

    def _compile_required_nodes(self) -> set[str]:
        if not self.config.emit_only:
            return set(self.nodes)

        required = set(self.emit_nodes)
        parents_by_target: Dict[str, set[str]] = defaultdict(set)
        for edge in self.graph.get("directed_proposal_edges", []):
            source, target = edge.get("source"), edge.get("target")
            if source in self.nodes and target in self.nodes:
                parents_by_target[target].add(source)
        for cpt in self.graph.get("full_cpts", []):
            target = cpt.get("target")
            if target in self.nodes:
                parents_by_target[target].update(p for p in cpt.get("parents", []) if p in self.nodes)
        for mask in self.graph.get("conditional_masks", []):
            target = mask.get("target")
            if target in self.nodes:
                parents_by_target[target].update(p for p in mask.get("condition", {}) if p in self.nodes)

        stack = list(required)
        while stack:
            nid = stack.pop()
            for parent in parents_by_target.get(nid, set()):
                if parent not in required:
                    required.add(parent)
                    stack.append(parent)
        return required

    def _compile_plan(self) -> None:
        """Build the fully vectorizable per-node execution plan.

        A parent contributes to a target only when it is sampled earlier in the
        topological order; the availability checks the sampling loop used to run
        per batch are resolved once here.
        """
        topo_pos: Dict[str, int] = {}
        for i, nid in enumerate(self.topological_order):
            if nid in self.nodes and nid not in topo_pos:
                topo_pos[nid] = i

        def sampled_before(parent: str, pos: int) -> bool:
            return (
                parent in self.required_nodes
                and topo_pos.get(parent, math.inf) < pos
            )

        self._plan: List[_NodePlan] = []
        for nid in topo_pos:
            if nid not in self.required_nodes:
                continue
            pos = topo_pos[nid]
            k = len(self.values[nid])
            gamma = self.gamma[nid]
            logprior32 = self.logprior[nid].astype(np.float32)
            plan = _NodePlan(nid=nid, k=k, logprior=np.ascontiguousarray(logprior32[:, None]))

            for cpt in self.full_cpts.get(nid, []):
                if not all(sampled_before(p, pos) for p in cpt["parents"]):
                    continue
                lut = np.zeros((cpt["code_space"], k), dtype=np.float32)
                scale = gamma * cpt["weight"]
                for code, logratio in cpt["lookup"].items():
                    lut[code] = scale * logratio
                plan.cpts.append(
                    (
                        tuple(cpt["parents"]),
                        tuple(int(m) for m in cpt["multipliers"]),
                        np.ascontiguousarray(lut.T),
                    )
                )

            repl = self.replaced_parents[nid]
            for edge in self.in_edges.get(nid, []):
                if edge["source"] in repl or not sampled_before(edge["source"], pos):
                    continue
                scaled = ((gamma * edge["weight"]) * edge["logratio"]).astype(np.float32)
                plan.edges.append((edge["source"], np.ascontiguousarray(scaled.T)))

            for mask in self.masks.get(nid, []):
                if any(len(allowed) == 0 for _, allowed in mask["condition"]):
                    continue  # empty allowed set can never match any row
                missing = [p for p, _ in mask["condition"] if not sampled_before(p, pos)]
                if missing:
                    raise ValueError(
                        f"Conditional mask on {nid!r} depends on {missing!r} "
                        "which is not sampled before the target"
                    )
                conds = []
                for p, allowed in mask["condition"]:
                    lut = np.zeros(len(self.values[p]), dtype=bool)
                    lut[allowed] = True
                    conds.append((p, lut))
                value_mult32 = mask["value_mult"].astype(np.float32)
                plan.masks.append(
                    (
                        conds or None,
                        np.ascontiguousarray(value_mult32[:, None]),
                    )
                )

            if not plan.cpts and not plan.edges and all(c is None for c, _ in plan.masks):
                probs = np.exp(logprior32 - logprior32.max())
                for _, value_mult in plan.masks:
                    probs *= value_mult[:, 0]
                plan.static_cdf = np.cumsum(probs, dtype=np.float32)
                plan.static_total = float(plan.static_cdf[-1])
                plan.masks = []
            self._plan.append(plan)

        # Required nodes outside the topological order fall back to prior draws,
        # in stable graph declaration order.
        self._prior_only_nodes = [
            nid for nid in self.nodes if nid in self.required_nodes and nid not in topo_pos
        ]
        self._plan_max_k = max((p.k for p in self._plan), default=1)
        self._index_dtype = _codes_dtype_for_value_counts(
            [len(self.values[nid]) for nid in self.required_nodes]
        )

    def sample_indices(self, n: int) -> Dict[str, np.ndarray]:
        """Sample N personas and return integer-coded node values."""
        idx: Dict[str, np.ndarray] = {}
        rng = self.rng
        out_dtype = self._index_dtype
        kmax = self._plan_max_k
        # All per-node work runs in reused value-major (k, n) views of these
        # buffers, keeping the hot loop allocation-free and every reduction a
        # contiguous pass along the sample axis.
        ws_flat = np.empty(kmax * n, dtype=np.float32)
        gb_flat = np.empty(kmax * n, dtype=np.float32)
        below_flat = np.empty(kmax * n, dtype=bool)
        u = np.empty(n, dtype=np.float64)
        bounds = np.empty(n, dtype=np.float32)
        code = np.empty(n, dtype=np.int64)
        tmp = np.empty(n, dtype=np.int64)
        sel = np.empty(n, dtype=np.int64)

        for plan in self._plan:
            k = plan.k
            rng.random(out=u)

            if plan.static_cdf is not None:
                np.multiply(u, plan.static_total, out=u)
                bounds[:] = u
                found = np.searchsorted(plan.static_cdf, bounds, side="left")
                np.minimum(found, k - 1, out=found)
                idx[plan.nid] = found.astype(out_dtype)
                continue

            logits = ws_flat[: k * n].reshape(k, n)
            gathered = gb_flat[: k * n].reshape(k, n)
            np.copyto(logits, plan.logprior)

            for parents, multipliers, lut in plan.cpts:
                code[:] = 0
                for p, mult in zip(parents, multipliers):
                    tmp[:] = idx[p]
                    tmp *= mult
                    code += tmp
                # Codes and indices are in-bounds by construction; clip mode
                # skips numpy's buffered bounds-checked path.
                np.take(lut, code, axis=1, out=gathered, mode="clip")
                logits += gathered

            for source, scaled_logratio in plan.edges:
                np.take(scaled_logratio, idx[source], axis=1, out=gathered, mode="clip")
                logits += gathered

            logits -= logits.max(axis=0, keepdims=True)
            probs = logits
            np.exp(probs, out=probs)

            for conds, value_mult in plan.masks:
                if conds is None:
                    probs *= value_mult
                    continue
                rows = conds[0][1][idx[conds[0][0]]]
                for p, lut in conds[1:]:
                    rows &= lut[idx[p]]
                row_ids = np.flatnonzero(rows)
                if row_ids.size == 0:
                    continue
                sub = probs[:, row_ids]
                sub *= value_mult
                dead = sub.sum(axis=0) <= 0.0
                if dead.any():
                    # Should not occur for validated full DAG graphs; keep fallback for robustness.
                    sub[:, dead] = 1.0
                probs[:, row_ids] = sub

            # Unnormalized inverse-CDF draw: P(sel = j) = probs[j] / probs.sum().
            # Row-by-row accumulation is a contiguous vector add per value and
            # outruns ufunc.accumulate along the value axis.
            for j in range(1, k):
                probs[j] += probs[j - 1]
            np.multiply(u, probs[-1], out=u)
            bounds[:] = u
            below = below_flat[: k * n].reshape(k, n)
            np.less(probs, bounds, out=below)
            np.sum(below, axis=0, dtype=np.int64, out=sel)
            np.minimum(sel, k - 1, out=sel)
            idx[plan.nid] = sel.astype(out_dtype)

        for nid in self._prior_only_nodes:
            idx[nid] = rng.choice(len(self.values[nid]), size=n, p=self.prior[nid]).astype(out_dtype)
        return idx

    def _codes_dtype(self) -> np.dtype:
        return _codes_dtype_for_value_counts([len(self.values[nid]) for nid in self.emit_nodes])

    def _codes_packing(self) -> str:
        if self._codes_dtype() == np.dtype("uint8") and all(
            len(self.values[nid]) <= _NIBBLE_MAX_VALUES for nid in self.emit_nodes
        ):
            return "nibble"
        return "none"

    def _codes_row_bytes(self) -> int:
        cols = len(self.emit_nodes)
        if self._codes_packing() == "nibble":
            return (cols + 1) // 2
        return cols * self._codes_dtype().itemsize

    def codes_matrix(self, idx: Dict[str, np.ndarray]) -> np.ndarray:
        n = len(next(iter(idx.values()))) if idx else 0
        dtype = self._codes_dtype()
        matrix = np.empty((n, len(self.emit_nodes)), dtype=dtype)
        for col, nid in enumerate(self.emit_nodes):
            matrix[:, col] = idx[nid].astype(dtype, copy=False)
        return matrix

    def encoded_codes(self, idx: Dict[str, np.ndarray]) -> np.ndarray:
        """Return the on-disk representation of a sampled batch."""
        matrix = self.codes_matrix(idx)
        if self._codes_packing() == "nibble":
            return _pack_nibbles(matrix)
        return matrix

    def write_codes(self, idx: Dict[str, np.ndarray], out: str | Path, *, compress: str | None = None) -> Dict[str, Any]:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        compression = _normalize_compression(compress)
        n = len(next(iter(idx.values()))) if idx else 0
        payload = self.encoded_codes(idx)
        if compression == "none":
            payload.tofile(out)
            stored = int(payload.nbytes)
        else:
            blob = _compress_payload(payload, compression)
            Path(out).write_bytes(blob)
            stored = len(blob)
        return {
            "dtype": str(self._codes_dtype()),
            "shape": [n, len(self.emit_nodes)],
            "bytes": stored,
            "packing": self._codes_packing(),
            "compression": compression,
        }

    def codes_schema(self, n: int, out: str | Path, *, compress: str | None = None) -> Dict[str, Any]:
        return {
            "format": "persona_codes",
            "format_version": COMPACT_CODES_FORMAT_VERSION,
            "code_base": 0,
            "dtype": str(self._codes_dtype()),
            "shape": [int(n), len(self.emit_nodes)],
            "packing": self._codes_packing(),
            "row_bytes": self._codes_row_bytes(),
            "compression": _normalize_compression(compress),
            "codes_path": str(out),
            "columns": [
                {
                    "id": nid,
                    "label": self.nodes[nid].get("label", nid),
                    "category": self.nodes[nid].get("category"),
                    "values": self.values[nid],
                }
                for nid in self.emit_nodes
            ],
            "graph": str(self.graph_path),
            "emit_only": self.config.emit_only,
        }

    def write_codes_schema(self, n: int, out: str | Path, *, compress: str | None = None) -> Path:
        schema_path = codes_schema_path(out)
        schema_path.write_text(
            json.dumps(self.codes_schema(n, out, compress=compress), indent=2), encoding="utf-8"
        )
        return schema_path

    def decode_row(self, idx: Dict[str, np.ndarray], row: int, *, include_hidden: Optional[bool] = None) -> Dict[str, str]:
        if include_hidden is None:
            node_ids = self.emit_nodes
        else:
            node_ids = [nid for nid, n in self.nodes.items() if include_hidden or n.get("emit", True) is not False]
        return {nid: self.values[nid][int(idx[nid][row])] for nid in node_ids if nid in idx}

    def sample(self, n: int) -> List[Dict[str, str]]:
        idx = self.sample_indices(n)
        return [self.decode_row(idx, i) for i in range(n)]

    def write_jsonl(self, idx: Dict[str, np.ndarray], out: str | Path) -> None:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        with Path(out).open("w", encoding="utf-8") as f:
            n = len(next(iter(idx.values())))
            for i in range(n):
                f.write(json.dumps(self.decode_row(idx, i), ensure_ascii=False) + "\n")

    def write_csv(self, idx: Dict[str, np.ndarray], out: str | Path) -> None:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        with Path(out).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.emit_nodes)
            w.writeheader()
            n = len(next(iter(idx.values())))
            for i in range(n):
                w.writerow(self.decode_row(idx, i))

    def sample_to_file(self, n: int, out: str | Path, fmt: str = "codes", *, compress: str | None = None) -> Dict[str, Any]:
        start = time.time()
        idx = self.sample_indices(n)
        if fmt == "jsonl":
            self.write_jsonl(idx, out)
        elif fmt == "csv":
            self.write_csv(idx, out)
        elif fmt == "codes":
            codes_meta = self.write_codes(idx, out, compress=compress)
            schema_path = self.write_codes_schema(n, out, compress=compress)
        else:
            raise ValueError(f"Unsupported format: {fmt}")
        meta = {
            "samples": n,
            "out": str(out),
            "format": fmt,
            "elapsed_seconds": time.time() - start,
            "emitted_nodes": len(self.emit_nodes),
            "graph": str(self.graph_path),
            "seed": self.config.seed,
        }
        if fmt == "codes":
            meta.update(
                {
                    "schema_out": str(schema_path),
                    "storage_bytes": codes_meta["bytes"],
                    "dtype": codes_meta["dtype"],
                    "packing": codes_meta["packing"],
                    "compression": codes_meta["compression"],
                }
            )
        return meta


def _planned_batches(n: int, workers: int, batch_size: int | None) -> tuple[List[int], int]:
    if n <= 0:
        raise ValueError("n must be positive")
    if workers <= 0:
        raise ValueError("workers must be positive")
    if batch_size is not None and batch_size <= 0:
        raise ValueError("batch_size must be positive when provided")

    effective_batch_size = batch_size or math.ceil(n / workers)
    batches = []
    remaining = n
    while remaining > 0:
        size = min(effective_batch_size, remaining)
        batches.append(size)
        remaining -= size
    return batches, effective_batch_size


def _batch_seeds(seed: int, count: int) -> List[int]:
    rng = np.random.default_rng(seed)
    return [int(v) for v in rng.integers(0, 2**63 - 1, size=count)]


def _worker_init(graph_path: str, emit_only: bool, eps: float) -> None:
    global _WORKER_SAMPLER
    _WORKER_SAMPLER = PersonaForwardSampler(
        graph_path,
        SamplingConfig(seed=0, emit_only=emit_only, eps=eps),
    )


def _write_shard(
    sampler: PersonaForwardSampler,
    *,
    n: int,
    seed: int,
    out: Path,
    fmt: str,
    compress: str | None = None,
) -> None:
    sampler.rng = np.random.default_rng(seed)
    idx = sampler.sample_indices(n)
    if fmt == "jsonl":
        sampler.write_jsonl(idx, out)
    elif fmt == "csv":
        sampler.write_csv(idx, out)
    elif fmt == "codes":
        sampler.write_codes(idx, out, compress=compress)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def _write_codes_at_offset(
    sampler: PersonaForwardSampler,
    *,
    n: int,
    seed: int,
    out: Path,
    offset: int,
) -> None:
    sampler.rng = np.random.default_rng(seed)
    payload = sampler.encoded_codes(sampler.sample_indices(n))
    with out.open("r+b") as f:
        f.seek(offset)
        f.write(payload.reshape(-1).data)


def _sample_without_saving(
    sampler: PersonaForwardSampler,
    *,
    n: int,
    seed: int,
) -> int:
    sampler.rng = np.random.default_rng(seed)
    sampler.sample_indices(n)
    return n


def _worker_sample(task: tuple[int, int, int, str, str, str | None]) -> tuple[int, int, str]:
    batch_index, n, seed, fmt, shard_path, compress = task
    if _WORKER_SAMPLER is None:
        raise RuntimeError("Parallel sampler worker was not initialized")
    _write_shard(
        _WORKER_SAMPLER,
        n=n,
        seed=seed,
        out=Path(shard_path),
        fmt=fmt,
        compress=compress,
    )
    return batch_index, n, shard_path


def _worker_sample_codes_at_offset(task: tuple[int, int, int, str, int]) -> tuple[int, int]:
    batch_index, n, seed, out_path, offset = task
    if _WORKER_SAMPLER is None:
        raise RuntimeError("Parallel sampler worker was not initialized")
    _write_codes_at_offset(
        _WORKER_SAMPLER,
        n=n,
        seed=seed,
        out=Path(out_path),
        offset=offset,
    )
    return batch_index, n


def _worker_sample_without_saving(task: tuple[int, int, int]) -> tuple[int, int]:
    batch_index, n, seed = task
    if _WORKER_SAMPLER is None:
        raise RuntimeError("Parallel sampler worker was not initialized")
    rows = _sample_without_saving(_WORKER_SAMPLER, n=n, seed=seed)
    return batch_index, rows


def _fork_context() -> mp.context.BaseContext | None:
    if "fork" not in mp.get_all_start_methods():
        return None
    return mp.get_context("fork")


def _run_worker_tasks(
    parent_sampler: PersonaForwardSampler,
    *,
    workers: int,
    tasks: List[Any],
    worker_fn: Callable[[Any], Any],
) -> List[Any]:
    """Run tasks in a process pool, preferring fork to reuse the parent's compiled sampler."""
    fork_context = _fork_context()
    if fork_context is None:
        graph_path = str(parent_sampler.graph_path)
        emit_only = parent_sampler.config.emit_only
        eps = parent_sampler.config.eps
        with ProcessPoolExecutor(
            max_workers=workers,
            initializer=_worker_init,
            initargs=(graph_path, emit_only, eps),
        ) as pool:
            futures = [pool.submit(worker_fn, task) for task in tasks]
            return [future.result() for future in as_completed(futures)]

    global _WORKER_SAMPLER
    previous_sampler = _WORKER_SAMPLER
    _WORKER_SAMPLER = parent_sampler
    try:
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=fork_context,
        ) as pool:
            futures = [pool.submit(worker_fn, task) for task in tasks]
            return [future.result() for future in as_completed(futures)]
    finally:
        _WORKER_SAMPLER = previous_sampler


def _merge_shards(shards: List[Path], out: Path, fmt: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "codes":
        with out.open("wb") as dest:
            for shard in shards:
                with shard.open("rb") as src:
                    shutil.copyfileobj(src, dest)
        return

    with out.open("w", encoding="utf-8", newline="") as dest:
        for index, shard in enumerate(shards):
            with shard.open("r", encoding="utf-8", newline="") as src:
                if fmt == "csv" and index > 0:
                    next(src, None)
                shutil.copyfileobj(src, dest)


def sample_to_file_parallel(
    graph_path: str | Path,
    *,
    n: int,
    out: str | Path | None,
    fmt: str = "codes",
    seed: int = 42,
    emit_only: bool = True,
    workers: int = 1,
    batch_size: int | None = None,
    eps: float = EPS,
    compress: str | None = None,
) -> Dict[str, Any]:
    """Sample personas with optional batch-level process concurrency.

    The sampling semantics are identical to ``PersonaForwardSampler``. Parallel
    mode only shards the requested row count into independent batches with
    deterministic child seeds. Uncompressed codes shards are written directly
    into their row offsets of the output file; compressed codes shards become
    independent gzip members concatenated in batch order, and jsonl/csv shards
    are written to temporary files and merged in batch order. When ``out`` is
    ``None``, samples are generated and discarded after timing.
    """
    if fmt not in {"jsonl", "csv", "codes"}:
        raise ValueError(f"Unsupported format: {fmt}")
    compression = _normalize_compression(compress)
    if compression != "none" and fmt != "codes":
        raise ValueError(f"Compression is only supported for codes output, not {fmt!r}")

    graph_path = Path(graph_path)
    out_path = Path(out) if out is not None else None
    workers = int(workers)
    batches, effective_batch_size = _planned_batches(n, workers, batch_size)
    actual_workers = min(workers, len(batches))
    seeds = _batch_seeds(seed, len(batches))

    if out_path is not None and workers == 1 and len(batches) == 1:
        sampler = PersonaForwardSampler(
            graph_path,
            SamplingConfig(seed=seed, emit_only=emit_only, eps=eps),
        )
        meta = sampler.sample_to_file(n, out_path, fmt, compress=compress)
        meta.update(
            {
                "workers": 1,
                "requested_workers": workers,
                "batch_size": effective_batch_size,
                "batches": 1,
                "parallel": False,
                "saved": True,
            }
        )
        return meta

    start = time.time()
    parent_sampler = PersonaForwardSampler(
        graph_path,
        SamplingConfig(seed=0, emit_only=emit_only, eps=eps),
    )

    def run_batches(tasks: List[Any], worker_fn: Callable[[Any], Any], inline_fn: Callable[[Any], Any]) -> List[Any]:
        if actual_workers == 1:
            return [inline_fn(task) for task in tasks]
        return _run_worker_tasks(
            parent_sampler,
            workers=actual_workers,
            tasks=tasks,
            worker_fn=worker_fn,
        )

    base_meta = {
        "format": fmt,
        "emitted_nodes": len(parent_sampler.emit_nodes),
        "graph": str(graph_path),
        "seed": seed,
        "workers": actual_workers,
        "requested_workers": workers,
        "batch_size": effective_batch_size,
        "batches": len(batches),
        "parallel": actual_workers > 1,
    }

    if out_path is None:
        tasks = [(i, size, seeds[i]) for i, size in enumerate(batches)]
        results = run_batches(
            tasks,
            _worker_sample_without_saving,
            lambda task: (
                task[0],
                _sample_without_saving(parent_sampler, n=task[1], seed=task[2]),
            ),
        )
        rows_sampled = sum(rows for _, rows in results)
        elapsed = time.time() - start
        return {
            "samples": rows_sampled,
            "out": None,
            "saved": False,
            "elapsed_seconds": elapsed,
            "sampling_throughput_per_second": rows_sampled / elapsed if elapsed > 0 else 0.0,
            **base_meta,
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "codes" and compression == "none":
        row_bytes = parent_sampler._codes_row_bytes()
        offsets = [0]
        for size in batches[:-1]:
            offsets.append(offsets[-1] + size * row_bytes)
        partial_path = out_path.with_name(out_path.name + ".partial")
        try:
            with partial_path.open("wb") as f:
                f.truncate(n * row_bytes)
            tasks = [
                (i, size, seeds[i], str(partial_path), offsets[i])
                for i, size in enumerate(batches)
            ]

            def inline_codes(task: tuple[int, int, int, str, int]) -> tuple[int, int]:
                batch_index, size, batch_seed, path, offset = task
                _write_codes_at_offset(
                    parent_sampler,
                    n=size,
                    seed=batch_seed,
                    out=Path(path),
                    offset=offset,
                )
                return batch_index, size

            run_batches(tasks, _worker_sample_codes_at_offset, inline_codes)
            partial_path.replace(out_path)
        except BaseException:
            partial_path.unlink(missing_ok=True)
            raise
        schema_path = parent_sampler.write_codes_schema(n, out_path, compress=compress)
        return {
            "samples": n,
            "out": str(out_path),
            "saved": True,
            "elapsed_seconds": time.time() - start,
            "schema_out": str(schema_path),
            "storage_bytes": out_path.stat().st_size,
            "dtype": parent_sampler._codes_dtype().name,
            "packing": parent_sampler._codes_packing(),
            "compression": compression,
            **base_meta,
        }

    shard_results: List[tuple[int, int, str]] = []
    with tempfile.TemporaryDirectory(
        prefix=f"{out_path.name}.shards.",
        dir=str(out_path.parent),
    ) as tmp:
        tmp_dir = Path(tmp)
        tasks = [
            (i, size, seeds[i], fmt, str(tmp_dir / f"batch_{i:06d}.{fmt}"), compress)
            for i, size in enumerate(batches)
        ]

        def inline_shard(task: tuple[int, int, int, str, str, str | None]) -> tuple[int, int, str]:
            batch_index, size, batch_seed, task_fmt, shard_path, task_compress = task
            _write_shard(
                parent_sampler,
                n=size,
                seed=batch_seed,
                out=Path(shard_path),
                fmt=task_fmt,
                compress=task_compress,
            )
            return batch_index, size, shard_path

        shard_results = run_batches(tasks, _worker_sample, inline_shard)
        shard_results.sort(key=lambda row: row[0])
        _merge_shards([Path(row[2]) for row in shard_results], out_path, fmt)

    meta = {
        "samples": n,
        "out": str(out_path),
        "saved": True,
        "elapsed_seconds": time.time() - start,
        **base_meta,
    }
    if fmt == "codes":
        schema_path = parent_sampler.write_codes_schema(n, out_path, compress=compress)
        meta.update(
            {
                "schema_out": str(schema_path),
                "storage_bytes": out_path.stat().st_size,
                "dtype": parent_sampler._codes_dtype().name,
                "packing": parent_sampler._codes_packing(),
                "compression": compression,
            }
        )
    return meta
