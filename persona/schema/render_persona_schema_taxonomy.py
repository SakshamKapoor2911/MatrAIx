#!/usr/bin/env python3
"""Render a clean taxonomy tree of the Persona schema for the paper appendix.

This is a three-level horizontal bracket tree, aligned to the count-validated
three-layer taxonomy in ``persona/schema/matraix_persona_taxonomy_3layer_1290.md``
(PR #221):

- **Group** (5 Layer-1 groups: Background, Psychology, Capability, Behavior and
  Interaction, Lifestyle and Health).
- **Subgroup** (16 Layer-2 groups).
- **Category** (55 Layer-3 groups, with attribute counts).

The grouping is the conceptual taxonomy, not the DAG edges. Three schema
categories are split at the attribute level (``Expertise: Domains`` into 12
groups, ``Interests: Culture`` into 2, ``State: Emotional`` into 2); their
Layer-3 counts are taken verbatim from the validated taxonomy. Totals sum to
1290 attributes across 43 schema categories.

Run from the repository root:

    uv run --extra viz python persona/schema/render_persona_schema_taxonomy.py

Writes ``persona_schema_taxonomy.png`` and ``persona_schema_taxonomy.pdf`` into
``persona/schema/``.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.font_manager
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.path import Path as MplPath

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPH_PATH = REPO_ROOT / "persona" / "synthesis" / "graph" / "full_dag.json"
DEFAULT_OUT_DIR = REPO_ROOT / "persona" / "schema"

# OFFICIAL three-layer taxonomy (Layer 1 -> Layer 2 -> Layer 3), aligned to
# persona/schema/matraix_persona_taxonomy_3layer_1290.md (PR #221, count
# validated: 5 Layer-1 groups, 16 Layer-2 groups, 55 Layer-3 groups, 1290
# attributes).
#
# Each Layer-1 group is (name, colour, [layer2, ...]);
# each Layer-2 group is (name, [(layer3 name, source), ...]).
# ``source`` is either a schema-category key (str) whose count is read from the
# graph, or an explicit int count for the three attribute-level splits
# (Expertise: Domains, Interests: Culture, State: Emotional) and the combined
# Health group. Explicit counts are taken verbatim from the validated taxonomy.
GROUPS = [
    ("Background", "#4C72B0", [
        ("Demographics", [
            ("Core Demographics", "Demographic: Core"),
            ("Family", "Demographic: Family"),
            ("Cultural Background", "Demographic: Cultural"),
            ("Life Events", "Demographic: Life Events"),
        ]),
        ("Language", [
            ("Language Profile", "Linguistic: Language"),
            ("Communication", "Linguistic: Communication"),
        ]),
        ("Education", [
            ("Academic Background", "Learning: Academic"),
            ("Learning Style", "Learning: Style"),
        ]),
        ("Career", [
            ("Career Profile", "Professional: Career"),
            ("Industry", "Professional: Industry"),
            ("Developer Professional Context", "Developer: Professional Context"),
        ]),
    ]),
    ("Psychology", "#8172B3", [
        ("Personality", [
            ("Character", "Personality: Character"),
            ("Big Five", "Personality: Big Five"),
            ("MBTI", "Personality: MBTI"),
            ("Relationships", "Personality: Relationships"),
        ]),
        ("Worldview", [
            ("Values & Motivation", "Values & Motivation"),
            ("Beliefs", "Worldview: Beliefs"),
        ]),
        ("Decision-Making", [
            ("Risk & Decision", "Risk & Decision"),
        ]),
    ]),
    ("Capability", "#DD8452", [
        # Expertise: Domains (144) split at attribute level into 12 Layer-3
        # groups; counts verbatim from the validated taxonomy (PR #221).
        ("Domains", [
            ("Cross-Domain Expertise Profile", 4),
            ("Computing, Data & AI", 18),
            ("Engineering, Energy & Infrastructure", 16),
            ("Medicine, Health & Life Sciences", 17),
            ("Natural & Environmental Sciences", 17),
            ("Law, Economics & Finance", 17),
            ("Social Sciences & Public Affairs", 7),
            ("Humanities & Cultural Studies", 10),
            ("Education & Human Services", 7),
            ("Arts, Design & Media", 17),
            ("Business, Management & Marketing", 11),
            ("Hospitality & Culinary", 3),
        ]),
        ("Skills", [
            ("General Skills", "Expertise: Skills"),
            ("Tools", "Skills: Tools"),
            ("Programming", "Skills: Programming"),
            ("Developer Code Maintenance", "Developer: Code Maintenance"),
        ]),
    ]),
    ("Behavior and Interaction", "#C44E52", [
        ("Personal Behavior", [
            ("Preferences", "Behavior: Preferences"),
            ("Habits", "Behavior: Habits"),
            ("Time Use", "Behavior: Time"),
        ]),
        # State: Emotional (5) split at attribute level into 2 Layer-3 groups.
        ("Interaction State", [
            ("Current Emotional State", 1),
            ("Task & Interaction Context", 4),
        ]),
        ("Work Practices", [
            ("General Work Practices", "Behavior: Work"),
            ("Developer Open Source Behavior", "Developer: Open Source Behavior"),
            ("Developer Community Behavior", "Developer: Community Behavior"),
        ]),
        ("Technology Use", [
            ("Developer AI Tool Adoption", "Developer: AI Adoption"),
            ("Developer AI Workflow Tasks", "Developer: AI Workflow Tasks"),
            ("Developer Coding Agent Adoption", "Developer: Agent Adoption"),
            ("Developer Technology Evaluation", "Developer: Technology Evaluation"),
        ]),
    ]),
    ("Lifestyle and Health", "#55A868", [
        ("Interests", [
            ("Broad Interest Areas", "Interests: Topics"),
            ("Media", "Interests: Media"),
            ("Hobbies", "Interests: Hobbies"),
            ("Sports", "Interests: Sports"),
            ("Food", "Interests: Food"),
        ]),
        # Interests: Culture (74) split by ID prefix into 2 Layer-3 groups.
        ("Culture and Daily Life", [
            ("Cultural Familiarity", 40),
            ("Lifestyle Patterns", 34),
        ]),
        # Health: Physical (25); Health: Fitness (2) + Health: Lifestyle (2) = 4.
        ("Health", [
            ("Health Status & Accessibility", "Health: Physical"),
            ("Health Orientation & Behaviors", 4),
        ]),
    ]),
]

TEXT_COLOR = "#000000"


def _display_path(path: Path) -> str:
    """Show a repo-relative path when possible, else the absolute path."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def _lighten(hex_color: str, factor: float) -> tuple[float, float, float]:
    r, g, b = mcolors.to_rgb(hex_color)
    return (r + (1 - r) * factor, g + (1 - g) * factor, b + (1 - b) * factor)


def _wrap(text: str, width: int) -> str:
    """Greedy word wrap so long names fit inside a box on multiple lines."""
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return "\n".join(lines)


def _wrap_with_count(name: str, count: int, width: int) -> str:
    """Wrap the name, then glue the count to the last line so it never wraps
    onto a line of its own."""
    wrapped = _wrap(name, width)
    lines = wrapped.split("\n")
    lines[-1] = f"{lines[-1]}  ({count})"
    return "\n".join(lines)


def render(graph_path: Path, out_dir: Path) -> None:
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    counts = collections.Counter(n.get("category") for n in graph["nodes"])

    # Register the bundled Inter font (falls back gracefully if unavailable).
    font_family = "DejaVu Sans"
    inter_path = Path(__file__).resolve().parent / "_fonts" / "Inter-Variable.ttf"
    if inter_path.exists():
        try:
            matplotlib.font_manager.fontManager.addfont(str(inter_path))
            font_family = matplotlib.font_manager.FontProperties(
                fname=str(inter_path)).get_name()
        except Exception:
            pass

    plt.rcParams.update({
        "font.family": font_family,
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    # Vertical layout: leaves top-to-bottom, spacing adapts to label lines and
    # a small gap between groups.
    group_gap = 0.8
    leaf_h = 0.72
    y_leaf: list[float] = []
    leaf_meta: list[tuple[str, int, str]] = []            # (display, count, colour)
    aspect_spans: list[tuple[str, str, list[int]]] = []   # (aspect, colour, leaf idxs)
    group_spans: list[tuple[str, str, int, list[int]]] = []  # (group, colour, total, aspect idxs)

    cursor = 0.0
    leaf_i = 0
    for group_name, color, aspects in GROUPS:
        group_total = 0
        aspect_idxs: list[int] = []
        for aspect_name, cats in aspects:
            idxs: list[int] = []
            for disp, key in cats:
                count = key if isinstance(key, int) else counts[key]
                group_total += count
                # Advance the cursor adaptively so multi-line leaf labels get
                # enough vertical room and never overlap. Must match the leaf
                # box height used when drawing (0.62 per line + 0.34) plus a gap.
                n_lines = _wrap_with_count(disp, count, 45).count("\n") + 1
                box_h = max(leaf_h, n_lines * 0.62 + 0.34)
                slot = box_h + 0.30
                cursor -= slot / 2.0
                y_leaf.append(cursor)
                cursor -= slot / 2.0
                leaf_meta.append((disp, count, color))
                idxs.append(leaf_i)
                leaf_i += 1
            aspect_idxs.append(len(aspect_spans))
            aspect_spans.append((aspect_name, color, idxs))
        group_spans.append((group_name, color, group_total, aspect_idxs))
        cursor -= group_gap

    shift = min(y_leaf)
    y_leaf = [y - shift for y in y_leaf]
    span = max(y_leaf)

    fig, ax = plt.subplots(figsize=(18.5, 0.34 * (span + 2) + 1.0))
    ax.axis("off")

    x_group, w_group = 0.0, 7.4
    x_aspect, w_aspect = 7.8, 5.2
    x_leaf, w_leaf = 13.3, 12.0

    def draw_box(x, y, w, h, text, face, edge, size, txt_color=TEXT_COLOR, weight="normal"):
        ax.add_patch(FancyBboxPatch(
            (x, y - h / 2), w, h,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            linewidth=1.0, edgecolor=edge, facecolor=face, zorder=3))
        ax.text(x + w / 2, y, text, ha="center", va="center", fontsize=size,
                color=txt_color, fontweight=weight, zorder=4)

    def connect(x0, y0, x1, y1, color):
        xm = (x0 + x1) / 2
        ax.add_patch(mpatches.PathPatch(MplPath(
            [(x0, y0), (xm, y0), (xm, y1), (x1, y1)],
            [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4]),
            fill=False, edgecolor=color, lw=1.0, alpha=0.55, zorder=1))

    # Category boxes (Layer 3 leaves); count stays glued to the last line.
    for i, (disp, count, color) in enumerate(leaf_meta):
        label = _wrap_with_count(disp, count, 45)
        n_lines = label.count("\n") + 1
        box_h = max(leaf_h, n_lines * 0.62 + 0.34)
        draw_box(x_leaf, y_leaf[i], w_leaf, box_h, label,
                 _lighten(color, 0.80), color, size=12.0)

    # Subgroup boxes (mid) at the mean y of their leaves, with brackets to leaves.
    aspect_y: list[float] = []
    for aspect_name, color, idxs in aspect_spans:
        y_mid = float(np.mean([y_leaf[i] for i in idxs]))
        aspect_y.append(y_mid)
        draw_box(x_aspect, y_mid, w_aspect, 0.72 + 0.40, aspect_name,
                 _lighten(color, 0.58), color, size=15.0)
        for i in idxs:
            connect(x_aspect + w_aspect, y_mid, x_leaf, y_leaf[i], color)

    # Group boxes at the mean y of their subgroups, with brackets to subgroups.
    for group_name, color, total, aspect_idxs in group_spans:
        y_mid = float(np.mean([aspect_y[a] for a in aspect_idxs]))
        label = f"{group_name}  ({total})"
        draw_box(x_group, y_mid, w_group, 0.80 + 0.50, label,
                 _lighten(color, 0.52), color, size=17.0,
                 txt_color="#000000")
        for a in aspect_idxs:
            connect(x_group + w_group, y_mid, x_aspect, aspect_y[a], color)

    # Column headers.
    top = span + 1.3
    ax.text(x_group + w_group / 2, top, "Group  (# attributes)",
            ha="center", va="center", fontsize=14.0, color=TEXT_COLOR)
    ax.text(x_aspect + w_aspect / 2, top, "Subgroup",
            ha="center", va="center", fontsize=14.0, color=TEXT_COLOR)
    ax.text(x_leaf + w_leaf / 2, top, "Category  (# attributes)",
            ha="center", va="center", fontsize=14.0, color=TEXT_COLOR)

    ax.set_xlim(-0.4, x_leaf + w_leaf + 0.4)
    ax.set_ylim(-1.0, top + 1.0)

    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "persona_schema_taxonomy.png"
    pdf_path = out_dir / "persona_schema_taxonomy.pdf"
    fig.savefig(png_path, dpi=300, facecolor="white")
    fig.savefig(pdf_path, facecolor="white")
    plt.close(fig)
    grand_total = sum(total for _n, _c, total, _a in group_spans)
    print(
        f"wrote {_display_path(png_path)} and {_display_path(pdf_path)} | "
        f"groups={len(GROUPS)} subgroups={len(aspect_spans)} "
        f"categories={len(leaf_meta)} attributes={grand_total} (expect 1290)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    render(args.graph, args.out_dir)


if __name__ == "__main__":
    main()
