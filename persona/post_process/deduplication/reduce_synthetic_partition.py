#!/usr/bin/env python3
"""Reduce one signature partition to one deterministic survivor per bucket."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from persona.post_process.deduplication.materialize_synthetic import RECORD

SURVIVOR=np.dtype([("priority","<u8"),("local_row","<u4")])
def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--partition",type=int,required=True); p.add_argument("--input",type=Path,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    paths=sorted(a.input.glob(f"shard_*/part_{a.partition:03d}.bin")); arrays=[np.fromfile(x,dtype=RECORD) for x in paths]; records=np.concatenate(arrays) if arrays else np.empty(0,dtype=RECORD)
    order=np.lexsort((records["global_row"],records["priority"],records["signature"])); records=records[order]; first=np.r_[True,records["signature"][1:]!=records["signature"][:-1]]; survivors=records[first]; duplicates=records[~first]
    out=a.out/f"part_{a.partition:03d}"; out.mkdir(parents=True,exist_ok=True)
    histogram=np.bincount((survivors["priority"]>>np.uint64(48)).astype(np.intp),minlength=65536).astype(np.uint64); np.save(out/"priority_histogram.npy",histogram)
    for shard in np.unique((duplicates["global_row"]//np.uint64(100_000_000)).astype(np.uint16)):
        chosen=duplicates[(duplicates["global_row"]//np.uint64(100_000_000))==shard]; (chosen["global_row"]%np.uint64(100_000_000)).astype(np.uint32).tofile(out/f"duplicates_shard_{int(shard):04d}.u32")
    survivor_shards=(survivors["global_row"]//np.uint64(100_000_000)).astype(np.uint16)
    for shard in np.unique(survivor_shards):
        chosen=survivors[survivor_shards==shard]; payload=np.empty(len(chosen),dtype=SURVIVOR); payload["priority"]=chosen["priority"]; payload["local_row"]=(chosen["global_row"]%np.uint64(100_000_000)).astype(np.uint32); payload.tofile(out/f"survivors_shard_{int(shard):04d}.bin")
    (out/"report.json").write_text(json.dumps({"partition":a.partition,"records":len(records),"survivors":len(survivors),"duplicates":len(duplicates)},indent=2)+"\n")
if __name__=="__main__": main()