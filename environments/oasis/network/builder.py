# network_builder.py — Construct social follow graphs for OASIS simulation from MatrAIx personas.
# Implements topic-based affinity clustering, influencer seeding (Barabasi-Albert inspired),
# cross-topic bridge edges, and optional seed post generation.
# Graph topology mirrors OASIS's generator/twitter/network.py approach: topic-star nodes with
# probabilistic following weighted by interest overlap, extraversion, and region proximity.

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from typing import Any

from environments.oasis.persona_loader.adapter import OasisUserInfo


INTEREST_AFFINITY_WEIGHT = 0.40
DOMAIN_AFFINITY_WEIGHT = 0.25
REGION_AFFINITY_WEIGHT = 0.15
PERSONALITY_AFFINITY_WEIGHT = 0.20

INTEREST_LEVEL_SCORES = {
    "Passionate": 1.0,
    "Interested": 0.7,
    "Neutral": 0.3,
    "Indifferent": 0.1,
    "Averse": 0.0,
}

EXTRAVERSION_FOLLOW_MULTIPLIER = {
    0.15: 0.4,
    0.30: 0.6,
    0.50: 1.0,
    0.70: 1.4,
    0.85: 2.0,
}

OPENNESS_CROSS_TOPIC_MULTIPLIER = {
    0.15: 0.3,
    0.30: 0.5,
    0.50: 1.0,
    0.70: 1.5,
    0.85: 2.0,
}


@dataclass
class NetworkConfig:
    min_following: int = 3
    max_following: int = 30
    influencer_percentile: float = 0.90
    influencer_boost_factor: float = 5.0
    cross_topic_base_probability: float = 0.08
    cross_topic_max_edges: int = 5
    seed_posts_per_influencer: int = 2
    reciprocal_follow_probability: float = 0.15
    random_seed: int | None = 42


@dataclass
class FollowEdge:
    follower_idx: int
    followee_idx: int
    weight: float = 1.0


@dataclass
class SeedPost:
    author_idx: int
    content: str
    topic: str


@dataclass
class SocialGraph:
    num_agents: int
    edges: list[FollowEdge]
    influencer_indices: list[int]
    seed_posts: list[SeedPost]
    topic_clusters: dict[str, list[int]]

    @property
    def num_edges(self) -> int:
        return len(self.edges)

    @property
    def avg_following(self) -> float:
        if self.num_agents == 0:
            return 0.0
        return self.num_edges / self.num_agents

    def followers_of(self, agent_idx: int) -> list[int]:
        return [e.follower_idx for e in self.edges if e.followee_idx == agent_idx]

    def following_of(self, agent_idx: int) -> list[int]:
        return [e.followee_idx for e in self.edges if e.follower_idx == agent_idx]

    def to_adjacency_list(self) -> dict[int, list[int]]:
        adj: dict[int, list[int]] = {i: [] for i in range(self.num_agents)}
        for edge in self.edges:
            adj[edge.follower_idx].append(edge.followee_idx)
        return adj

    def to_edge_list_csv(self) -> str:
        lines = ["follower_id,followee_id"]
        for edge in self.edges:
            lines.append(f"{edge.follower_idx},{edge.followee_idx}")
        return "\n".join(lines)


def _deterministic_seed(persona_id: str, salt: str = "") -> int:
    h = hashlib.md5(f"{persona_id}{salt}".encode()).hexdigest()
    return int(h[:8], 16)


def _get_extraversion_multiplier(big5_extraversion: float) -> float:
    closest = min(EXTRAVERSION_FOLLOW_MULTIPLIER.keys(), key=lambda k: abs(k - big5_extraversion))
    return EXTRAVERSION_FOLLOW_MULTIPLIER[closest]


def _get_openness_multiplier(big5_openness: float) -> float:
    closest = min(OPENNESS_CROSS_TOPIC_MULTIPLIER.keys(), key=lambda k: abs(k - big5_openness))
    return OPENNESS_CROSS_TOPIC_MULTIPLIER[closest]


def _extract_interest_vector(persona: OasisUserInfo) -> dict[str, float]:
    interests = {}
    dims = persona.raw_dimensions
    for key, value in dims.items():
        if key.startswith("topic_"):
            score = INTEREST_LEVEL_SCORES.get(value, 0.3)
            if score > 0.0:
                interests[key] = score
    if not interests:
        for topic in persona.interested_topics:
            interests[f"topic_{topic.lower().replace(' ', '_')}"] = 0.8
    return interests


def _compute_interest_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    all_keys = set(vec_a.keys()) | set(vec_b.keys())
    if not all_keys:
        return 0.0
    dot = sum(vec_a.get(k, 0.0) * vec_b.get(k, 0.0) for k in all_keys)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def _compute_domain_similarity(a: OasisUserInfo, b: OasisUserInfo) -> float:
    if a.profession == b.profession:
        return 1.0
    topics_a = set(a.interested_topics)
    topics_b = set(b.interested_topics)
    overlap = len(topics_a & topics_b)
    total = len(topics_a | topics_b)
    return overlap / total if total > 0 else 0.0


def _compute_region_similarity(a: OasisUserInfo, b: OasisUserInfo) -> float:
    if a.country == b.country:
        return 1.0
    dims_a = a.raw_dimensions
    dims_b = b.raw_dimensions
    if dims_a.get("region") == dims_b.get("region"):
        return 0.6
    return 0.0


def _compute_personality_similarity(a: OasisUserInfo, b: OasisUserInfo) -> float:
    diff_sum = 0.0
    for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
        diff_sum += abs(a.big_five.get(trait, 0.5) - b.big_five.get(trait, 0.5))
    max_diff = 5.0 * 0.70
    return 1.0 - (diff_sum / max_diff)


def compute_affinity(a: OasisUserInfo, b: OasisUserInfo) -> float:
    interest_sim = _compute_interest_similarity(
        _extract_interest_vector(a), _extract_interest_vector(b)
    )
    domain_sim = _compute_domain_similarity(a, b)
    region_sim = _compute_region_similarity(a, b)
    personality_sim = _compute_personality_similarity(a, b)

    score = (
        INTEREST_AFFINITY_WEIGHT * interest_sim
        + DOMAIN_AFFINITY_WEIGHT * domain_sim
        + REGION_AFFINITY_WEIGHT * region_sim
        + PERSONALITY_AFFINITY_WEIGHT * personality_sim
    )
    return min(max(score, 0.0), 1.0)


def _identify_influencers(personas: list[OasisUserInfo], percentile: float) -> list[int]:
    scores = []
    for i, p in enumerate(personas):
        extraversion = p.big_five.get("extraversion", 0.5)
        conscientiousness = p.big_five.get("conscientiousness", 0.5)
        openness = p.big_five.get("openness", 0.5)
        influence_score = 0.5 * extraversion + 0.3 * conscientiousness + 0.2 * openness
        scores.append((i, influence_score))

    scores.sort(key=lambda x: x[1], reverse=True)
    cutoff = max(1, int(len(scores) * (1.0 - percentile)))
    return [idx for idx, _ in scores[:cutoff]]


def _cluster_by_topic(personas: list[OasisUserInfo]) -> dict[str, list[int]]:
    clusters: dict[str, list[int]] = {}
    for i, p in enumerate(personas):
        primary_topic = p.interested_topics[0] if p.interested_topics else "General"
        if primary_topic not in clusters:
            clusters[primary_topic] = []
        clusters[primary_topic].append(i)
    return clusters


def _compute_follow_budget(persona: OasisUserInfo, config: NetworkConfig) -> int:
    extraversion_mult = _get_extraversion_multiplier(persona.big_five.get("extraversion", 0.5))
    base = (config.min_following + config.max_following) / 2.0
    budget = int(base * extraversion_mult)
    return max(config.min_following, min(budget, config.max_following))


def _generate_seed_post_content(persona: OasisUserInfo, topic: str) -> str:
    name = persona.name
    domain = persona.profession
    intent = persona.raw_dimensions.get("intent", "share ideas")
    emotional_state = persona.raw_dimensions.get("emotional_state", "thoughtful")

    templates = [
        f"Thoughts on {topic.lower()} from someone in {domain.lower()}: the industry is shifting in ways that align with my goal to {intent}.",
        f"As a {domain.lower()} professional, I've been {emotional_state.lower()} about recent developments in {topic.lower()}. What does everyone think?",
        f"Interesting patterns emerging in {topic.lower()}. From my perspective in {domain.lower()}, this could change how we approach things.",
    ]

    seed = _deterministic_seed(persona.persona_id, topic)
    return templates[seed % len(templates)]


def build_social_graph(
    personas: list[OasisUserInfo],
    config: NetworkConfig | None = None,
) -> SocialGraph:
    if config is None:
        config = NetworkConfig()

    rng = random.Random(config.random_seed)

    if len(personas) < 2:
        return SocialGraph(
            num_agents=len(personas),
            edges=[],
            influencer_indices=[],
            seed_posts=[],
            topic_clusters={},
        )

    influencer_indices = _identify_influencers(personas, config.influencer_percentile)
    topic_clusters = _cluster_by_topic(personas)
    interest_vectors = [_extract_interest_vector(p) for p in personas]

    edges: list[FollowEdge] = []
    edge_set: set[tuple[int, int]] = set()

    for i, persona in enumerate(personas):
        follow_budget = _compute_follow_budget(persona, config)

        candidates_with_scores: list[tuple[int, float]] = []

        for j, other in enumerate(personas):
            if i == j:
                continue
            if (i, j) in edge_set:
                continue

            affinity = compute_affinity(persona, other)

            if j in influencer_indices:
                affinity = min(affinity * config.influencer_boost_factor, 1.0)

            if affinity > 0.05:
                candidates_with_scores.append((j, affinity))

        candidates_with_scores.sort(key=lambda x: x[1], reverse=True)

        selected_count = 0
        for candidate_idx, affinity in candidates_with_scores:
            if selected_count >= follow_budget:
                break

            follow_probability = affinity
            if rng.random() < follow_probability:
                edges.append(FollowEdge(follower_idx=i, followee_idx=candidate_idx, weight=affinity))
                edge_set.add((i, candidate_idx))
                selected_count += 1

                if (candidate_idx, i) not in edge_set:
                    if rng.random() < config.reciprocal_follow_probability:
                        edges.append(FollowEdge(follower_idx=candidate_idx, followee_idx=i, weight=affinity * 0.8))
                        edge_set.add((candidate_idx, i))

    openness_values = [p.big_five.get("openness", 0.5) for p in personas]
    for i, persona in enumerate(personas):
        cross_prob = config.cross_topic_base_probability * _get_openness_multiplier(persona.big_five.get("openness", 0.5))
        primary_topic = persona.interested_topics[0] if persona.interested_topics else "General"

        cross_count = 0
        other_clusters = [
            idx for topic, indices in topic_clusters.items()
            if topic != primary_topic for idx in indices
        ]
        rng.shuffle(other_clusters)

        for j in other_clusters:
            if cross_count >= config.cross_topic_max_edges:
                break
            if i == j or (i, j) in edge_set:
                continue
            if rng.random() < cross_prob:
                affinity = compute_affinity(persona, personas[j])
                edges.append(FollowEdge(follower_idx=i, followee_idx=j, weight=affinity))
                edge_set.add((i, j))
                cross_count += 1

    seed_posts: list[SeedPost] = []
    for inf_idx in influencer_indices:
        inf_persona = personas[inf_idx]
        topics = inf_persona.interested_topics
        for t_idx in range(min(config.seed_posts_per_influencer, len(topics))):
            topic = topics[t_idx % len(topics)]
            content = _generate_seed_post_content(inf_persona, topic)
            seed_posts.append(SeedPost(author_idx=inf_idx, content=content, topic=topic))

    return SocialGraph(
        num_agents=len(personas),
        edges=edges,
        influencer_indices=influencer_indices,
        seed_posts=seed_posts,
        topic_clusters=topic_clusters,
    )


def graph_stats(graph: SocialGraph) -> dict[str, Any]:
    follower_counts = [0] * graph.num_agents
    following_counts = [0] * graph.num_agents

    for edge in graph.edges:
        following_counts[edge.follower_idx] += 1
        follower_counts[edge.followee_idx] += 1

    return {
        "num_agents": graph.num_agents,
        "num_edges": graph.num_edges,
        "avg_following": graph.avg_following,
        "avg_followers": graph.num_edges / graph.num_agents if graph.num_agents > 0 else 0,
        "max_followers": max(follower_counts) if follower_counts else 0,
        "max_following": max(following_counts) if following_counts else 0,
        "min_followers": min(follower_counts) if follower_counts else 0,
        "min_following": min(following_counts) if following_counts else 0,
        "num_influencers": len(graph.influencer_indices),
        "num_seed_posts": len(graph.seed_posts),
        "num_topic_clusters": len(graph.topic_clusters),
        "topic_cluster_sizes": {k: len(v) for k, v in graph.topic_clusters.items()},
    }


def build_oasis_follow_data(
    graph: SocialGraph, personas: list[OasisUserInfo]
) -> list[dict[str, Any]]:
    adj = graph.to_adjacency_list()
    result = []
    for i, persona in enumerate(personas):
        result.append({
            "agent_id": i,
            "persona_id": persona.persona_id,
            "user_name": persona.user_name,
            "following_agentid_list": adj[i],
        })
    return result


def build_simple_topic_graph(
    personas: list[OasisUserInfo],
    follow_probability: float = 0.2,
    random_seed: int | None = 42,
) -> SocialGraph:
    rng = random.Random(random_seed)

    if len(personas) < 2:
        return SocialGraph(
            num_agents=len(personas), edges=[], influencer_indices=[],
            seed_posts=[], topic_clusters={},
        )

    influencer_indices = _identify_influencers(personas, percentile=0.90)
    topic_clusters = _cluster_by_topic(personas)

    edges: list[FollowEdge] = []
    edge_set: set[tuple[int, int]] = set()

    for i, persona in enumerate(personas):
        persona_topics = set(persona.interested_topics)

        for inf_idx in influencer_indices:
            if inf_idx == i:
                continue
            inf_topics = set(personas[inf_idx].interested_topics)
            if persona_topics & inf_topics:
                if rng.random() <= follow_probability:
                    if (i, inf_idx) not in edge_set:
                        edges.append(FollowEdge(follower_idx=i, followee_idx=inf_idx))
                        edge_set.add((i, inf_idx))

    seed_posts: list[SeedPost] = []
    for inf_idx in influencer_indices:
        inf_persona = personas[inf_idx]
        topics = inf_persona.interested_topics
        if topics:
            content = _generate_seed_post_content(inf_persona, topics[0])
            seed_posts.append(SeedPost(author_idx=inf_idx, content=content, topic=topics[0]))

    return SocialGraph(
        num_agents=len(personas),
        edges=edges,
        influencer_indices=influencer_indices,
        seed_posts=seed_posts,
        topic_clusters=topic_clusters,
    )
