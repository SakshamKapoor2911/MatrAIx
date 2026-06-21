# reddit_profiles.py — Generate Reddit-style agent profiles matching OASIS's generator/reddit/user_generate.py.
# Weighted demographics (gender 35/64, age groups, MBTI, country with US=48%, profession).
# Topic selection and profile narrative generated via LLM.

from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests


GENDERS = ["female", "male"]
P_GENDERS = [0.351, 0.636]

AGE_GROUPS = ["18-29", "30-49", "50-64", "65-100", "underage"]
P_AGES = [0.44, 0.31, 0.11, 0.03, 0.11]

MBTIS = [
    "ISTJ", "ISFJ", "INFJ", "INTJ", "ISTP", "ISFP", "INFP", "INTP",
    "ESTP", "ESFP", "ENFP", "ENTP", "ESTJ", "ESFJ", "ENFJ", "ENTJ",
]
P_MBTI = [
    0.12625, 0.11625, 0.02125, 0.03125, 0.05125, 0.07125, 0.04625, 0.04125,
    0.04625, 0.06625, 0.07125, 0.03625, 0.10125, 0.11125, 0.03125, 0.03125,
]

COUNTRIES = ["US", "UK", "Canada", "Australia", "Germany", "Other"]
P_COUNTRIES = [0.4833, 0.0733, 0.0697, 0.0416, 0.0306, 0.3016]
OTHER_COUNTRIES = [
    "India", "Brazil", "France", "Japan", "Nigeria", "Mexico",
    "South Korea", "Indonesia", "Italy", "Spain", "Netherlands",
    "Sweden", "Poland", "Argentina", "Turkey", "Egypt",
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

REDDIT_TOPICS = [
    "Economics",
    "Information Technology",
    "Culture & Society",
    "General News",
    "Politics",
    "Business",
    "Fun",
]

PROFILE_PROMPT = """Generate a Reddit user profile based on the provided demographics. Output a JSON object.

Input:
    age: {age}
    gender: {gender}
    mbti: {mbti}
    country: {country}
    profession: {profession}
    interested topics: {topics}

Output format:
{{
    "realname": "full name appropriate to country/culture",
    "username": "reddit_style_username",
    "bio": "short reddit bio (1-2 sentences)",
    "persona": "detailed paragraph describing their personality, values, communication style, and what they typically post about on Reddit"
}}

Respond with ONLY the JSON object. /no_think"""


def _get_random_age() -> int:
    group = random.choices(AGE_GROUPS, P_AGES)[0]
    if group == "underage":
        return random.randint(13, 17)
    elif group == "18-29":
        return random.randint(18, 29)
    elif group == "30-49":
        return random.randint(30, 49)
    elif group == "50-64":
        return random.randint(50, 64)
    else:
        return random.randint(65, 85)


def _get_random_country() -> str:
    country = random.choices(COUNTRIES, P_COUNTRIES)[0]
    if country == "Other":
        return random.choice(OTHER_COUNTRIES)
    return country


def _select_topics(mbti: str, age: int, profession: str) -> list[str]:
    weights = [1.0] * len(REDDIT_TOPICS)

    if "T" in mbti:
        weights[0] += 0.5
        weights[1] += 1.0
        weights[5] += 0.5
    if "F" in mbti:
        weights[2] += 1.0
        weights[6] += 0.5
    if "N" in mbti:
        weights[4] += 0.5
    if age < 25:
        weights[1] += 0.5
        weights[6] += 1.0
    if age > 40:
        weights[0] += 0.5
        weights[4] += 0.5

    if "Information Technology" in profession or "Science" in profession:
        weights[1] += 1.5
    if "Finance" in profession or "Business" in profession:
        weights[0] += 1.0
        weights[5] += 1.0
    if "Government" in profession or "Law" in profession:
        weights[4] += 1.5

    total = sum(weights)
    probs = [w / total for w in weights]
    num_topics = random.choice([2, 2, 2, 3])
    selected_indices = []
    remaining_probs = list(probs)
    for _ in range(num_topics):
        chosen = random.choices(range(len(REDDIT_TOPICS)), remaining_probs)[0]
        if chosen not in selected_indices:
            selected_indices.append(chosen)
            remaining_probs[chosen] = 0
            total_r = sum(remaining_probs)
            if total_r > 0:
                remaining_probs = [p / total_r for p in remaining_probs]

    return [REDDIT_TOPICS[i] for i in selected_indices]


def _call_llm(
    base_url: str,
    api_key: str,
    model: str,
    age: int,
    gender: str,
    mbti: str,
    country: str,
    profession: str,
    topics: list[str],
) -> dict[str, Any] | None:
    prompt = PROFILE_PROMPT.format(
        age=age, gender=gender, mbti=mbti, country=country,
        profession=profession, topics=topics,
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


def generate_reddit_profiles(
    n: int = 100,
    llm_base_url: str = "http://localhost:8002/v1",
    llm_api_key: str = "no-key",
    llm_model: str = "Qwen/Qwen3-4B",
    max_workers: int = 10,
    seed: int | None = 42,
) -> list[dict[str, Any]]:
    if seed is not None:
        random.seed(seed)

    profiles = []

    def _create_one(i: int) -> dict[str, Any]:
        gender = random.choices(GENDERS, P_GENDERS)[0]
        age = _get_random_age()
        mbti = random.choices(MBTIS, P_MBTI)[0]
        country = _get_random_country()
        profession = random.choices(PROFESSIONS, P_PROFESSIONS)[0]
        topics = _select_topics(mbti, age, profession)

        result = _call_llm(llm_base_url, llm_api_key, llm_model, age, gender, mbti, country, profession, topics)

        if result is None:
            result = {
                "realname": f"Redditor_{i:04d}",
                "username": f"redditor_{i:04d}",
                "bio": f"{profession} enthusiast from {country}",
                "persona": f"A {age}-year-old {gender} ({mbti}) from {country} working in {profession}. Active in {', '.join(topics)} discussions.",
            }

        result["age"] = age
        result["gender"] = gender
        result["mbti"] = mbti
        result["country"] = country
        result["profession"] = profession
        result["interested_topics"] = topics
        return result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_create_one, i): i for i in range(n)}
        for future in as_completed(futures):
            profiles.append(future.result())

    profiles.sort(key=lambda x: x.get("realname", ""))
    return profiles
