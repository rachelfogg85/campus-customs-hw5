from pathlib import Path

from pydantic_ai import Agent

from backend.agents.config import ROLE_TOOLS, build_model, scoped_toolset
from backend.agents.delegation import delegate_tools_for
from backend.agents.registry import register
from backend.models import AGENT_ROLES, ShopDeps

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "customer_service.md").read_text()

customer_service_agent = Agent(
    build_model(),
    name="customer_service",
    deps_type=ShopDeps,
    instructions=PROMPT,
    toolsets=[scoped_toolset(ROLE_TOOLS["customer_service"])],
    tools=delegate_tools_for("customer_service", AGENT_ROLES),
)

register("customer_service", customer_service_agent)
