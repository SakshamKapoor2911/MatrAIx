import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STEP3 = ROOT / "outputs" / "step3_dedup_categorize"
STEP5 = ROOT / "outputs" / "step5_embedding_llm_dedup"
OUT = ROOT / "outputs" / "step6_final_merged"
OUT.mkdir(parents=True, exist_ok=True)

ATTRIBUTES_CSV = STEP3 / "deduped_attributes_high_quality.csv"
MERGES_CSV = STEP5 / "llm_confirmed_merges.csv"
GRAPH_EDGES_CSV = STEP5 / "llm_graph_edges.csv"


def read_csv(path):
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_json_list(value):
    try:
        parsed = json.loads(value or "[]")
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def parse_json_object(value):
    try:
        parsed = json.loads(value or "{}")
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def as_float(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def as_int(value):
    try:
        return int(float(value or 0))
    except Exception:
        return 0


class UnionFind:
    def __init__(self, ids):
        self.parent = {item: item for item in ids}

    def find(self, item):
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, a, b):
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return False
        if ra > rb:
            ra, rb = rb, ra
        self.parent[rb] = ra
        return True


def stable_cluster_id(member_ids):
    if len(member_ids) == 1:
        return member_ids[0]
    digest = hashlib.sha1("\n".join(sorted(member_ids)).encode("utf-8")).hexdigest()[
        :12
    ]
    return f"merged_attr_{digest}"


def representative_key(row):
    return (
        as_int(row.get("source_count")),
        as_float(row.get("max_normalized_quality_score")),
        as_int(row.get("candidate_count")),
        -len(row.get("canonical_label", "")),
    )


def merge_json_lists(rows, column):
    values = []
    seen = set()
    for row in rows:
        for item in parse_json_list(row.get(column, "")):
            key = (
                json.dumps(item, ensure_ascii=False, sort_keys=True)
                if isinstance(item, (dict, list))
                else str(item)
            )
            if key not in seen:
                values.append(item)
                seen.add(key)
    return values


def merge_json_count_maps(rows, column):
    counts = defaultdict(int)
    for row in rows:
        parsed = parse_json_object(row.get(column, ""))
        for key, value in parsed.items():
            try:
                counts[str(key)] += int(value)
            except Exception:
                counts[str(key)] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def build_final_attributes(attributes, merges):
    attr_by_id = {row["canonical_attribute_id"]: row for row in attributes}
    uf = UnionFind(attr_by_id.keys())
    accepted_merge_edges = []
    for row in merges:
        a = row.get("source_attribute_id")
        b = row.get("target_attribute_id")
        if a in attr_by_id and b in attr_by_id:
            did_union = uf.union(a, b)
            edge = dict(row)
            edge["union_applied"] = str(did_union).lower()
            accepted_merge_edges.append(edge)

    clusters = defaultdict(list)
    for attr_id in attr_by_id:
        clusters[uf.find(attr_id)].append(attr_id)

    final_rows = []
    member_rows = []
    attr_to_final = {}

    for member_ids in sorted(clusters.values(), key=lambda ids: sorted(ids)[0]):
        member_attrs = [attr_by_id[attr_id] for attr_id in member_ids]
        representative = max(member_attrs, key=representative_key)
        final_id = stable_cluster_id(member_ids)
        all_labels = []
        for row in member_attrs:
            all_labels.append(row.get("canonical_label", ""))
            all_labels.extend(parse_json_list(row.get("aliases_json", "")))
        aliases = []
        seen_aliases = set()
        for label in all_labels:
            label = str(label).strip()
            if not label or label == representative.get("canonical_label"):
                continue
            key = label.lower()
            if key not in seen_aliases:
                aliases.append(label)
                seen_aliases.add(key)

        candidate_count = sum(
            as_int(row.get("candidate_count")) for row in member_attrs
        )
        source_map = merge_json_count_maps(member_attrs, "sources_json")
        source_family_map = merge_json_count_maps(member_attrs, "source_families_json")
        source_count = len(source_map)
        quality_score = max(
            as_float(row.get("max_normalized_quality_score")) for row in member_attrs
        )
        needs_review = any(
            str(row.get("needs_review", "")).lower() == "true" for row in member_attrs
        )
        if len(member_ids) > 1:
            needs_review = False

        final_row = dict(representative)
        final_row.update(
            {
                "final_attribute_id": final_id,
                "representative_canonical_attribute_id": representative[
                    "canonical_attribute_id"
                ],
                "merged_member_count": len(member_ids),
                "merged_member_ids_json": json.dumps(
                    sorted(member_ids), ensure_ascii=False
                ),
                "candidate_count": candidate_count,
                "source_count": source_count,
                "max_normalized_quality_score": quality_score,
                "merge_status": "llm_merged" if len(member_ids) > 1 else "singleton",
                "sources_json": json.dumps(source_map, ensure_ascii=False),
                "source_families_json": json.dumps(
                    source_family_map, ensure_ascii=False
                ),
                "aliases_json": json.dumps(aliases, ensure_ascii=False),
                "candidate_ids_json": json.dumps(
                    merge_json_lists(member_attrs, "candidate_ids_json"),
                    ensure_ascii=False,
                ),
                "needs_review": str(needs_review).lower(),
            }
        )
        final_rows.append(final_row)

        for rank, attr_id in enumerate(sorted(member_ids)):
            attr_to_final[attr_id] = final_id
            member = attr_by_id[attr_id]
            member_rows.append(
                {
                    "final_attribute_id": final_id,
                    "member_attribute_id": attr_id,
                    "member_label": member.get("canonical_label", ""),
                    "is_representative": str(
                        attr_id == representative["canonical_attribute_id"]
                    ).lower(),
                    "member_rank": rank,
                    "member_source_count": member.get("source_count", ""),
                    "member_quality_score": member.get(
                        "max_normalized_quality_score", ""
                    ),
                }
            )

    return final_rows, member_rows, accepted_merge_edges, attr_to_final


def build_final_graph_edges(graph_edges, attr_to_final, final_by_id):
    grouped = {}
    for row in graph_edges:
        a = attr_to_final.get(row.get("source_attribute_id"))
        b = attr_to_final.get(row.get("target_attribute_id"))
        if not a or not b or a == b:
            continue
        relation = row.get("relation_type", "related_but_distinct")
        key = tuple(sorted([a, b]) + [relation])
        current = grouped.get(key)
        confidence = as_float(row.get("llm_confidence"))
        weight = as_float(row.get("edge_weight")) or as_float(
            row.get("final_merge_confidence")
        )
        if current is None:
            grouped[key] = {
                "source_final_attribute_id": a,
                "target_final_attribute_id": b,
                "source_label": final_by_id[a].get("canonical_label", ""),
                "target_label": final_by_id[b].get("canonical_label", ""),
                "relation_type": relation,
                "edge_weight": round(weight, 4),
                "max_llm_confidence": confidence,
                "supporting_pair_count": 1,
                "supporting_pair_ids_json": json.dumps(
                    [row.get("pair_id", "")], ensure_ascii=False
                ),
            }
        else:
            current["edge_weight"] = max(
                as_float(current.get("edge_weight")), round(weight, 4)
            )
            current["max_llm_confidence"] = max(
                as_float(current.get("max_llm_confidence")), confidence
            )
            current["supporting_pair_count"] = (
                as_int(current.get("supporting_pair_count")) + 1
            )
            pair_ids = parse_json_list(current.get("supporting_pair_ids_json"))
            pair_ids.append(row.get("pair_id", ""))
            current["supporting_pair_ids_json"] = json.dumps(
                pair_ids, ensure_ascii=False
            )
    return list(grouped.values())


def main():
    attributes = read_csv(ATTRIBUTES_CSV)
    merges = read_csv(MERGES_CSV)
    graph_edges = read_csv(GRAPH_EDGES_CSV)

    final_rows, member_rows, merge_edges, attr_to_final = build_final_attributes(
        attributes, merges
    )
    final_by_id = {row["final_attribute_id"]: row for row in final_rows}
    final_graph_edges = build_final_graph_edges(graph_edges, attr_to_final, final_by_id)

    write_csv(OUT / "final_merged_attributes.csv", final_rows)
    write_csv(OUT / "merge_cluster_members.csv", member_rows)
    write_csv(OUT / "accepted_llm_merge_edges.csv", merge_edges)
    write_csv(OUT / "final_graph_edges.csv", final_graph_edges)

    report = [
        "# Step 6 Final Merged Attribute Set",
        "",
        "Generated by `build_final_merged_attributes.py`.",
        "",
        f"- Input canonical attributes from Step 3: {len(attributes)}",
        f"- High-confidence LLM merge edges from Step 5: {len(merges)}",
        f"- Final merged attributes: {len(final_rows)}",
        f"- Multi-member merged clusters: {sum(1 for row in final_rows if as_int(row.get('merged_member_count')) > 1)}",
        f"- Final graph edges after merging duplicate nodes: {len(final_graph_edges)}",
        "",
        "Only Step 5 pairs in `llm_confirmed_merges.csv` are collapsed. Correlated, inverse, broader/narrower, conflict, review, and rejected pairs remain separate attributes and are represented as graph edges or review rows.",
    ]
    (OUT / "step6_final_merged_report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "input_attributes": len(attributes),
                "llm_merge_edges": len(merges),
                "final_merged_attributes": len(final_rows),
                "merged_clusters": sum(
                    1
                    for row in final_rows
                    if as_int(row.get("merged_member_count")) > 1
                ),
                "final_graph_edges": len(final_graph_edges),
                "output_dir": str(OUT),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
