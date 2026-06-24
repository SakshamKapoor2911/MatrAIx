from __future__ import annotations

import asyncio
from typing import Dict, List

from harbor_api.finance_openbb import (
    AgentResult,
    FinanceAgentConfig,
    FinanceChatService,
    FinanceOpenBBApplication,
    _select_openbb_categories,
)


class FakeFinanceRunner:
    def __init__(self) -> None:
        self.messages: List[List[Dict[str, str]]] = []

    async def run(self, *, messages, config):
        self.messages.append(messages)
        return AgentResult(
            assistant_message="I used OpenBB data to compare VTI and BND.",
            tool_calls=[
                {"name": "etf_search", "status": "ok", "type": "mcp_tool_call"}
            ],
            raw={"model": config.model},
        )


def test_finance_chat_service_builds_grounded_turns():
    runner = FakeFinanceRunner()
    service = FinanceChatService(
        runner=runner,
        config=FinanceAgentConfig(model="gpt-4o-mini", openbb_mcp_url="http://mcp/mcp"),
    )

    turn = asyncio.run(service.chat(message="Compare conservative ETF options."))

    assert turn["backend"] == "finance_openbb"
    assert turn["assistantMessage"].startswith("I used OpenBB data")
    assert turn["groundedItems"] == [
        {
            "itemId": "finance:openbb:etf_search:0",
            "rank": 1,
            "title": "OpenBB etf_search",
            "meta": "mcp_tool_call",
        }
    ]
    assert turn["recommendedItems"] == turn["groundedItems"]
    assert runner.messages[0][-1] == {
        "role": "user",
        "content": "Compare conservative ETF options.",
    }


def test_openbb_category_selector_limits_active_tools_for_blockchain_query():
    config = FinanceAgentConfig(max_active_categories=3)

    categories = _select_openbb_categories(
        [
            {
                "role": "user",
                "content": "Which blockchain and distributed ledger companies have momentum?",
            }
        ],
        config,
    )

    assert categories == ("crypto", "equity", "news")


def test_openbb_category_selector_honors_configured_categories_and_limit():
    config = FinanceAgentConfig(
        openbb_categories=("etf", "fixedincome", "economy"),
        max_active_categories=2,
    )

    categories = _select_openbb_categories(
        [{"role": "user", "content": "Compare bond ETF duration and yield risk."}],
        config,
    )

    assert categories == ("etf", "fixedincome")


def test_finance_application_exposes_generic_result(monkeypatch):
    runner = FakeFinanceRunner()
    app = FinanceOpenBBApplication(
        service=FinanceChatService(
            runner=runner,
            config=FinanceAgentConfig(
                model="gpt-4o-mini",
                openbb_mcp_url="http://mcp/mcp",
            ),
        )
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    app.ready("financial_research")
    message = app.send_message(
        session_id=None,
        message="Compare conservative ETF options.",
        title=None,
        context="financial_research",
        engine=None,
        bot_type=None,
    )
    result = app.recommendations(session_id=message["sessionId"])

    assert message["applicationId"] == "finance_openbb"
    assert message["applicationContext"] == "financial_research"
    assert message["groundedItems"][0]["itemId"] == "finance:openbb:etf_search:0"
    assert result["groundedItems"][0]["title"] == "OpenBB etf_search"
    assert result["turnsToResult"] == 1
