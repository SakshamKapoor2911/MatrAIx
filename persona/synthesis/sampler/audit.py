from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np

from .sampler import PersonaForwardSampler


def total_variation(p: Dict[str, float], q: Dict[str, float]) -> float:
    keys = set(p) | set(q)
    return 0.5 * sum(abs(float(p.get(k, 0.0)) - float(q.get(k, 0.0))) for k in keys)


def prior_dict(node: Dict[str, Any]) -> Dict[str, float]:
    vals = list(node.get("values", []))
    pr = node.get("prior", {})
    if isinstance(pr, dict):
        raw = {v: float(pr.get(v, 0.0)) for v in vals}
    else:
        raw = {v: float(p) for v, p in zip(vals, pr)}
    s = sum(raw.values()) or 1.0
    return {k: v / s for k, v in raw.items()}


def marginal_audit(sampler: PersonaForwardSampler, idx: Dict[str, np.ndarray], nodes: Iterable[str] | None = None) -> List[Dict[str, Any]]:
    node_ids = list(nodes) if nodes else list(sampler.nodes)
    out = []
    n = len(next(iter(idx.values())))
    for nid in node_ids:
        if nid not in idx or nid not in sampler.nodes:
            continue
        vals = sampler.values[nid]
        counts = Counter(int(x) for x in idx[nid])
        empirical = {vals[i]: counts.get(i, 0) / n for i in range(len(vals))}
        prior = prior_dict(sampler.nodes[nid])
        out.append({
            "node": nid,
            "tvd_vs_prior": total_variation(prior, empirical),
            "prior": prior,
            "empirical": empirical,
        })
    return sorted(out, key=lambda r: r["tvd_vs_prior"], reverse=True)


def _v(sample: Dict[str, str], key: str) -> str | None:
    return sample.get(key)


def consistency_issues(sample: Dict[str, str]) -> List[Dict[str, str]]:
    """High-confidence persona-internal consistency checks.

    This rule set mirrors the full DAG refined audit: hard contradictions should be zero;
    soft warnings are intentionally retained for ambiguous cases.
    """
    issues: List[Dict[str, str]] = []
    def add(rule: str, severity: str, group: str, detail: str = "") -> None:
        issues.append({"rule": rule, "severity": severity, "group": group, "detail": detail})

    age = _v(sample, "age_bracket")
    children = _v(sample, "demo_children_count")
    parent = _v(sample, "demo_parental_status")
    life = _v(sample, "life_stage")
    emp = _v(sample, "demo_employment_status")
    years = _v(sample, "years_experience")
    banking = _v(sample, "lstyle_banking_style")
    payment = _v(sample, "lstyle_payment_pref")
    invest = _v(sample, "lstyle_investment_style")
    smoking = _v(sample, "lstyle_smoking_status")
    alcohol = _v(sample, "lstyle_alcohol_use")
    domain = _v(sample, "domain")
    role = _v(sample, "role_function")
    tech = _v(sample, "tech_savviness")

    parent_like = {"New parent", "Parent of minors", "Parent of adults", "Grandparent", "Step / foster parent"}
    child_present = {"1 child", "2 children", "3+ children", "Adult children", "Expecting"}
    adult_child_signal = parent in {"Parent of adults", "Grandparent"} or children == "Adult children"

    if children == "None" and parent in parent_like:
        add("children_none_but_parent_like", "hard", "family")
    if children in child_present and parent == "Not a parent":
        add("children_present_but_not_parent", "hard", "family")
    if life == "Parent of young kids" and (children not in child_present or parent == "Not a parent"):
        add("life_parent_young_kids_no_child_signal", "hard", "life_stage")
    if life == "Empty nester" and not adult_child_signal:
        add("empty_nester_without_adult_child_signal", "strong", "life_stage")
    if life == "Retirement" and age in {"13-17", "18-24", "25-34", "35-44"} and emp != "Retired":
        add("retirement_under45_without_retired_status", "strong", "life_stage")

    if age == "13-17":
        if years in {"3-5", "6-10", "11-20", "20+"}:
            add("minor_3plus_years_experience", "hard", "career")
        if children in {"2 children", "3+ children", "Adult children"}:
            add("minor_2plus_or_adult_children", "hard", "family")
        if payment in {"Credit card", "BNPL / installment"}:
            add("minor_credit_or_bnpl", "strong", "finance")
        if invest in {"Active trader", "Index investor", "Real-estate investor", "Crypto-heavy"}:
            add("minor_active_investment", "strong", "finance")
        if smoking == "Regular smoker":
            add("minor_regular_smoking", "strong", "lifestyle")
        if alcohol == "Heavy":
            add("minor_heavy_alcohol", "strong", "lifestyle")

    if banking == "Unbanked":
        if payment in {"Credit card", "Debit card", "BNPL / installment"}:
            add("unbanked_credit_debit_or_bnpl", "strong", "finance")
        if invest in {"Active trader", "Index investor", "Real-estate investor"}:
            add("unbanked_noncrypto_investment", "strong", "finance")
        if payment in {"Mobile wallet", "Crypto payment"}:
            add("unbanked_mobile_wallet_or_crypto_payment", "soft", "finance")

    if role == "Clinical" and domain != "Healthcare & Medicine":
        add("clinical_outside_healthcare", "strong", "domain_role")

    if tech in {"Reluctant", "Avoidant"}:
        core_tools = [
            "tool_docker", "tool_kubernetes", "tool_terraform", "tool_aws", "tool_azure", "tool_google_cloud",
            "tool_git", "tool_github", "tool_gitlab", "tool_github_copilot", "tool_python", "tool_r",
            "tool_sql", "tool_jupyter", "tool_vs_code", "tool_jetbrains_ides", "tool_vim", "tool_linux_cli", "tool_postman",
        ]
        if any(sample.get(t) == "Power user" for t in core_tools):
            add("low_tech_power_user_core_dev_tool", "hard", "digital")

    # Language consistency for primary language nodes.
    lang_map = {
        "English": "lang_english", "Mandarin": "lang_mandarin", "Spanish": "lang_spanish", "Hindi": "lang_hindi",
        "Arabic": "lang_arabic", "French": "lang_french", "Portuguese": "lang_portuguese", "Bengali": "lang_bengali",
        "Russian": "lang_russian", "Japanese": "lang_japanese", "German": "lang_german", "Swahili": "lang_swahili",
    }
    primary = sample.get("primary_language")
    if primary in lang_map and sample.get(lang_map[primary]) not in {"Native", "Fluent"}:
        add("primary_language_not_native_or_fluent", "hard", "language", f"{primary} -> {sample.get(lang_map[primary])}")
    if primary == "English" and sample.get("english_proficiency") in {"Basic", "None"}:
        add("primary_english_but_low_english_proficiency", "hard", "language")

    if sample.get("health_vision") == "Blind" and sample.get("demo_driver_status") in {"Daily driver", "Occasional driver", "Licensed but rarely drives"}:
        add("blind_current_or_licensed_driver", "hard", "health_driving")

    if sample.get("demo_religion_affiliation") in {"Atheist / agnostic", "None"} and sample.get("religiosity") in {"Observant", "Devout"}:
        add("unaffiliated_observant_or_devout", "hard", "religion")

    return issues


def consistency_audit(samples: Iterable[Dict[str, str]]) -> Dict[str, Any]:
    total = 0
    by_rule = Counter()
    by_severity = Counter()
    by_group = Counter()
    flagged_any = 0
    flagged_hard = 0
    flagged_hard_strong = 0
    examples: List[Dict[str, Any]] = []
    for sample in samples:
        total += 1
        issues = consistency_issues(sample)
        if issues:
            flagged_any += 1
            if len(examples) < 20:
                examples.append({"persona": sample, "issues": issues})
        if any(i["severity"] == "hard" for i in issues):
            flagged_hard += 1
        if any(i["severity"] in {"hard", "strong"} for i in issues):
            flagged_hard_strong += 1
        for i in issues:
            by_rule[(i["rule"], i["severity"], i["group"])] += 1
            by_severity[i["severity"]] += 1
            by_group[i["group"]] += 1
    return {
        "n": total,
        "any_hard": flagged_hard,
        "any_hard_share": flagged_hard / total if total else 0,
        "any_hard_or_strong": flagged_hard_strong,
        "any_hard_or_strong_share": flagged_hard_strong / total if total else 0,
        "any_flagged": flagged_any,
        "any_flagged_share": flagged_any / total if total else 0,
        "severity_issue_counts": dict(by_severity),
        "group_issue_counts": dict(by_group),
        "rules": [
            {"rule": r, "severity": s, "group": g, "count": c, "share": c / total if total else 0}
            for (r, s, g), c in by_rule.most_common()
        ],
        "examples": examples,
    }


def read_jsonl(path: str | Path) -> Iterable[Dict[str, str]]:
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write_rules_csv(summary: Dict[str, Any], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rule", "severity", "group", "count", "share"])
        w.writeheader()
        for row in summary.get("rules", []):
            w.writerow(row)
