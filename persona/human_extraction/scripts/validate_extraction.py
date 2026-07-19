#!/usr/bin/env python3
"""Validate a MatrAIx 1290-dimension persona *extraction* against the schema.

Complements ``scripts/validate_submission.py`` (which checks the 8-field submission
schema). This validates the full **1290-dim extraction** output produced by the
``human_extraction`` pipeline — the per-persona field list — for any dataset shard
(``.jsonl`` or ``.jsonl.gz``): field schema, allowed values, ``assignment_type``,
null/provenance consistency, per-record completeness, and (optionally) whether every
"supported" value is grounded by a verbatim quote from the source ``profile_text``.

Usage
-----
    python validate_extraction.py --input shard_00.jsonl.gz --schema ../schema/dimensions.json
    # optional evidence-grounding pass (needs the profiles fed to the extractor):
    python validate_extraction.py --input shard.jsonl --schema dims.json --profiles profiles.jsonl

Exit code: 0 = valid (no errors); 1 = errors found (``--strict`` also fails on warnings),
so it can gate CI. ERRORS = invalid data (off-schema); WARNINGS = quality/consistency signals.
"""

import argparse
import collections
import gzip
import json
import re
import sys

VALID_AT = {"direct", "structured_claim", "summary_inference", "unsupported"}
SUPPORTED_AT = {"direct", "structured_claim", "summary_inference"}


def _open(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt")
    return open(path)


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _grounded(evidence, profile):
    ev = _norm(evidence)
    if not ev:
        return None  # no quote to check
    if ev in profile:
        return True
    if len(ev) > 30 and (ev[:30] in profile or ev[-30:] in profile):
        return True  # truncated/shortened but real span
    return False


def validate(args):
    dims = json.load(open(args.schema))["dimensions"]
    allowed = {d["id"]: set(d.get("values") or []) for d in dims}
    all_ids = set(allowed)
    n_dims = len(all_ids)

    profiles = {}
    if args.profiles:
        for line in _open(args.profiles):
            p = json.loads(line)
            uid = p.get("user_id", p.get("uuid"))
            if uid is not None:
                profiles[uid] = _norm(p.get("profile_text"))

    errors = collections.Counter()
    warnings = collections.Counter()
    examples = collections.defaultdict(list)

    def err(kind, detail):
        errors[kind] += 1
        if len(examples["E:" + kind]) < 3:
            examples["E:" + kind].append(detail)

    def warn(kind, detail):
        warnings[kind] += 1
        if len(examples["W:" + kind]) < 3:
            examples["W:" + kind].append(detail)

    seen_uids = set()
    at_counts = collections.Counter()
    n = 0
    covered_per = []
    nonnull_per = []
    grounded_per = []

    for lineno, line in enumerate(_open(args.input), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            err("malformed_json", f"line {lineno}")
            continue
        if not isinstance(rec, dict):
            err("record_not_object", f"line {lineno}")
            continue

        uid = rec.get("user_id", rec.get("uuid"))
        if uid is None:
            err("missing_user_id", f"line {lineno}")
        elif uid in seen_uids:
            err("duplicate_user_id", str(uid))
        else:
            seen_uids.add(uid)

        fields = rec.get("fields")
        if not isinstance(fields, list):
            err("fields_not_list", f"user {uid}")
            continue

        n += 1
        profile = profiles.get(uid, "")
        seen_dims = set()
        nonnull = 0
        grounded = 0
        for f in fields:
            if not isinstance(f, dict):
                err("field_not_object", f"user {uid}")
                continue
            fid = f.get("field_id")
            if fid not in all_ids:
                err("unknown_field_id", f"{fid!r} (user {uid})")
                continue
            if fid in seen_dims:
                warn("duplicate_field_id", f"{fid} (user {uid})")
            seen_dims.add(fid)

            at = f.get("assignment_type")
            if at not in VALID_AT:
                err("invalid_assignment_type", f"{at!r} @ {fid} (user {uid})")
            at_counts[at] += 1

            conf = f.get("confidence")
            bad_conf = conf is not None and (
                not isinstance(conf, (int, float))
                or isinstance(conf, bool)
                or not 0.0 <= conf <= 1.0
            )
            if bad_conf:
                err("confidence_out_of_range", f"{conf!r} @ {fid} (user {uid})")

            value = f.get("value")
            if value in (None, "null", ""):
                if at in SUPPORTED_AT:
                    warn("null_value_marked_supported", f"{fid}={at} (user {uid})")
                continue

            nonnull += 1
            if allowed[fid] and value not in allowed[fid]:
                err("value_not_in_allowed_set", f"{fid}={value!r} (user {uid})")

            if args.profiles and at in SUPPORTED_AT:
                g = _grounded(f.get("evidence"), profile)
                if g is True:
                    grounded += 1
                elif g is False:
                    warn("ungrounded_evidence", f"{fid} (user {uid})")
                else:
                    warn("supported_without_evidence", f"{fid}={at} (user {uid})")

        covered_per.append(len(seen_dims))
        nonnull_per.append(nonnull)
        grounded_per.append(grounded)
        if len(seen_dims) < n_dims:
            warn("incomplete_record", f"user {uid}: {len(seen_dims)}/{n_dims} dims")

    _report(
        args,
        n,
        seen_uids,
        n_dims,
        covered_per,
        nonnull_per,
        grounded_per,
        at_counts,
        errors,
        warnings,
        examples,
    )
    if errors or (args.strict and warnings):
        return 1
    return 0


def _report(
    args,
    n,
    seen_uids,
    n_dims,
    covered_per,
    nonnull_per,
    grounded_per,
    at_counts,
    errors,
    warnings,
    examples,
):
    print("=" * 66)
    print(f"VALIDATION  {args.input}")
    print(f"records: {n:,}   unique users: {len(seen_uids):,}   schema dims: {n_dims}")
    if n:
        complete = sum(1 for c in covered_per if c >= n_dims)
        print(
            f"avg dims/record: {sum(covered_per) / n:.0f}   "
            f"avg non-null/record: {sum(nonnull_per) / n:.1f}   "
            f"complete records: {complete:,}/{n:,}"
        )
        if args.profiles:
            print(f"avg grounded attributions/record: {sum(grounded_per) / n:.1f}")
    print(f"assignment_type mix: {dict(at_counts)}")
    print("-" * 66)

    n_err = sum(errors.values())
    n_warn = sum(warnings.values())
    if errors:
        print(f"ERRORS ({n_err:,}):")
        for kind, count in errors.most_common():
            print(f"  ✗ {kind}: {count:,}")
            for ex in examples["E:" + kind]:
                print(f"      e.g. {ex}")
    if warnings:
        print(f"WARNINGS ({n_warn:,}):")
        for kind, count in warnings.most_common():
            print(f"  ! {kind}: {count:,}")
            for ex in examples["W:" + kind]:
                print(f"      e.g. {ex}")
    if not errors and not warnings:
        print("✅ all checks passed — no errors, no warnings")
    elif not errors:
        print(f"✅ no errors ({n_warn:,} warnings)")
    else:
        print(f"❌ {n_err:,} errors, {n_warn:,} warnings")
    print("=" * 66)


def main():
    ap = argparse.ArgumentParser(
        description="Validate a 1290-dim persona extraction shard."
    )
    ap.add_argument(
        "--input", required=True, help="extraction shard (.jsonl or .jsonl.gz)"
    )
    ap.add_argument(
        "--schema", required=True, help="path to persona/schema/dimensions.json"
    )
    ap.add_argument(
        "--profiles", help="optional profiles jsonl (enables evidence-grounding check)"
    )
    ap.add_argument(
        "--strict", action="store_true", help="exit non-zero on warnings too"
    )
    args = ap.parse_args()
    sys.exit(validate(args))


if __name__ == "__main__":
    main()
