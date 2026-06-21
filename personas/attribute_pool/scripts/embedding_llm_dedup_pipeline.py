import argparse
import csv
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
STEP3 = ROOT / "candidate_pool_outputs" / "step3_dedup_categorize"
STEP4 = ROOT / "candidate_pool_outputs" / "step4_llm_graph"
OUT = ROOT / "candidate_pool_outputs" / "step5_embedding_llm_dedup"
OUT.mkdir(parents=True, exist_ok=True)

ATTRIBUTES_CSV = STEP3 / "deduped_attributes_high_quality.csv"
STEP4_PAIR_CANDIDATES = STEP4 / "llm_pair_adjudication_candidates.csv"

DEFAULT_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
DEFAULT_LLM_MODEL = os.environ.get("OPENAI_LLM_MODEL", "gpt-4.1-mini")
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_OLLAMA_EMBEDDING_MODEL = os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
DEFAULT_OLLAMA_LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "qwen3:8b")

RELATION_BASE_WEIGHT = {
    "duplicate_of": 1.00,
    "alias_of": 0.95,
    "broader_than": 0.78,
    "narrower_than": 0.78,
    "positively_correlated": 0.70,
    "negatively_correlated": 0.70,
    "inverse_pole": 0.86,
    "conflicts_with": 0.82,
    "related_but_distinct": 0.58,
    "not_related": 0.0,
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "do", "does",
    "for", "from", "has", "have", "how", "i", "if", "in", "is", "it", "me", "my",
    "of", "on", "or", "r", "respondent", "respondents", "s", "the", "their", "them",
    "they", "this", "to", "what", "when", "where", "which", "who", "why", "with",
    "you", "your",
}


def clean_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\u00a0", " ").replace("\ufeff", "")).strip()


def parse_json_list(value):
    try:
        parsed = json.loads(value or "[]")
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def tokens(text):
    text = clean_text(text).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    out = []
    for token in text.split():
        if token in STOPWORDS or len(token) <= 1:
            continue
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        out.append(token)
    return out


def slugify(value, max_len=80):
    value = clean_text(value).lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return (value[:max_len].strip("_") or "item")


def stable_pair_id(a_id, b_id):
    ordered = sorted([a_id, b_id])
    digest = hashlib.sha1("|".join(ordered).encode("utf-8")).hexdigest()[:12]
    return f"pair_{slugify(ordered[0], 36)}__{slugify(ordered[1], 36)}__{digest}"


def load_attributes():
    df = pd.read_csv(ATTRIBUTES_CSV, dtype=str, keep_default_na=False)
    rows = df.to_dict(orient="records")
    for row in rows:
        aliases = " ".join(parse_json_list(row.get("aliases_json", ""))[:8])
        row["_text_for_embedding"] = " ".join(
            [
                row.get("canonical_label", ""),
                aliases,
                row.get("final_primary_category", ""),
                row.get("final_subcategory", ""),
                row.get("normalized_definition", ""),
            ]
        )
        row["_label_text"] = " ".join([row.get("canonical_label", ""), aliases])
        row["_tokens"] = set(tokens(row["_label_text"]))
    return rows


def evidence_support(row):
    quality = {"A": 1.0, "B": 0.72, "C": 0.35}.get(row.get("quality_tier", ""), 0.5)
    try:
        source_count = int(row.get("source_count", "1") or 1)
        candidate_count = int(row.get("candidate_count", "1") or 1)
    except Exception:
        source_count = 1
        candidate_count = 1
    support = min(1.0, 0.55 + 0.15 * math.log1p(source_count) + 0.08 * math.log1p(candidate_count))
    return round(quality * support, 4)


def lexical_similarity(a, b):
    label_a = clean_text(a.get("canonical_label", "")).lower()
    label_b = clean_text(b.get("canonical_label", "")).lower()
    seq = SequenceMatcher(None, label_a, label_b).ratio() if label_a and label_b else 0.0
    ta = a.get("_tokens", set())
    tb = b.get("_tokens", set())
    if ta and tb:
        jaccard = len(ta & tb) / len(ta | tb)
        containment = max(len(ta & tb) / len(ta), len(ta & tb) / len(tb))
        return round(max(seq, jaccard, containment), 4)
    return round(seq, 4)


def hash_bucket(feature, dim):
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little") % dim


def fallback_hash_tfidf_embeddings(rows, dim=2048):
    tokenized = [tokens(row["_text_for_embedding"]) for row in rows]
    df = Counter()
    for toks in tokenized:
        df.update(set(toks))
    n = len(rows)
    idf = {tok: math.log((n + 1) / (count + 1)) + 1 for tok, count in df.items()}
    matrix = np.zeros((n, dim), dtype=np.float32)
    for i, toks in enumerate(tokenized):
        counts = Counter(toks)
        for tok, count in counts.items():
            bucket = hash_bucket(tok, dim)
            matrix[i, bucket] += (1 + math.log(count)) * idf.get(tok, 1.0)
    norms = np.linalg.norm(matrix, axis=1)
    norms[norms == 0] = 1
    matrix /= norms[:, None]
    return matrix, "lexical_hash_tfidf_fallback"


def rate_limit_sleep_seconds(body):
    match = re.search(r"try again in (?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", body, flags=re.I)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    total = hours * 3600 + minutes * 60 + seconds
    return total if total > 0 else None


def openai_request(path, payload, api_key, timeout=120, retries=6, wait_on_rate_limit=False):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.openai.com/v1/{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if "insufficient_quota" in body:
                raise RuntimeError("OpenAI insufficient_quota: add API credits or update billing before rerunning.") from exc
            wait_seconds = rate_limit_sleep_seconds(body) if wait_on_rate_limit else None
            if wait_seconds and wait_seconds <= 7200:
                sleep_for = wait_seconds + 5
                print(f"Rate limit reached; sleeping {sleep_for} seconds before retrying.", flush=True)
                time.sleep(sleep_for)
                continue
            if exc.code in {408, 409, 429, 500, 502, 503, 504} and attempt < retries - 1:
                time.sleep(min(60, 2 ** attempt))
                continue
            raise RuntimeError(f"OpenAI API error {exc.code}: {body[:1000]}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt < retries - 1:
                time.sleep(min(60, 2 ** attempt))
                continue
            raise RuntimeError(f"OpenAI request failed after retries: {exc}") from exc
    raise RuntimeError("OpenAI request failed after retries.")


def ollama_request(path, payload, base_url=DEFAULT_OLLAMA_URL, timeout=300):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def openai_embeddings(rows, api_key, model, batch_size=256):
    vectors = []
    texts = [row["_text_for_embedding"][:8000] for row in rows]
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = openai_request("embeddings", {"model": model, "input": batch}, api_key)
        vectors.extend(item["embedding"] for item in response["data"])
        time.sleep(0.05)
    matrix = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1)
    norms[norms == 0] = 1
    matrix /= norms[:, None]
    return matrix, f"openai::{model}"


def ollama_embeddings(rows, base_url, model, batch_size=64):
    vectors = []
    texts = [row["_text_for_embedding"][:8000] for row in rows]
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = ollama_request("embed", {"model": model, "input": batch}, base_url=base_url, timeout=600)
        batch_vectors = response.get("embeddings")
        if not batch_vectors:
            raise RuntimeError(
                f"Ollama /api/embed did not return embeddings. Is model `{model}` pulled and Ollama running?"
            )
        vectors.extend(batch_vectors)
    matrix = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1)
    norms[norms == 0] = 1
    matrix /= norms[:, None]
    return matrix, f"ollama::{model}"


def compute_embeddings(rows, provider="auto", force_fallback=False, ollama_url=DEFAULT_OLLAMA_URL, ollama_model=DEFAULT_OLLAMA_EMBEDDING_MODEL):
    if provider == "fallback" or force_fallback:
        return fallback_hash_tfidf_embeddings(rows)
    if provider == "ollama":
        return ollama_embeddings(rows, ollama_url, ollama_model)
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required when --provider openai is used.")
        return openai_embeddings(rows, api_key, DEFAULT_EMBEDDING_MODEL)

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key and not force_fallback:
        return openai_embeddings(rows, api_key, DEFAULT_EMBEDDING_MODEL)
    return fallback_hash_tfidf_embeddings(rows)


def relation_hint(a, b):
    ta = a.get("_tokens", set())
    tb = b.get("_tokens", set())
    if {"risk", "aversion"} <= ta and {"risk", "tolerance"} <= tb:
        return "inverse_pole"
    if {"risk", "tolerance"} <= ta and {"risk", "aversion"} <= tb:
        return "inverse_pole"
    if "extraversion" in ta and "introversion" in tb or "introversion" in ta and "extraversion" in tb:
        return "inverse_pole"
    if "optimism" in ta and "pessimism" in tb or "pessimism" in ta and "optimism" in tb:
        return "inverse_pole"
    return ""


def generate_embedding_pairs(rows, embeddings, top_k=25, min_similarity=0.62, block_size=512):
    by_id = {row["canonical_attribute_id"]: row for row in rows}
    pairs = {}
    n = len(rows)
    for start in range(0, n, block_size):
        end = min(n, start + block_size)
        sims = embeddings[start:end] @ embeddings.T
        for local_i, scores in enumerate(sims):
            i = start + local_i
            scores[i] = -1.0
            if top_k < len(scores):
                idxs = np.argpartition(scores, -top_k)[-top_k:]
            else:
                idxs = np.arange(len(scores))
            for j in idxs:
                score = float(scores[j])
                if score < min_similarity:
                    continue
                a = rows[i]
                b = rows[j]
                key = tuple(sorted([a["canonical_attribute_id"], b["canonical_attribute_id"]]))
                if key in pairs and pairs[key]["embedding_similarity"] >= score:
                    continue
                relation = relation_hint(a, b)
                if not relation:
                    relation = "embedding_candidate"
                lex = lexical_similarity(a, b)
                ev = round((evidence_support(a) + evidence_support(b)) / 2, 4)
                pairs[key] = {
                    "pair_id": stable_pair_id(*key),
                    "source_attribute_id": key[0],
                    "target_attribute_id": key[1],
                    "source_label": by_id[key[0]]["canonical_label"],
                    "target_label": by_id[key[1]]["canonical_label"],
                    "source_category": by_id[key[0]]["final_primary_category"],
                    "target_category": by_id[key[1]]["final_primary_category"],
                    "source_subcategory": by_id[key[0]]["final_subcategory"],
                    "target_subcategory": by_id[key[1]]["final_subcategory"],
                    "embedding_similarity": round(score, 4),
                    "lexical_similarity": lex,
                    "evidence_support": ev,
                    "retrieval_relation_hint": relation,
                    "retrieval_status": "needs_llm_adjudication",
                }
    return sorted(pairs.values(), key=lambda r: (float(r["embedding_similarity"]), float(r["lexical_similarity"])), reverse=True)


def merge_with_step4_pairs(embedding_pairs, rows, max_pairs=7000):
    by_id = {row["canonical_attribute_id"]: row for row in rows}
    combined = {}
    for row in embedding_pairs:
        key = tuple(sorted([row["source_attribute_id"], row["target_attribute_id"]]))
        row = dict(row)
        row["candidate_source"] = "embedding_retrieval"
        combined[key] = row

    if STEP4_PAIR_CANDIDATES.exists():
        step4 = pd.read_csv(STEP4_PAIR_CANDIDATES, dtype=str, keep_default_na=False).to_dict(orient="records")
        for row in step4:
            key = tuple(sorted([row["source_attribute_id"], row["target_attribute_id"]]))
            if key in combined:
                combined[key]["candidate_source"] += "+step4_heuristic"
                combined[key]["step4_relation_hint"] = row.get("heuristic_relation_candidate", "")
                combined[key]["step4_score"] = row.get("heuristic_score", "")
                continue
            a = by_id.get(key[0])
            b = by_id.get(key[1])
            if not a or not b:
                continue
            combined[key] = {
                "pair_id": stable_pair_id(*key),
                "source_attribute_id": key[0],
                "target_attribute_id": key[1],
                "source_label": a["canonical_label"],
                "target_label": b["canonical_label"],
                "source_category": a["final_primary_category"],
                "target_category": b["final_primary_category"],
                "source_subcategory": a["final_subcategory"],
                "target_subcategory": b["final_subcategory"],
                "embedding_similarity": "",
                "lexical_similarity": lexical_similarity(a, b),
                "evidence_support": round((evidence_support(a) + evidence_support(b)) / 2, 4),
                "retrieval_relation_hint": row.get("heuristic_relation_candidate", ""),
                "retrieval_status": "needs_llm_adjudication",
                "candidate_source": "step4_heuristic",
                "step4_relation_hint": row.get("heuristic_relation_candidate", ""),
                "step4_score": row.get("heuristic_score", ""),
            }

    def rank(row):
        emb = float(row["embedding_similarity"] or 0)
        lex = float(row["lexical_similarity"] or 0)
        ev = float(row["evidence_support"] or 0)
        source_bonus = 0.05 if "embedding" in row.get("candidate_source", "") and "step4" in row.get("candidate_source", "") else 0
        return emb * 0.55 + lex * 0.25 + ev * 0.15 + source_bonus

    rows_out = list(combined.values())
    for row in rows_out:
        row["pre_llm_pair_score"] = round(rank(row), 4)
    rows_out.sort(key=lambda r: float(r["pre_llm_pair_score"]), reverse=True)
    return rows_out[:max_pairs]


def prompt_for_pair(row, attr_by_id):
    a = attr_by_id[row["source_attribute_id"]]
    b = attr_by_id[row["target_attribute_id"]]
    return {
        "task": "LLM_deduplicate_and_classify_persona_attribute_pair",
        "instructions": [
            "Judge whether A and B are the same persona attribute, aliases, hierarchical variants, correlated, inverse/conflicting, related but distinct, or not related.",
            "Only choose merge when relation_type is duplicate_of or alias_of.",
            "Do not merge inverse poles, correlated constructs, related constructs, or broad/narrow variants.",
            "Return JSON only.",
        ],
        "allowed_relation_types": [
            "duplicate_of", "alias_of", "broader_than", "narrower_than",
            "positively_correlated", "negatively_correlated", "inverse_pole",
            "conflicts_with", "related_but_distinct", "not_related",
        ],
        "pair": {
            "pair_id": row["pair_id"],
            "embedding_similarity": row.get("embedding_similarity", ""),
            "lexical_similarity": row.get("lexical_similarity", ""),
            "attribute_a": {
                "id": a["canonical_attribute_id"],
                "label": a["canonical_label"],
                "category": a["final_primary_category"],
                "subcategory": a["final_subcategory"],
                "definition": a["normalized_definition"],
                "sources": a["sources_json"],
            },
            "attribute_b": {
                "id": b["canonical_attribute_id"],
                "label": b["canonical_label"],
                "category": b["final_primary_category"],
                "subcategory": b["final_subcategory"],
                "definition": b["normalized_definition"],
                "sources": b["sources_json"],
            },
        },
        "output_schema": {
            "pair_id": "string",
            "relation_type": "one allowed relation",
            "merge_decision": "merge | keep_separate | unsure",
            "direction": "A_to_B | B_to_A | symmetric | none",
            "llm_confidence": "0.0-1.0",
            "rationale": "short",
        },
    }


def final_merge_confidence(row):
    llm = float(row.get("llm_confidence", 0) or 0)
    emb = float(row.get("embedding_similarity", 0) or 0)
    lex = float(row.get("lexical_similarity", 0) or 0)
    ev = float(row.get("evidence_support", 0) or 0)
    return round(0.45 * llm + 0.30 * emb + 0.15 * lex + 0.10 * ev, 4)


def openai_adjudicate_one(row, attr_by_id, api_key, model):
    prompt = prompt_for_pair(row, attr_by_id)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a careful persona taxonomy adjudicator. Return JSON only.",
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 300,
    }
    response = openai_request("chat/completions", payload, api_key)
    text = response["choices"][0]["message"]["content"].strip()
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = {
            "pair_id": row["pair_id"],
            "relation_type": "not_related",
            "merge_decision": "unsure",
            "direction": "none",
            "llm_confidence": 0,
            "rationale": f"Could not parse LLM JSON: {text[:200]}",
        }
    merged = dict(row)
    merged.update(parsed)
    merged["pair_id"] = row["pair_id"]
    merged["final_merge_confidence"] = final_merge_confidence(merged)
    merged["llm_provider"] = "openai"
    merged["llm_model"] = model
    return merged


def openai_llm_adjudicate(pair_rows, attr_by_id, api_key, model, max_pairs, workers=8, resume=False, checkpoint_every=25):
    selected = pair_rows[:max_pairs]
    checkpoint_path = OUT / "llm_adjudicated_pairs.csv"
    results = []
    done_ids = set()
    if resume and checkpoint_path.exists() and checkpoint_path.stat().st_size > 0:
        with checkpoint_path.open("r", encoding="utf-8-sig", newline="") as f:
            existing = list(csv.DictReader(f))
        selected_ids = {row["pair_id"] for row in selected}
        for row in existing:
            if row.get("pair_id") in selected_ids and row.get("pair_id") not in done_ids:
                results.append(row)
                done_ids.add(row["pair_id"])

    to_run = [row for row in selected if row["pair_id"] not in done_ids]
    print(f"OpenAI LLM adjudication: {len(done_ids)} already done, {len(to_run)} remaining, workers={workers}", flush=True)
    if not to_run:
        return results

    completed = len(results)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_to_index = {
            executor.submit(openai_adjudicate_one, row, attr_by_id, api_key, model): index
            for index, row in enumerate(to_run)
        }
        for future in as_completed(future_to_index):
            result = future.result()
            results.append(result)
            completed += 1
            if completed % checkpoint_every == 0 or completed == len(selected):
                write_csv(checkpoint_path, results)
                print(f"Checkpoint: {completed}/{len(selected)} LLM pairs adjudicated", flush=True)

    write_csv(checkpoint_path, results)
    return results


def compact_pair_for_batch(row, attr_by_id):
    a = attr_by_id[row["source_attribute_id"]]
    b = attr_by_id[row["target_attribute_id"]]
    return {
        "pair_id": row["pair_id"],
        "attribute_a": {
            "label": a["canonical_label"],
            "category": a["final_primary_category"],
            "subcategory": a["final_subcategory"],
            "definition": a["normalized_definition"][:300],
        },
        "attribute_b": {
            "label": b["canonical_label"],
            "category": b["final_primary_category"],
            "subcategory": b["final_subcategory"],
            "definition": b["normalized_definition"][:300],
        },
        "signals": {
            "embedding_similarity": row.get("embedding_similarity", ""),
            "lexical_similarity": row.get("lexical_similarity", ""),
            "relation_hint": row.get("retrieval_relation_hint", "") or row.get("step4_relation_hint", ""),
        },
    }


def normalize_batch_item(item, row):
    parsed = item if isinstance(item, dict) else {}
    merged = dict(row)
    merged.update(
        {
            "pair_id": row["pair_id"],
            "relation_type": parsed.get("relation_type", "not_related"),
            "merge_decision": parsed.get("merge_decision", "unsure"),
            "direction": parsed.get("direction", "none"),
            "llm_confidence": parsed.get("llm_confidence", 0),
            "rationale": parsed.get("rationale", ""),
            "llm_provider": "openai",
            "llm_model": DEFAULT_LLM_MODEL,
        }
    )
    merged["final_merge_confidence"] = final_merge_confidence(merged)
    return merged


def openai_adjudicate_batch(batch_rows, attr_by_id, api_key, model):
    compact_pairs = [compact_pair_for_batch(row, attr_by_id) for row in batch_rows]
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a careful persona taxonomy adjudicator. Return JSON only. "
                    "For each input pair, decide whether the attributes should be merged, kept separate, "
                    "or linked as a graph relation."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "allowed_relation_types": [
                            "duplicate_of",
                            "alias_of",
                            "broader_than",
                            "narrower_than",
                            "positively_correlated",
                            "negatively_correlated",
                            "inverse_pole",
                            "conflicts_with",
                            "related_but_distinct",
                            "not_related",
                        ],
                        "decision_rules": [
                            "Use duplicate_of or alias_of only when the two attributes measure the same construct.",
                            "Do not merge inverse poles, correlated constructs, risk variants, or broad/narrow constructs.",
                            "Use broader_than/narrower_than for hierarchy; use inverse_pole for conceptual opposites.",
                        ],
                        "output_schema": {
                            "results": [
                                {
                                    "pair_id": "same pair_id as input",
                                    "relation_type": "one allowed relation",
                                    "merge_decision": "merge | keep_separate | unsure",
                                    "direction": "A_to_B | B_to_A | symmetric | none",
                                    "llm_confidence": "0.0-1.0",
                                    "rationale": "short",
                                }
                            ]
                        },
                        "pairs": compact_pairs,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": max(1000, len(batch_rows) * 120),
    }
    response = openai_request("chat/completions", payload, api_key, timeout=300, retries=12, wait_on_rate_limit=True)
    text = response["choices"][0]["message"]["content"].strip()
    try:
        parsed = json.loads(text)
        result_items = parsed.get("results", [])
    except Exception:
        result_items = []

    by_id = {item.get("pair_id"): item for item in result_items if isinstance(item, dict)}
    return [normalize_batch_item(by_id.get(row["pair_id"], {}), row) for row in batch_rows]


def openai_llm_adjudicate_batched(pair_rows, attr_by_id, api_key, model, max_pairs, batch_size=150, resume=False):
    selected = pair_rows[:max_pairs]
    checkpoint_path = OUT / "llm_adjudicated_pairs.csv"
    results = []
    done_ids = set()
    if resume and checkpoint_path.exists() and checkpoint_path.stat().st_size > 0:
        with checkpoint_path.open("r", encoding="utf-8-sig", newline="") as f:
            existing = list(csv.DictReader(f))
        selected_ids = {row["pair_id"] for row in selected}
        for row in existing:
            if row.get("pair_id") in selected_ids and row.get("pair_id") not in done_ids:
                results.append(row)
                done_ids.add(row["pair_id"])

    to_run = [row for row in selected if row["pair_id"] not in done_ids]
    total = len(selected)
    print(f"OpenAI batched adjudication: {len(done_ids)} already done, {len(to_run)} remaining, batch_size={batch_size}", flush=True)
    for start in range(0, len(to_run), batch_size):
        batch = to_run[start : start + batch_size]
        batch_results = openai_adjudicate_batch(batch, attr_by_id, api_key, model)
        results.extend(batch_results)
        write_csv(checkpoint_path, results)
        print(f"Checkpoint: {len(results)}/{total} LLM pairs adjudicated", flush=True)
    return results


def ollama_llm_adjudicate(pair_rows, attr_by_id, base_url, model, max_pairs):
    results = []
    for row in pair_rows[:max_pairs]:
        prompt = prompt_for_pair(row, attr_by_id)
        payload = {
            "model": model,
            "prompt": (
                "You are a careful persona taxonomy adjudicator. Return JSON only.\n\n"
                + json.dumps(prompt, ensure_ascii=False)
            ),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        response = ollama_request("generate", payload, base_url=base_url, timeout=600)
        text = clean_text(response.get("response", ""))
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = {
                "pair_id": row["pair_id"],
                "relation_type": "not_related",
                "merge_decision": "unsure",
                "direction": "none",
                "llm_confidence": 0,
                "rationale": f"Could not parse Ollama JSON: {text[:200]}",
            }
        merged = dict(row)
        merged.update(parsed)
        merged["final_merge_confidence"] = final_merge_confidence(merged)
        merged["llm_provider"] = "ollama"
        merged["llm_model"] = model
        results.append(merged)
    return results


def split_llm_results(results):
    confirmed = []
    graph_edges = []
    review = []
    rejected = []
    for row in results:
        relation = row.get("relation_type", "")
        decision = row.get("merge_decision", "")
        conf = float(row.get("final_merge_confidence", 0) or 0)
        if relation in {"duplicate_of", "alias_of"} and decision == "merge" and conf >= 0.85:
            confirmed.append(row)
        elif relation in {"broader_than", "narrower_than", "positively_correlated", "negatively_correlated", "inverse_pole", "conflicts_with", "related_but_distinct"}:
            edge = dict(row)
            llm_conf = float(row.get("llm_confidence", 0) or 0)
            edge["edge_weight"] = round(RELATION_BASE_WEIGHT.get(relation, 0.5) * max(llm_conf, 0.1), 4)
            graph_edges.append(edge)
        elif decision == "unsure" or 0.6 <= conf < 0.85:
            review.append(row)
        else:
            rejected.append(row)
    return confirmed, graph_edges, review, rejected


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_report(backend, pair_rows, llm_results, run_llm, provider, credential_status):
    relation_counts = Counter(row.get("retrieval_relation_hint", "") for row in pair_rows)
    lines = [
        "# Step 5 Embedding + LLM Dedup Report",
        "",
        "Generated by `embedding_llm_dedup_pipeline.py`.",
        "",
        f"- Embedding backend: {backend}",
        f"- LLM provider: {provider}",
        f"- Candidate pairs for LLM: {len(pair_rows)}",
        f"- LLM adjudicated pairs: {len(llm_results)}",
        f"- LLM run requested: {run_llm}",
        f"- Provider status: {credential_status}",
        "",
        "## Retrieval Candidate Types",
        "",
    ]
    for relation, count in relation_counts.most_common():
        lines.append(f"- {relation or 'unspecified'}: {count}")
    lines += [
        "",
        "## Merge Rule",
        "",
        "`final_merge_confidence = 0.45*LLM_confidence + 0.30*embedding_similarity + 0.15*lexical_similarity + 0.10*evidence_support`",
        "",
        "Only merge if `relation_type` is `duplicate_of` or `alias_of`, `merge_decision` is `merge`, and `final_merge_confidence >= 0.85`.",
    ]
    if credential_status != "ready":
        lines += [
            "",
            "## Current Limitation",
            "",
            "This run did not complete external/local LLM adjudication.",
            "For Ollama, install Ollama, start the local server, and pull the embedding and judge models before running with `--provider ollama --run-llm`.",
        ]
    (OUT / "step5_embedding_llm_dedup_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["auto", "openai", "ollama", "fallback"], default="auto")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--ollama-embedding-model", default=DEFAULT_OLLAMA_EMBEDDING_MODEL)
    parser.add_argument("--ollama-llm-model", default=DEFAULT_OLLAMA_LLM_MODEL)
    parser.add_argument("--run-llm", action="store_true")
    parser.add_argument("--max-llm-pairs", type=int, default=200)
    parser.add_argument("--llm-workers", type=int, default=8)
    parser.add_argument("--llm-batch-size", type=int, default=150)
    parser.add_argument("--batch-llm", action="store_true")
    parser.add_argument("--resume-llm", action="store_true")
    parser.add_argument("--reuse-existing-pairs", action="store_true")
    parser.add_argument("--force-fallback-embeddings", action="store_true")
    parser.add_argument("--top-k", type=int, default=25)
    parser.add_argument("--min-similarity", type=float, default=0.62)
    args = parser.parse_args()

    rows = load_attributes()
    attr_by_id = {row["canonical_attribute_id"]: row for row in rows}
    existing_pairs_path = OUT / "combined_pairs_for_llm.csv"
    if args.reuse_existing_pairs and existing_pairs_path.exists():
        with existing_pairs_path.open("r", encoding="utf-8-sig", newline="") as f:
            pair_rows = list(csv.DictReader(f))
        embedding_pairs = []
        backend = "reused_existing_pairs"
    else:
        embeddings, backend = compute_embeddings(
            rows,
            provider=args.provider,
            force_fallback=args.force_fallback_embeddings,
            ollama_url=args.ollama_url,
            ollama_model=args.ollama_embedding_model,
        )
        embedding_pairs = generate_embedding_pairs(rows, embeddings, top_k=args.top_k, min_similarity=args.min_similarity)
        pair_rows = merge_with_step4_pairs(embedding_pairs, rows)
        prompts = [prompt_for_pair(row, attr_by_id) for row in pair_rows]

        write_csv(OUT / "embedding_retrieved_pairs.csv", embedding_pairs)
        write_csv(OUT / "combined_pairs_for_llm.csv", pair_rows)
        write_jsonl(OUT / "combined_pairs_for_llm_prompts.jsonl", prompts)

    api_key = os.environ.get("OPENAI_API_KEY", "")
    credential_status = "ready"
    llm_results = []
    if args.run_llm and args.provider == "openai":
        if not api_key:
            credential_status = "missing_openai_api_key"
        else:
            if args.batch_llm:
                llm_results = openai_llm_adjudicate_batched(
                    pair_rows,
                    attr_by_id,
                    api_key,
                    DEFAULT_LLM_MODEL,
                    args.max_llm_pairs,
                    batch_size=args.llm_batch_size,
                    resume=args.resume_llm,
                )
            else:
                llm_results = openai_llm_adjudicate(
                    pair_rows,
                    attr_by_id,
                    api_key,
                    DEFAULT_LLM_MODEL,
                    args.max_llm_pairs,
                    workers=args.llm_workers,
                    resume=args.resume_llm,
                )
    elif args.run_llm and args.provider == "ollama":
        llm_results = ollama_llm_adjudicate(
            pair_rows,
            attr_by_id,
            args.ollama_url,
            args.ollama_llm_model,
            args.max_llm_pairs,
        )
    elif args.run_llm and args.provider == "auto":
        if api_key:
            if args.batch_llm:
                llm_results = openai_llm_adjudicate_batched(
                    pair_rows,
                    attr_by_id,
                    api_key,
                    DEFAULT_LLM_MODEL,
                    args.max_llm_pairs,
                    batch_size=args.llm_batch_size,
                    resume=args.resume_llm,
                )
            else:
                llm_results = openai_llm_adjudicate(
                    pair_rows,
                    attr_by_id,
                    api_key,
                    DEFAULT_LLM_MODEL,
                    args.max_llm_pairs,
                    workers=args.llm_workers,
                    resume=args.resume_llm,
                )
        else:
            credential_status = "missing_provider_for_auto_mode"

    if llm_results:
        confirmed, graph_edges, review, rejected = split_llm_results(llm_results)
        write_csv(OUT / "llm_adjudicated_pairs.csv", llm_results)
        write_csv(OUT / "llm_confirmed_merges.csv", confirmed)
        write_csv(OUT / "llm_graph_edges.csv", graph_edges)
        write_csv(OUT / "llm_review_needed.csv", review)
        write_csv(OUT / "llm_rejected_pairs.csv", rejected)
    elif args.run_llm:
        for name in [
            "llm_adjudicated_pairs.csv",
            "llm_confirmed_merges.csv",
            "llm_graph_edges.csv",
            "llm_review_needed.csv",
            "llm_rejected_pairs.csv",
        ]:
            (OUT / name).write_text("", encoding="utf-8")

    write_report(backend, pair_rows, llm_results, args.run_llm, args.provider, credential_status)
    print(
        json.dumps(
            {
                "embedding_backend": backend,
                "embedding_retrieved_pairs": len(embedding_pairs),
                "combined_pairs_for_llm": len(pair_rows),
                "llm_adjudicated_pairs": len(llm_results),
                "provider_status": credential_status,
                "output_dir": str(OUT),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
