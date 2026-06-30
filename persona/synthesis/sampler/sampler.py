from __future__ import annotations

import csv
import json
import math
import shutil
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import numpy as np

EPS = 1e-12
_WORKER_SAMPLER: "PersonaForwardSampler | None" = None


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


@dataclass(frozen=True)
class SamplingConfig:
    seed: int = 42
    emit_only: bool = True
    eps: float = EPS


class PersonaForwardSampler:
    """Vectorized forward sampler for the Persona Full DAG.

    The graph is interpreted as a DAG-style proposal distribution. For node i:

        q_i(v) ∝ P0_i(v) * exp(gamma_i * [pairwise log-ratio evidence + full-CPT log-ratio evidence])
                 * local mask multipliers.

    Pairwise and full-CPT contributions are represented as log-likelihood ratios against
    the target node prior. Conditional masks implement explicit local hard/soft guards.
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

    @staticmethod
    def _condition_rows(idx: Dict[str, np.ndarray], cond: List[tuple[str, np.ndarray]], n: int) -> np.ndarray | None:
        if not cond:
            return None
        row_mask = np.ones(n, dtype=bool)
        for p, allowed in cond:
            if len(allowed) == 0:
                return np.zeros(n, dtype=bool)
            row_mask &= np.isin(idx[p], allowed)
        return row_mask

    def sample_indices(self, n: int) -> Dict[str, np.ndarray]:
        """Sample N personas and return integer-coded node values."""
        idx: Dict[str, np.ndarray] = {}
        for nid in self.topological_order:
            if nid not in self.nodes:
                continue
            k = len(self.values[nid])
            logits = np.tile(self.logprior[nid], (n, 1))
            gamma = self.gamma[nid]

            for cpt in self.full_cpts.get(nid, []):
                if not all(p in idx for p in cpt["parents"]):
                    continue
                code = np.zeros(n, dtype=np.int64)
                for j, p in enumerate(cpt["parents"]):
                    code += idx[p].astype(np.int64) * int(cpt["multipliers"][j])
                for cd in np.unique(code):
                    lr = cpt["lookup"].get(int(cd))
                    if lr is not None:
                        logits[code == cd] += gamma * cpt["weight"] * lr

            repl = self.replaced_parents[nid]
            for edge in self.in_edges.get(nid, []):
                if edge["source"] in repl or edge["source"] not in idx:
                    continue
                logits += gamma * edge["weight"] * edge["logratio"][idx[edge["source"]]]

            logits -= logits.max(axis=1, keepdims=True)
            probs = np.exp(logits)
            probs /= probs.sum(axis=1, keepdims=True)

            for mask in self.masks.get(nid, []):
                rows = self._condition_rows(idx, mask["condition"], n)
                if rows is None:
                    probs *= mask["value_mult"][None, :]
                    probs /= probs.sum(axis=1, keepdims=True)
                elif rows.any():
                    probs[rows] *= mask["value_mult"][None, :]
                    s = probs[rows].sum(axis=1, keepdims=True)
                    zero = s[:, 0] <= 0
                    if zero.any():
                        # Should not occur for validated full DAG graphs; keep fallback for robustness.
                        probs[rows][zero] = 1.0 / k
                        s = probs[rows].sum(axis=1, keepdims=True)
                    probs[rows] /= s

            probs = np.maximum(probs, 0)
            probs /= probs.sum(axis=1, keepdims=True)
            u = self.rng.random(n)
            cum = np.cumsum(probs, axis=1)
            idx[nid] = (cum < u[:, None]).sum(axis=1).astype(np.int16)

        # If graph contains nodes outside topological order, sample them from priors.
        for nid in self.nodes:
            if nid not in idx:
                idx[nid] = self.rng.choice(len(self.values[nid]), size=n, p=self.prior[nid]).astype(np.int16)
        return idx

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

    def sample_to_file(self, n: int, out: str | Path, fmt: str = "jsonl") -> Dict[str, Any]:
        start = time.time()
        idx = self.sample_indices(n)
        if fmt == "jsonl":
            self.write_jsonl(idx, out)
        elif fmt == "csv":
            self.write_csv(idx, out)
        else:
            raise ValueError(f"Unsupported format: {fmt}")
        return {
            "samples": n,
            "out": str(out),
            "format": fmt,
            "elapsed_seconds": time.time() - start,
            "emitted_nodes": len(self.emit_nodes),
            "graph": str(self.graph_path),
            "seed": self.config.seed,
        }


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


def _emitted_node_count(graph_path: str | Path, emit_only: bool) -> int:
    with Path(graph_path).open("r", encoding="utf-8") as f:
        graph = json.load(f)
    nodes = graph.get("nodes", [])
    if not emit_only:
        return len(nodes)
    return sum(1 for node in nodes if node.get("emit", True) is not False)


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
) -> None:
    sampler.rng = np.random.default_rng(seed)
    idx = sampler.sample_indices(n)
    if fmt == "jsonl":
        sampler.write_jsonl(idx, out)
    elif fmt == "csv":
        sampler.write_csv(idx, out)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def _worker_sample(task: tuple[int, int, int, str, str]) -> tuple[int, int, str]:
    batch_index, n, seed, fmt, shard_path = task
    if _WORKER_SAMPLER is None:
        raise RuntimeError("Parallel sampler worker was not initialized")
    _write_shard(
        _WORKER_SAMPLER,
        n=n,
        seed=seed,
        out=Path(shard_path),
        fmt=fmt,
    )
    return batch_index, n, shard_path


def _merge_shards(shards: List[Path], out: Path, fmt: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
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
    out: str | Path,
    fmt: str = "jsonl",
    seed: int = 42,
    emit_only: bool = True,
    workers: int = 1,
    batch_size: int | None = None,
    eps: float = EPS,
) -> Dict[str, Any]:
    """Sample personas with optional batch-level process concurrency.

    The sampling semantics are identical to ``PersonaForwardSampler``. Parallel
    mode only shards the requested row count into independent batches with
    deterministic child seeds, then merges shard files in batch order.
    """
    if fmt not in {"jsonl", "csv"}:
        raise ValueError(f"Unsupported format: {fmt}")

    graph_path = Path(graph_path)
    out = Path(out)
    workers = int(workers)
    batches, effective_batch_size = _planned_batches(n, workers, batch_size)

    if workers == 1 and len(batches) == 1:
        sampler = PersonaForwardSampler(
            graph_path,
            SamplingConfig(seed=seed, emit_only=emit_only, eps=eps),
        )
        meta = sampler.sample_to_file(n, out, fmt)
        meta.update(
            {
                "workers": 1,
                "requested_workers": workers,
                "batch_size": effective_batch_size,
                "batches": 1,
                "parallel": False,
            }
        )
        return meta

    start = time.time()
    seeds = _batch_seeds(seed, len(batches))
    out.parent.mkdir(parents=True, exist_ok=True)
    actual_workers = min(workers, len(batches))
    shard_results: List[tuple[int, int, str]] = []

    with tempfile.TemporaryDirectory(
        prefix=f"{out.name}.shards.",
        dir=str(out.parent),
    ) as tmp:
        tmp_dir = Path(tmp)
        tasks = [
            (i, size, seeds[i], fmt, str(tmp_dir / f"batch_{i:06d}.{fmt}"))
            for i, size in enumerate(batches)
        ]
        if actual_workers == 1:
            sampler = PersonaForwardSampler(
                graph_path,
                SamplingConfig(seed=0, emit_only=emit_only, eps=eps),
            )
            for task in tasks:
                batch_index, size, batch_seed, task_fmt, shard_path = task
                _write_shard(
                    sampler,
                    n=size,
                    seed=batch_seed,
                    out=Path(shard_path),
                    fmt=task_fmt,
                )
                shard_results.append((batch_index, size, shard_path))
        else:
            with ProcessPoolExecutor(
                max_workers=actual_workers,
                initializer=_worker_init,
                initargs=(str(graph_path), emit_only, eps),
            ) as pool:
                futures = [pool.submit(_worker_sample, task) for task in tasks]
                for future in as_completed(futures):
                    shard_results.append(future.result())

        shard_results.sort(key=lambda row: row[0])
        _merge_shards([Path(row[2]) for row in shard_results], out, fmt)

    return {
        "samples": n,
        "out": str(out),
        "format": fmt,
        "elapsed_seconds": time.time() - start,
        "emitted_nodes": _emitted_node_count(graph_path, emit_only),
        "graph": str(graph_path),
        "seed": seed,
        "workers": actual_workers,
        "requested_workers": workers,
        "batch_size": effective_batch_size,
        "batches": len(batches),
        "parallel": actual_workers > 1,
    }
