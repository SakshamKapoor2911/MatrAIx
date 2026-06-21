# alignment_analysis.py — Compare simulated Twitter propagation against real-world data.
# Plots scale/depth/max_breadth over time with 95% CI bands.
# Computes normalized RMSE between simulated and real propagation curves.

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from environments.oasis.visualization.twitter.propagation_graph import PropagationGraph


def pad_to_length(data: list, length: int = 300) -> list:
    if len(data) >= length:
        return data[:length]
    return data + [data[-1] if data else 0] * (length - len(data))


def compute_propagation_stats(db_path: str, source_post_id: int | None = None, max_time: int = 300) -> dict[str, list[int]]:
    pg = PropagationGraph(source_post_id=source_post_id, db_path=db_path)
    if not pg.build_graph():
        return {"scale": [0] * max_time, "depth": [0] * max_time, "max_breadth": [0] * max_time}

    _, scale = pg.get_scale_over_time()
    _, depth = pg.get_depth_over_time()
    _, breadth = pg.get_max_breadth_over_time()

    return {
        "scale": pad_to_length(scale, max_time),
        "depth": pad_to_length(depth, max_time),
        "max_breadth": pad_to_length(breadth, max_time),
    }


def compute_rmse(simulated: np.ndarray, real: np.ndarray) -> float:
    max_real = real.max()
    if max_real == 0:
        return 0.0
    return float(np.sqrt(np.mean((simulated - real) ** 2)) / max_real)


def compute_rmse_over_time(simulated: np.ndarray, real: np.ndarray) -> np.ndarray:
    max_real = real.max()
    if max_real == 0:
        return np.zeros_like(simulated)
    return np.abs(simulated - real) / max_real


def plot_propagation_trends(
    sim_stats_list: list[dict[str, list[int]]],
    real_stats: dict[str, list[int]] | None = None,
    labels: list[str] | None = None,
    output_path: str | Path | None = None,
    max_time: int = 150,
    show: bool = False,
) -> dict[str, Any]:
    stat_names = ["scale", "depth", "max_breadth"]
    colors = ["blue", "red", "orange", "magenta", "green", "purple"]

    if labels is None:
        labels = [f"Sim_{i}" for i in range(len(sim_stats_list))]
    if real_stats:
        labels.append("Real")

    fig, axes = plt.subplots(1, 3, figsize=(21, 7))

    for stat_idx, stat_name in enumerate(stat_names):
        ax = axes[stat_idx]

        all_data = []
        for sim_stats in sim_stats_list:
            all_data.append(np.array(sim_stats[stat_name][:max_time]))
        if real_stats:
            all_data.append(np.array(real_stats[stat_name][:max_time]))

        for i, (data, label) in enumerate(zip(all_data, labels)):
            if data.ndim == 1:
                ax.plot(data, label=label, color=colors[i % len(colors)])
            else:
                mean_vals = np.mean(data, axis=0)
                std_vals = np.std(data, axis=0)
                ci = 1.96 * (std_vals / np.sqrt(max(data.shape[0], 1)))
                ax.plot(mean_vals, label=label, color=colors[i % len(colors)])
                ax.fill_between(range(len(mean_vals)), mean_vals - ci, mean_vals + ci, color=colors[i % len(colors)], alpha=0.2)

        ax.set_xlabel("Time (steps)")
        ax.set_ylabel(stat_name.replace("_", " ").title())
        ax.set_title(f"{stat_name.replace('_', ' ').title()} Over Time")
        ax.grid(True, alpha=0.3)
        ax.legend()

    plt.tight_layout()
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    plt.close()

    return {"labels": labels, "max_time": max_time}


def plot_rmse_trends(
    sim_stats_list: list[dict[str, list[int]]],
    real_stats: dict[str, list[int]],
    labels: list[str] | None = None,
    output_path: str | Path | None = None,
    max_time: int = 150,
    show: bool = False,
) -> dict[str, float]:
    stat_names = ["scale", "depth", "max_breadth"]
    colors = ["blue", "red", "orange", "magenta", "green"]
    markers = ["o", "^", "s", "D", "v"]

    if labels is None:
        labels = [f"Sim_{i}" for i in range(len(sim_stats_list))]

    fig, axes = plt.subplots(1, 3, figsize=(21, 7))
    rmse_results = {}

    for stat_idx, stat_name in enumerate(stat_names):
        ax = axes[stat_idx]
        real_arr = np.array(real_stats[stat_name][:max_time])

        for i, (sim_stats, label) in enumerate(zip(sim_stats_list, labels)):
            sim_arr = np.array(sim_stats[stat_name][:max_time])
            rmse_per_step = compute_rmse_over_time(sim_arr, real_arr)
            total_rmse = compute_rmse(sim_arr, real_arr)
            rmse_results[f"{label}_{stat_name}"] = total_rmse

            ax.plot(rmse_per_step, label=label, color=colors[i % len(colors)], marker=markers[i % len(markers)], markevery=10)

        ax.set_xlabel("Time (steps)")
        if stat_idx == 0:
            ax.set_ylabel("Normalized RMSE")
        ax.set_title(f"{stat_name.replace('_', ' ').title()} RMSE")
        ax.grid(True, alpha=0.3)
        ax.legend()

    plt.tight_layout()
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    plt.close()

    return rmse_results
