import csv
import html
import json
import math
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
STEP3 = ROOT / "outputs" / "step3_dedup_categorize"
NORMALIZED = ROOT / "outputs" / "normalized"
OUT = ROOT / "outputs" / "step4_llm_graph"
OUT.mkdir(parents=True, exist_ok=True)

ATTRIBUTES_CSV = STEP3 / "deduped_attributes_high_quality.csv"
STEP3_EDGES_CSV = STEP3 / "related_attribute_edges.csv"
RAW_EXTENDED_NORMALIZED_CSV = NORMALIZED / "candidate_pool_raw_extended_normalized.csv"

MAX_PAIR_CANDIDATES = 5000
MAX_EXTENDED_MAPPING_CANDIDATES = 3000
MAX_IDS_PER_BLOCKING_TOKEN = 80
MAX_RAW_PAIR_BLOCKS_TO_SCORE = 180000

ALLOWED_RELATIONS = [
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
]

QUALITY_TIER_WEIGHT = {
    "A": 1.0,
    "B": 0.72,
    "C": 0.35,
    "Unknown": 0.5,
}

RELATION_BASE_WEIGHT = {
    "duplicate_of": 1.0,
    "alias_of": 0.95,
    "broader_than": 0.78,
    "narrower_than": 0.78,
    "positively_correlated": 0.7,
    "negatively_correlated": 0.7,
    "inverse_pole": 0.86,
    "conflicts_with": 0.82,
    "related_but_distinct": 0.58,
    "possible_duplicate": 0.72,
    "possible_broader_narrower": 0.62,
    "possible_related_or_correlated": 0.48,
    "contains_attribute": 0.22,
    "has_subcategory": 0.4,
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "could",
    "do",
    "does",
    "for",
    "from",
    "has",
    "have",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "r",
    "respondent",
    "respondents",
    "s",
    "the",
    "their",
    "them",
    "they",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "you",
    "your",
}

ANTONYM_RULES = [
    ({"risk", "aversion"}, {"risk", "tolerance"}, "inverse_pole"),
    ({"risk", "avoidance"}, {"risk", "taking"}, "inverse_pole"),
    ({"optimism"}, {"pessimism"}, "inverse_pole"),
    ({"optimistic"}, {"pessimistic"}, "inverse_pole"),
    ({"trust"}, {"distrust"}, "inverse_pole"),
    ({"trust"}, {"mistrust"}, "inverse_pole"),
    ({"extraversion"}, {"introversion"}, "inverse_pole"),
    ({"liberal"}, {"conservative"}, "conflicts_with"),
    ({"liberalism"}, {"conservatism"}, "conflicts_with"),
    ({"support"}, {"oppose"}, "conflicts_with"),
    ({"approval"}, {"disapproval"}, "conflicts_with"),
]


def clean_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    value = str(value).replace("\u00a0", " ").replace("\ufeff", "")
    return re.sub(r"\s+", " ", value).strip()


def slugify(value, max_len=120):
    value = clean_text(value).lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:max_len].strip("_") or "node"


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
    return set(out)


def parse_json_list(value):
    try:
        parsed = json.loads(value or "[]")
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def label_context(row):
    aliases = " ".join(parse_json_list(row.get("aliases_json", ""))[:8])
    return " ".join(
        [row.get("canonical_label", ""), row.get("canonical_name", ""), aliases]
    )


def label_only_context(row):
    aliases = " ".join(parse_json_list(row.get("aliases_json", ""))[:8])
    return " ".join(
        [row.get("canonical_label", ""), row.get("canonical_name", ""), aliases]
    )


def similarity(a, b):
    label_a = clean_text(a.get("canonical_label", "")).lower()
    label_b = clean_text(b.get("canonical_label", "")).lower()
    seq = (
        SequenceMatcher(None, label_a, label_b).ratio() if label_a and label_b else 0.0
    )
    ta = tokens(label_only_context(a))
    tb = tokens(label_only_context(b))
    if not ta or not tb:
        return seq, 0.0, 0.0
    jaccard = len(ta & tb) / len(ta | tb)
    containment = max(len(ta & tb) / len(ta), len(ta & tb) / len(tb))
    return seq, jaccard, containment


def antonym_relation(a, b):
    ta = tokens(label_context(a))
    tb = tokens(label_context(b))
    for left, right, relation in ANTONYM_RULES:
        if left <= ta and right <= tb:
            return relation
        if right <= ta and left <= tb:
            return relation
    return ""


def evidence_weight(row):
    quality = QUALITY_TIER_WEIGHT.get(row.get("quality_tier", "Unknown"), 0.5)
    try:
        source_count = int(row.get("source_count", "1") or 1)
    except Exception:
        source_count = 1
    try:
        candidate_count = int(row.get("candidate_count", "1") or 1)
    except Exception:
        candidate_count = 1
    support = min(
        1.0, 0.55 + 0.15 * math.log1p(source_count) + 0.08 * math.log1p(candidate_count)
    )
    return round(quality * support, 4)


def node_weight(row):
    try:
        candidate_count = int(row.get("candidate_count", "1") or 1)
    except Exception:
        candidate_count = 1
    return round(evidence_weight(row) * (1 + math.log1p(candidate_count)), 4)


def proposed_edge_weight(relation, heuristic_score):
    base = RELATION_BASE_WEIGHT.get(relation, 0.45)
    return round(min(1.0, max(0.05, base * (0.55 + 0.45 * float(heuristic_score)))), 4)


def infer_pair_candidate(a, b):
    seq, label_jaccard, label_containment = similarity(a, b)
    same_category = a["final_primary_category"] == b["final_primary_category"]
    same_subcategory = a["final_subcategory"] == b["final_subcategory"]
    ta = tokens(label_only_context(a))
    tb = tokens(label_only_context(b))
    context_a = tokens(label_context(a))
    context_b = tokens(label_context(b))
    context_jaccard = (
        len(context_a & context_b) / len(context_a | context_b)
        if context_a and context_b
        else 0.0
    )
    context_containment = (
        max(
            len(context_a & context_b) / len(context_a),
            len(context_a & context_b) / len(context_b),
        )
        if context_a and context_b
        else 0.0
    )
    antonym = antonym_relation(a, b)

    if antonym:
        return antonym, 0.92, "explicit_antonym_or_opposite_pole_rule"

    if same_category and (seq >= 0.92 or label_jaccard >= 0.82 or (ta == tb and ta)):
        return (
            "possible_duplicate",
            max(seq, label_jaccard, label_containment),
            "high_label_or_token_similarity",
        )

    if same_category and label_containment >= 0.9 and abs(len(ta) - len(tb)) >= 1:
        return (
            "possible_broader_narrower",
            label_containment,
            "one_label_tokens_contained_in_other",
        )

    if same_subcategory and (context_jaccard >= 0.34 or context_containment >= 0.58):
        return (
            "possible_related_or_correlated",
            max(context_jaccard, context_containment),
            "same_subcategory_token_overlap",
        )

    if same_category and context_jaccard >= 0.45:
        return (
            "possible_related_or_correlated",
            context_jaccard,
            "same_category_token_overlap",
        )

    return "", 0.0, ""


def load_attributes():
    df = pd.read_csv(ATTRIBUTES_CSV, dtype=str, keep_default_na=False)
    rows = df.to_dict(orient="records")
    for row in rows:
        row["_tokens"] = tokens(label_context(row))
    return rows


def build_inverted_index(rows):
    by_category = defaultdict(list)
    for row in rows:
        by_category[row["final_primary_category"]].append(row)

    pair_counts = Counter()
    for category, group in by_category.items():
        token_df = Counter()
        for row in group:
            token_df.update(row["_tokens"])
        useful_tokens = {
            t for t, c in token_df.items() if 2 <= c <= MAX_IDS_PER_BLOCKING_TOKEN
        }
        token_index = defaultdict(list)
        for row in group:
            for token in row["_tokens"] & useful_tokens:
                token_index[token].append(row["canonical_attribute_id"])
        for ids in token_index.values():
            ids = sorted(set(ids))
            if len(ids) > MAX_IDS_PER_BLOCKING_TOKEN:
                continue
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    pair_counts[(ids[i], ids[j])] += 1
                    if len(pair_counts) >= MAX_RAW_PAIR_BLOCKS_TO_SCORE:
                        return pair_counts
    return pair_counts


def generate_pair_candidates(rows):
    by_id = {row["canonical_attribute_id"]: row for row in rows}
    pair_counts = build_inverted_index(rows)
    candidates = []
    seen = set()
    for (left_id, right_id), shared_token_count in pair_counts.most_common(
        MAX_RAW_PAIR_BLOCKS_TO_SCORE
    ):
        a = by_id[left_id]
        b = by_id[right_id]
        relation, score, reason = infer_pair_candidate(a, b)
        if not relation:
            continue
        pair_id = f"pair_{slugify(left_id, 40)}__{slugify(right_id, 40)}"
        key = tuple(sorted([left_id, right_id]))
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "pair_id": pair_id,
                "source_attribute_id": left_id,
                "target_attribute_id": right_id,
                "source_label": a["canonical_label"],
                "target_label": b["canonical_label"],
                "source_category": a["final_primary_category"],
                "target_category": b["final_primary_category"],
                "source_subcategory": a["final_subcategory"],
                "target_subcategory": b["final_subcategory"],
                "source_definition": a["normalized_definition"],
                "target_definition": b["normalized_definition"],
                "source_sources_json": a["sources_json"],
                "target_sources_json": b["sources_json"],
                "heuristic_relation_candidate": relation,
                "heuristic_score": round(score, 4),
                "proposed_edge_weight": proposed_edge_weight(relation, score),
                "weight_basis": "relation_base_weight * heuristic_score; replace with LLM confidence/strength after adjudication",
                "shared_token_count": shared_token_count,
                "heuristic_reason": reason,
                "llm_status": "needs_llm_adjudication",
            }
        )

    relation_priority = {
        "possible_duplicate": 5,
        "possible_broader_narrower": 4,
        "inverse_pole": 4,
        "conflicts_with": 4,
        "possible_related_or_correlated": 3,
    }
    candidates.sort(
        key=lambda r: (
            relation_priority.get(r["heuristic_relation_candidate"], 0),
            float(r["heuristic_score"]),
            int(r["shared_token_count"]),
        ),
        reverse=True,
    )
    return candidates[:MAX_PAIR_CANDIDATES]


def llm_pair_prompt(row):
    return {
        "task": "adjudicate_persona_attribute_pair",
        "allowed_relation_types": ALLOWED_RELATIONS,
        "instructions": [
            "Decide whether two persona attribute candidates should be merged or linked in the graph.",
            "Use duplicate_of or alias_of only when they represent the same attribute/construct.",
            "Use broader_than/narrower_than for taxonomy hierarchy.",
            "Use positively_correlated or negatively_correlated only when the relation is conceptually expected, not merely same category.",
            "Use inverse_pole for opposite ends of one construct, and conflicts_with for mutually inconsistent beliefs/attitudes.",
            "Use related_but_distinct when they should be connected but not merged.",
            "Use not_related when the heuristic candidate is spurious.",
            "Return compact JSON only.",
        ],
        "input_pair": {
            "pair_id": row["pair_id"],
            "heuristic_relation_candidate": row["heuristic_relation_candidate"],
            "attribute_a": {
                "id": row["source_attribute_id"],
                "label": row["source_label"],
                "category": row["source_category"],
                "subcategory": row["source_subcategory"],
                "definition": row["source_definition"],
                "sources": row["source_sources_json"],
            },
            "attribute_b": {
                "id": row["target_attribute_id"],
                "label": row["target_label"],
                "category": row["target_category"],
                "subcategory": row["target_subcategory"],
                "definition": row["target_definition"],
                "sources": row["target_sources_json"],
            },
        },
        "output_schema": {
            "pair_id": "string",
            "relation_type": ALLOWED_RELATIONS,
            "merge_decision": "merge | keep_separate | unsure",
            "direction": "A_to_B | B_to_A | symmetric | none",
            "confidence": "0.0-1.0",
            "rationale": "short explanation",
        },
    }


def generate_extended_mapping_candidates(attributes):
    if not RAW_EXTENDED_NORMALIZED_CSV.exists():
        return []

    attrs_by_category = defaultdict(list)
    attr_token_index_by_category = defaultdict(lambda: defaultdict(list))
    for attr in attributes:
        attrs_by_category[attr["final_primary_category"]].append(attr)
        for token in attr["_tokens"]:
            attr_token_index_by_category[attr["final_primary_category"]][token].append(
                attr
            )

    raw_df = pd.read_csv(RAW_EXTENDED_NORMALIZED_CSV, dtype=str, keep_default_na=False)
    raw_rows = raw_df.to_dict(orient="records")
    extended = [
        row
        for row in raw_rows
        if "DeepPersona" in row.get("source", "")
        or row.get("source_family") == "llm_mined"
    ]

    candidates = []
    for row in extended:
        label = clean_text(row.get("canonical_label", ""))
        if not label:
            continue
        category = row.get("normalized_primary_category", "")
        row_tokens = tokens(
            " ".join(
                [
                    label,
                    row.get("normalized_subcategory", ""),
                    row.get("normalized_definition", ""),
                ]
            )
        )
        if not row_tokens:
            continue
        token_index = attr_token_index_by_category.get(category, {})
        candidate_attrs = {}
        for token in row_tokens:
            attrs = token_index.get(token, [])
            if len(attrs) > MAX_IDS_PER_BLOCKING_TOKEN:
                continue
            for attr in attrs:
                candidate_attrs[attr["canonical_attribute_id"]] = attr
        scored = []
        for attr in candidate_attrs.values():
            inter = row_tokens & attr["_tokens"]
            if not inter:
                continue
            jaccard = len(inter) / len(row_tokens | attr["_tokens"])
            containment = max(
                len(inter) / len(row_tokens), len(inter) / len(attr["_tokens"])
            )
            seq = SequenceMatcher(
                None, label.lower(), attr["canonical_label"].lower()
            ).ratio()
            score = max(jaccard, containment, seq)
            if score >= 0.58:
                scored.append((score, len(inter), attr))
        for score, shared, attr in sorted(
            scored, key=lambda x: (x[0], x[1]), reverse=True
        )[:3]:
            candidates.append(
                {
                    "mapping_candidate_id": f"map_{slugify(row['candidate_id'], 52)}__{slugify(attr['canonical_attribute_id'], 52)}",
                    "extended_candidate_id": row["candidate_id"],
                    "extended_source": row["source"],
                    "extended_label": label,
                    "extended_category": category,
                    "canonical_attribute_id": attr["canonical_attribute_id"],
                    "canonical_label": attr["canonical_label"],
                    "canonical_category": attr["final_primary_category"],
                    "heuristic_score": round(score, 4),
                    "proposed_mapping_weight": proposed_edge_weight(
                        "possible_duplicate", score
                    ),
                    "weight_basis": "candidate-to-canonical mapping similarity; replace with LLM confidence after adjudication",
                    "shared_token_count": shared,
                    "llm_status": "needs_llm_mapping_adjudication",
                }
            )

    candidates.sort(
        key=lambda r: (float(r["heuristic_score"]), int(r["shared_token_count"])),
        reverse=True,
    )
    return candidates[:MAX_EXTENDED_MAPPING_CANDIDATES]


def build_graph_nodes(attributes):
    nodes = []
    categories = sorted(set(a["final_primary_category"] for a in attributes))
    for category in categories:
        count = sum(1 for a in attributes if a["final_primary_category"] == category)
        nodes.append(
            {
                "node_id": f"cat::{slugify(category)}",
                "node_type": "category",
                "label": category,
                "category": category,
                "subcategory": "",
                "size": count,
                "node_weight": round(1 + math.log1p(count), 4),
                "evidence_weight": "",
                "weight_basis": "log scaled number of attributes in category",
                "quality_tier": "",
                "source_count": "",
            }
        )

    subcats = Counter(
        (a["final_primary_category"], a["final_subcategory"]) for a in attributes
    )
    for (category, subcategory), count in sorted(subcats.items()):
        nodes.append(
            {
                "node_id": f"subcat::{slugify(category, 50)}::{slugify(subcategory, 80)}",
                "node_type": "subcategory",
                "label": subcategory,
                "category": category,
                "subcategory": subcategory,
                "size": count,
                "node_weight": round(0.6 + math.log1p(count), 4),
                "evidence_weight": "",
                "weight_basis": "log scaled number of attributes in subcategory",
                "quality_tier": "",
                "source_count": "",
            }
        )

    for attr in attributes:
        nodes.append(
            {
                "node_id": attr["canonical_attribute_id"],
                "node_type": "attribute",
                "label": attr["canonical_label"],
                "category": attr["final_primary_category"],
                "subcategory": attr["final_subcategory"],
                "size": attr.get("candidate_count", "1"),
                "node_weight": node_weight(attr),
                "evidence_weight": evidence_weight(attr),
                "weight_basis": "quality tier * source support * candidate support",
                "quality_tier": attr.get("quality_tier", ""),
                "source_count": attr.get("source_count", ""),
            }
        )
    return nodes


def build_graph_edges(attributes):
    edges = []
    seen = set()

    def add_edge(
        source,
        target,
        relation,
        status,
        confidence="",
        reason="",
        weight=None,
        weight_basis="",
    ):
        key = (source, target, relation)
        if key in seen:
            return
        seen.add(key)
        if weight is None:
            weight = RELATION_BASE_WEIGHT.get(relation, 0.5)
        edges.append(
            {
                "edge_id": f"edge_{len(edges) + 1:07d}",
                "source_node_id": source,
                "target_node_id": target,
                "relation_type": relation,
                "edge_status": status,
                "edge_weight": round(float(weight), 4),
                "confidence_score": confidence,
                "weight_basis": weight_basis or "relation base weight",
                "reason": reason,
            }
        )

    subcat_counts = Counter(
        (a["final_primary_category"], a["final_subcategory"]) for a in attributes
    )
    for category, subcategory in sorted(subcat_counts):
        add_edge(
            f"cat::{slugify(category)}",
            f"subcat::{slugify(category, 50)}::{slugify(subcategory, 80)}",
            "has_subcategory",
            "schema_edge",
            "1.0",
            "category hierarchy",
            weight=round(
                min(2.5, 0.4 + math.log1p(subcat_counts[(category, subcategory)]) / 3),
                4,
            ),
            weight_basis="category-subcategory structural edge, log scaled by subcategory size",
        )
    for attr in attributes:
        add_edge(
            f"subcat::{slugify(attr['final_primary_category'], 50)}::{slugify(attr['final_subcategory'], 80)}",
            attr["canonical_attribute_id"],
            "contains_attribute",
            "schema_edge",
            "1.0",
            "subcategory membership",
            weight=round(0.18 + 0.12 * evidence_weight(attr), 4),
            weight_basis="weak structural membership edge weighted by attribute evidence",
        )

    if STEP3_EDGES_CSV.exists():
        df = pd.read_csv(STEP3_EDGES_CSV, dtype=str, keep_default_na=False)
        for _, row in df.iterrows():
            add_edge(
                row["source_attribute_id"],
                row["target_attribute_id"],
                row["relation_type"],
                "rule_seed",
                row.get("confidence", "rule_seed"),
                row.get("reason", ""),
                weight=RELATION_BASE_WEIGHT.get(row["relation_type"], 0.65),
                weight_basis="conservative rule-seed attribute relation",
            )
    return edges


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_graphml(path, nodes, edges):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="label" for="all" attr.name="label" attr.type="string"/>',
        '  <key id="node_type" for="node" attr.name="node_type" attr.type="string"/>',
        '  <key id="category" for="node" attr.name="category" attr.type="string"/>',
        '  <key id="node_weight" for="node" attr.name="node_weight" attr.type="double"/>',
        '  <key id="relation_type" for="edge" attr.name="relation_type" attr.type="string"/>',
        '  <key id="edge_status" for="edge" attr.name="edge_status" attr.type="string"/>',
        '  <key id="edge_weight" for="edge" attr.name="edge_weight" attr.type="double"/>',
        '  <graph id="persona_attribute_graph_seed" edgedefault="directed">',
    ]
    for node in nodes:
        node_id = html.escape(node["node_id"], quote=True)
        lines.append(f'    <node id="{node_id}">')
        for key in ["label", "node_type", "category", "node_weight"]:
            lines.append(
                f'      <data key="{key}">{html.escape(str(node.get(key, "")))}</data>'
            )
        lines.append("    </node>")
    for edge in edges:
        source = html.escape(edge["source_node_id"], quote=True)
        target = html.escape(edge["target_node_id"], quote=True)
        edge_id = html.escape(edge["edge_id"], quote=True)
        lines.append(f'    <edge id="{edge_id}" source="{source}" target="{target}">')
        for key in ["relation_type", "edge_status", "edge_weight", "label"]:
            value = (
                edge.get("relation_type", "") if key == "label" else edge.get(key, "")
            )
            lines.append(f'      <data key="{key}">{html.escape(str(value))}</data>')
        lines.append("    </edge>")
    lines += ["  </graph>", "</graphml>"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_instructions(pair_count, mapping_count):
    text = f"""# LLM Deduplication and Relation Adjudication Instructions

Generated by `prepare_llm_dedup_and_graph.py`.

## Goal

Use an LLM to adjudicate whether candidate persona attributes should be merged, linked, or kept separate before drawing the final attribute graph.

## Pair Review

Input file:

- `llm_pair_adjudication_prompts.jsonl`

Each line is one JSON object with two attributes. The LLM should return compact JSON with:

- `pair_id`
- `relation_type`
- `merge_decision`
- `direction`
- `confidence`
- `rationale`

Allowed relation types:

{json.dumps(ALLOWED_RELATIONS, indent=2)}

Use `duplicate_of` or `alias_of` only when two labels represent the same persona attribute/construct. Use `related_but_distinct`, `positively_correlated`, `negatively_correlated`, `inverse_pole`, or `conflicts_with` when they should be graph edges but not merged.

## Extended Source Mapping

Input file:

- `llm_extended_mapping_prompts.jsonl`

This file is for low-evidence / LLM-mined / DeepPersona-style candidates. The LLM should decide whether the extended candidate maps to an existing canonical attribute, should become a new candidate, or should be rejected as non-attribute / too vague.

## Counts

- Pair adjudication prompts: {pair_count}
- Extended mapping prompts: {mapping_count}

## Graph Files

- `graph_nodes.csv`
- `graph_edges_seed.csv`
- `persona_attribute_graph_seed.graphml`

The seed graph contains category/subcategory membership edges and conservative rule-seed relation edges. LLM-adjudicated relation outputs should be appended as attribute-attribute edges.
"""
    (OUT / "llm_adjudication_instructions.md").write_text(text, encoding="utf-8")


def write_report(
    attributes, pair_candidates, mapping_candidates, graph_nodes, graph_edges
):
    relation_counts = Counter(
        p["heuristic_relation_candidate"] for p in pair_candidates
    )
    category_counts = Counter(a["final_primary_category"] for a in attributes)
    report = [
        "# Step 4 LLM Graph Preparation Report",
        "",
        "Generated by `prepare_llm_dedup_and_graph.py`.",
        "",
        f"- Canonical high-quality attributes: {len(attributes)}",
        f"- LLM pair adjudication candidates: {len(pair_candidates)}",
        f"- Extended / DeepPersona mapping candidates: {len(mapping_candidates)}",
        f"- Graph nodes: {len(graph_nodes)}",
        f"- Graph seed edges: {len(graph_edges)}",
        "",
        "## Pair Candidate Types",
        "",
    ]
    for relation, count in relation_counts.most_common():
        report.append(f"- {relation}: {count}")
    report += ["", "## Category Counts", ""]
    for category, count in category_counts.most_common():
        report.append(f"- {category}: {count}")
    report += [
        "",
        "## Important Note",
        "",
        "No external LLM API key was available in the environment, so this step generated LLM-ready prompts and a graph seed instead of claiming completed LLM adjudication.",
        "Run the prompts through an LLM, then append confirmed relation outputs to the graph edge table.",
    ]
    (OUT / "step4_llm_graph_report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )


def main():
    attributes = load_attributes()
    pair_candidates = generate_pair_candidates(attributes)
    mapping_candidates = generate_extended_mapping_candidates(attributes)
    graph_nodes = build_graph_nodes(attributes)
    graph_edges = build_graph_edges(attributes)

    write_csv(OUT / "llm_pair_adjudication_candidates.csv", pair_candidates)
    write_jsonl(OUT / "llm_pair_adjudication_candidates.jsonl", pair_candidates)
    write_jsonl(
        OUT / "llm_pair_adjudication_prompts.jsonl",
        [llm_pair_prompt(row) for row in pair_candidates],
    )

    write_csv(OUT / "extended_mapping_candidates_for_llm.csv", mapping_candidates)
    write_jsonl(OUT / "extended_mapping_candidates_for_llm.jsonl", mapping_candidates)
    write_jsonl(
        OUT / "llm_extended_mapping_prompts.jsonl",
        [
            {
                "task": "map_low_evidence_candidate_to_canonical_persona_attribute",
                "instructions": [
                    "Decide whether the extended/LLM-mined candidate maps to the canonical attribute.",
                    "Return compact JSON with mapping_decision: map_to_existing | new_attribute_candidate | reject_non_attribute | unsure.",
                ],
                "input": row,
            }
            for row in mapping_candidates
        ],
    )

    write_csv(OUT / "graph_nodes.csv", graph_nodes)
    write_csv(OUT / "graph_edges_seed.csv", graph_edges)
    write_graphml(
        OUT / "persona_attribute_graph_seed.graphml", graph_nodes, graph_edges
    )
    write_instructions(len(pair_candidates), len(mapping_candidates))
    write_report(
        attributes, pair_candidates, mapping_candidates, graph_nodes, graph_edges
    )

    print(
        json.dumps(
            {
                "canonical_attributes": len(attributes),
                "pair_candidates_for_llm": len(pair_candidates),
                "extended_mapping_candidates_for_llm": len(mapping_candidates),
                "graph_nodes": len(graph_nodes),
                "graph_seed_edges": len(graph_edges),
                "output_dir": str(OUT),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
