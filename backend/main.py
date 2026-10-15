"""Campus Customs dashboard API — routes only.

Run from backend/:  uvicorn main:app --reload --port 8000
Open API docs:       http://localhost:8000/docs

This is what the React dashboard (built in the next problem) talks to. It
never touches data/campus_customs_new.db directly — every route goes through
the campus-customs MCP server (mcp_server/), either via an agent run or via a
direct tool call (backend/mcp_client.py), so the same shop rules (vendor
blocked by unpaid invoice, human approval required, no negative balances)
apply no matter which path a request takes.

Crucially: the agent team only ever *prepares* a payment or purchase order
(create_purchase_order leaves an invoice `pending_approval`; nothing an agent
does moves cash). The only route that actually moves cash is
POST /api/payments/approve, which is called after a human clicks approve on
the dashboard — agents never call pay_invoice/pay_lease with
human_approved=True themselves.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

# Every internal module uses absolute `backend.xxx` imports (so they also
# work as `python3 -m backend.orchestrator` from hw5/). Running uvicorn
# directly from backend/, as the docstring above does, puts backend/ itself
# on sys.path instead of its parent — add the parent (hw5/) too so
# `import backend` still resolves either way.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.agents.config import PROJECT_ROOT
from backend.agents.tracing import AUDIT_TRAIL_PATH
from backend.mcp_client import call_tool
from backend.models import (
    ApprovePaymentRequest,
    CashResponse,
    EventsResponse,
    ResetResponse,
    RunTicketResponse,
    TicketsResponse,
    TicketStatusOut,
)
from backend.orchestrator import resolve_ticket

ORIGINAL_DB = PROJECT_ROOT / "data" / "campus_customs.db"
WORKING_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"

# The shop currently has exactly these three tickets; see output/harness.md
# for how each one works. A later problem could grow this into a real
# "list every ticket" route, but the dashboard only needs these three.
TICKET_IDS = (101, 102, 103)

# The Vite dashboard (frontend/) runs on 5173 by default and falls through to
# the next free port if that's taken, so allow a small fixed range rather than
# a wildcard (allow_credentials=True can't be combined with "*" anyway).
VITE_ORIGINS = [f"http://localhost:{port}" for port in range(5173, 5178)] + [
    f"http://127.0.0.1:{port}" for port in range(5173, 5178)
]

app = FastAPI(title="Campus Customs Agent Desk", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=VITE_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "db": WORKING_DB.name}


@app.get("/api/tickets", response_model=TicketsResponse)
async def get_tickets():
    """1. The three tickets and whether each is open or resolved."""
    tickets = []
    for ticket_id in TICKET_IDS:
        row = await call_tool("get_ticket", {"ticket_id": ticket_id})
        if not row.get("found"):
            continue
        row = {k: v for k, v in row.items() if k != "found"}
        tickets.append(TicketStatusOut(**row, is_open=row["status"] == "open"))
    return TicketsResponse(tickets=tickets)


@app.post("/api/tickets/{ticket_id}/run", response_model=RunTicketResponse)
async def run_ticket(ticket_id: int):
    """2. Run the agent team (Boss + whoever it delegates to) on one ticket."""
    if ticket_id not in TICKET_IDS:
        raise HTTPException(status_code=404, detail=f"Unknown ticket id {ticket_id}")
    outcome, delegations = await resolve_ticket(ticket_id)
    return RunTicketResponse(ticket_id=ticket_id, outcome=outcome, delegations=delegations)


@app.get("/api/events", response_model=EventsResponse)
def get_events(limit: int = 50, ticket_id: int | None = None):
    """3. Recent agent-loop events (what each agent said, which tools it used) for the board to refresh."""
    if not AUDIT_TRAIL_PATH.exists():
        return EventsResponse(count=0, events=[])

    events = []
    with AUDIT_TRAIL_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            if ticket_id is not None and event.get("ticket_id") != ticket_id:
                continue
            events.append(event)

    recent = events[-limit:]
    return EventsResponse(count=len(recent), events=recent)


@app.post("/api/payments/approve")
async def approve_payment(body: ApprovePaymentRequest):
    """4. Approve a payment or purchase order after a human clicks approve.

    Agents only ever prepare a payment (a `pending_approval` invoice, or a
    recommendation to pay rent) — this is the only route that actually calls
    pay_invoice/pay_lease with human_approved=True, i.e. the only route that
    changes cash_accounts.
    """
    tool_name = "pay_invoice" if body.kind == "invoice" else "pay_lease"
    id_field = "invoice_id" if body.kind == "invoice" else "lease_id"
    result = await call_tool(
        tool_name,
        {id_field: body.ref_id, "approved_by": body.approved_by, "human_approved": True},
    )
    if not result.get("paid"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Payment refused."))
    return result


@app.get("/api/cash", response_model=CashResponse)
async def get_cash():
    """5. The current checking balance from cash_accounts."""
    result = await call_tool("get_cash_balance", {"account": "checking"})
    if not result.get("found"):
        raise HTTPException(status_code=404, detail="No checking account found.")
    return CashResponse(account=result["account"], balance=result["balance"], as_of=result["as_of"])


@app.post("/api/reset", response_model=ResetResponse)
def reset_database():
    """6. Reset data/campus_customs_new.db back to the original values, for a fresh run."""
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    return ResetResponse(reset=True, message=f"{WORKING_DB.name} reset from {ORIGINAL_DB.name}.")
