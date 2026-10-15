"""Importing this package builds and registers all five agents.

Order doesn't matter for correctness (delegation tools look agents up lazily
at call time via the registry), but importing them all here means any other
module can just `from backend.agents import boss_agent` or go through the
registry with `get_agent("inventory")`.
"""

from backend.agents.accounting import accounting_agent
from backend.agents.boss import boss_agent
from backend.agents.customer_service import customer_service_agent
from backend.agents.facilities import facilities_agent
from backend.agents.inventory import inventory_agent
from backend.agents.registry import get_agent

__all__ = [
    "boss_agent",
    "inventory_agent",
    "accounting_agent",
    "facilities_agent",
    "customer_service_agent",
    "get_agent",
]
