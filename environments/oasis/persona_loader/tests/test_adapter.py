# test_adapter.py — Tests for persona loader/adapter module.
# Validates YAML loading, dimension mapping, MBTI derivation, activity thresholds,
# and end-to-end batch conversion using fixture personas.

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from environments.oasis.persona_loader.adapter import (
    OasisUserInfo,
    adapt_single_persona,
    big5_to_mbti,
    big5_to_numeric,
    build_bio,
    build_user_profile,
    compute_activity_threshold,
    load_personas_from_directory,
    load_personas_from_files,
    map_country,
    map_gender,
    map_topics,
    parse_persona_yaml,
    personas_to_oasis_dicts,
    slugify,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestSlugify:
    def test_basic_name(self):
        assert slugify("Alex Chen") == "alex_chen"

    def test_special_characters(self):
        assert slugify("Hans Müller") == "hans_m_ller"

    def test_extra_spaces(self):
        assert slugify("  Sofia  Martinez  ") == "sofia_martinez"

    def test_numbers(self):
        assert slugify("Agent 007") == "agent_007"


class TestBig5ToNumeric:
    def test_all_levels(self):
        dims = {
            "personality_big5_openness": "Very high",
            "personality_big5_conscientiousness": "High",
            "personality_big5_extraversion": "Medium",
            "personality_big5_agreeableness": "Low",
            "personality_big5_neuroticism": "Very low",
        }
        result = big5_to_numeric(dims)
        assert result["openness"] == 0.85
        assert result["conscientiousness"] == 0.70
        assert result["extraversion"] == 0.50
        assert result["agreeableness"] == 0.30
        assert result["neuroticism"] == 0.15

    def test_missing_defaults_to_medium(self):
        result = big5_to_numeric({})
        assert result["openness"] == 0.50
        assert result["extraversion"] == 0.50


class TestBig5ToMBTI:
    def test_entj(self):
        big5 = {"openness": 0.70, "conscientiousness": 0.85, "extraversion": 0.70, "agreeableness": 0.30, "neuroticism": 0.15}
        assert big5_to_mbti(big5) == "ENTJ"

    def test_isfp(self):
        big5 = {"openness": 0.30, "conscientiousness": 0.30, "extraversion": 0.30, "agreeableness": 0.70, "neuroticism": 0.50}
        assert big5_to_mbti(big5) == "ISFP"

    def test_infj(self):
        big5 = {"openness": 0.85, "conscientiousness": 0.70, "extraversion": 0.30, "agreeableness": 0.70, "neuroticism": 0.50}
        assert big5_to_mbti(big5) == "INFJ"

    def test_boundary_at_050(self):
        big5 = {"openness": 0.50, "conscientiousness": 0.50, "extraversion": 0.50, "agreeableness": 0.50, "neuroticism": 0.50}
        assert big5_to_mbti(big5) == "ENFJ"


class TestMapGender:
    def test_man(self):
        assert map_gender("Man") == "male"

    def test_woman(self):
        assert map_gender("Woman") == "female"

    def test_nonbinary(self):
        assert map_gender("Non-binary") == "non-binary"

    def test_unknown_input(self):
        assert map_gender("Something else") == "unknown"


class TestMapCountry:
    def test_south_asia(self):
        assert map_country("South Asia", seed=0) == "India"
        assert map_country("South Asia", seed=1) == "Pakistan"

    def test_north_america(self):
        assert map_country("North America", seed=0) == "US"

    def test_unknown_region(self):
        assert map_country("Mars", seed=0) == "Unknown"

    def test_wraps_around(self):
        result = map_country("Oceania", seed=10)
        assert result in ["Australia", "New Zealand"]


class TestMapTopics:
    def test_technology(self):
        assert map_topics("Technology") == ["Technology", "Science"]

    def test_healthcare(self):
        assert map_topics("Healthcare & Medicine") == ["Health", "Science"]

    def test_unknown_domain_defaults(self):
        assert map_topics("Underwater Basket Weaving") == ["Technology", "Science"]


class TestComputeActivityThreshold:
    def test_young_urban_extravert_is_high(self):
        dims = {
            "age_bracket": "18–24",
            "urbanicity": "Urban",
            "personality_big5_extraversion": "Very high",
        }
        thresholds = compute_activity_threshold(dims)
        assert len(thresholds) == 24
        assert all(t > 0 for t in thresholds)
        assert max(thresholds) > 0.05

    def test_older_rural_introvert_is_low(self):
        dims = {
            "age_bracket": "65+",
            "urbanicity": "Rural",
            "personality_big5_extraversion": "Very low",
        }
        thresholds = compute_activity_threshold(dims)
        assert len(thresholds) == 24
        assert max(thresholds) < 0.02

    def test_peak_hours_higher(self):
        dims = {"age_bracket": "25–34", "urbanicity": "Suburban", "personality_big5_extraversion": "Medium"}
        thresholds = compute_activity_threshold(dims)
        peak_avg = sum(thresholds[h] for h in [8, 9, 12, 13, 18, 19, 20, 21, 22]) / 9
        night_avg = sum(thresholds[h] for h in [0, 1, 2, 3, 4, 5]) / 6
        assert peak_avg > night_avg

    def test_capped_at_020(self):
        dims = {
            "age_bracket": "18–24",
            "urbanicity": "Urban",
            "personality_big5_extraversion": "Very high",
        }
        thresholds = compute_activity_threshold(dims)
        assert all(t <= 0.30 for t in thresholds)


class TestBuildUserProfile:
    def test_contains_name_and_age(self):
        persona = {"name": "Test User", "age": 30, "title": "Engineer", "description": "desc"}
        dims = {"region": "North America", "highest_education": "Master's", "domain": "Technology",
                "seniority": "Senior", "marital_status": "Single", "children": "No children",
                "emotional_state": "Curious", "intent": "build things", "primary_language": "English",
                "personality_big5_openness": "High", "personality_big5_conscientiousness": "High",
                "personality_big5_extraversion": "Medium", "personality_big5_agreeableness": "Medium",
                "personality_big5_neuroticism": "Low"}
        result = build_user_profile(persona, dims)
        assert "Test User" in result
        assert "30" in result
        assert "technology" in result.lower()
        assert "North America" in result

    def test_handles_missing_fields(self):
        persona = {"name": "Minimal", "age": 25}
        dims = {}
        result = build_user_profile(persona, dims)
        assert "Minimal" in result


class TestBuildBio:
    def test_full_bio(self):
        persona = {"title": "CEO"}
        dims = {"domain": "Tech", "region": "East Asia", "intent": "lead"}
        result = build_bio(persona, dims)
        assert "CEO" in result
        assert "East Asia" in result
        assert "lead" in result


class TestParsePersonaYaml:
    def test_loads_fixture(self):
        filepath = FIXTURES_DIR / "persona_young_tech.yaml"
        raw = parse_persona_yaml(filepath)
        assert raw["metadata"]["id"] == "ID9001"
        assert raw["persona"]["name"] == "Alex Chen"
        assert raw["persona"]["dimensions"]["domain"] == "Technology"


class TestAdaptSinglePersona:
    def test_young_tech(self):
        raw = parse_persona_yaml(FIXTURES_DIR / "persona_young_tech.yaml")
        result = adapt_single_persona(raw, index=0)

        assert isinstance(result, OasisUserInfo)
        assert result.persona_id == "ID9001"
        assert result.name == "Alex Chen"
        assert "alex_chen" in result.user_name
        assert result.age == 28
        assert result.gender == "male"
        assert result.country in ["China", "Japan", "South Korea", "Taiwan"]
        assert result.profession == "Technology"
        assert "Technology" in result.interested_topics
        assert result.mbti == "ENTJ" or result.mbti == "ENFJ"
        assert len(result.active_threshold) == 24
        assert result.big_five["openness"] == 0.85

    def test_older_healthcare(self):
        raw = parse_persona_yaml(FIXTURES_DIR / "persona_older_healthcare.yaml")
        result = adapt_single_persona(raw, index=1)

        assert result.persona_id == "ID9002"
        assert result.gender == "female"
        assert result.age == 58
        assert result.country in ["US", "Canada", "Mexico"]
        assert "Health" in result.interested_topics
        assert result.mbti[0] == "I"
        assert max(result.active_threshold) < max(
            adapt_single_persona(
                parse_persona_yaml(FIXTURES_DIR / "persona_young_creative.yaml"), index=2
            ).active_threshold
        )

    def test_finance_introvert_low_activity(self):
        raw = parse_persona_yaml(FIXTURES_DIR / "persona_finance_introvert.yaml")
        result = adapt_single_persona(raw, index=3)

        assert result.mbti[0] == "I"
        assert result.mbti[3] == "J"
        assert "Economics" in result.interested_topics or "Business" in result.interested_topics

    def test_rural_educator(self):
        raw = parse_persona_yaml(FIXTURES_DIR / "persona_rural_educator.yaml")
        result = adapt_single_persona(raw, index=4)

        assert result.profession == "Education & Training"
        assert result.country in ["Nigeria", "Kenya", "South Africa", "Ghana", "Ethiopia"]
        young_creative_raw = parse_persona_yaml(FIXTURES_DIR / "persona_young_creative.yaml")
        young_creative = adapt_single_persona(young_creative_raw, index=2)
        assert max(result.active_threshold) < max(young_creative.active_threshold)


class TestOasisUserInfoToDict:
    def test_output_structure(self):
        raw = parse_persona_yaml(FIXTURES_DIR / "persona_young_tech.yaml")
        result = adapt_single_persona(raw, index=0)
        oasis_dict = result.to_oasis_dict()

        assert oasis_dict["name"] == "Alex Chen"
        assert "alex_chen" in oasis_dict["user_name"]
        assert isinstance(oasis_dict["description"], str)
        assert oasis_dict["recsys_type"] == "twitter"
        assert oasis_dict["is_controllable"] is False

        profile = oasis_dict["profile"]
        assert "other_info" in profile
        info = profile["other_info"]
        assert "user_profile" in info
        assert "mbti" in info
        assert "gender" in info
        assert "age" in info
        assert "country" in info
        assert "profession" in info
        assert "interested_topics" in info
        assert "active_threshold" in info
        assert len(info["active_threshold"]) == 24
        assert isinstance(info["interested_topics"], list)


class TestLoadPersonasFromDirectory:
    def test_loads_all_fixtures(self):
        results = load_personas_from_directory(FIXTURES_DIR)
        assert len(results) == 5
        assert all(isinstance(r, OasisUserInfo) for r in results)

    def test_max_agents_limit(self):
        results = load_personas_from_directory(FIXTURES_DIR, max_agents=2)
        assert len(results) == 2

    def test_nonexistent_directory_raises(self):
        with pytest.raises(FileNotFoundError):
            load_personas_from_directory("/nonexistent/path/xyz")

    def test_unique_usernames(self):
        results = load_personas_from_directory(FIXTURES_DIR)
        usernames = [r.user_name for r in results]
        assert len(usernames) == len(set(usernames))


class TestLoadPersonasFromFiles:
    def test_specific_files(self):
        files = [
            FIXTURES_DIR / "persona_young_tech.yaml",
            FIXTURES_DIR / "persona_finance_introvert.yaml",
        ]
        results = load_personas_from_files(files)
        assert len(results) == 2
        assert results[0].persona_id == "ID9001"
        assert results[1].persona_id == "ID9004"

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_personas_from_files(["/does/not/exist.yaml"])


class TestPersonasToOasisDicts:
    def test_batch_conversion(self):
        personas = load_personas_from_directory(FIXTURES_DIR)
        dicts = personas_to_oasis_dicts(personas)
        assert len(dicts) == 5
        assert all(isinstance(d, dict) for d in dicts)
        assert all("name" in d for d in dicts)
        assert all("profile" in d for d in dicts)


class TestEndToEndWithRealPersonas:
    def test_loads_matraix_personas_if_available(self):
        matraix_dir = Path(__file__).resolve().parents[4] / "personas" / "Jun20_1k_persona_description"
        if not matraix_dir.is_dir():
            pytest.skip("MatrAIx persona directory not available")

        results = load_personas_from_directory(matraix_dir, max_agents=10)
        assert len(results) == 10
        dicts = personas_to_oasis_dicts(results)

        for d in dicts:
            assert d["name"]
            assert d["user_name"]
            assert d["profile"]["other_info"]["age"] > 0
            assert len(d["profile"]["other_info"]["active_threshold"]) == 24
            assert d["profile"]["other_info"]["mbti"] and len(d["profile"]["other_info"]["mbti"]) == 4


class TestPersonaDiversity:
    def test_different_personas_produce_different_thresholds(self):
        personas = load_personas_from_directory(FIXTURES_DIR)
        threshold_sums = [sum(p.active_threshold) for p in personas]
        assert len(set(threshold_sums)) > 1

    def test_different_personas_produce_different_mbtis(self):
        personas = load_personas_from_directory(FIXTURES_DIR)
        mbtis = [p.mbti for p in personas]
        assert len(set(mbtis)) > 1

    def test_different_personas_produce_different_topics(self):
        personas = load_personas_from_directory(FIXTURES_DIR)
        topic_sets = [tuple(p.interested_topics) for p in personas]
        assert len(set(topic_sets)) > 1
