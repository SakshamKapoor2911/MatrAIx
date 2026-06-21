# counterfactual_analysis.py — Analyze Reddit counterfactual experiments.
# Measures herding effect: do artificially upvoted/downvoted comments accumulate
# more/fewer votes from agents compared to the control group?
# Produces bar charts with 95% confidence intervals (matching OASIS's visualization).

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


def get_comment_score(db_path: str, comment_id: int) -> int | None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT (num_likes - num_dislikes) AS score FROM comment WHERE comment_id = ?",
        (comment_id,),
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def get_post_score(db_path: str, post_id: int) -> int | None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT (num_likes - num_dislikes) AS score FROM post WHERE post_id = ?",
        (post_id,),
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def collect_group_scores(
    db_path: str,
    experiment_info: dict[str, list[int]],
    score_type: str = "comment",
) -> dict[str, list[int]]:
    score_fn = get_comment_score if score_type == "comment" else get_post_score
    results = {}
    for group_name, ids in experiment_info.items():
        scores = []
        for item_id in ids:
            score = score_fn(db_path, item_id)
            if score is not None:
                scores.append(score)
        results[group_name] = scores
    return results


def mean_confidence_interval(data: list[float], confidence: float = 0.95) -> tuple[float, float, float]:
    a = np.array(data, dtype=float)
    n = len(a)
    if n < 2:
        m = np.mean(a) if n > 0 else 0.0
        return m, m, m
    m = np.mean(a)
    se = stats.sem(a)
    h = se * stats.t.ppf((1 + confidence) / 2.0, n - 1)
    return float(m), float(m - h), float(m + h)


def plot_counterfactual_scores(
    group_scores: dict[str, list[int]],
    output_path: str | Path | None = None,
    title: str = "Mean Scores with 95% Confidence Intervals",
    show: bool = False,
) -> dict[str, Any]:
    labels = []
    means = []
    ci_lows = []
    ci_highs = []

    order = ["down", "control", "up"]
    for group in order:
        if group in group_scores and group_scores[group]:
            m, lo, hi = mean_confidence_interval(group_scores[group])
            labels.append(group.capitalize())
            means.append(m)
            ci_lows.append(lo)
            ci_highs.append(hi)

    if not labels:
        return {"error": "No data to plot"}

    yerr = [[m - lo for m, lo in zip(means, ci_lows)],
            [hi - m for m, hi in zip(means, ci_highs)]]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, means, color=["#ff6b6b", "#a8dadc", "#4ecdc4"], yerr=yerr, capsize=10, edgecolor="black", linewidth=0.8)

    for i, m in enumerate(means):
        ax.plot(i, m, "ko", markersize=6)

    ax.set_ylabel("Score (likes - dislikes)")
    ax.set_title(title)
    ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()
    plt.close()

    return {
        "labels": labels,
        "means": means,
        "ci_low": ci_lows,
        "ci_high": ci_highs,
        "n_per_group": {g: len(group_scores.get(g, [])) for g in order},
    }


def analyze_herding_effect(
    db_path: str,
    exp_info_path: str,
    output_dir: str | None = None,
    score_type: str = "comment",
) -> dict[str, Any]:
    with open(exp_info_path) as f:
        exp_info = json.load(f)

    experiment_info = {}
    if "up_comment_id" in exp_info:
        experiment_info["up"] = exp_info["up_comment_id"]
        experiment_info["down"] = exp_info["down_comment_id"]
        experiment_info["control"] = exp_info["control_comment_id"]
    elif "up" in exp_info:
        experiment_info = exp_info
    else:
        raise ValueError("Unrecognized experiment info format")

    group_scores = collect_group_scores(db_path, experiment_info, score_type=score_type)

    output_path = None
    if output_dir:
        output_path = Path(output_dir) / "herding_effect_scores.png"

    stats_result = plot_counterfactual_scores(
        group_scores,
        output_path=output_path,
        title="Herding Effect: Score by Initial Vote Manipulation",
    )

    stats_result["group_scores"] = group_scores
    stats_result["herding_detected"] = (
        stats_result.get("means", [0, 0, 0])[2] > stats_result.get("means", [0, 0, 0])[1] > stats_result.get("means", [0, 0, 0])[0]
        if len(stats_result.get("means", [])) == 3 else False
    )

    return stats_result


def analyze_from_counterfactual_json(
    db_path: str,
    counterfactual_path: str,
    output_dir: str | None = None,
) -> dict[str, Any]:
    with open(counterfactual_path) as f:
        entries = json.load(f)

    up_posts = []
    down_posts = []
    control_posts = []

    for i, entry in enumerate(entries):
        group = entry["RC_1"]["group"]
        post_id = i + 1
        if group == "up":
            up_posts.append(post_id)
        elif group == "down":
            down_posts.append(post_id)
        else:
            control_posts.append(post_id)

    experiment_info = {"up": up_posts, "down": down_posts, "control": control_posts}
    group_scores = collect_group_scores(db_path, experiment_info, score_type="post")

    output_path = None
    if output_dir:
        output_path = Path(output_dir) / "counterfactual_post_scores.png"

    return plot_counterfactual_scores(
        group_scores,
        output_path=output_path,
        title="Counterfactual Analysis: Post Scores by Initial Manipulation",
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python counterfactual_analysis.py <db_path> <exp_info_or_counterfactual.json> [output_dir]")
        sys.exit(1)

    db_path = sys.argv[1]
    info_path = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "./output"

    if "counterfactual" in info_path:
        result = analyze_from_counterfactual_json(db_path, info_path, output_dir)
    else:
        result = analyze_herding_effect(db_path, info_path, output_dir)

    print(json.dumps({k: v for k, v in result.items() if k != "group_scores"}, indent=2))
