#!/usr/bin/env python3
"""Post-process raw extraction into the team's deliverable format, applying the
team's own BENCHMARK.md §8 guidance.

Input : out/prism_extracted.jsonl   {uuid, observed, fields:[...]}   (raw, emit-all)
Output: out/prism_personas_v1.jsonl {user_id, source, model, fields:[1290], observed}
        one line/user, field schema identical to the wiki/amazon extractor.

§8 post-processing (verbatim from the team's runbook):
  "when value is None/absence -> force assignment_type=unsupported and drop the
   echoed evidence; treat confidence/assignment_type as weak signals. Positive-
   attribution value+evidence+description are trustworthy."

Operationalized faithfully:
  * A non-null value is a TRUSTWORTHY POSITIVE iff its evidence is grounded
    (a verbatim span of profile_text) AND is not an argument-from-absence phrase.
  * Otherwise -> assignment_type="unsupported", evidence="" (value kept as a weak
    signal, exactly as the team prescribes; downstream treats unsupported as weak).
  * A value not in the dim's allowed set is invalid -> value=null, unsupported.
  * Exact rule-based `observed` dims OVERRIDE the LLM (ground truth): value set,
    assignment_type="direct", confidence=1.0 (our value-add over the wiki pipeline).
Nothing is fabricated; unreliable inferences are demoted, not deleted.
"""

import json
import re
import argparse
import collections

ABSENCE = re.compile(
    r"no (mention|indication|reference|evidence|sign|record|major|significant|clear)"
    r"|not (mention|indicat|stat|explicit|specif|discuss)"
    r"|absence of|no \w+ (mention|mentioned|indicat)|does ?n['o]t (mention|indicat)",
    re.I,
)


def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def grounded(ev, pt):
    e = norm(ev)
    if not e:
        return False
    if e in pt:
        return True
    if len(e) > 30 and (
        e[:30] in pt or e[-30:] in pt
    ):  # truncated/…-shortened real quote
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="out/prism_extracted.jsonl")
    ap.add_argument("--out", default="out/prism_personas_v1.jsonl")
    ap.add_argument("--profiles", default="out/prism_profiles.jsonl")
    ap.add_argument("--schema", default="dimensions.json")
    ap.add_argument(
        "--model", default="Qwen3-235B-A22B"
    )  # recorded in output metadata only
    args = ap.parse_args()

    dims = json.load(open(args.schema))["dimensions"]
    order = [d["id"] for d in dims]
    allowed = {d["id"]: set(d.get("values") or []) for d in dims}
    labels = {d["id"]: d.get("label", d["id"]) for d in dims}
    ptext = {
        json.loads(line)["uuid"]: norm(json.loads(line)["profile_text"])
        for line in open(args.profiles)
    }

    st = collections.Counter()
    n = 0
    with open(args.out, "w") as out:
        for line in open(args.inp):
            r = json.loads(line)
            pt = ptext.get(r["uuid"], "")
            by_id = {}
            for f in r.get("fields", []):
                fid = f.get("field_id")
                if fid in allowed:
                    by_id[fid] = f
            fields = []
            for fid in order:
                f = by_id.get(fid) or {
                    "field_id": fid,
                    "value": None,
                    "confidence": 0.0,
                    "evidence": "",
                    "description": "",
                    "assignment_type": "unsupported",
                }
                f = {
                    "field_id": fid,
                    "value": f.get("value"),
                    "confidence": f.get("confidence", 0.0),
                    "evidence": f.get("evidence", ""),
                    "description": f.get("description", ""),
                    "assignment_type": f.get("assignment_type", "unsupported"),
                }
                v = f["value"]
                if v in (None, "null", ""):
                    f["value"] = None
                    f["assignment_type"] = "unsupported"
                    f["evidence"] = ""
                elif v not in allowed[fid]:  # off-allowed -> invalid
                    st["offallowed_nulled"] += 1
                    f["value"] = None
                    f["assignment_type"] = "unsupported"
                    f["evidence"] = ""
                    f["description"] = ""
                elif (not grounded(f["evidence"], pt)) or ABSENCE.search(
                    f["evidence"] or ""
                ):
                    st["demoted_to_unsupported"] += 1  # §8: absence/ungrounded
                    f["assignment_type"] = "unsupported"
                    f["evidence"] = ""
                else:
                    st["trustworthy_positive"] += 1
                fields.append(f)

            by_order = {f["field_id"]: f for f in fields}
            for d, val in (
                r.get("observed") or {}
            ).items():  # exact overlay wins (ground truth)
                if d in by_order and val in allowed.get(d, set()):
                    o = by_order[d]
                    o["value"] = val
                    o["assignment_type"] = "direct"
                    o["confidence"] = 1.0
                    if not o["description"]:
                        o["description"] = f"{labels[d]}: {val}."
                    st["observed_exact"] += 1

            out.write(
                json.dumps(
                    {
                        "user_id": r["uuid"],
                        "source": "PRISM",
                        "model": args.model,
                        "fields": fields,
                        "observed": r.get("observed", {}),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            n += 1

    pos = st["trustworthy_positive"]
    dem = st["demoted_to_unsupported"]
    obs = st["observed_exact"]
    print(f"personas: {n}")
    print(f"  trustworthy positives (grounded)      : {pos}  ({pos / n:.1f}/persona)")
    print(f"  demoted to unsupported (§8 absence)    : {dem}  ({dem / n:.1f}/persona)")
    print(f"  observed exact overlays (ground truth) : {obs}  ({obs / n:.1f}/persona)")
    print(f"  off-allowed values nulled              : {st['offallowed_nulled']}")
    print(f"  every record has exactly {len(order)} field objects -> {args.out}")


if __name__ == "__main__":
    main()
