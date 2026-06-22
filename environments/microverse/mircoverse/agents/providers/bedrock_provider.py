"""AWS Bedrock provider — neutral tool-use surface over the Converse API (Protocol.md §7).

A thin translator at the edge of the reference agent's tool-use loop (§7): it consumes
the provider-neutral `complete(system, messages, tools)` surface (llm_types.py) and
speaks Bedrock's native Converse dialect. The engine never imports this on the hot path
(§7.3) — only the participant-side reference agent does.

Bedrock's `bedrock-runtime` boto3 client is SYNCHRONOUS, so `complete()` runs the blocking
`converse` call in a worker thread (`asyncio.to_thread`) to stay async-friendly. The class
is STATELESS w.r.t. the conversation: it re-translates the full neutral `messages` history
to native form on every call.

boto3 is lazy-imported ONLY when no `client` is injected, so the test suite runs with no
AWS SDK installed and no network/credentials touched (tests inject a fake client whose
`.converse` returns a canned native response).

Native Converse shapes (translated here):

    system  -> system=[{"text": <system>}]
    tools   -> toolConfig={"tools": [{"toolSpec": {"name", "description",
                                                   "inputSchema": {"json": <input_schema>}}}]}
    user        -> {"role": "user",      "content": [{"text": <text>}]}
    assistant   -> {"role": "assistant", "content": [{"toolUse": {"toolUseId","name","input"}}]}
    tool_results-> {"role": "user",      "content": [{"toolResult": {"toolUseId",
                                                      "content": [{"text": <content>}]}}]}

    resp["output"]["message"]["content"] : list of items;
        {"toolUse": {...}} -> ToolCall(id, name, input)
        {"text": "..."}    -> accumulated into Completion.text
    resp["stopReason"]     -> Completion.stop_reason
"""

from __future__ import annotations

import asyncio
import os
import random
from typing import Any, Optional

from mircoverse.agents.llm_types import Completion, ToolCall

# Error codes/classes worth retrying at the APPLICATION layer. boto3's own (adaptive) retries are the
# first line of defence; this set is the safety net for when those are exhausted and a throttle/timeout
# still propagates. Detected by error-code string and class name so the module stays SDK-free at import.
_RETRYABLE_CODES = frozenset({
    "ThrottlingException", "TooManyRequestsException", "ModelTimeoutException",
    "ServiceUnavailableException", "InternalServerException", "ModelNotReadyException",
})
_RETRYABLE_CLASSES = frozenset({
    "ThrottlingException", "ReadTimeoutError", "ConnectTimeoutError", "ConnectionError",
    "EndpointConnectionError",
})


def _is_retryable(exc: BaseException) -> bool:
    """True if ``exc`` is a transient Bedrock throttle/timeout worth a backoff-retry (not a 4xx like
    a malformed request, which must surface immediately rather than being silently retried)."""
    resp = getattr(exc, "response", None)
    if isinstance(resp, dict):
        code = (resp.get("Error") or {}).get("Code")
        if code in _RETRYABLE_CODES:
            return True
    return type(exc).__name__ in _RETRYABLE_CLASSES


class BedrockProvider:
    """An `LLMProvider` backed by AWS Bedrock's Converse API (boto3 bedrock-runtime).

    Construction is SDK-free when a `client` is injected (the test path). With no
    client, boto3 is lazy-imported on first construction to build a real
    `bedrock-runtime` client. Region/credentials fall back to the AWS env/config in
    the usual boto3 way; an explicit `region_name=` overrides `AWS_REGION` /
    `MIRCOVERSE_BEDROCK_REGION`.
    """

    provider_name: str = "bedrock"

    def __init__(
        self,
        model: str,
        *,
        client: Optional[Any] = None,
        region_name: Optional[str] = None,
        max_retries: int = 5,
        **_kw: Any,
    ) -> None:
        self.model = model
        # App-level backoff budget (the safety net beyond boto3's own retries). Each call that
        # retries increments ``retry_count`` so the driver can log a per-tick throttle time series
        # and distinguish "throttled-but-recovered" from "agent genuinely errored".
        self.max_retries = max_retries
        self.retry_count = 0
        if client is not None:
            # Test / injection path: never touch boto3 or AWS.
            self._client = client
            return
        # Real path: lazy-import boto3 only now, so the suite runs without it installed.
        import boto3  # noqa: PLC0415 — deliberately deferred to first real use
        from botocore.config import Config  # noqa: PLC0415

        region = region_name or os.getenv("AWS_REGION") or os.getenv("MIRCOVERSE_BEDROCK_REGION")
        # Adaptive retries (client-side rate limiting + more attempts) are boto3's first line of
        # defence under the concurrent fan-out (25 agents x N processes). The app-level loop in
        # complete() is the second line for when these are exhausted.
        cfg = Config(retries={"max_attempts": 8, "mode": "adaptive"},
                     read_timeout=120, connect_timeout=15)
        self._client = boto3.client("bedrock-runtime", region_name=region, config=cfg)

    async def complete(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> Completion:
        """Translate the neutral request to Converse, call it off-thread, normalize back.

        boto3's `converse` is blocking, so it is dispatched via `asyncio.to_thread`.
        The full neutral `messages` history is re-translated every call (stateless)."""
        native_system = [{"text": system}]
        native_messages = _to_native_messages(messages)
        tool_config = _to_tool_config(tools)

        # Bounded exponential backoff + full jitter on transient throttles/timeouts. Without this, a
        # ThrottlingException propagates up to the driver's per-agent guard, the agent gets NO accepted
        # action that tick, and the resolver defaults it to `wait` — which still debits water. Under
        # parallel fan-out that manufactures throttle-correlated deaths indistinguishable from (and
        # pointed straight at) the H1 scarcity-death channel. Retrying here keeps a throttle from
        # becoming a silent death. A non-retryable error (e.g. a 4xx validation failure) raises at once.
        attempt = 0
        while True:
            try:
                resp = await asyncio.to_thread(
                    self._client.converse,
                    modelId=self.model,
                    system=native_system,
                    messages=native_messages,
                    toolConfig=tool_config,
                )
                return _from_native_response(resp)
            except Exception as exc:  # noqa: BLE001 — re-raised below unless transient+budget remains
                if attempt >= self.max_retries or not _is_retryable(exc):
                    raise
                attempt += 1
                self.retry_count += 1
                # Full jitter: sleep ~U(0, base*2^attempt), capped, so concurrent agents that all got
                # throttled don't retry in lockstep (which would just re-throttle).
                backoff = min(20.0, 0.5 * (2 ** attempt))
                await asyncio.sleep(backoff * (0.5 + 0.5 * random.random()))


# ── Pure translation helpers (unit-testable, no I/O) ────────────────────────────


def _to_tool_config(tools: list[dict]) -> dict:
    """Wrap neutral tool dicts ({name, description, input_schema}) in Converse toolSpecs."""
    return {
        "tools": [
            {
                "toolSpec": {
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": {"json": t["input_schema"]},
                }
            }
            for t in tools
        ]
    }


def _to_native_messages(messages: list[dict]) -> list[dict]:
    """Translate the neutral conversation history into Converse `messages`.

    The three neutral role shapes (llm_types.py) map to:
      * user         -> a single text content block under role "user"
      * assistant    -> toolUse content blocks (+ optional leading text) under "assistant"
      * tool_results -> toolResult content blocks under role "user" (Converse carries
        tool results on a user turn)
    """
    native: list[dict] = []
    for msg in messages:
        role = msg.get("role")
        if role == "user":
            native.append({"role": "user", "content": [{"text": msg.get("content", "")}]})
        elif role == "assistant":
            content: list[dict] = []
            text = msg.get("text") or ""
            if text:
                content.append({"text": text})
            for call in msg.get("tool_calls", []):
                content.append(
                    {
                        "toolUse": {
                            "toolUseId": call["id"],
                            "name": call["name"],
                            "input": call["input"],
                        }
                    }
                )
            native.append({"role": "assistant", "content": content})
        elif role == "tool_results":
            content = [
                {
                    "toolResult": {
                        "toolUseId": r["id"],
                        "content": [{"text": r["content"]}],
                    }
                }
                for r in msg.get("results", [])
            ]
            native.append({"role": "user", "content": content})
        else:  # pragma: no cover - defensive; the loop only emits the three shapes
            raise ValueError(f"Unknown neutral message role: {role!r}")
    return native


def _from_native_response(resp: dict) -> Completion:
    """Normalize a Converse response into a `Completion` (tool_calls + text + stop_reason)."""
    message = (resp.get("output") or {}).get("message") or {}
    tool_calls: list[ToolCall] = []
    text_parts: list[str] = []
    for item in message.get("content", []) or []:
        if "toolUse" in item:
            tu = item["toolUse"]
            tool_calls.append(
                ToolCall(id=tu["toolUseId"], name=tu["name"], input=tu.get("input", {}))
            )
        elif "text" in item:
            text_parts.append(item["text"])
    return Completion(
        tool_calls=tool_calls,
        text="".join(text_parts),
        stop_reason=resp.get("stopReason", ""),
    )
