"""Data types shared across the campus customs agent team.

These mirror the tables in data/campus_customs_new.db (for typed references
to shop facts) plus the small amount of state the agent loop itself needs
(ShopDeps, AuditEvent). The agents never construct these from imagination —
every field is populated from an MCP tool call against the real database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel


class Ticket(BaseModel):
    id: int
    type: str
    requester: str
    subject: str
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    lease_id: int | None = None
    invoice_id: int | None = None
    status: str
    notes: str | None = None
    created_at: str


class InventoryLine(BaseModel):
    sku: str
    name: str
    size: str
    qty: int
    location: str


class Vendor(BaseModel):
    id: int
    name: str
    specialty: str
    lead_days: int


class Invoice(BaseModel):
    id: int
    vendor_id: int
    amount: float
    due_date: str
    status: str
    description: str | None = None


class Lease(BaseModel):
    id: int
    space_name: str
    landlord: str
    monthly_rent: float
    next_due: str
    notes: str | None = None


class Pricing(BaseModel):
    sku: str
    unit_cost: float
    list_price: float


class CashAccount(BaseModel):
    name: str
    balance: float
    date: str


class Payment(BaseModel):
    id: int
    kind: str
    ref_id: int | None
    amount: float
    account: str
    paid_at: str
    approved_by: str


AGENT_ROLES = ("boss", "inventory", "accounting", "facilities", "customer_service")


@dataclass
class ShopDeps:
    """Shared run state passed to every agent in a ticket's delegation tree.

    The same instance flows through every nested .run() call (boss -> any
    specialist -> any other specialist), so delegation_count is a real,
    shared counter across the whole tree, not per-agent.
    """

    ticket_id: int | None = None
    delegation_count: int = 0
    max_delegations: int = 8


@dataclass
class AuditEvent:
    """One row appended to output/audit_trail.json for every agent loop step."""

    ticket_id: int | None
    agent: str
    step: int
    kind: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "ticket_id": self.ticket_id,
            "agent": self.agent,
            "step": self.step,
            "kind": self.kind,
            **self.data,
        }


# --- FastAPI request/response shapes (backend/main.py) ---------------------


class TicketStatusOut(Ticket):
    is_open: bool


class TicketsResponse(BaseModel):
    tickets: list[TicketStatusOut]


class RunTicketResponse(BaseModel):
    ticket_id: int
    outcome: str
    delegations: int


class EventsResponse(BaseModel):
    count: int
    events: list[dict[str, Any]]


class ApprovePaymentRequest(BaseModel):
    kind: Literal["invoice", "rent"]
    ref_id: int
    approved_by: str


class CashResponse(BaseModel):
    account: str
    balance: float
    as_of: str


class ResetResponse(BaseModel):
    reset: bool
    message: str
