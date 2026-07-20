#!/usr/bin/env python3
"""Find an exact deterministic priority cutoff for the synthetic target."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from persona.post_process.deduplication.reduce_synthetic_partition import SURVIVOR

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--input",type=Path,required=True); p.add_argument("--target",type=int,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    reports=[json.loads(x.read_text()) for x in sorted(a.input.glob("part_*/report.json"))]; unique=sum(x["survivors"] for x in reports)
    if len(reports)!=256 or unique<a.target: raise ValueError(f"need 256 partitions and unique >= target; got {len(reports)}, {unique}")
    hist=sum((np.load(x) for x in sorted(a.input.glob("part_*/priority_histogram.npy"))),start=np.zeros(65536,dtype=np.uint64)); cumulative=np.cumsum(hist,dtype=np.uint64); boundary=int(np.searchsorted(cumulative,a.target,side="left")); before=int(cumulative[boundary-1]) if boundary else 0; need=a.target-before
    candidates=[]
    for path in sorted(a.input.glob("part_*/survivors_shard_*.bin")):
        shard=int(path.stem.split("_")[-1]); data=np.fromfile(path,dtype=SURVIVOR); chosen=data[(data["priority"]>>np.uint64(48))==boundary]
        if len(chosen):
            global_rows=np.uint64(shard*100_000_000)+chosen["local_row"].astype(np.uint64); candidates.append(np.rec.fromarrays([chosen["priority"],global_rows],names="priority,global_row"))
    boundary_rows=np.concatenate(candidates); order=np.lexsort((boundary_rows["global_row"],boundary_rows["priority"])); selected=boundary_rows[order[need-1]]
    result={"unique_projection_buckets":unique,"target":a.target,"priority_bin":boundary,"cutoff_priority":int(selected["priority"]),"cutoff_global_row":int(selected["global_row"]),"kept_before_boundary_bin":before,"kept_from_boundary_bin":need}; a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2))
if __name__=="__main__": main()