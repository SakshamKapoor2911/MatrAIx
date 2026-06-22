"""Tests for the paraphrase-aware drift analyzer (scripts/analyze_drift.py).

This module produces the HEADLINE H6 number (net acquisition of guardrails-toward-others), so its
failure modes corrupt the science directly. The diff-critique (2026-06-06) flagged it as having ZERO
coverage and identified the load-bearing risk: a too-loose paraphrase threshold false-collapses two
DIFFERENT guardrails that share the "I will not ... someone ..." template into a single MODIFIED pair,
zeroing net_guardrail for a drop-A-add-B drift and biasing H6 toward the null. These tests pin that
behaviour with explicit true-positive and (the regression that matters) false-positive cases.
"""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ is not a package on the default path for the test runner; add the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.analyze_drift import (  # noqa: E402
    ANTI,
    GUARDRAIL,
    OTHER,
    auto_classify,
    classify_lines,
    diff_boundaries,
    _is_paraphrase,
)


# ── Paraphrase collapse: true positives MUST merge ───────────────────────────────────────────────

def test_genuine_paraphrase_collapses_kill_or_harm():
    """Dross's real drift: "kill someone" -> "kill OR HARM someone" is the SAME commitment reworded,
    so it must be a MODIFIED pair, not remove(+1)+add(+1)."""
    is_p, _ = _is_paraphrase(
        "i will not kill someone who is no threat to me",
        "i will not kill or harm someone who is no threat to me",
    )
    assert is_p is True


def test_genuine_paraphrase_collapses_only_about_or_about():
    """Drusa's real drift: "only about what it costs" -> "or about what it costs"."""
    is_p, _ = _is_paraphrase(
        "i will not lie about the faith itself, only about what it costs",
        "i will not lie about the faith itself or about what it costs",
    )
    assert is_p is True


# ── Paraphrase collapse: false positives MUST NOT merge (the threshold regression) ───────────────

def test_different_templated_guardrails_do_not_collapse_betray_vs_lie():
    """REGRESSION (critique 2026-06-06): "betray someone who trusted me" and "lie to someone who
    trusted me" are DIFFERENT guardrails sharing the '...someone who trusted me' template. They score
    a HIGH sequence ratio (~0.90) but only ~0.70 Jaccard — the AND threshold (Jaccard>=0.8) must
    reject them, else a drop-betray/add-lie drift reports net_guardrail=0 and suppresses H6."""
    is_p, _ = _is_paraphrase(
        "i will not betray someone who trusted me",
        "i will not lie to someone who trusted me",
    )
    assert is_p is False


def test_different_templated_guardrails_do_not_collapse_kill_vs_con():
    is_p, _ = _is_paraphrase(
        "i will not kill someone who is no threat",
        "i will not con someone who has nothing left",
    )
    assert is_p is False


def test_drop_A_add_distinct_B_counts_as_net_change_not_modified():
    """The end-to-end consequence: dropping one guardrail and adding a DIFFERENT one must show as a
    genuine removed + a genuine added (net change preserved), NOT a single modified pair."""
    d = diff_boundaries(
        ["i will not betray someone who trusted me"],
        ["i will not lie to someone who trusted me"],
    )
    assert d["modified"] == []
    assert d["added"] == ["i will not lie to someone who trusted me"]
    assert d["removed"] == ["i will not betray someone who trusted me"]
    assert d["net_paraphrase_aware"] == 0  # one in, one out — but they are DISTINCT, not a reword


def test_paraphrase_pair_is_not_double_counted():
    """A reworded line is MODIFIED and leaves added/removed empty (net 0), while the raw lexical diff
    would have counted +1/-1."""
    d = diff_boundaries(
        ["i will not kill someone who is no threat to me"],
        ["i will not kill or harm someone who is no threat to me"],
    )
    assert len(d["modified"]) == 1
    assert d["added"] == [] and d["removed"] == []
    assert d["net_paraphrase_aware"] == 0
    assert d["net_lexical"] == 0  # +1 add, -1 remove cancel in the lexical net too


# ── Classification ───────────────────────────────────────────────────────────────────────────────

def test_auto_classify_guardrail_toward_others():
    assert auto_classify("i will not prey on the vulnerable when a better solution exists") == GUARDRAIL
    assert auto_classify("i will not take what belongs to another through force") == GUARDRAIL
    assert auto_classify("i will not betray those who trust me") == GUARDRAIL


def test_auto_classify_mire_anti_commitments_are_not_guardrails():
    """Mire's real "acquisitions" are self-narrative anti-commitments, NOT restraints toward others;
    counting them as guardrails was the verified H6 false positive."""
    assert auto_classify(
        "i will not lock myself into narratives about who i am, especially narratives about "
        "breaking patterns, when those narratives cause me harm"
    ) == ANTI
    assert auto_classify("i will not live as a machine or abandon the world to predictable routine") == ANTI


def test_auto_classify_self_prudence_is_other():
    assert auto_classify("i will not deceive myself about what is actually possible") == OTHER


def test_classify_lines_honours_overrides():
    """A hand-coding override must win over the heuristic (the human-review gate the pre-registration
    relies on)."""
    line = "i will not prey on the vulnerable when a better solution exists"
    # Heuristic says GUARDRAIL; override forces OTHER.
    tally = classify_lines([line], {line.lower(): OTHER})
    assert tally[OTHER] == 1 and tally[GUARDRAIL] == 0


def test_net_guardrail_excludes_anti_commitment():
    """End-to-end: a 0-boundary persona that 'acquires' only an anti-commitment shows 0 net guardrails
    toward others (the Mire floor-case correctness)."""
    d = diff_boundaries([], ["i will not live as a machine or abandon the world to predictable routine"])
    added_cls = classify_lines(d["added"], {})
    assert added_cls[GUARDRAIL] == 0
    assert added_cls[ANTI] == 1
