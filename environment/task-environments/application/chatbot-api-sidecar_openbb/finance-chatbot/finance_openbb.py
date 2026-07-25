"""OpenBB-backed finance chatbot adapter for the Harbor chatbot API."""

from __future__ import annotations

import asyncio
import datetime as _dt
import os
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Protocol, Tuple

from fastapi import HTTPException

DEFAULT_OPENBB_CATEGORIES: Tuple[str, ...] = (
    "equity",
    "etf",
    "economy",
    "news",
    "crypto",
    "fixedincome",
    "index",
    "technical",
)


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str) -> str:
    return "{}_{}".format(prefix, uuid.uuid4().hex[:12])


def _split_csv(value: Optional[str], default: Tuple[str, ...]) -> Tuple[str, ...]:
    if value is None:
        return default
    parts = tuple(part.strip() for part in value.split(",") if part.strip())
    return parts or default


def _truncate_text(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    suffix = "\n[truncated]"
    return text[: max(0, limit - len(suffix))].rstrip() + suffix


def _message_chars(messages: List[Dict[str, str]]) -> int:
    return sum(len(message.get("content", "")) for message in messages)


def _is_context_length_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return (
        "context_length_exceeded" in text
        or "exceeds the context window" in text
        or "context window" in text
    )


def _is_transient_agent_error(exc: BaseException) -> bool:
    """True for flaky upstream OpenAI / MCP transport failures worth retrying."""
    text = str(exc).lower()
    needles = (
        "connection error",
        "connection reset",
        "connection aborted",
        "connect error",
        "timed out",
        "timeout",
        "temporarily unavailable",
        "rate limit",
        "too many requests",
        "429",
        "502",
        "503",
        "504",
        "overloaded",
        "server disconnected",
        "remote protocol",
        "apiconnectionerror",
        "network error",
        "eof occurred",
    )
    return any(needle in text for needle in needles)


_AGENT_SEM: threading.Semaphore | None = None
_AGENT_SEM_LOCK = threading.Lock()


def _agent_semaphore() -> threading.Semaphore:
    """Cap concurrent OpenAI+MCP agent runs across FastAPI worker threads.

    Each Harbor trial hits ``asyncio.run`` in its own thread; an asyncio
    semaphore would not serialize those. Queueing beats stampeding the API.
    """
    global _AGENT_SEM
    with _AGENT_SEM_LOCK:
        if _AGENT_SEM is None:
            raw = os.environ.get("FINANCE_AGENT_MAX_CONCURRENT", "6").strip()
            try:
                limit = max(1, int(raw))
            except ValueError:
                limit = 6
            _AGENT_SEM = threading.Semaphore(limit)
        return _AGENT_SEM


def _agent_retry_limit() -> int:
    raw = os.environ.get("FINANCE_AGENT_RETRIES", "4").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 4


def _agent_max_turns() -> int:
    # Agents SDK max_turns = tool-loop steps for ONE user message (not chat
    # turns). Live OpenBB cohorts routinely issue 10–40 MCP tool calls on a
    # single research question; 20 was too low (trials 503'd), 30 is still
    # tight. Default 50; override with FINANCE_AGENT_MAX_TURNS.
    raw = os.environ.get("FINANCE_AGENT_MAX_TURNS", "50").strip()
    try:
        return max(4, int(raw))
    except ValueError:
        return 50


def _is_max_turns_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "max turns" in text or "max_turns" in text


def _select_openbb_categories(
    messages: List[Dict[str, str]], config: FinanceAgentConfig
) -> Tuple[str, ...]:
    allowed = tuple(dict.fromkeys(config.openbb_categories))
    allowed_set = set(allowed)
    limit = max(1, min(len(allowed), int(config.max_active_categories)))
    text = " ".join(str(message.get("content", "")) for message in messages).lower()
    selected: List[str] = []

    def add(category: str) -> None:
        if category in allowed_set and category not in selected:
            selected.append(category)

    keyword_map: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...]], ...] = (
        (
            ("etf", "fund", "portfolio", "allocation", "expense ratio"),
            ("etf", "equity"),
        ),
        (
            ("crypto", "bitcoin", "ethereum", "blockchain", "distributed ledger"),
            ("crypto", "equity"),
        ),
        (
            ("news", "headline", "recent", "momentum", "catalyst", "event"),
            ("news", "equity"),
        ),
        (
            ("macro", "inflation", "gdp", "fed", "rate", "yield curve"),
            ("economy", "fixedincome"),
        ),
        (
            ("bond", "fixed income", "treasury", "credit", "duration", "yield"),
            ("fixedincome", "etf"),
        ),
        (("index", "s&p", "nasdaq", "dow"), ("index", "equity")),
        (
            ("technical", "rsi", "moving average", "trend", "support", "resistance"),
            ("technical", "equity"),
        ),
        (
            ("stock", "ticker", "company", "companies", "security", "securities"),
            ("equity", "news"),
        ),
    )
    for keywords, categories in keyword_map:
        if any(keyword in text for keyword in keywords):
            for category in categories:
                add(category)
                if len(selected) >= limit:
                    return tuple(selected)

    for fallback in ("equity", "news", "etf", "economy", "crypto"):
        add(fallback)
        if len(selected) >= limit:
            return tuple(selected)
    for category in allowed:
        add(category)
        if len(selected) >= limit:
            return tuple(selected)
    return tuple(selected)


def finance_system_prompt() -> str:
    return (
        "You are a financial research chatbot for evaluation. Help users with "
        "company analysis, ETF comparison, macroeconomic research, market/news "
        "lookup, crypto research, index data, fixed-income data, and technical "
        "indicator lookup. Use concrete OpenBB MCP tools before making specific "
        "factual claims about prices, fundamentals, ETF details, macro data, "
        "news, index data, fixed-income data, crypto data, or technical signals. "
        "Ask concise clarification questions when the objective, ticker, "
        "geography, time horizon, or risk constraints are ambiguous. Do not "
        "provide personalized investment advice or tell the user what to buy or "
        "sell. Clearly separate observed data from analysis, state uncertainty, "
        "and include risk/disclaimer language when the answer could influence "
        "financial decisions."
    )


@dataclass(frozen=True)
class FinanceAgentConfig:
    model: str = "gpt-4o-mini"
    openbb_mcp_url: str = "http://openbb-mcp:8001/mcp"
    openbb_categories: Tuple[str, ...] = DEFAULT_OPENBB_CATEGORIES
    agent_name: str = "Financial Research Chatbot"
    mcp_timeout_seconds: float = 30.0
    instructions: str = ""
    max_history_messages: int = 4
    max_history_chars: int = 8000
    max_message_chars: int = 2000
    max_active_categories: int = 3

    @classmethod
    def from_env(
        cls, environ: Optional[Mapping[str, str]] = None
    ) -> "FinanceAgentConfig":
        env = os.environ if environ is None else environ
        return cls(
            model=env.get("FINANCE_AGENT_MODEL", "gpt-4o-mini"),
            openbb_mcp_url=env.get("OPENBB_MCP_URL", "http://openbb-mcp:8001/mcp"),
            openbb_categories=_split_csv(
                env.get("OPENBB_MCP_CATEGORIES"),
                DEFAULT_OPENBB_CATEGORIES,
            ),
            agent_name=env.get("FINANCE_AGENT_NAME", "Financial Research Chatbot"),
            mcp_timeout_seconds=float(env.get("OPENBB_MCP_TIMEOUT_SECONDS", "30")),
            instructions=env.get("FINANCE_AGENT_SYSTEM_PROMPT", finance_system_prompt()),
            max_history_messages=int(env.get("FINANCE_AGENT_MAX_HISTORY_MESSAGES", "4")),
            max_history_chars=int(env.get("FINANCE_AGENT_MAX_HISTORY_CHARS", "8000")),
            max_message_chars=int(env.get("FINANCE_AGENT_MAX_MESSAGE_CHARS", "2000")),
            max_active_categories=int(env.get("OPENBB_MCP_MAX_ACTIVE_CATEGORIES", "3")),
        )

    def mcp_headers(self, environ: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
        env = os.environ if environ is None else environ
        authorization = env.get("OPENBB_MCP_AUTHORIZATION")
        bearer = env.get("OPENBB_MCP_AUTH_BEARER")
        if authorization:
            return {"Authorization": authorization}
        if bearer:
            return {"Authorization": "Bearer {}".format(bearer)}
        return {}

    def mcp_params(self, environ: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "url": self.openbb_mcp_url,
            "timeout": self.mcp_timeout_seconds,
        }
        headers = self.mcp_headers(environ)
        if headers:
            params["headers"] = headers
        return params

    def to_public_metadata(
        self, environ: Optional[Mapping[str, str]] = None
    ) -> Dict[str, Any]:
        env = os.environ if environ is None else environ
        return {
            "applicationId": "finance_openbb",
            "product": "OpenBB-powered financial research chatbot",
            "agent": "OpenAI Agents SDK",
            "agentName": self.agent_name,
            "model": self.model,
            "dataLayer": "OpenBB MCP",
            "mcpServer": {
                "transport": "streamable-http",
                "url": self.openbb_mcp_url,
                "categories": list(self.openbb_categories),
                "maxActiveCategories": self.max_active_categories,
                "authConfigured": bool(
                    env.get("OPENBB_MCP_AUTHORIZATION")
                    or env.get("OPENBB_MCP_AUTH_BEARER")
                ),
            },
            "safety": {
                "mode": "financial research and decision support",
                "personalizedAdvice": False,
            },
        }


@dataclass
class AgentResult:
    assistant_message: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


class FinanceAgentRunner(Protocol):
    async def run(
        self, *, messages: List[Dict[str, str]], config: FinanceAgentConfig
    ) -> AgentResult:
        """Run one assistant turn over the full conversation history."""


class OpenAIAgentsFinanceRunner:
    async def run(
        self, *, messages: List[Dict[str, str]], config: FinanceAgentConfig
    ) -> AgentResult:
        categories = _select_openbb_categories(messages, config)
        attempts = _agent_retry_limit()
        last_exc: BaseException | None = None
        for attempt in range(attempts):
            await asyncio.to_thread(_agent_semaphore().acquire)
            try:
                try:
                    return await self._run_with_categories(
                        messages=messages, config=config, categories=categories
                    )
                except Exception as exc:
                    if len(categories) > 1 and _is_context_length_error(exc):
                        return await self._run_with_categories(
                            messages=messages,
                            config=config,
                            categories=categories[:1],
                        )
                    raise
            except Exception as exc:
                last_exc = exc
                if attempt + 1 >= attempts or not _is_transient_agent_error(exc):
                    raise
            finally:
                _agent_semaphore().release()
            # Exponential backoff between transient failures (cap 8s).
            await asyncio.sleep(min(8.0, 0.6 * (2**attempt)))
        assert last_exc is not None
        raise last_exc

    async def _run_with_categories(
        self,
        *,
        messages: List[Dict[str, str]],
        config: FinanceAgentConfig,
        categories: Tuple[str, ...],
    ) -> AgentResult:
        try:
            from agents import Agent, Runner
            from agents.mcp import MCPServerStreamableHttp
        except ImportError as exc:  # pragma: no cover - depends on live env
            raise RuntimeError(
                "Finance application runtime is not installed. Install "
                "openai-agents in the chatbot sidecar image."
            ) from exc

        async with MCPServerStreamableHttp(
            name="OpenBB MCP",
            params=config.mcp_params(),
            cache_tools_list=True,
            client_session_timeout_seconds=config.mcp_timeout_seconds,
        ) as server:
            for category in categories:
                await server.call_tool("activate_category", {"category": category})
            server.invalidate_tools_cache()
            agent = Agent(
                name=config.agent_name,
                instructions=config.instructions,
                model=config.model,
                mcp_servers=[server],
            )
            try:
                result = await Runner.run(
                    agent, input=messages, max_turns=_agent_max_turns()
                )
            except Exception as exc:
                # Tool-loop exhaustion must not 503 the whole Harbor trial.
                if not _is_max_turns_error(exc):
                    raise
                partial = (
                    getattr(exc, "result", None)
                    or getattr(exc, "run_result", None)
                    or getattr(exc, "data", None)
                )
                partial_text = str(getattr(partial, "final_output", "") or "").strip()
                message = partial_text or (
                    "I hit an internal research step limit while gathering market "
                    "data and could not finish a complete answer this turn. Please "
                    "ask again with a narrower question (one ticker or one metric)."
                )
                return AgentResult(
                    assistant_message=message,
                    tool_calls=_extract_tool_calls(partial) if partial else [],
                    citations=_extract_citations(partial) if partial else [],
                    raw={
                        "maxTurnsExceeded": True,
                        "activeOpenBBCategories": list(categories),
                        "error": str(exc)[:300],
                    },
                )

        return AgentResult(
            assistant_message=str(getattr(result, "final_output", "") or ""),
            tool_calls=_extract_tool_calls(result),
            citations=_extract_citations(result),
            raw={
                **_result_summary(result),
                "activeOpenBBCategories": list(categories),
            },
        )


@dataclass
class FinanceSession:
    id: str
    title: str = "New finance chat"
    messages: List[Dict[str, str]] = field(default_factory=list)
    turns: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now)
    turn_lock: Any = field(default_factory=threading.Lock, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "config": {
                "applicationId": "finance_openbb",
                "applicationContext": "financial_research",
            },
            "messages": [dict(message) for message in self.messages],
            "turns": [dict(turn) for turn in self.turns],
            "createdAt": self.created_at,
        }


class FinanceChatService:
    def __init__(
        self,
        *,
        runner: Optional[FinanceAgentRunner] = None,
        config: Optional[FinanceAgentConfig] = None,
    ) -> None:
        self.runner = runner or OpenAIAgentsFinanceRunner()
        self.config = config or FinanceAgentConfig.from_env()
        self._sessions: Dict[str, FinanceSession] = {}
        self._guard = threading.RLock()

    def create_session(self, title: Optional[str] = None) -> FinanceSession:
        session = FinanceSession(
            id=_new_id("fin_ses"),
            title=(title or "").strip() or "New finance chat",
        )
        with self._guard:
            self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[FinanceSession]:
        with self._guard:
            return self._sessions.get(session_id)

    async def chat(
        self, *, message: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if session_id:
            session = self.get_session(session_id)
            if session is None:
                raise KeyError("unknown session: {}".format(session_id))
        else:
            session = self.create_session()
        return await self.run_turn(session.id, message)

    async def run_turn(self, session_id: str, message: str) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if session is None:
            raise KeyError("unknown session: {}".format(session_id))
        user_text = (message or "").strip()
        if not user_text:
            raise ValueError("message must not be empty")

        acquired = False
        await asyncio.to_thread(session.turn_lock.acquire)
        acquired = True
        try:
            with self._guard:
                messages = [dict(existing) for existing in session.messages]
                messages.append({"role": "user", "content": user_text})

            runner_messages = self._messages_for_runner(messages)
            try:
                result = await self.runner.run(messages=runner_messages, config=self.config)
            except RuntimeError as exc:
                # Soft-degrade so a flaky upstream blip does not kill the trial.
                if not (_is_transient_agent_error(exc) or _is_max_turns_error(exc)):
                    raise
                result = AgentResult(
                    assistant_message=(
                        "I'm having trouble reaching live market data right now. "
                        "Please try that question again in a moment."
                    ),
                    raw={"degraded": True, "error": str(exc)[:300]},
                )
            except Exception as exc:
                if _is_transient_agent_error(exc) or _is_max_turns_error(exc):
                    result = AgentResult(
                        assistant_message=(
                            "I'm having trouble reaching live market data right now. "
                            "Please try that question again in a moment."
                        ),
                        raw={"degraded": True, "error": str(exc)[:300]},
                    )
                else:
                    raise RuntimeError(
                        "Finance application failed: {}".format(exc)
                    ) from exc
            turn = self._build_turn(session, user_text, result)

            with self._guard:
                session.messages.append({"role": "user", "content": user_text})
                session.messages.append(
                    {"role": "assistant", "content": result.assistant_message}
                )
                session.turns.append(turn)
            return dict(turn)
        finally:
            if acquired:
                session.turn_lock.release()

    def _build_turn(
        self, session: FinanceSession, user_message: str, result: AgentResult
    ) -> Dict[str, Any]:
        grounded_items = _grounded_items(result)
        return {
            "turnId": _new_id("fin_turn"),
            "conversationId": session.id,
            "backend": "finance_openbb",
            "userMessage": user_message,
            "assistantMessage": result.assistant_message,
            "plan": [
                {
                    "tool": str(call.get("name") or "OpenBB MCP"),
                    "detail": str(call.get("type") or ""),
                    "status": str(call.get("status") or "ok"),
                }
                for call in result.tool_calls
            ],
            "recommendedItems": [dict(item) for item in grounded_items],
            "groundedItems": [dict(item) for item in grounded_items],
            "nativeRaw": None,
            "rawToolOutputs": {"toolCalls": result.tool_calls, "citations": result.citations},
            "metadata": self.config.to_public_metadata(),
            "createdAt": _utc_now(),
        }

    def _messages_for_runner(
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        max_messages = max(1, int(self.config.max_history_messages))
        max_history_chars = max(1, int(self.config.max_history_chars))
        max_message_chars = max(1, int(self.config.max_message_chars))
        normalized = [
            {
                "role": str(message.get("role", "user")),
                "content": _truncate_text(str(message.get("content", "")), max_message_chars),
            }
            for message in messages
        ]
        if (
            len(normalized) <= max_messages
            and _message_chars(normalized) <= max_history_chars
        ):
            return normalized

        recent = normalized[-max_messages:]
        older = normalized[: -max_messages]
        summary_budget = min(
            max_message_chars, max(120, max_history_chars - _message_chars(recent))
        )
        summary = self._history_summary(older, summary_budget)
        compacted = [{"role": "assistant", "content": summary}] + recent
        while len(compacted) > 1 and _message_chars(compacted) > max_history_chars:
            del compacted[1]
        return compacted

    def _history_summary(self, messages: List[Dict[str, str]], budget: int) -> str:
        lines = ["Earlier conversation summary for continuity (truncated):"]
        remaining = max(0, budget - len(lines[0]) - 1)
        for message in messages:
            if remaining <= 0:
                break
            role = message.get("role", "user")
            prefix = "User" if role == "user" else "Assistant"
            line = "{}: {}".format(prefix, message.get("content", "").replace("\n", " "))
            line = _truncate_text(line, min(remaining, self.config.max_message_chars))
            lines.append(line)
            remaining -= len(line) + 1
        if len(lines) == 1:
            lines.append("Earlier details omitted to keep the live prompt within budget.")
        return "\n".join(lines)


class FinanceOpenBBApplication:
    application_id = "finance_openbb"
    default_context = "financial_research"
    contexts = ("financial_research",)

    def __init__(self, service: Optional[FinanceChatService] = None) -> None:
        self.service = service or FinanceChatService()

    def ready(self, context: str) -> None:
        if context != self.default_context:
            raise HTTPException(status_code=422, detail="unknown applicationContext")
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required for finance chatbot turns")
        try:
            from agents import Agent, Runner  # noqa: F401
            from agents.mcp import MCPServerStreamableHttp  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Finance application runtime is not installed. Install "
                "openai-agents in the chatbot sidecar image."
            ) from exc
        config = self.service.config
        mcp_url = config.openbb_mcp_url
        try:
            import socket
            from urllib.parse import urlparse

            parsed = urlparse(mcp_url)
            host = parsed.hostname
            if not host:
                raise RuntimeError("OPENBB_MCP_URL is missing a host")
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            with socket.create_connection(
                (host, port),
                timeout=min(5.0, config.mcp_timeout_seconds),
            ):
                pass
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "OpenBB MCP is not ready at {}: {}".format(mcp_url, exc)
            ) from exc

    def create_session(
        self,
        *,
        title: Optional[str],
        context: str,
        engine: Optional[str],
        bot_type: Optional[str],
    ) -> Dict[str, Any]:
        del engine, bot_type
        if context != self.default_context:
            raise HTTPException(status_code=422, detail="unknown applicationContext")
        session = self.service.create_session(title=title)
        payload = session.to_dict()
        return {
            "sessionId": session.id,
            "applicationId": self.application_id,
            "applicationContext": context,
            "config": dict(payload["config"]),
            "session": payload,
        }

    def send_message(
        self,
        *,
        session_id: Optional[str],
        message: str,
        title: Optional[str],
        context: str,
        engine: Optional[str],
        bot_type: Optional[str],
    ) -> Dict[str, Any]:
        del title, engine, bot_type
        if context != self.default_context:
            raise HTTPException(status_code=422, detail="unknown applicationContext")
        try:
            turn = asyncio.run(
                self.service.chat(message=message, session_id=session_id)
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="session not found")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        session = self.service.get_session(str(turn["conversationId"]))
        messages = [dict(message) for message in session.messages] if session else []
        grounded_items = turn.get("groundedItems") or turn.get("recommendedItems") or []
        return {
            "sessionId": turn["conversationId"],
            "applicationId": self.application_id,
            "applicationContext": self.default_context,
            "reply": turn.get("assistantMessage") or "",
            "turn": turn,
            "recommendedItems": grounded_items,
            "groundedItems": grounded_items,
            "messages": messages,
        }

    def conversation(self, *, session_id: str) -> Dict[str, Any]:
        session = self.service.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        payload = session.to_dict()
        return {
            "sessionId": session.id,
            "applicationId": self.application_id,
            "applicationContext": self.default_context,
            "domain": self.default_context,
            "messages": payload["messages"],
            "turns": payload["turns"],
        }

    def recommendations(self, *, session_id: str) -> Dict[str, Any]:
        session = self.service.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        items = _dedupe_grounded_items(session.turns)
        return {
            "sessionId": session.id,
            "applicationId": self.application_id,
            "applicationContext": self.default_context,
            "domain": self.default_context,
            "recommendedItems": items,
            "groundedItems": items,
            "turnsToResult": len(session.turns),
            "total": len(items),
        }


def _extract_tool_calls(result: Any) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    for item in getattr(result, "new_items", []) or []:
        raw = getattr(item, "raw_item", None) or getattr(item, "item", None) or item
        name = (
            getattr(raw, "name", None)
            or getattr(raw, "tool_name", None)
            or getattr(item, "name", None)
            or getattr(item, "tool_name", None)
        )
        item_type = getattr(item, "type", None) or getattr(raw, "type", None)
        if name or (isinstance(item_type, str) and "tool" in item_type):
            calls.append(
                {
                    "name": str(name or item_type or "tool_call"),
                    "status": "ok",
                    "type": str(item_type or "tool_call"),
                }
            )
    return calls


def _extract_citations(result: Any) -> List[Dict[str, Any]]:
    if _extract_tool_calls(result):
        return [{"source": "OpenBB", "label": "OpenBB MCP tool result"}]
    return []


def _result_summary(result: Any) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    final_output = getattr(result, "final_output", None)
    if final_output is not None:
        summary["final_output"] = str(final_output)
    last_agent = getattr(result, "last_agent", None)
    if last_agent is not None:
        summary["last_agent"] = str(getattr(last_agent, "name", last_agent))
    new_items = getattr(result, "new_items", None)
    if new_items is not None:
        summary["newItemCount"] = len(new_items)
    return summary


def _grounded_items(result: AgentResult) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for index, call in enumerate(result.tool_calls):
        name = str(call.get("name") or "openbb_tool")
        items.append(
            {
                "itemId": "finance:openbb:{}:{}".format(name, index),
                "rank": index + 1,
                "title": "OpenBB {}".format(name),
                "meta": str(call.get("type") or "tool result"),
            }
        )
    for citation in result.citations:
        if items:
            break
        label = str(citation.get("label") or citation.get("source") or "OpenBB")
        items.append(
            {
                "itemId": "finance:openbb:citation",
                "rank": 1,
                "title": label,
                "meta": str(citation.get("source") or "OpenBB"),
            }
        )
    return items


def _dedupe_grounded_items(turns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    items: List[Dict[str, Any]] = []
    for turn in reversed(turns):
        for item in turn.get("groundedItems") or turn.get("recommendedItems") or []:
            if not isinstance(item, dict):
                continue
            item_id = item.get("itemId", item.get("id"))
            if item_id is None:
                continue
            item_id = str(item_id)
            if item_id in seen:
                continue
            seen.add(item_id)
            items.append({**item, "itemId": item_id})
    return items
