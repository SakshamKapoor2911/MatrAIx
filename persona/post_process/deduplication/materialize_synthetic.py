#!/usr/bin/env python3
"""Partition synthetic projection records for global diversity deduplication."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from persona.post_process.deduplication.hll import splitmix64
from persona.synthesis.scripts.decode_persona_codes import _iter_code_chunks, _load_schema

RECORD = np.dtype([("signature", "<u8"), ("priority", "<u8"), ("global_row", "<u8")])

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--shard",type=int,required=True); p.add_argument("--projection",required=True); p.add_argument("--config",type=Path,required=True); p.add_argument("--source",type=Path,required=True); p.add_argument("--quality-bitmap",type=Path,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    schema=_load_schema(a.source); config=json.loads(a.config.read_text()); projection=next(x for x in config["projections"] if x["id"]==a.projection); by_id={c["id"]:i for i,c in enumerate(schema["columns"])}; columns=[by_id[x["id"]] for x in projection["fields"]]
    rows=int(schema["shape"][0]); rejected=np.unpackbits(np.fromfile(a.quality_bitmap,dtype=np.uint8),bitorder="little",count=rows).astype(bool); a.out.mkdir(parents=True,exist_ok=True)
    handles=[(a.out/f"part_{i:03d}.bin").open("wb") for i in range(256)]; offset=kept=0
    try:
        for codes in _iter_code_chunks(a.source,schema):
            n=len(codes); local=np.arange(offset,offset+n,dtype=np.uint64); keep=~rejected[offset:offset+n]; local=local[keep]; selected=codes[keep]; sig=np.zeros(len(selected),dtype=np.uint64)
            for pos,col in enumerate(columns): sig |= selected[:,col].astype(np.uint64)<<np.uint64(4*pos)
            global_rows=np.uint64(a.shard*100_000_000)+local; priority=splitmix64(global_rows^np.uint64(0xD3D3D3D320260719)); records=np.empty(len(sig),dtype=RECORD); records["signature"]=sig; records["priority"]=priority; records["global_row"]=global_rows
            parts=(splitmix64(sig)&np.uint64(255)).astype(np.uint8)
            for part in np.unique(parts): handles[int(part)].write(records[parts==part].tobytes())
            kept+=len(sig); offset+=n
    finally:
        for h in handles: h.close()
    (a.out/"report.json").write_text(json.dumps({"shard":a.shard,"rows":rows,"kept":kept,"projection":a.projection},indent=2)+"\n")
if __name__=="__main__": main()
