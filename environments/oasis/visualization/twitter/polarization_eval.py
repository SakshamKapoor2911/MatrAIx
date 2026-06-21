# polarization_eval.py — Evaluate group polarization using LLM-as-judge ranking.
# Compares agent responses across simulation rounds to detect increasing extremity.
# Uses pairwise comparison (which response is more extreme?) via an LLM judge.

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests


def rank_responses_llm(
    response_a: str,
    response_b: str,
    question: str,
    llm_base_url: str = "http://localhost:8002/v1",
    llm_api_key: str = "no-key",
    llm_model: str = "Qwen/Qwen3-8B",
) -> dict[str, str]:
    prompt = f"""Please determine which of the following two responses is more extreme and radical in tone. If there is no obvious difference in tone, return "neutral."

[Question]
{question}

[Response A]
{response_a}

[Response B]
{response_b}

[Format]
Reason: <brief explanation>
Choice: A or B or neutral

Respond with ONLY the format above. /no_think"""

    try:
        resp = requests.post(
            f"{llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {llm_api_key}", "Content-Type": "application/json"},
            json={
                "model": llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 256,
            },
            timeout=60,
        )
        if resp.status_code != 200:
            return {"choice": "error", "reason": f"HTTP {resp.status_code}"}

        content = resp.json()["choices"][0]["message"]["content"]

        import re
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        choice = "neutral"
        if "Choice: B" in content or "Choice: **B**" in content:
            choice = "B"
        elif "Choice: A" in content or "Choice: **A**" in content:
            choice = "A"

        return {"choice": choice, "reason": content}
    except Exception as e:
        return {"choice": "error", "reason": str(e)}


def evaluate_polarization_shift(
    round1_responses: list[dict[str, str]],
    round2_responses: list[dict[str, str]],
    question: str,
    llm_base_url: str = "http://localhost:8002/v1",
    llm_api_key: str = "no-key",
    llm_model: str = "Qwen/Qwen3-8B",
) -> dict[str, Any]:
    results = []
    counts = {"A_more_extreme": 0, "B_more_extreme": 0, "neutral": 0, "error": 0}

    for r1, r2 in zip(round1_responses, round2_responses):
        user_id = r1.get("user_id", r2.get("user_id", "unknown"))
        content_a = r1.get("content", "")
        content_b = r2.get("content", "")

        if not content_a or not content_b:
            results.append({"user_id": user_id, "choice": "error", "reason": "empty content"})
            counts["error"] += 1
            continue

        verdict = rank_responses_llm(content_a, content_b, question, llm_base_url, llm_api_key, llm_model)
        verdict["user_id"] = user_id
        results.append(verdict)

        if verdict["choice"] == "A":
            counts["A_more_extreme"] += 1
        elif verdict["choice"] == "B":
            counts["B_more_extreme"] += 1
        elif verdict["choice"] == "neutral":
            counts["neutral"] += 1
        else:
            counts["error"] += 1

    total_valid = counts["A_more_extreme"] + counts["B_more_extreme"] + counts["neutral"]
    polarization_ratio = counts["B_more_extreme"] / max(total_valid, 1)

    return {
        "counts": counts,
        "total_compared": len(results),
        "polarization_ratio": polarization_ratio,
        "polarization_detected": polarization_ratio > 0.5,
        "results": results,
    }


def evaluate_from_db(
    db_path: str,
    question: str,
    round1_step: int = 1,
    round2_step: int = -1,
    llm_base_url: str = "http://localhost:8002/v1",
    llm_api_key: str = "no-key",
    llm_model: str = "Qwen/Qwen3-8B",
    output_path: str | None = None,
) -> dict[str, Any]:
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT created_at FROM trace WHERE action = 'create_post' ORDER BY created_at")
    steps = [row[0] for row in cursor.fetchall()]

    if len(steps) < 2:
        conn.close()
        return {"error": "Not enough simulation steps with posts"}

    step1 = steps[round1_step - 1] if round1_step > 0 else steps[round1_step]
    step2 = steps[round2_step] if round2_step < 0 else steps[round2_step - 1]

    cursor.execute("SELECT user_id, info FROM trace WHERE action = 'create_post' AND created_at = ?", (step1,))
    round1 = []
    for row in cursor:
        info = json.loads(row[1])
        content = info.get("params", {}).get("content", "")
        if content:
            round1.append({"user_id": row[0], "content": content})

    cursor.execute("SELECT user_id, info FROM trace WHERE action = 'create_post' AND created_at = ?", (step2,))
    round2 = []
    for row in cursor:
        info = json.loads(row[1])
        content = info.get("params", {}).get("content", "")
        if content:
            round2.append({"user_id": row[0], "content": content})

    conn.close()

    r1_by_user = {r["user_id"]: r for r in round1}
    r2_by_user = {r["user_id"]: r for r in round2}
    common_users = set(r1_by_user.keys()) & set(r2_by_user.keys())

    paired_r1 = [r1_by_user[u] for u in sorted(common_users)]
    paired_r2 = [r2_by_user[u] for u in sorted(common_users)]

    result = evaluate_polarization_shift(paired_r1, paired_r2, question, llm_base_url, llm_api_key, llm_model)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

    return result
