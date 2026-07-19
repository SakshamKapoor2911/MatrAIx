import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = (
    ROOT
    / "outputs"
    / "normalized"
    / "candidate_pool_high_quality_normalized.csv"
)
OUT = ROOT / "outputs" / "step3_dedup_categorize"
OUT.mkdir(parents=True, exist_ok=True)


SOURCE_FAMILY_PRIORITY = {
    "psychometric": 6,
    "validated_theory": 6,
    "official_population_survey": 5,
    "official_survey": 5,
    "research_dataset": 4,
    "persona_dataset": 3,
    "local_project": 3,
    "llm_mined": 1,
    "other": 0,
}

LICENSE_RISK_RANK = {
    "low": 1,
    "medium": 2,
    "unknown": 3,
    "medium_high": 4,
}

GENERIC_FREE_TEXT_PATTERNS = [
    r"please explain",
    r"explain your answer",
    r"question above",
    r"provide 2 4 sentences",
    r"provide 2-4 sentences",
    r"other specify",
    r"other / specify",
    r"write in",
    r"^comment$",
    r"^comments$",
]

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
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


class UnionFind:
    def __init__(self, items):
        self.parent = {item: item for item in items}

    def find(self, item):
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, a, b):
        ra = self.find(a)
        rb = self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def clean_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    value = str(value).replace("\u00a0", " ").replace("\ufeff", "")
    return re.sub(r"\s+", " ", value).strip()


def slugify(value, max_len=100):
    value = clean_text(value).lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:max_len].strip("_") or "attribute"


def label_text(row):
    return f"{row.get('canonical_label', '')} {row.get('canonical_name', '')} {row.get('normalized_definition', '')}".lower()


def token_set(label):
    text = clean_text(label).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = []
    for token in text.split():
        if token in STOPWORDS or len(token) <= 1:
            continue
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        tokens.append(token)
    return set(tokens)


def label_similarity(a, b):
    a = clean_text(a).lower()
    b = clean_text(b).lower()
    if not a or not b:
        return 0.0
    sequence = SequenceMatcher(None, a, b).ratio()
    ta = token_set(a)
    tb = token_set(b)
    if not ta or not tb:
        return sequence
    jaccard = len(ta & tb) / len(ta | tb)
    return max(sequence, jaccard)


def is_generic_or_free_text(row):
    text = label_text(row)
    if row.get("normalized_data_type") == "free_text":
        return True
    if any(re.search(pattern, text) for pattern in GENERIC_FREE_TEXT_PATTERNS):
        return True
    label = clean_text(row.get("canonical_label", "")).lower()
    return label in {
        "other",
        "none",
        "not applicable",
        "unknown",
        "refused",
        "do not know",
    }


def non_attribute_artifact_reason(row):
    label = clean_text(row.get("canonical_label", ""))
    label_norm = re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()
    data_type = row.get("normalized_data_type", "")

    if re.search(
        r"\bplease explain\b|\bexplain your answer\b|\bquestion above\b", label_norm
    ):
        return "explanation_prompt_not_attribute"
    if re.search(
        r"\bother specify\b|\bother please specify\b|\bwrite in\b", label_norm
    ):
        return "other_specify_field_not_attribute"
    if label_norm in {
        "other",
        "none",
        "not applicable",
        "unknown",
        "refused",
        "do not know",
    }:
        return "generic_response_option_not_attribute"
    if data_type == "free_text" and any(
        re.search(pattern, label_norm) for pattern in GENERIC_FREE_TEXT_PATTERNS
    ):
        return "generic_free_text_prompt_not_attribute"
    return ""


def is_non_attribute_artifact(row):
    return bool(non_attribute_artifact_reason(row))


def relation_hint(a, b):
    if "/" in a.get("canonical_label", "") and "/" in b.get("canonical_label", ""):
        if token_set(a.get("canonical_label", "")) == token_set(
            b.get("canonical_label", "")
        ):
            return "", ""

    ca = slugify(a.get("canonical_label", ""), 200)
    cb = slugify(b.get("canonical_label", ""), 200)
    pair = f"{ca} || {cb}"
    reverse_pair = f"{cb} || {ca}"
    joined = f"{pair} || {reverse_pair}"

    def has(left, right):
        return left in ca and right in cb or left in cb and right in ca

    if has("risk_aversion", "risk_tolerance"):
        return (
            "inverse_pole",
            "Risk aversion and risk tolerance are inverse but not identical constructs.",
        )
    if (
        "risk_aversion" in joined
        or "risk_tolerance" in joined
        or "risk_taking" in joined
    ) and ("sensation_seeking" in joined or "thrill_seeking" in joined):
        return (
            "related_but_distinct",
            "Risk orientation and sensation/thrill seeking should be linked but not automatically merged.",
        )
    if has("optimism", "pessimism"):
        return "inverse_pole", "Optimism and pessimism are opposite-valence constructs."
    if has("extraversion", "introversion"):
        return (
            "opposite_trait_pole",
            "Extraversion and introversion are opposite poles, not duplicate labels.",
        )
    precise_liberal = ca in {"liberal", "liberalism", "political_liberalism"} or cb in {
        "liberal",
        "liberalism",
        "political_liberalism",
    }
    precise_conservative = ca in {
        "conservative",
        "conservatism",
        "political_conservatism",
    } or cb in {"conservative", "conservatism", "political_conservatism"}
    if precise_liberal and precise_conservative:
        return (
            "opposite_attitude_pole",
            "Liberal and conservative orientations should remain distinct.",
        )
    return "", ""


def refine_category(row):
    category = row["normalized_primary_category"]
    subcategory = row["normalized_subcategory"]
    text = label_text(row)
    source_family = row.get("source_family", "")

    if (
        source_family != "psychometric"
        and "trust" in text
        and not any(k in text for k in ["trust fund", "trustee"])
    ):
        return (
            "Worldview, Beliefs & Attitudes",
            "social and institutional trust",
            "trust keyword refinement",
        )

    if any(
        k in text
        for k in [
            "risk_aversion",
            "risk tolerance",
            "risk_tolerance",
            "sensation_seeking",
            "thrill_seeking",
        ]
    ):
        return (
            "Personality Traits",
            "risk orientation and sensation seeking",
            "risk/sensation construct refinement",
        )

    if "risk_taking" in text or "risk-taking" in text:
        if "attitude" in text:
            return (
                "Worldview, Beliefs & Attitudes",
                "risk attitudes",
                "risk attitude refinement",
            )
        return (
            "Personality Traits",
            "risk orientation and sensation seeking",
            "risk-taking construct refinement",
        )

    if source_family != "psychometric" and any(
        k in text for k in ["religion", "religious", "church", "faith in god"]
    ):
        return (
            "Worldview, Beliefs & Attitudes",
            "religiosity and spiritual beliefs",
            "religion keyword refinement",
        )

    return category, subcategory, "kept_normalized_category"


def can_auto_merge(a, b, mode):
    if a["final_primary_category"] != b["final_primary_category"]:
        return False
    if is_generic_or_free_text(a) or is_generic_or_free_text(b):
        return False
    if relation_hint(a, b)[0]:
        return False
    if mode == "strict":
        return True

    sim = label_similarity(a["canonical_label"], b["canonical_label"])
    if sim >= 0.97:
        return True
    if token_set(a["canonical_label"]) == token_set(b["canonical_label"]):
        if "/" in a["canonical_label"] or "/" in b["canonical_label"]:
            return True
    return False


def load_rows():
    df = pd.read_csv(INPUT, dtype=str, keep_default_na=False)
    rows = df.to_dict(orient="records")
    for row in rows:
        final_category, final_subcategory, reason = refine_category(row)
        row["final_primary_category"] = final_category
        row["final_subcategory"] = final_subcategory
        row["category_refinement_reason"] = reason
        row["step3_dedup_key_strict"] = (
            f"{slugify(final_category, 50)}::{slugify(row['canonical_label'], 110)}"
        )
        row["step3_dedup_key_loose"] = (
            f"{slugify(final_category, 50)}::{'_'.join(sorted(token_set(row['canonical_label']))[:12])}"
        )
    return rows


def build_auto_merge_clusters(rows):
    by_id = {row["candidate_id"]: row for row in rows}
    uf = UnionFind(by_id)
    merge_reasons = defaultdict(set)

    for key, group in group_by(rows, "step3_dedup_key_strict").items():
        eligible = [r for r in group if not is_generic_or_free_text(r)]
        for row in eligible[1:]:
            if can_auto_merge(eligible[0], row, "strict"):
                uf.union(eligible[0]["candidate_id"], row["candidate_id"])
                merge_reasons[eligible[0]["candidate_id"]].add(
                    "auto_merge_exact_strict_key"
                )
                merge_reasons[row["candidate_id"]].add("auto_merge_exact_strict_key")

    for key, group in group_by(rows, "step3_dedup_key_loose").items():
        if len(group) < 2 or len(group) > 80:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if uf.find(a["candidate_id"]) == uf.find(b["candidate_id"]):
                    continue
                if can_auto_merge(a, b, "loose"):
                    uf.union(a["candidate_id"], b["candidate_id"])
                    merge_reasons[a["candidate_id"]].add("auto_merge_strong_loose_key")
                    merge_reasons[b["candidate_id"]].add("auto_merge_strong_loose_key")

    clusters = defaultdict(list)
    for row in rows:
        clusters[uf.find(row["candidate_id"])].append(row)
    return clusters, merge_reasons


def representative_row(cluster):
    def score(row):
        return (
            int(float(row.get("normalized_quality_score") or 0)),
            SOURCE_FAMILY_PRIORITY.get(row.get("source_family", ""), 0),
            0 if is_generic_or_free_text(row) else 1,
            len(row.get("normalized_definition", "")),
        )

    return sorted(cluster, key=score, reverse=True)[0]


def cluster_id(rep, cluster):
    base = f"{rep['final_primary_category']}|{rep['canonical_label']}|{'|'.join(sorted(r['candidate_id'] for r in cluster))}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]
    return f"attr_{slugify(rep['final_primary_category'], 28)}__{slugify(rep['canonical_label'], 54)}__{digest}"


def parse_json_list(value):
    try:
        parsed = json.loads(value or "[]")
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def merged_aliases(cluster, rep):
    aliases = []
    for row in cluster:
        for alias in parse_json_list(row.get("alias_candidates_json", "")):
            alias = clean_text(alias)
            if alias and alias.lower() not in {a.lower() for a in aliases}:
                aliases.append(alias)
    if rep["canonical_label"].lower() not in {a.lower() for a in aliases}:
        aliases.insert(0, rep["canonical_label"])
    return aliases[:25]


def worst_license_risk(cluster):
    risks = [r.get("license_risk", "unknown") for r in cluster]
    return sorted(risks, key=lambda x: LICENSE_RISK_RANK.get(x, 3), reverse=True)[0]


def cluster_merge_status(cluster, merge_reasons):
    if len(cluster) == 1:
        return "singleton"
    reasons = set()
    for row in cluster:
        reasons.update(merge_reasons.get(row["candidate_id"], set()))
    if "auto_merge_strong_loose_key" in reasons:
        return "auto_merged_strong"
    if "auto_merge_exact_strict_key" in reasons:
        return "auto_merged_exact"
    return "clustered"


def build_deduped_attributes(clusters, merge_reasons):
    attributes = []
    assignments = []
    for cluster in clusters.values():
        rep = representative_row(cluster)
        attr_id = cluster_id(rep, cluster)
        status = cluster_merge_status(cluster, merge_reasons)
        source_counts = Counter(r["source"] for r in cluster)
        family_counts = Counter(r["source_family"] for r in cluster)
        tier_counts = Counter(r["quality_tier"] for r in cluster)
        dtype_counts = Counter(r["normalized_data_type"] for r in cluster)
        measurement_counts = Counter(r["measurement_level"] for r in cluster)
        subcat_counts = Counter(r["final_subcategory"] for r in cluster)

        attributes.append(
            {
                "canonical_attribute_id": attr_id,
                "canonical_label": rep["canonical_label"],
                "canonical_name": slugify(rep["canonical_label"]),
                "final_primary_category": rep["final_primary_category"],
                "final_subcategory": subcat_counts.most_common(1)[0][0],
                "representative_candidate_id": rep["candidate_id"],
                "representative_source": rep["source"],
                "representative_source_family": rep["source_family"],
                "normalized_definition": rep["normalized_definition"],
                "normalized_data_type": dtype_counts.most_common(1)[0][0],
                "measurement_level": measurement_counts.most_common(1)[0][0],
                "quality_tier": tier_counts.most_common(1)[0][0],
                "max_normalized_quality_score": max(
                    int(float(r.get("normalized_quality_score") or 0)) for r in cluster
                ),
                "license_risk": worst_license_risk(cluster),
                "candidate_count": len(cluster),
                "source_count": len(source_counts),
                "merge_status": status,
                "sources_json": json.dumps(dict(source_counts), ensure_ascii=False),
                "source_families_json": json.dumps(
                    dict(family_counts), ensure_ascii=False
                ),
                "aliases_json": json.dumps(
                    merged_aliases(cluster, rep), ensure_ascii=False
                ),
                "candidate_ids_json": json.dumps(
                    [r["candidate_id"] for r in cluster], ensure_ascii=False
                ),
                "category_refinement_reasons_json": json.dumps(
                    dict(Counter(r["category_refinement_reason"] for r in cluster)),
                    ensure_ascii=False,
                ),
                "needs_review": any(
                    str(r.get("needs_review", "")).lower() == "true" for r in cluster
                )
                or status != "singleton",
            }
        )

        for row in cluster:
            assignment = dict(row)
            assignment.update(
                {
                    "canonical_attribute_id": attr_id,
                    "dedup_cluster_size": len(cluster),
                    "dedup_status": status,
                    "dedup_merge_reasons_json": json.dumps(
                        sorted(merge_reasons.get(row["candidate_id"], set())),
                        ensure_ascii=False,
                    ),
                }
            )
            assignments.append(assignment)

    attributes.sort(
        key=lambda r: (
            r["final_primary_category"],
            r["final_subcategory"],
            r["canonical_label"].lower(),
        )
    )
    assignments.sort(key=lambda r: (r["canonical_attribute_id"], r["candidate_id"]))
    return attributes, assignments


def build_review_clusters(rows, assignments):
    attr_by_candidate = {
        r["candidate_id"]: r["canonical_attribute_id"] for r in assignments
    }
    review_rows = []
    counter = 0
    for key, group in group_by(rows, "step3_dedup_key_loose").items():
        attr_ids = sorted(set(attr_by_candidate[r["candidate_id"]] for r in group))
        if len(attr_ids) <= 1:
            continue
        relation_types = Counter()
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                rel, _ = relation_hint(group[i], group[j])
                if rel:
                    relation_types[rel] += 1
        counter += 1
        labels = sorted(set(r["canonical_label"] for r in group))
        review_rows.append(
            {
                "review_cluster_id": f"review_{counter:05d}",
                "step3_dedup_key_loose": key,
                "final_primary_category": Counter(
                    r["final_primary_category"] for r in group
                ).most_common(1)[0][0],
                "candidate_count": len(group),
                "canonical_attribute_count": len(attr_ids),
                "candidate_labels_json": json.dumps(labels[:40], ensure_ascii=False),
                "canonical_attribute_ids_json": json.dumps(
                    attr_ids, ensure_ascii=False
                ),
                "review_reason": "related_not_duplicate"
                if relation_types
                else "same_loose_key_needs_human_review",
                "relation_hints_json": json.dumps(
                    dict(relation_types), ensure_ascii=False
                ),
            }
        )
    return review_rows


def build_relation_edges(attributes):
    edges = []
    attrs = attributes

    def contains(attr, terms):
        hay = f"{attr['canonical_name']} {attr['canonical_label']}".lower()
        return any(term in hay for term in terms)

    relation_rules = [
        (
            ["risk_aversion"],
            ["risk_tolerance"],
            "inverse_pole",
            "Risk aversion and risk tolerance are inverse but should not be merged.",
        ),
        (
            ["risk_aversion", "risk_tolerance", "risk_taking"],
            ["sensation_seeking", "thrill_seeking"],
            "related_but_distinct",
            "Risk orientation and sensation/thrill seeking are related but distinct constructs.",
        ),
        (
            ["optimism"],
            ["pessimism"],
            "inverse_pole",
            "Optimism and pessimism are opposite-valence constructs.",
        ),
        (
            ["extraversion"],
            ["introversion"],
            "opposite_trait_pole",
            "Extraversion and introversion are opposite trait poles.",
        ),
    ]

    seen = set()
    for left_terms, right_terms, relation_type, reason in relation_rules:
        left = [a for a in attrs if contains(a, left_terms)]
        right = [a for a in attrs if contains(a, right_terms)]
        for a in left:
            for b in right:
                if a["canonical_attribute_id"] == b["canonical_attribute_id"]:
                    continue
                key = tuple(
                    sorted([a["canonical_attribute_id"], b["canonical_attribute_id"]])
                    + [relation_type]
                )
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    {
                        "source_attribute_id": a["canonical_attribute_id"],
                        "target_attribute_id": b["canonical_attribute_id"],
                        "source_label": a["canonical_label"],
                        "target_label": b["canonical_label"],
                        "relation_type": relation_type,
                        "confidence": "rule_seed",
                        "merge_policy": "do_not_auto_merge",
                        "reason": reason,
                    }
                )
    return edges


def write_csv(path, rows):
    if not rows:
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


def group_by(rows, key):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row)
    return grouped


def write_summaries(
    attributes, assignments, review_clusters, edges, input_count, excluded_count
):
    category_rows = []
    for category, group in group_by(attributes, "final_primary_category").items():
        category_rows.append(
            {
                "final_primary_category": category,
                "deduped_attribute_count": len(group),
                "source_candidate_count": sum(int(g["candidate_count"]) for g in group),
                "auto_merged_attribute_count": sum(
                    1 for g in group if g["merge_status"] != "singleton"
                ),
                "needs_review_attribute_count": sum(
                    str(g["needs_review"]).lower() == "true" for g in group
                ),
            }
        )
    category_rows.sort(
        key=lambda r: (-int(r["deduped_attribute_count"]), r["final_primary_category"])
    )
    write_csv(OUT / "category_summary.csv", category_rows)

    subcategory_rows = []
    for key, group in group_by(attributes, "final_primary_category").items():
        for subcategory, sub_group in group_by(group, "final_subcategory").items():
            subcategory_rows.append(
                {
                    "final_primary_category": key,
                    "final_subcategory": subcategory,
                    "deduped_attribute_count": len(sub_group),
                    "source_candidate_count": sum(
                        int(g["candidate_count"]) for g in sub_group
                    ),
                }
            )
    subcategory_rows.sort(
        key=lambda r: (
            r["final_primary_category"],
            -int(r["deduped_attribute_count"]),
            r["final_subcategory"],
        )
    )
    write_csv(OUT / "subcategory_summary.csv", subcategory_rows)

    report = [
        "# Step 3 Deduplication and Categorization Report",
        "",
        "Generated by `dedup_and_categorize_candidate_pool.py` from the high-quality normalized pool.",
        "",
        f"- Input high-quality normalized candidates: {input_count}",
        f"- Excluded non-attribute artifacts: {excluded_count}",
        f"- Attribute candidate rows used for deduplication: {len(assignments)}",
        f"- Deduped canonical attributes: {len(attributes)}",
        f"- Auto-merged candidate rows: {sum(1 for r in assignments if int(r['dedup_cluster_size']) > 1)}",
        f"- Auto-merged attribute clusters: {sum(1 for r in attributes if r['merge_status'] != 'singleton')}",
        f"- Review clusters from loose keys: {len(review_clusters)}",
        f"- Seed relation edges: {len(edges)}",
        "",
        "## Dedup Policy",
        "",
        "- Auto-merge exact duplicates only when final category and canonical label match and the row is not generic/free-text.",
        "- Auto-merge strong loose-key duplicates only when label similarity is very high or token sets are equivalent variants.",
        "- Exclude questionnaire artifacts such as explanation prompts, `Other / specify`, write-in fields, and generic response options from canonical attributes.",
        "- Do not auto-merge inverse or related constructs such as risk aversion, risk tolerance, and sensation seeking; write relation edges instead.",
        "- Keep original normalized categories and add Step 3 `final_primary_category` / `final_subcategory` for category refinement.",
        "",
        "## Final Category Counts",
        "",
    ]
    for row in category_rows:
        report.append(
            f"- {row['final_primary_category']}: {row['deduped_attribute_count']}"
        )
    report += [
        "",
        "## Outputs",
        "",
        "- `deduped_attributes_high_quality.csv`",
        "- `candidate_assignments_high_quality.csv`",
        "- `excluded_non_attribute_artifacts.csv`",
        "- `dedup_review_clusters.csv`",
        "- `related_attribute_edges.csv`",
        "- `category_summary.csv`",
        "- `subcategory_summary.csv`",
    ]
    (OUT / "step3_dedup_categorize_report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )


def main():
    rows = load_rows()
    excluded = []
    attribute_rows = []
    for row in rows:
        reason = non_attribute_artifact_reason(row)
        if reason:
            excluded_row = dict(row)
            excluded_row["exclusion_reason"] = reason
            excluded_row["step3_status"] = "excluded_non_attribute_artifact"
            excluded.append(excluded_row)
        else:
            attribute_rows.append(row)

    clusters, merge_reasons = build_auto_merge_clusters(attribute_rows)
    attributes, assignments = build_deduped_attributes(clusters, merge_reasons)
    review_clusters = build_review_clusters(attribute_rows, assignments)
    edges = build_relation_edges(attributes)

    write_csv(OUT / "deduped_attributes_high_quality.csv", attributes)
    write_jsonl(OUT / "deduped_attributes_high_quality.jsonl", attributes)
    write_csv(OUT / "candidate_assignments_high_quality.csv", assignments)
    write_jsonl(OUT / "candidate_assignments_high_quality.jsonl", assignments)
    write_csv(OUT / "excluded_non_attribute_artifacts.csv", excluded)
    write_csv(OUT / "dedup_review_clusters.csv", review_clusters)
    write_csv(OUT / "related_attribute_edges.csv", edges)
    write_summaries(
        attributes, assignments, review_clusters, edges, len(rows), len(excluded)
    )

    print(
        json.dumps(
            {
                "input_candidates": len(rows),
                "attribute_candidate_rows": len(attribute_rows),
                "excluded_non_attribute_artifacts": len(excluded),
                "deduped_attributes": len(attributes),
                "auto_merged_attribute_clusters": sum(
                    1 for r in attributes if r["merge_status"] != "singleton"
                ),
                "review_clusters": len(review_clusters),
                "relation_edges": len(edges),
                "output_dir": str(OUT),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
