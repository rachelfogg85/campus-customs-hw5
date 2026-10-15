"""Lookup table of role name -> Agent, so delegation tools can reach any agent
without every agent module importing every other agent module.

Each agents/<role>.py module registers itself at import time. Delegation
tools (agents/delegation.py) look up their target lazily, at call time, so
construction order never matters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_ai import Agent

_AGENTS: dict[str, "Agent"] = {}


def register(role: str, agent: "Agent") -> None:
    _AGENTS[role] = agent


def get_agent(role: str) -> "Agent":
    return _AGENTS[role]


def all_roles() -> list[str]:
    return list(_AGENTS.keys())
