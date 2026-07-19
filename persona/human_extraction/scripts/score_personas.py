#!/usr/bin/env python3
"""Quality scoring digest for extracted personas (selected cat50 config).

Computes automated validity metrics + prints readable per-persona digests
(profile snippet + sampled non-null fields with value/evidence/description) so
the extraction quality can be manually scored against the source profile.
"""
import json
import textwrap
from collections import Counter
from pathlib import Path

REPO = Path("/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx")
DIMS = json.load(open(REPO / "persona/schema/dimensions.json"))["dimensions"]
ALLOWED = {d["id"]: set(str(v) for v in d.get("values", [])) for d in DIMS}
N_DIMS = len(DIMS)
JSONL = REPO / "persona/human_extraction/data/bench_cat50_random_pc1.jsonl"

with open(JSONL) as fh:
    rows = [json.loads(line) for line in fh]
print(f"file: {JSONL.name}   personas: {len(rows)}   schema dims: {N_DIMS}\n")

# ---------- aggregate validity metrics ----------
tot_fields = tot_nonnull = tot_valid = tot_eviq = tot_descq = 0
atypes = Counter()
per_persona = []
for r in rows:
    fields = r["fields"]
    seen = set(f.get("field_id") for f in fields)
    nn = valid = eviq = descq = 0
    for f in fields:
        atypes[f.get("assignment_type")] += 1
        v = f.get("value")
        if v in (None, "null", ""):
            continue
        nn += 1
        fid = f.get("field_id")
        av = ALLOWED.get(fid)
        # valid if dimension is free-value OR value in allowed set
        if av is None or len(av) == 0 or str(v) in av:
            valid += 1
        if str(f.get("evidence") or "").strip():
            eviq += 1
        if str(f.get("description") or "").strip():
            descq += 1
    per_persona.append({
        "title": r["title"], "n_fields": len(fields), "uniq": len(seen),
        "nonnull": nn, "valid": valid, "eviq": eviq, "descq": descq,
        "coverage": len(seen) / N_DIMS,
    })
    tot_fields += len(fields)
    tot_nonnull += nn
    tot_valid += valid
    tot_eviq += eviq
    tot_descq += descq

print("=" * 78)
print("AUTOMATED VALIDITY METRICS (all 20 personas)")
print("=" * 78)
print(f"avg fields/persona        : {tot_fields/len(rows):.0f} (schema has {N_DIMS})")
print(f"avg non-null/persona      : {tot_nonnull/len(rows):.0f}")
print(f"value-in-allowed-set rate : {100*tot_valid/max(1,tot_nonnull):.1f}%  (of non-null)")
print(f"evidence-present rate     : {100*tot_eviq/max(1,tot_nonnull):.1f}%  (of non-null)")
print(f"description-present rate  : {100*tot_descq/max(1,tot_nonnull):.1f}%  (of non-null)")
print(f"assignment_type dist      : {dict(atypes)}")
print("\nper-persona coverage (unique field_ids / schema):")
for p in per_persona:
    flag = "" if p["coverage"] > 0.99 else "  <-- INCOMPLETE"
    print(f"  {p['title'][:30]:30s} fields={p['n_fields']:4d} uniq={p['uniq']:4d} "
          f"nn={p['nonnull']:3d} valid={100*p['valid']/max(1,p['nonnull']):3.0f}% "
          f"cov={100*p['coverage']:3.0f}%{flag}")

# ---------- readable digests for manual scoring ----------
def digest(r, k=10):
    print("\n" + "#" * 78)
    print(f"# {r['title']}   (global_idx={r['global_idx']})")
    print("#" * 78)
    prof = (r.get("profile_text") or "").strip().replace("\n", " ")
    print("PROFILE (first 700 chars):")
    print(textwrap.fill(prof[:700], 100))
    nn = [f for f in r["fields"] if f.get("value") not in (None, "null", "")]
    # sort by confidence desc, show a spread
    nn.sort(key=lambda f: -(f.get("confidence") or 0))
    print(f"\n{len(nn)} non-null fields. Sample (high-confidence first):")
    for f in nn[:k]:
        print(f"  • {f.get('field_id')} = {f.get('value')!r}  "
              f"[{f.get('assignment_type')}] conf={f.get('confidence')}")
        print(f"      desc: {str(f.get('description'))[:160]}")
        print(f"      evid: {str(f.get('evidence'))[:120]}")

# show a diverse set: first 6 personas
for r in rows[:6]:
    digest(r, k=10)
