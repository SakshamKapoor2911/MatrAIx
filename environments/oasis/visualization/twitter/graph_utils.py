# graph_utils.py — Utility functions for propagation graph analysis.
# Provides depth calculation, time-filtered subgraphs, and tree-layout visualization.

from __future__ import annotations

import matplotlib.pyplot as plt
import networkx as nx


def get_depth(G: nx.Graph, source=0) -> int:
    dfs_tree = nx.dfs_tree(G, source=source)
    max_depth = max(nx.single_source_shortest_path_length(dfs_tree, source=source).values())
    return max_depth


def get_subgraph_by_time(G: nx.Graph, time_threshold: int = 10) -> nx.DiGraph:
    filtered_nodes = []
    for node, attr in G.nodes(data=True):
        if attr.get("timestamp", 0) <= time_threshold:
            filtered_nodes.append(node)
    return G.subgraph(filtered_nodes).copy()


def hierarchy_pos(G, root=None, width=1.0, vert_gap=0.2, vert_loc=0, xcenter=0.5):
    pos = _hierarchy_pos(G, root, width, vert_gap, vert_loc, xcenter)
    return pos


def _hierarchy_pos(G, root, width=1.0, vert_gap=0.2, vert_loc=0, xcenter=0.5, pos=None, parent=None, parsed=None):
    if pos is None:
        pos = {root: (xcenter, vert_loc)}
    else:
        pos[root] = (xcenter, vert_loc)

    if parsed is None:
        parsed = {root}
    else:
        parsed.add(root)

    neighbors = list(G.neighbors(root))
    if not isinstance(G, nx.DiGraph) and parent is not None:
        neighbors.remove(parent)

    if len(neighbors) != 0:
        dx = width / len(neighbors)
        nextx = xcenter - width / 2 - dx / 2
        for neighbor in neighbors:
            nextx += dx
            pos = _hierarchy_pos(G, neighbor, width=dx, vert_gap=vert_gap, vert_loc=vert_loc - vert_gap, xcenter=nextx, pos=pos, parent=root, parsed=parsed)
    return pos


def plot_graph_like_tree(G: nx.DiGraph, root, output_path: str | None = None, show: bool = False):
    pos = hierarchy_pos(G, root)
    plt.figure(figsize=(12, 8))
    nx.draw(G, pos, with_labels=True, node_size=3000, node_color="lightblue", font_size=10, font_weight="bold", arrows=True)
    plt.title("Repost Propagation Tree")
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    plt.close()
