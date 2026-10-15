"""Entry point that drives the Boss agent over the shop's open tickets.

Run `python3 -m backend.orchestrator` from hw5/ to resolve every ticket
currently open in data/campus_customs_new.db. Each ticket gets a fresh
ShopDeps (so the delegation cap resets per ticket) but every agent-loop step,
across every ticket, keeps accumulating in output/audit_trail.json.
"""

from __future__ import annotations

import asyncio

from pydantic_ai.usage import RunUsage, UsageLimits

from backend.agents import boss_agent
from backend.agents.tracing import append_audit_event, run_with_audit
from backend.mcp_client import call_tool
from backend.models import AuditEvent, ShopDeps

# Hard cap on token/request/tool-call spend for resolving a single ticket,
# shared across the WHOLE delegation tree (Boss + every specialist it calls
# into) via PydanticAI's native usage= / usage_limits= passing. This is what
# stops one confused ticket from running up an unbounded bill.
TICKET_USAGE_LIMITS = UsageLimits(
    request_limit=30,
    tool_calls_limit=40,
    total_tokens_limit=200_000,
)


async def resolve_ticket(ticket_id: int) -> tuple[str, int]:
    """Run the Boss agent (and whichever specialists it delegates to) on one ticket.

    Returns (outcome_text, delegation_count).
    """
    deps = ShopDeps(ticket_id=ticket_id)
    usage = RunUsage()
    prompt = (
        f"Work ticket {ticket_id}. Look it up with get_ticket, decide which "
        "specialists need to weigh in, delegate to them, and close the "
        "ticket out with update_ticket_status once you have a real answer."
    )

    append_audit_event(AuditEvent(ticket_id=ticket_id, agent="orchestrator", step=0, kind="ticket_start", data={}))
    output = await run_with_audit(
        boss_agent,
        prompt,
        agent_name="boss",
        ticket_id=ticket_id,
        deps=deps,
        usage=usage,
        usage_limits=TICKET_USAGE_LIMITS,
    )
    append_audit_event(
        AuditEvent(
            ticket_id=ticket_id,
            agent="orchestrator",
            step=10**6,
            kind="ticket_end",
            data={"output": str(output)[:2000], "delegations": deps.delegation_count},
        )
    )
    return str(output), deps.delegation_count


async def _list_open_ticket_ids() -> list[int]:
    """Fetch open ticket ids straight from the MCP server (no second data layer)."""
    rows = await call_tool("list_open_tickets")
    return [row["id"] for row in rows]


async def resolve_all_open_tickets() -> dict[int, tuple[str, int]]:
    results: dict[int, tuple[str, int]] = {}
    for ticket_id in await _list_open_ticket_ids():
        results[ticket_id] = await resolve_ticket(ticket_id)
    return results


if __name__ == "__main__":
    outcomes = asyncio.run(resolve_all_open_tickets())
    for ticket_id, (outcome, delegations) in outcomes.items():
        print(f"--- ticket {ticket_id} ({delegations} delegations) ---")
        print(outcome)
        print()
