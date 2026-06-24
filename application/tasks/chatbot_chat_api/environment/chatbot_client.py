from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a real multi-turn conversation with the chatbot API."
    )
    parser.add_argument("--api-url", default="http://chatbot-api:8000")
    parser.add_argument("--application-id", required=True)
    parser.add_argument("--application-context", required=True)
    parser.add_argument("--domain", default=None)
    parser.add_argument("--message", action="append", required=True)
    parser.add_argument("--output-dir", default="/app/output")
    parser.add_argument("--retries", type=int, default=6)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    return parser.parse_args()


def request_json(
    *,
    api_url: str,
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    query: Optional[Dict[str, Any]] = None,
    retries: int,
    retry_delay: float,
) -> Dict[str, Any]:
    base = api_url.rstrip("/")
    query_string = urllib.parse.urlencode(
        {key: value for key, value in (query or {}).items() if value is not None}
    )
    url = "{}{}{}".format(base, path, "?{}".format(query_string) if query_string else "")
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    last_error: Optional[BaseException] = None
    for attempt in range(max(1, retries)):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            if not isinstance(payload, dict):
                raise RuntimeError("API returned non-object JSON")
            return payload
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError("HTTP {} from {}: {}".format(exc.code, url, detail)) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(retry_delay)
    raise RuntimeError("request failed for {}: {}".format(url, last_error))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def item_count(payload: Dict[str, Any]) -> int:
    items = payload.get("groundedItems") or payload.get("recommendedItems") or []
    return len(items) if isinstance(items, list) else 0


def run(messages: Iterable[str], args: argparse.Namespace) -> Dict[str, Any]:
    request_kwargs = {
        "api_url": args.api_url,
        "retries": args.retries,
        "retry_delay": args.retry_delay,
    }
    ready = request_json(
        method="GET",
        path="/ready",
        query={
            "applicationId": args.application_id,
            "applicationContext": args.application_context,
            "domain": args.domain,
        },
        **request_kwargs,
    )
    print("READY {}".format(json.dumps(ready, ensure_ascii=False)), flush=True)

    session_id: Optional[str] = None
    turn_count = 0
    for message in messages:
        text = str(message or "").strip()
        if not text:
            continue
        body: Dict[str, Any] = {
            "applicationId": args.application_id,
            "applicationContext": args.application_context,
            "message": text,
        }
        if args.domain:
            body["domain"] = args.domain
        if session_id:
            body["sessionId"] = session_id
        payload = request_json(
            method="POST",
            path="/v1/messages",
            body=body,
            **request_kwargs,
        )
        session_id = str(payload.get("sessionId") or session_id or "")
        if not session_id:
            raise RuntimeError("chatbot response did not include sessionId")
        turn_count += 1
        print(
            "TURN {} {}".format(
                turn_count,
                json.dumps(
                    {
                        "sessionId": session_id,
                        "reply": payload.get("reply"),
                        "groundedItems": item_count(payload),
                    },
                    ensure_ascii=False,
                ),
            ),
            flush=True,
        )

    if not session_id:
        raise RuntimeError("no messages were sent")

    transcript = request_json(
        method="GET",
        path="/v1/conversation",
        query={"sessionId": session_id, "applicationId": args.application_id},
        **request_kwargs,
    )
    result = request_json(
        method="GET",
        path="/v1/application-result",
        query={"sessionId": session_id, "applicationId": args.application_id},
        **request_kwargs,
    )
    if item_count(result) < 1:
        raise RuntimeError("application result contains no grounded items")

    output_dir = Path(args.output_dir)
    write_json(output_dir / "transcript.json", transcript)
    write_json(output_dir / "application_result.json", result)
    print(
        "SAVED {}".format(
            json.dumps(
                {
                    "sessionId": session_id,
                    "turns": turn_count,
                    "groundedItems": item_count(result),
                    "outputDir": str(output_dir),
                },
                ensure_ascii=False,
            )
        ),
        flush=True,
    )
    return {"transcript": transcript, "applicationResult": result}


def main() -> int:
    args = parse_args()
    if len([message for message in args.message if str(message).strip()]) < 3:
        raise RuntimeError("provide at least three non-empty --message values")
    run(args.message, args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        raise SystemExit(1)
