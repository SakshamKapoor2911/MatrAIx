#!/usr/bin/env python3
"""Combine quality, duplicate, and target-cutoff rejection decisions."""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
import numpy as np
from persona.post_process.deduplication.reduce_synthetic_partition import SURVIVOR

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--shard",type=int,required=True); p.add_argument("--quality",type=Path,required=True); p.add_argument("--reduced",type=Path,required=True); p.add_argument("--cutoff",type=Path,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    rows=100_000_000; rejected=np.unpackbits(np.fromfile(a.quality,dtype=np.uint8),bitorder="little",count=rows).astype(bool); cutoff=json.loads(a.cutoff.read_text()); cp=np.uint64(cutoff["cutoff_priority"]); cg=np.uint64(cutoff["cutoff_global_row"])
    for path in a.reduced.glob(f"part_*/duplicates_shard_{a.shard:04d}.u32"): rejected[np.fromfile(path,dtype=np.uint32)]=True
    for path in a.reduced.glob(f"part_*/survivors_shard_{a.shard:04d}.bin"):
        data=np.fromfile(path,dtype=SURVIVOR); global_rows=np.uint64(a.shard*rows)+data["local_row"].astype(np.uint64); remove=(data["priority"]>cp)|((data["priority"]==cp)&(global_rows>cg)); rejected[data["local_row"][remove]]=True
    a.out.parent.mkdir(parents=True,exist_ok=True); temporary=a.out.with_suffix(a.out.suffix+".part"); temporary.write_bytes(np.packbits(rejected,bitorder="little").tobytes()); os.replace(temporary,a.out); report={"shard":a.shard,"rows":rows,"rejected":int(np.count_nonzero(rejected)),"kept":rows-int(np.count_nonzero(rejected))}; a.out.with_suffix(".json").write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__": main()