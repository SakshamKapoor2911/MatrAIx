"""Run the OpenBB MCP data service for Harbor finance chatbot runs."""

from __future__ import annotations

import argparse
from typing import Sequence

DEFAULT_OPENBB_CATEGORIES = (
    "equity",
    "etf",
    "economy",
    "news",
    "crypto",
    "fixedincome",
    "index",
    "technical",
)

TECHNICAL_ENABLED_MODULE_EXCLUSION_MAP = {
    "econometrics": "openbb_econometrics",
    "quantitative": "openbb_quantitative",
    "coverage": "openbb_core",
}


def parse_categories(value: str | None) -> list[str]:
    if not value:
        return list(DEFAULT_OPENBB_CATEGORIES)
    categories = [part.strip() for part in value.split(",") if part.strip()]
    return categories or list(DEFAULT_OPENBB_CATEGORIES)


def build_mcp_settings(
    *,
    categories: Sequence[str],
    host: str,
    port: int,
    tool_discovery: bool,
):
    from openbb_mcp_server.models.settings import MCPSettings

    category_list = [str(category).strip() for category in categories if category]
    if not category_list:
        category_list = list(DEFAULT_OPENBB_CATEGORIES)
    return MCPSettings(
        allowed_tool_categories=category_list,
        default_tool_categories=category_list,
        enable_tool_discovery=tool_discovery,
        module_exclusion_map=TECHNICAL_ENABLED_MODULE_EXCLUSION_MAP,
        uvicorn_config={"host": host, "port": str(port)},
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--categories", default=",".join(DEFAULT_OPENBB_CATEGORIES))
    parser.add_argument("--transport", default="streamable-http")
    parser.set_defaults(tool_discovery=True)
    parser.add_argument("--tool-discovery", dest="tool_discovery", action="store_true")
    parser.add_argument(
        "--no-tool-discovery",
        dest="tool_discovery",
        action="store_false",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    from openbb_core.api.rest_api import app
    from openbb_mcp_server.app.app import create_mcp_server

    settings = build_mcp_settings(
        categories=parse_categories(args.categories),
        host=args.host,
        port=args.port,
        tool_discovery=args.tool_discovery,
    )
    mcp_server = create_mcp_server(
        settings,
        app,
        settings.get_httpx_kwargs(),
        auth=settings.server_auth,
    )
    mcp_server.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(0) from None
