# alignment_analysis.py — Measure alignment between simulated agent behavior and real human data.
# Compares agent vote distributions, engagement patterns, and opinion formation
# against ground-truth human behavior from real Reddit data.
# Produces correlation plots and alignment metrics.

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


def get_simulation_vote_distribution(db_path: str) -> dict[str, Any]:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM \"like\"")
    total_likes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM dislike")
    total_dislikes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM post")
    total_posts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM comment")
    total_comments = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM follow")
    total_follows = cursor.fetchone()[0]

    cursor.execute("SELECT action, COUNT(*) as cnt FROM trace GROUP BY action ORDER BY cnt DESC")
    action_counts = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT (num_likes - num_dislikes) as score FROM post")
    post_scores = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT (num_likes - num_dislikes) as score FROM comment")
    comment_scores = [row[0] for row in cursor.fetchall()]

    conn.close()

    return {
        "total_likes": total_likes,
        "total_dislikes": total_dislikes,
        "total_posts": total_posts,
        "total_comments": total_comments,
        "total_follows": total_follows,
        "action_counts": action_counts,
        "post_scores": post_scores,
        "comment_scores": comment_scores,
        "like_ratio": total_likes / max(total_likes + total_dislikes, 1),
    }


def compute_alignment_metrics(
    sim_scores: list[int],
    human_scores: list[int],
) -> dict[str, float]:
    if not sim_scores or not human_scores:
        return {"correlation": 0.0, "p_value": 1.0, "mae": 0.0, "rmse": 0.0}

    min_len = min(len(sim_scores), len(human_scores))
    sim = np.array(sim_scores[:min_len], dtype=float)
    human = np.array(human_scores[:min_len], dtype=float)

    if len(sim) < 2:
        return {"correlation": 0.0, "p_value": 1.0, "mae": 0.0, "rmse": 0.0}

    corr, p_val = stats.pearsonr(sim, human)
    mae = float(np.mean(np.abs(sim - human)))
    rmse = float(np.sqrt(np.mean((sim - human) ** 2)))

    return {
        "correlation": float(corr),
        "p_value": float(p_val),
        "mae": mae,
        "rmse": rmse,
    }


def plot_score_comparison(
    sim_scores: list[int],
    human_scores: list[int],
    output_path: str | Path | None = None,
    title: str = "Simulated vs Human Scores",
    show: bool = False,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    min_len = min(len(sim_scores), len(human_scores))
    sim = sim_scores[:min_len]
    human = human_scores[:min_len]

    axes[0].scatter(human, sim, alpha=0.6, edgecolors="black", linewidth=0.3, s=40)
    axes[0].set_xlabel("Human Scores")
    axes[0].set_ylabel("Simulated Agent Scores")
    axes[0].set_title(f"{title}\n(n={min_len})")

    if min_len > 1:
        z = np.polyfit(human, sim, 1)
        p = np.poly1d(z)
        x_range = np.linspace(min(human), max(human), 50)
        axes[0].plot(x_range, p(x_range), "r--", alpha=0.8, label=f"fit: y={z[0]:.2f}x+{z[1]:.2f}")
        axes[0].legend()

    lim_min = min(min(sim + human) - 1, -2)
    lim_max = max(max(sim + human) + 1, 2)
    axes[0].plot([lim_min, lim_max], [lim_min, lim_max], "k--", alpha=0.3, label="y=x")
    axes[0].set_xlim(lim_min, lim_max)
    axes[0].set_ylim(lim_min, lim_max)

    bins = range(int(min(min(sim), min(human))) - 1, int(max(max(sim), max(human))) + 2)
    axes[1].hist(human, bins=bins, alpha=0.5, label="Human", color="#4ecdc4", edgecolor="black", linewidth=0.5)
    axes[1].hist(sim, bins=bins, alpha=0.5, label="Simulated", color="#ff6b6b", edgecolor="black", linewidth=0.5)
    axes[1].set_xlabel("Score")
    axes[1].set_ylabel("Count")
    axes[1].set_title("Score Distribution Comparison")
    axes[1].legend()

    plt.tight_layout()

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()
    plt.close()


def plot_action_distribution(
    action_counts: dict[str, int],
    output_path: str | Path | None = None,
    title: str = "Agent Action Distribution",
    show: bool = False,
) -> None:
    filtered = {k: v for k, v in action_counts.items() if k != "refresh"}
    if not filtered:
        return

    sorted_actions = sorted(filtered.items(), key=lambda x: -x[1])
    labels = [a[0] for a in sorted_actions]
    counts = [a[1] for a in sorted_actions]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
    bars = ax.barh(labels, counts, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_xlabel("Count")
    ax.set_title(title)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2, str(count), va="center", fontsize=9)

    plt.tight_layout()

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()
    plt.close()


def full_alignment_report(
    db_path: str,
    human_scores: list[int] | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    sim_data = get_simulation_vote_distribution(db_path)

    report = {
        "simulation_stats": {
            "total_likes": sim_data["total_likes"],
            "total_dislikes": sim_data["total_dislikes"],
            "total_posts": sim_data["total_posts"],
            "total_comments": sim_data["total_comments"],
            "total_follows": sim_data["total_follows"],
            "like_ratio": sim_data["like_ratio"],
        },
        "action_distribution": sim_data["action_counts"],
    }

    if output_dir:
        plot_action_distribution(
            sim_data["action_counts"],
            output_path=Path(output_dir) / "action_distribution.png",
        )

    if human_scores and sim_data["post_scores"]:
        metrics = compute_alignment_metrics(sim_data["post_scores"], human_scores)
        report["alignment_metrics"] = metrics

        if output_dir:
            plot_score_comparison(
                sim_data["post_scores"],
                human_scores,
                output_path=Path(output_dir) / "score_alignment.png",
            )

    return report


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python alignment_analysis.py <db_path> [output_dir]")
        sys.exit(1)

    db_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./output"
    report = full_alignment_report(db_path, output_dir=output_dir)
    print(json.dumps(report, indent=2))
