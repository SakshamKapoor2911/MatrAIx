# propagation_graph.py — Build and analyze information propagation graphs from simulation DBs.
# Tracks how a source post spreads through reposts over time.
# Computes: depth, scale, max breadth, structural virality — all as time series.

from __future__ import annotations

import sqlite3
from typing import Any

import networkx as nx
import pandas as pd

from environments.oasis.visualization.twitter.graph_utils import get_depth, get_subgraph_by_time, plot_graph_like_tree


class PropagationGraph:
    def __init__(self, source_post_id: int | None = None, source_content: str | None = None, db_path: str = ""):
        self.source_post_id = source_post_id
        self.source_content = source_content
        self.db_path = db_path
        self.G = nx.DiGraph()
        self.root_id = None
        self.total_depth = 0
        self.total_scale = 0
        self.total_max_breadth = 0
        self.total_structural_virality = 0.0
        self.start_timestamp = 0
        self.end_timestamp = 0

    def build_graph(self) -> bool:
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql("SELECT * FROM post", conn)
        conn.close()

        if df.empty:
            return False

        if self.source_post_id is not None:
            source_row = df[df["post_id"] == self.source_post_id]
            if source_row.empty:
                return False
            self.root_id = int(source_row.iloc[0]["user_id"])
            root_post_id = self.source_post_id
        elif self.source_content is not None:
            matches = df[df["content"].str.contains(self.source_content[:10], na=False)]
            if matches.empty:
                return False
            self.root_id = int(matches.iloc[0]["user_id"])
            root_post_id = int(matches.iloc[0]["post_id"])
        else:
            root_post_id = int(df.iloc[0]["post_id"])
            self.root_id = int(df.iloc[0]["user_id"])

        self.G.add_node(self.root_id, timestamp=0)

        reposts = df[df["original_post_id"] == root_post_id]
        for _, row in reposts.iterrows():
            user_id = int(row["user_id"])
            created_at = row["created_at"]
            try:
                timestamp = int(created_at)
            except (ValueError, TypeError):
                timestamp = 1
            if user_id not in self.G:
                self.G.add_node(user_id, timestamp=timestamp)
            self.G.add_edge(self.root_id, user_id)

        second_level = df[df["original_post_id"].isin(reposts["post_id"].tolist())]
        for _, row in second_level.iterrows():
            user_id = int(row["user_id"])
            original_id = int(row["original_post_id"])
            original_author = df[df["post_id"] == original_id]
            if original_author.empty:
                continue
            parent_user = int(original_author.iloc[0]["user_id"])
            created_at = row["created_at"]
            try:
                timestamp = int(created_at)
            except (ValueError, TypeError):
                timestamp = 2
            if user_id not in self.G:
                self.G.add_node(user_id, timestamp=timestamp)
            self.G.add_edge(parent_user, user_id)

        if self.G.number_of_nodes() < 2:
            self.total_depth = 0
            self.total_scale = 1
            self.end_timestamp = 1
            return True

        timestamps = nx.get_node_attributes(self.G, "timestamp")
        self.end_timestamp = max(timestamps.values()) + 3 if timestamps else 1
        self.total_depth = get_depth(self.G, source=self.root_id)
        self.total_scale = self.G.number_of_nodes()

        self.total_max_breadth = 0
        cumulative = [1]
        for depth in range(self.total_depth):
            breadth = len(list(nx.bfs_tree(self.G, source=self.root_id, depth_limit=depth + 1).nodes())) - sum(cumulative)
            cumulative.append(breadth)
            self.total_max_breadth = max(self.total_max_breadth, breadth)

        if nx.is_connected(self.G.to_undirected()):
            self.total_structural_virality = nx.average_shortest_path_length(self.G.to_undirected())

        return True

    def get_scale_over_time(self) -> tuple[list[int], list[int]]:
        t_list = list(range(self.start_timestamp, int(self.end_timestamp), 1))
        node_nums = []
        for t in t_list:
            sub_g = get_subgraph_by_time(self.G, time_threshold=t)
            node_nums.append(sub_g.number_of_nodes())
        return t_list, node_nums

    def get_depth_over_time(self) -> tuple[list[int], list[int]]:
        t_list = list(range(self.start_timestamp, int(self.end_timestamp), 1))
        depth_list = []
        for t in t_list:
            sub_g = get_subgraph_by_time(self.G, time_threshold=t)
            if sub_g.number_of_nodes() > 1:
                depth_list.append(get_depth(sub_g, source=self.root_id))
            else:
                depth_list.append(0)
        return t_list, depth_list

    def get_max_breadth_over_time(self) -> tuple[list[int], list[int]]:
        t_list = list(range(self.start_timestamp, int(self.end_timestamp), 1))
        breadth_list = []
        for t in t_list:
            sub_g = get_subgraph_by_time(self.G, time_threshold=t)
            max_b = 0
            if sub_g.number_of_nodes() > 1:
                depth = get_depth(sub_g, source=self.root_id)
                cumulative = [1]
                for d in range(depth):
                    b = len(list(nx.bfs_tree(sub_g, source=self.root_id, depth_limit=d + 1).nodes())) - sum(cumulative)
                    cumulative.append(b)
                    max_b = max(max_b, b)
            breadth_list.append(max_b)
        return t_list, breadth_list

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_depth": self.total_depth,
            "total_scale": self.total_scale,
            "total_max_breadth": self.total_max_breadth,
            "total_structural_virality": self.total_structural_virality,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "num_nodes": self.G.number_of_nodes(),
            "num_edges": self.G.number_of_edges(),
        }

    def visualize(self, output_path: str | None = None, show: bool = False):
        if self.root_id is not None and self.G.number_of_nodes() > 1:
            plot_graph_like_tree(self.G, self.root_id, output_path=output_path, show=show)
