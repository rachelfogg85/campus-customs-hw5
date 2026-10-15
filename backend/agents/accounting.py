from pathlib import Path

from pydantic_ai import Agent

from backend.agents.config import ROLE_TOOLS, build_model, scoped_toolset
from backend.agents.delegation import delegate_tools_for
from backend.agents.registry import register
from backend.models import AGENT_ROLES, ShopDeps

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "accounting.md").read_text()

accounting_agent = Agent(
    build_model(),
    name="accounting",
    deps_type=ShopDeps,
    instructions=PROMPT,
    toolsets=[scoped_toolset(ROLE_TOOLS["accounting"])],
    tools=delegate_tools_for("accounting", AGENT_ROLES),
)

register("accounting", accounting_agent)
