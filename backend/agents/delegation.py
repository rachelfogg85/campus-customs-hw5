"""Delegation tools: how one agent asks another agent for help.

The team has "full connectivity" — any of the five agents can delegate to any
other — implemented as the standard PydanticAI "agent as tool" pattern: a
thin async function that runs the target agent and hands back its text
output. Construction order never matters because the target is looked up in
the shared registry at call time, not at import time, which avoids the
circular imports that five mutually-delegating agent modules would otherwise
need.

Two guardrails live here, since this is the one chokepoint every delegation
passes through:
  - delegation_count / max_delegations on the shared ShopDeps hard-caps how
    many times one ticket's resolution can bounce between agents, so a
    confused model can't loop forever.
  - usage / usage_limits are threaded through every nested run via
    PydanticAI's native usage-sharing, so a single UsageLimits set on the
    top-level Boss run caps token/request/tool-call spend across the WHOLE
    delegation tree, not just the Boss's own calls.
"""

from __future__ import annotations

from pydantic_ai import ModelRetry, RunContext, Tool

from backend.agents.registry import get_agent
from backend.agents.tracing import run_with_audit
from backend.models import AuditEvent, ShopDeps
from backend.agents.tracing import append_audit_event

ROLE_DESCRIPTIONS = {
    "boss": "Reads tickets, decides who should work them, and makes the final call.",
    "inventory": "Checks stock by SKU/size, spots shortfalls, and identifies which vendor can restock.",
    "accounting": "Watches cash and invoices, checks margins, and prepares payments or purchase orders for human approval.",
    "facilities": "Handles the shop's lease / physical space side.",
    "customer_service": "Drafts (never sends) messages to customers.",
}


def make_delegate_tool(caller_role: str, target_role: str) -> Tool:
    async def delegate(ctx: RunContext[ShopDeps], question: str) -> str:
        ctx.deps.delegation_count += 1
        if ctx.deps.delegation_count > ctx.deps.max_delegations:
            raise ModelRetry(
                f"Delegation cap ({ctx.deps.max_delegations}) reached for this ticket. "
                "Stop delegating and finalize your answer with what you already have."
            )

        append_audit_event(
            AuditEvent(
                ticket_id=ctx.deps.ticket_id,
                agent=caller_role,
                step=ctx.deps.delegation_count,
                kind="delegation_start",
                data={"from": caller_role, "to": target_role, "question": question},
            )
        )

        target = get_agent(target_role)
        output = await run_with_audit(
            target,
            question,
            agent_name=target_role,
            ticket_id=ctx.deps.ticket_id,
            deps=ctx.deps,
            usage=ctx.usage,
            usage_limits=ctx.usage_limits,
        )

        append_audit_event(
            AuditEvent(
                ticket_id=ctx.deps.ticket_id,
                agent=target_role,
                step=ctx.deps.delegation_count,
                kind="delegation_end",
                data={"from": target_role, "to": caller_role, "output": str(output)[:2000]},
            )
        )
        return str(output)

    delegate.__name__ = f"ask_{target_role}"
    return Tool(
        delegate,
        name=f"ask_{target_role}",
        description=f"Delegate to the {target_role} agent for help. {ROLE_DESCRIPTIONS[target_role]}",
    )


def delegate_tools_for(role: str, all_roles: tuple[str, ...]) -> list[Tool]:
    """Every delegate tool for `role` except one that would let it ask itself."""
    return [make_delegate_tool(role, other) for other in all_roles if other != role]
