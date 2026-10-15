from pathlib import Path

from pydantic_ai import Agent

from backend.agents.config import ROLE_TOOLS, build_model, scoped_toolset
from backend.agents.delegation import delegate_tools_for
from backend.agents.registry import register
from backend.models import AGENT_ROLES, ShopDeps

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "facilities.md").read_text()

facilities_agent = Agent(
    build_model(),
    name="facilities",
    deps_type=ShopDeps,
    instructions=PROMPT,
    toolsets=[scoped_toolset(ROLE_TOOLS["facilities"])],
    tools=delegate_tools_for("facilities", AGENT_ROLES),
)

register("facilities", facilities_agent)
