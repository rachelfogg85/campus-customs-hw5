"""One-off MCP tool calls outside the agent loop.

The FastAPI routes (and the orchestrator's ticket listing) sometimes need a
single shop fact or action without spinning up an LLM — for example, the
dashboard polling the checking balance, or a human clicking "approve" on a
payment. Those calls go through the *same* MCP server and the *same* tools
the agents use (pay_invoice, pay_lease, etc.) — this is not a second,
ungoverned path to the database, just a direct client connection instead of
one wrapped in an Agent's toolset.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from backend.agents.config import PROJECT_ROOT


def _transport() -> StdioTransport:
    return StdioTransport(command="python3", args=["-m", "mcp_server.server"], cwd=str(PROJECT_ROOT))


async def call_tool(name: str, args: dict[str, Any] | None = None) -> Any:
    async with Client(_transport()) as client:
        result = await client.call_tool(name, args or {})
        return result.data
