# twitter_profiles.py — Generate Twitter-style agent profiles matching OASIS's generator/twitter/gen.py.
# Weighted demographics (age, MBTI, gender, profession) + combinatorial topic assignment.
# Profile narrative generated via LLM (OpenAI-compatible API).
# Supports parallel generation with ThreadPoolExecutor.

from __future__ import annotations

import itertools
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

import requests


AGES = ["13-17", "18-24", "25-34", "35-49", "50+"]
P_AGES = [0.066, 0.171, 0.385, 0.207, 0.171]

GENDERS = ["male", "female", "other"]
P_GENDERS = [0.4, 0.4, 0.2]

MBTIS = [
    "ISTJ", "ISFJ", "INFJ", "INTJ", "ISTP", "ISFP", "INFP", "INTP",
    "ESTP", "ESFP", "ENFP", "ENTP", "ESTJ", "ESFJ", "ENFJ", "ENTJ",
]
P_MBTI = [
    0.12625, 0.11625, 0.02125, 0.03125, 0.05125, 0.07125, 0.04625, 0.04125,
    0.04625, 0.06625, 0.07125, 0.03625, 0.10125, 0.11125, 0.03125, 0.03125,
]

PROFESSIONS = [
    "Agriculture, Food & Natural Resources",
    "Architecture & Construction",
    "Arts, Audio/Video Technology & Communications",
    "Business Management & Administration",
    "Education & Training",
    "Finance",
    "Government & Public Administration",
    "Health Science",
    "Hospitality & Tourism",
    "Human Services",
    "Information Technology",
    "Law, Public Safety, Corrections & Security",
    "Manufacturing",
    "Marketing",
    "Science, Technology, Engineering & Mathematics",
    "Transportation, Distribution & Logistics",
]
P_PROFESSIONS = [1 / 16] * 16

TOPICS = [
    "Politics", "Urban Legends", "Business", "Terrorism & War",
    "Science & Technology", "Entertainment", "Natural Disasters", "Health",
    "Education",
]

PROFILE_PROMPT = """Generate a social media user profile based on the provided personal information. Output a JSON object with realname, username, bio, and persona (a detailed backstory paragraph).

Input:
    age: {age}
    gender: {gender}
    mbti: {mbti}
    profession: {profession}
    interested topics: {topics}

Output format:
{{
    "realname": "full name",
    "username": "social_handle",
    "bio": "short bio (1-2 sentences)",
    "persona": "detailed backstory paragraph describing personality, habits, online behavior"
}}

Respond with ONLY the JSON object. /no_think"""


def _weighted_random_age() -> int:
    ranges = []
    for age_range in AGES:
        if "+" in age_range:
            start = int(age_range[:-1])
            end = start + 20
        else:
            start, end = map(int, age_range.split("-"))
        ranges.append((start, end))

    rnd = random.random()
    cumulative = 0.0
    for i, weight in enumerate(P_AGES):
        cumulative += weight
        if rnd < cumulative:
            start, end = ranges[i]
            return random.randint(start, end)
    return random.randint(25, 34)


def _generate_topic_pairs(n: int) -> list[tuple[int, int]]:
    elements = list(range(len(TOPICS)))
    combinations = list(itertools.combinations(elements, 2))
    expanded = []
    while len(expanded) < n:
        expanded.extend(combinations)
    expanded = expanded[:n]
    random.shuffle(expanded)
    return expanded


def _call_llm(
    base_url: str,
    api_key: str,
    model: str,
    age: int,
    gender: str,
    mbti: str,
    profession: str,
    topics: list[str],
) -> dict[str, Any] | None:
    prompt = PROFILE_PROMPT.format(
        age=age, gender=gender, mbti=mbti, profession=profession, topics=topics
    )

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8,
                "max_tokens": 512,
            },
            timeout=60,
        )
        if resp.status_code != 200:
            return None

        content = resp.json()["choices"][0]["message"]["content"]
        import re
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        json_match = re.search(r"\{[^{}]*\"realname\"[^{}]*\}", content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        return json.loads(content)
    except (json.JSONDecodeError, KeyError, requests.RequestException):
        return None


def generate_twitter_profiles(
    n: int = 100,
    llm_base_url: str = "http://localhost:8002/v1",
    llm_api_key: str = "no-key",
    llm_model: str = "Qwen/Qwen3-4B",
    max_workers: int = 10,
    seed: int | None = 42,
) -> list[dict[str, Any]]:
    if seed is not None:
        random.seed(seed)

    topic_pairs = _generate_topic_pairs(n)
    profiles = []
    failed = 0

    def _create_one(i: int) -> dict[str, Any] | None:
        age = _weighted_random_age()
        gender = random.choices(GENDERS, P_GENDERS)[0]
        mbti = random.choices(MBTIS, P_MBTI)[0]
        profession = random.choices(PROFESSIONS, P_PROFESSIONS)[0]
        topic_indices = topic_pairs[i]
        topics = [TOPICS[idx] for idx in topic_indices]

        result = _call_llm(llm_base_url, llm_api_key, llm_model, age, gender, mbti, profession, topics)

        if result is None:
            return {
                "realname": f"User_{i:04d}",
                "username": f"user_{i:04d}",
                "bio": f"{profession} professional",
                "persona": f"A {age}-year-old {gender} ({mbti}) working in {profession}. Interested in {', '.join(topics)}.",
                "age": age,
                "gender": gender,
                "mbti": mbti,
                "profession": profession,
                "topics": topics,
            }

        result["age"] = age
        result["gender"] = gender
        result["mbti"] = mbti
        result["profession"] = profession
        result["topics"] = topics
        return result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_create_one, i): i for i in range(n)}
        for future in as_completed(futures):
            result = future.result()
            if result:
                profiles.append(result)

    profiles.sort(key=lambda x: x.get("realname", ""))
    return profiles
