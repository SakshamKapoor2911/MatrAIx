# network.py — Social network generation matching OASIS's two approaches.
# 1. Topic-based: users follow "star" accounts by topic with flat probability (OASIS network.py)
# 2. Random: Barabasi-Albert-style random directed edges (OASIS ba.py)

from __future__ import annotations

import random
from typing import Any


def generate_topic_network(
    profiles: list[dict[str, Any]],
    star_indices: list[int] | None = None,
    star_topics: dict[int, list[str]] | None = None,
    follow_probability: float = 0.2,
    seed: int | None = 42,
) -> list[list[int]]:
    if seed is not None:
        random.seed(seed)

    n = len(profiles)
    if star_indices is None:
        star_indices = list(range(min(20, n // 5)))

    if star_topics is None:
        star_topics = {}
        for idx in star_indices:
            topics = profiles[idx].get("topics") or profiles[idx].get("interested_topics") or []
            star_topics[idx] = topics

    following_lists: list[list[int]] = [[] for _ in range(n)]

    for i, profile in enumerate(profiles):
        if i in star_indices:
            continue

        user_topics = set(profile.get("topics") or profile.get("interested_topics") or [])

        for star_idx in star_indices:
            if star_idx == i:
                continue
            star_topic_set = set(star_topics[star_idx])
            if user_topics & star_topic_set:
                if random.random() <= follow_probability:
                    following_lists[i].append(star_idx)

    return following_lists


def generate_random_network(
    n: int,
    num_edges: int = 7000,
    seed: int | None = 42,
) -> list[list[int]]:
    if seed is not None:
        random.seed(seed)

    edges: set[tuple[int, int]] = set()
    while len(edges) < num_edges:
        follower = random.randint(0, n - 1)
        followee = random.randint(0, n - 1)
        if follower != followee:
            edges.add((follower, followee))

    following_lists: list[list[int]] = [[] for _ in range(n)]
    for follower, followee in edges:
        following_lists[follower].append(followee)

    return following_lists
