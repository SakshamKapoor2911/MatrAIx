#!/usr/bin/env python3
"""Verify exact final synthetic plus human corpus size."""
from __future__ import annotations
import argparse, json
from pathlib import Path
def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--synthetic",type=Path,required=True); p.add_argument("--human",type=Path,required=True); p.add_argument("--total-target",type=int,default=8_400_000_000); p.add_argument("--out",type=Path,required=True); a=p.parse_args(); reports=[json.loads(x.read_text()) for x in sorted(a.synthetic.glob("shard_*.json"))]
    if len(reports)!=100: raise ValueError(f"expected 100 synthetic reports, got {len(reports)}")
    human=json.loads(a.human.read_text()); synthetic=sum(x["kept"] for x in reports); total=synthetic+human["dedup_kept_rows"]; result={"synthetic_kept_rows":synthetic,"human_kept_rows":human["dedup_kept_rows"],"total_kept_rows":total,"target":a.total_target,"target_met":total==a.total_target}
    if not result["target_met"]: raise ValueError(result)
    a.out.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2))
if __name__=="__main__": main()