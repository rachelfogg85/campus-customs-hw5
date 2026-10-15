"""Model + MCP wiring shared by every agent in the team.

Model: every agent uses gpt-6-luna only, routed through Portkey with
PORTKEY_API_KEY from a .env file (never hardcoded here). gpt-6-luna needs the
Responses API (not chat/completions) to support function tool calls, so we
build an OpenAIResponsesModel pointed at Portkey's OpenAI-compatible gateway.

MCP: all shop facts come from the campus-customs MCP server (mcp_server/),
which is the only thing that touches data/campus_customs_new.db. Agents never
query the database directly — that would be the "second shop-tools layer"
the assignment says not to build.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from fastmcp.client.transports import StdioTransport
from openai import AsyncOpenAI
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

# hw5/backend/agents/config.py -> parents[2] is hw5, the project root for this assignment.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for folder in [PROJECT_ROOT, *PROJECT_ROOT.parents]:
    if (folder / ".env").exists():
        load_dotenv(folder / ".env", override=False)
        break

MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")


def require_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "PORTKEY_API_KEY is missing. Put it in a .env in this project or a parent folder."
        )
    return key


@lru_cache(maxsize=1)
def build_model() -> OpenAIResponsesModel:
    """Build the single model every agent shares: gpt-6-luna over Portkey."""
    client = AsyncOpenAI(
        api_key=require_api_key(),
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-provider": "openai"},
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


@lru_cache(maxsize=1)
def _mcp_toolset() -> MCPToolset:
    """The single connection to the campus-customs MCP server, shared by all agents.

    Spawned over stdio exactly like `.mcp.json` configures it, with cwd set to
    the project root so `python -m mcp_server.server` resolves its package
    imports and finds data/campus_customs_new.db regardless of caller cwd.
    """
    transport = StdioTransport(
        command="python3",
        args=["-m", "mcp_server.server"],
        cwd=str(PROJECT_ROOT),
    )
    return MCPToolset(transport)


def scoped_toolset(allowed_tools: set[str]):
    """Return the shared MCP toolset filtered down to one agent's allowed tools.

    This is the least-privilege guardrail: Customer Service, for example,
    never even sees pay_invoice or create_purchase_order as callable tools,
    regardless of what the model might otherwise try.
    """
    return _mcp_toolset().filtered(lambda ctx, tool_def: tool_def.name in allowed_tools)


# Least-privilege tool grants per role. Every agent also gets get_ticket and
# get_shop_clock so it can ground itself in which ticket it's working and
# what day the shop thinks it is.
_COMMON = {"get_ticket", "get_shop_clock"}

ROLE_TOOLS: dict[str, set[str]] = {
    "boss": _COMMON | {"list_open_tickets", "update_ticket_status"},
    "inventory": _COMMON | {"check_inventory", "list_vendors"},
    "accounting": _COMMON
    | {
        "get_invoice_status",
        "get_cash_balance",
        "get_pricing",
        "create_purchase_order",
        "pay_invoice",
        "pay_lease",
        "get_lease_payment_status",
    },
    "facilities": _COMMON | {"get_lease_payment_status"},
    "customer_service": _COMMON,
}
