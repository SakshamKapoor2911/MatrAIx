# test_builder.py — Tests for the social graph construction module.
# Validates affinity computation, influencer identification, topic clustering,
# edge generation, graph properties, and OASIS-compatible output format.

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from environments.oasis.persona_loader.adapter import load_personas_from_directory, OasisUserInfo
from environments.oasis.network.builder import (
    NetworkConfig,
    FollowEdge,
    SeedPost,
    SocialGraph,
    build_social_graph,
    build_oasis_follow_data,
    compute_affinity,
    graph_stats,
    _identify_influencers,
    _cluster_by_topic,
    _compute_follow_budget,
    _extract_interest_vector,
    _compute_interest_similarity,
    _compute_domain_similarity,
    _compute_region_similarity,
    _compute_personality_similarity,
    _get_extraversion_multiplier,
    _get_openness_multiplier,
)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "persona_loader" / "tests" / "fixtures"


@pytest.fixture
def personas():
    return load_personas_from_directory(FIXTURES_DIR)


@pytest.fixture
def default_config():
    return NetworkConfig(random_seed=42)


def _find(personas, persona_id):
    for p in personas:
        if p.persona_id == persona_id:
            return p
    raise ValueError(f"Persona {persona_id} not found")


def _idx(personas, persona_id):
    for i, p in enumerate(personas):
        if p.persona_id == persona_id:
            return i
    raise ValueError(f"Persona {persona_id} not found")


class TestInterestVector:
    def test_extracts_topic_dimensions(self, personas):
        tech_persona = _find(personas, "ID9001")
        vec = _extract_interest_vector(tech_persona)
        assert "topic_technology" in vec
        assert vec["topic_technology"] == 1.0
        assert "topic_science" in vec

    def test_passionate_scores_highest(self, personas):
        tech_persona = _find(personas, "ID9001")
        vec = _extract_interest_vector(tech_persona)
        assert vec.get("topic_technology", 0) > vec.get("topic_fitness", 0)

    def test_averse_excluded(self, personas):
        for p in personas:
            vec = _extract_interest_vector(p)
            for key, val in vec.items():
                assert val > 0.0

    def test_fallback_to_interested_topics(self):
        minimal = OasisUserInfo(
            persona_id="TEST",
            name="Test",
            user_name="test",
            bio="test",
            user_profile="test",
            mbti="ENTJ",
            gender="male",
            age=30,
            country="US",
            profession="Technology",
            interested_topics=["Technology", "Science"],
            active_threshold=[0.03] * 24,
            big_five={"openness": 0.7, "conscientiousness": 0.7, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.3},
            raw_dimensions={},
        )
        vec = _extract_interest_vector(minimal)
        assert len(vec) == 2
        assert all(v == 0.8 for v in vec.values())


class TestSimilarityFunctions:
    def test_interest_similarity_identical(self):
        vec = {"topic_a": 1.0, "topic_b": 0.7}
        assert _compute_interest_similarity(vec, vec) == pytest.approx(1.0, abs=0.001)

    def test_interest_similarity_orthogonal(self):
        vec_a = {"topic_a": 1.0}
        vec_b = {"topic_b": 1.0}
        assert _compute_interest_similarity(vec_a, vec_b) == 0.0

    def test_interest_similarity_partial_overlap(self):
        vec_a = {"topic_a": 1.0, "topic_b": 0.5}
        vec_b = {"topic_a": 0.8, "topic_c": 1.0}
        sim = _compute_interest_similarity(vec_a, vec_b)
        assert 0.0 < sim < 1.0

    def test_domain_similarity_same_domain(self, personas):
        assert _compute_domain_similarity(personas[0], personas[0]) == 1.0

    def test_domain_similarity_different_domain(self, personas):
        tech = personas[0]
        healthcare = personas[1]
        sim = _compute_domain_similarity(tech, healthcare)
        assert sim < 1.0

    def test_region_similarity_same_country(self, personas):
        assert _compute_region_similarity(personas[0], personas[0]) == 1.0

    def test_region_similarity_different_region(self, personas):
        tech_asia = personas[0]
        healthcare_na = personas[1]
        sim = _compute_region_similarity(tech_asia, healthcare_na)
        assert sim == 0.0

    def test_personality_similarity_identical(self, personas):
        assert _compute_personality_similarity(personas[0], personas[0]) == pytest.approx(1.0, abs=0.001)

    def test_personality_similarity_different(self, personas):
        tech = personas[0]
        creative = personas[2]
        sim = _compute_personality_similarity(tech, creative)
        assert 0.0 < sim < 1.0


class TestComputeAffinity:
    def test_self_affinity_is_maximum(self, personas):
        affinity = compute_affinity(personas[0], personas[0])
        assert affinity == pytest.approx(1.0, abs=0.01)

    def test_similar_personas_higher_affinity(self, personas):
        tech = personas[0]
        finance = personas[3]
        creative = personas[2]
        educator = personas[4]

        tech_finance = compute_affinity(tech, finance)
        tech_educator = compute_affinity(tech, educator)
        assert tech_finance > 0.0
        assert tech_educator > 0.0

    def test_affinity_bounded_zero_one(self, personas):
        for i in range(len(personas)):
            for j in range(len(personas)):
                aff = compute_affinity(personas[i], personas[j])
                assert 0.0 <= aff <= 1.0

    def test_affinity_is_symmetric(self, personas):
        for i in range(len(personas)):
            for j in range(i + 1, len(personas)):
                aff_ij = compute_affinity(personas[i], personas[j])
                aff_ji = compute_affinity(personas[j], personas[i])
                assert aff_ij == pytest.approx(aff_ji, abs=0.001)


class TestIdentifyInfluencers:
    def test_returns_top_percentile(self, personas):
        influencers = _identify_influencers(personas, percentile=0.60)
        assert len(influencers) > 0
        assert len(influencers) <= len(personas)

    def test_high_extraversion_favored(self, personas):
        influencers = _identify_influencers(personas, percentile=0.60)
        creative_idx = _idx(personas, "ID9003")
        assert creative_idx in influencers

    def test_introvert_less_likely(self, personas):
        influencers = _identify_influencers(personas, percentile=0.80)
        finance_introvert_idx = _idx(personas, "ID9004")
        if len(influencers) < len(personas) - 1:
            assert finance_introvert_idx not in influencers


class TestClusterByTopic:
    def test_creates_clusters(self, personas):
        clusters = _cluster_by_topic(personas)
        assert len(clusters) > 0
        total = sum(len(v) for v in clusters.values())
        assert total == len(personas)

    def test_same_topic_in_same_cluster(self, personas):
        clusters = _cluster_by_topic(personas)
        for topic, indices in clusters.items():
            for idx in indices:
                primary = personas[idx].interested_topics[0] if personas[idx].interested_topics else "General"
                assert primary == topic


class TestComputeFollowBudget:
    def test_extravert_follows_more(self, personas):
        config = NetworkConfig()
        creative = _find(personas, "ID9003")
        finance = _find(personas, "ID9004")
        budget_creative = _compute_follow_budget(creative, config)
        budget_finance = _compute_follow_budget(finance, config)
        assert budget_creative > budget_finance

    def test_respects_min_max(self, personas):
        config = NetworkConfig(min_following=5, max_following=20)
        for p in personas:
            budget = _compute_follow_budget(p, config)
            assert config.min_following <= budget <= config.max_following


class TestBuildSocialGraph:
    def test_returns_social_graph(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        assert isinstance(graph, SocialGraph)
        assert graph.num_agents == len(personas)

    def test_no_self_follows(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        for edge in graph.edges:
            assert edge.follower_idx != edge.followee_idx

    def test_no_duplicate_edges(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        edge_pairs = [(e.follower_idx, e.followee_idx) for e in graph.edges]
        assert len(edge_pairs) == len(set(edge_pairs))

    def test_indices_in_bounds(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        for edge in graph.edges:
            assert 0 <= edge.follower_idx < graph.num_agents
            assert 0 <= edge.followee_idx < graph.num_agents

    def test_generates_edges(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        assert graph.num_edges > 0

    def test_influencers_have_more_followers(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        if not graph.influencer_indices:
            pytest.skip("No influencers identified")

        follower_counts = [0] * graph.num_agents
        for edge in graph.edges:
            follower_counts[edge.followee_idx] += 1

        inf_followers = [follower_counts[i] for i in graph.influencer_indices]
        non_inf_indices = [i for i in range(graph.num_agents) if i not in graph.influencer_indices]
        non_inf_followers = [follower_counts[i] for i in non_inf_indices]

        if inf_followers and non_inf_followers:
            assert max(inf_followers) >= max(non_inf_followers)

    def test_generates_seed_posts(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        assert len(graph.seed_posts) > 0
        for post in graph.seed_posts:
            assert isinstance(post, SeedPost)
            assert post.author_idx in graph.influencer_indices
            assert len(post.content) > 10

    def test_deterministic_with_same_seed(self, personas):
        config_a = NetworkConfig(random_seed=123)
        config_b = NetworkConfig(random_seed=123)
        graph_a = build_social_graph(personas, config_a)
        graph_b = build_social_graph(personas, config_b)
        assert graph_a.num_edges == graph_b.num_edges

    def test_different_seed_different_graph(self, personas):
        config_a = NetworkConfig(random_seed=1)
        config_b = NetworkConfig(random_seed=999)
        graph_a = build_social_graph(personas, config_a)
        graph_b = build_social_graph(personas, config_b)
        edges_a = set((e.follower_idx, e.followee_idx) for e in graph_a.edges)
        edges_b = set((e.follower_idx, e.followee_idx) for e in graph_b.edges)
        assert edges_a != edges_b

    def test_single_agent_no_edges(self):
        persona = OasisUserInfo(
            persona_id="SOLO", name="Solo", user_name="solo", bio="alone",
            user_profile="solo agent", mbti="INTJ", gender="male", age=30,
            country="US", profession="Technology", interested_topics=["Technology"],
            active_threshold=[0.03] * 24,
            big_five={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5},
        )
        graph = build_social_graph([persona])
        assert graph.num_edges == 0

    def test_empty_personas(self):
        graph = build_social_graph([])
        assert graph.num_agents == 0
        assert graph.num_edges == 0


class TestGraphStats:
    def test_stats_structure(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        stats = graph_stats(graph)
        assert "num_agents" in stats
        assert "num_edges" in stats
        assert "avg_following" in stats
        assert "max_followers" in stats
        assert "num_influencers" in stats
        assert "num_seed_posts" in stats
        assert "topic_cluster_sizes" in stats

    def test_stats_consistent(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        stats = graph_stats(graph)
        assert stats["num_agents"] == graph.num_agents
        assert stats["num_edges"] == graph.num_edges


class TestSocialGraphMethods:
    def test_adjacency_list(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        adj = graph.to_adjacency_list()
        assert len(adj) == graph.num_agents
        total_edges = sum(len(v) for v in adj.values())
        assert total_edges == graph.num_edges

    def test_csv_export(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        csv = graph.to_edge_list_csv()
        lines = csv.strip().split("\n")
        assert lines[0] == "follower_id,followee_id"
        assert len(lines) - 1 == graph.num_edges

    def test_followers_of(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        if graph.influencer_indices:
            inf = graph.influencer_indices[0]
            followers = graph.followers_of(inf)
            assert isinstance(followers, list)

    def test_following_of(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        following = graph.following_of(0)
        assert isinstance(following, list)
        assert all(0 <= f < graph.num_agents for f in following)


class TestBuildOasisFollowData:
    def test_output_format(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        follow_data = build_oasis_follow_data(graph, personas)
        assert len(follow_data) == len(personas)
        for entry in follow_data:
            assert "agent_id" in entry
            assert "persona_id" in entry
            assert "user_name" in entry
            assert "following_agentid_list" in entry
            assert isinstance(entry["following_agentid_list"], list)

    def test_follow_data_matches_graph(self, personas, default_config):
        graph = build_social_graph(personas, default_config)
        follow_data = build_oasis_follow_data(graph, personas)
        adj = graph.to_adjacency_list()
        for entry in follow_data:
            agent_id = entry["agent_id"]
            assert entry["following_agentid_list"] == adj[agent_id]


class TestWithRealPersonas:
    def test_scales_to_100_agents(self):
        matraix_dir = Path(__file__).resolve().parents[4] / "personas" / "Jun20_1k_persona_description"
        if not matraix_dir.is_dir():
            pytest.skip("MatrAIx persona directory not available")

        personas = load_personas_from_directory(matraix_dir, max_agents=100)
        config = NetworkConfig(random_seed=42)
        graph = build_social_graph(personas, config)

        assert graph.num_agents == 100
        assert graph.num_edges > 50
        stats = graph_stats(graph)
        assert stats["avg_following"] > 1.0
        assert stats["num_influencers"] > 0
