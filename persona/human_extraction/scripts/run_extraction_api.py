#!/usr/bin/env python3
"""LLM persona extraction via an OpenAI-compatible API endpoint (-> Qwen/...).

Your API key is read from the LLM_API_KEY env var — it is NEVER written in code or logs.
Reuses the team's evidence-grounded prompt. Concurrent + resumable.

SETUP: none — uses Python stdlib only (urllib), so no pip install is required.

RUN (fill in your proxy's base URL + the model name it exposes for Qwen):
  export LLM_API_KEY='...'                          # your key — stays in your shell
  export LLM_API_BASE_URL='https://<your-api-host>/v1'
  python run_extraction_api.py \
      --profiles prism_profiles.jsonl \
      --model 'qwen3.6-35b' \
      --out out/prism_extracted.jsonl \
      --workers 24
  # smoke test first:  add  --limit 5
"""

import os
import json
import argparse
import time
import threading
import concurrent.futures as cf
import ssl
import urllib.request
import urllib.error  # stdlib only — no pip install needed


class TokenBucket:
    """Thread-safe token-rate limiter: paces total tokens/min under the key's TPM
    cap so we never 429. Workers block in acquire() until budget is available."""

    def __init__(self, per_min):
        self.rate = per_min / 60.0  # tokens/sec
        self.capacity = per_min  # allow up to ~1 min burst
        self.tokens = per_min
        self.last = time.time()
        self.lock = threading.Lock()

    def acquire(self, n):
        n = min(n, self.capacity)
        while True:
            with self.lock:
                now = time.time()
                self.tokens = min(
                    self.capacity, self.tokens + (now - self.last) * self.rate
                )
                self.last = now
                if self.tokens >= n:
                    self.tokens -= n
                    return
                wait = (n - self.tokens) / self.rate
            time.sleep(min(wait, 1.0))


def build_prompt(profile_text, dimensions):
    lines = [
        "You are extracting persona-attribution fields from a survey-derived profile.",
        "",
        "Return ONLY JSON with this shape (no markdown, no commentary):",
        '{"fields": [{"field_id": "<one id from DIMENSIONS below>", '
        '"value": "<one allowed value, copied verbatim, or null>", '
        '"confidence": 0.0, "evidence": "<short quote copied from profile_text>", '
        '"description": "<1-2 sentence description of this person for this attribute>", '
        '"assignment_type": "direct"}]}',
        "",
        "Allowed assignment_type values:",
        "- direct: explicitly stated.  - structured_claim: from structured facts.",
        "- summary_inference: reasonable inference.  - unsupported: not supported by the input.",
        "",
        "Rules:",
        "- Emit exactly one object per dimension listed below.",
        "- value MUST be exactly one of that dimension's allowed values (verbatim), OR null.",
        '- If unsupported: value null, assignment_type "unsupported", description "".',
        "- Every non-null value MUST include a short evidence quote from profile_text.",
        "- Do not infer sensitive/psychological traits unless supported; when unsure prefer null.",
        "- Return valid JSON only.",
        "",
        "DIMENSIONS (field_id — label — description — allowed values):",
    ]
    for d in dimensions:
        allowed = " | ".join(str(v) for v in d.get("values", [])) or "(free value)"
        lines.append(
            f"- {d['id']} — {d.get('label', d['id'])} — "
            f"{str(d.get('description', '')).strip()} — [{allowed}]"
        )
    lines += ["", "PROFILE:", profile_text]
    return "\n".join(lines)


def parse_fields(text):
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return []
    try:
        obj = json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return []
    return obj.get("fields", []) if isinstance(obj, dict) else []


def cat_chunks(by_cat, per):
    out = []
    for dims in by_cat.values():
        for i in range(0, len(dims), per):
            out.append(dims[i : i + per])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", required=True)
    ap.add_argument("--schema", default="dimensions.json")
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--model", required=True, help="model name as your API proxy exposes it"
    )
    ap.add_argument("--base-url", default=os.environ.get("LLM_API_BASE_URL"))
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument(
        "--max-dims-per-chunk", type=int, default=50
    )  # 50 = team-consistent; raise for speed
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument(
        "--retries", type=int, default=6
    )  # 429s wait 20s each -> survive a bad minute
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument(
        "--batch",
        type=int,
        default=16,
        help="profiles per window; keeps all workers saturated across profile boundaries",
    )
    ap.add_argument(
        "--tpm",
        type=int,
        default=180000,
        help="token/min budget to pace under (keep < your key's TPM cap for margin)",
    )
    ap.add_argument(
        "--out-tok-per-dim",
        type=int,
        default=18,
        help="est output tokens per dim, for throttle accounting (emit-all~18)",
    )
    args = ap.parse_args()

    key = os.environ.get("LLM_API_KEY")
    if not key:
        raise SystemExit("Set your key first:  export LLM_API_KEY='...'")
    if not args.base_url:
        raise SystemExit("Set --base-url or LLM_API_BASE_URL (your API proxy /v1 URL)")
    endpoint = args.base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    try:  # verify TLS with certifi's CA bundle if present (conda ships it)
        import certifi

        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:  # fallback for a broken cert store: skip verification
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        print(
            "  [note] certifi not found — TLS verification OFF (calling your own trusted proxy).",
            flush=True,
        )

    dims_doc = json.load(open(args.schema))["dimensions"]
    by_cat = {}
    for d in dims_doc:
        by_cat.setdefault(d.get("category", "Uncategorized"), []).append(d)
    chunks = cat_chunks(by_cat, args.max_dims_per_chunk)

    profiles = [json.loads(line) for line in open(args.profiles)]
    if args.limit:
        profiles = profiles[: args.limit]

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    MIN_FIELDS = (
        1280  # "done" only if ~all 53 chunks landed; else redo (rate-limit self-heal)
    )
    done = set()
    if os.path.exists(args.out):
        kept = []
        for line in open(args.out).read().splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if len(r.get("fields", [])) >= MIN_FIELDS and r["uuid"] not in done:
                done.add(r["uuid"])
                kept.append(line)  # keep first complete, drop partials & dups
        with open(args.out, "w") as f:  # rewrite clean (self-heals corrupted runs)
            for line in kept:
                f.write(line + "\n")
    todo = [p for p in profiles if p["uuid"] not in done]
    print(
        f"profiles={len(profiles)} done={len(done)} todo={len(todo)} "
        f"chunks/profile={len(chunks)} calls={len(todo) * len(chunks):,}",
        flush=True,
    )

    bucket = TokenBucket(args.tpm)

    def call_chunk(profile_text, chunk):
        prompt = build_prompt(profile_text, chunk)
        body = json.dumps(
            {
                "model": args.model,
                "temperature": 0,
                "max_tokens": args.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        est = (
            len(prompt) // 4 + len(chunk) * args.out_tok_per_dim
        )  # ~input+output tokens
        for attempt in range(args.retries):
            try:
                bucket.acquire(est)  # pace under the TPM cap
                req = urllib.request.Request(endpoint, data=body, headers=headers)
                with urllib.request.urlopen(req, timeout=180, context=ssl_ctx) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return parse_fields(data["choices"][0]["message"]["content"])
            except Exception as ex:
                code = getattr(ex, "code", None)
                if attempt == args.retries - 1:
                    detail = (
                        ex.read().decode("utf-8", "ignore")[:300]
                        if hasattr(ex, "read")
                        else str(ex)
                    )
                    print(
                        f"  [warn] chunk failed after {args.retries} tries: {detail}",
                        flush=True,
                    )
                    return []
                time.sleep(
                    20 if code == 429 else 2**attempt
                )  # 429 -> wait out the minute window

    # Windowed submission: enqueue all chunks for a window of `batch` profiles at once so
    # the worker pool stays saturated across profile boundaries (no per-profile tail idle).
    # Writes happen only in this (main) thread as each profile's last chunk lands -> no lock,
    # and resume-safe (a killed run keeps every fully-written profile).
    t0 = time.time()
    n = 0
    with (
        open(args.out, "a") as fh,
        cf.ThreadPoolExecutor(max_workers=args.workers) as ex,
    ):
        for i in range(0, len(todo), args.batch):
            window = todo[i : i + args.batch]
            pmeta = {p["uuid"]: p for p in window}
            acc = {p["uuid"]: [] for p in window}
            remaining = {p["uuid"]: len(chunks) for p in window}
            fut2uid = {
                ex.submit(call_chunk, p["profile_text"], c): p["uuid"]
                for p in window
                for c in chunks
            }
            for fut in cf.as_completed(fut2uid):
                uid = fut2uid[fut]
                acc[uid].extend(fut.result())
                remaining[uid] -= 1
                if remaining[uid] == 0:  # profile complete -> write now
                    p = pmeta[uid]
                    rec = {
                        "uuid": uid,
                        "observed": p.get("observed", {}),
                        "fields": acc.pop(uid),
                    }
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
                    n += 1
                    if n % 25 == 0 or n == len(todo):
                        rate = n / max(1e-9, time.time() - t0)
                        print(
                            f"  {n}/{len(todo)} profiles  {rate:.2f} prof/s  "
                            f"ETA {(len(todo) - n) / max(1e-9, rate) / 60:.0f} min",
                            flush=True,
                        )
    print(f"DONE {n} profiles -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
