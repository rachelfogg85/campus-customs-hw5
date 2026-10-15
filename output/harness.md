# Harness Notes — Campus Customs Database

Source: `data/campus_customs.db` (working copy for the agents: `data/campus_customs_new.db`).

## Tables

### desk
- `date_today` (TEXT), `notes` (TEXT)
- Single-row clock for the whole shop — every agent must treat `date_today` as "today" when deciding if a lease, invoice, or lead time is overdue.

### cash_accounts
- `name` (TEXT, PK), `balance` (REAL), `date` (TEXT)
- Accounting's source of truth for how much cash exists; the pay tool must refuse any payment that would push `balance` negative.

### vendors
- `id` (PK), `name`, `specialty`, `lead_days`
- Inventory uses this to pick who can restock a shortfall and how long it will take; Accounting checks it for the "no shipping with an unpaid invoice" rule.

### inventory
- `sku`, `name`, `size`, `qty`, `location` (PK: `sku`+`size`)
- Inventory's live stock levels by SKU/size — this is where shortfalls against a ticket's requested qty are detected.

### pricing
- `sku` (PK), `unit_cost`, `list_price`
- Accounting uses this to check margin before approving a discount or price override.

### invoices
- `id` (PK), `vendor_id` (FK → vendors), `amount`, `due_date`, `status`, `description`
- Accounting tracks what's owed to each vendor; an `open`/unpaid invoice past `desk.date_today` blocks that vendor from shipping new stock.

### leases
- `id` (PK), `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`
- Facilities' record of shop space obligations — rent due dates drive rent-notice tickets and required payments.

### payments
- `id` (PK), `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`
- The audit trail Accounting writes to once a human approves a payment (invoice or rent) — also what the pay tool checks/updates against `cash_accounts`.

### tickets
- `id` (PK), `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id` (FK → leases), `invoice_id` (FK → invoices), `status`, `notes`, `created_at`
- The Boss agent's inbox — each row is a unit of work that gets routed to Inventory, Accounting, Facilities, and/or Customer Service based on its `type` and linked FKs.

## The three open tickets

- **#101** `customer_order` — Tauhid Zaman wants `CC-TEE-WHITE` size S, qty 1. Inventory shows 0 on hand for that SKU/size. Linked to `invoice_id` 501 (Bulldog Print Co, $840, due 2026-08-28 — already overdue vs. `desk.date_today` 2026-08-31, status `open`). Per the vendor rule, Bulldog Print Co won't ship a restock while that invoice is unpaid, so Accounting must clear it before Inventory can reorder; Customer Service needs to draft a delay message to the customer.
- **#102** `rent_notice` — Elm City Properties, rent due in 2 days. Linked to `lease_id` 1 (Chapel Street shop, $2,400/mo, `next_due` 2026-09-02). Cash on hand is $3,400 (enough), but payment requires human approval before Accounting can pay.
- **#103** `price_override` — Yale AI Club wants 20× `CC-HOOD-NAVY` size M at a bulk discount. Inventory only has 8 on hand (shortfall of 12). Unit cost $22 vs. list $58, so Accounting needs to check margin on any discount before approving. Any restock would also go through Bulldog Print Co (5-day lead time) — currently blocked by the same unpaid invoice 501.

## MCP tools (`mcp_server/`)

All three tools are read-only and query `data/campus_customs_new.db` directly — nothing is invented beyond what's in the tables.

### `check_inventory(sku, size=None)`
- **Reads:** `inventory`
- **Unlocks:** #101, #103
- **Why:** For #101 it returns `CC-TEE-WHITE`/S → qty 0, which is the actual proof there's nothing on hand to fill Tauhid Zaman's order. For #103 it returns `CC-HOOD-NAVY`/M → qty 8, which is exactly the number Inventory needs to see that Yale AI Club's request for 20 is 12 short.

### `get_invoice_status(invoice_id)`
- **Reads:** `invoices` joined with `vendors`, compared against `desk.date_today`
- **Unlocks:** #101
- **Why:** Ticket #101's `invoice_id` FK points straight at invoice 501 (Bulldog Print Co, due 2026-08-28). This tool is what turns that FK into an actionable fact — status `open` and due date before `date_today` means the invoice is overdue, and per the vendor rule that means Bulldog Print Co is blocked from shipping a tee restock until it's paid.

### `get_lease_payment_status(lease_id)`
- **Reads:** `leases` joined with `cash_accounts` (checking balance), compared against `desk.date_today`
- **Unlocks:** #102
- **Why:** Ticket #102's `lease_id` FK points at lease 1 (Chapel St, $2,400/mo, due 2026-09-02). This tool answers the two questions Accounting actually needs before asking a human to approve payment: how many days are left (2) and does the $3,400 checking balance cover the $2,400 rent (yes).

## Connecting the MCP server to the vibe coder (Problem 4)

- `.mcp.json` was added at the project root (`hw5/.mcp.json`), registering the `campus-customs` server with command `python3 -m mcp_server.server` so the vibe coder (Claude Code) can launch it over stdio and call its tools directly instead of querying SQLite by hand.
- With the server connected, each of the three tools was called and the raw output checked against `data/campus_customs_new.db`:
  - `check_inventory({"sku": "CC-TEE-WHITE", "size": "S"})` → qty 0, matching the inventory table exactly.
  - `get_invoice_status({"invoice_id": 501})` → Bulldog Print Co, status `open`, due 2026-08-28, `is_overdue: true`, `vendor_blocked_from_shipping: true` — matching the invoices/vendors tables and `desk.date_today` (2026-08-31).
  - `get_lease_payment_status({"lease_id": 1})` → Chapel St lease, $2,400/mo due 2026-09-02, `days_until_due: 2`, checking balance $3,400, `cash_covers_rent: true` — matching the leases/cash_accounts tables.
- Full evidence (prompt used, tool name, input, and output for each call) is saved in [`output/mcp_smoke.json`](mcp_smoke.json).

## The agent team (Problem 5)

Built with PydanticAI in `backend/`, all five agents run on `gpt-6-luna` via Portkey (`backend/agents/config.py`), with prompts in `backend/prompts/*.md` and shared data types in `backend/models.py`. Every agent connects to the same `mcp_server/` process over stdio — none of them query SQLite directly. The team has full connectivity: each agent has an `ask_<role>` delegation tool for every other agent, implemented as the standard "agent as tool" pattern (`backend/agents/delegation.py`), with a hard delegation cap (`ShopDeps.max_delegations`, default 8) shared across the whole tree so a confused run can't loop forever.

Each agent only gets the MCP tools its job actually needs (least privilege, enforced via `MCPToolset.filtered()` in `backend/agents/config.py`), not the full set below:

| Agent | Prompt | MCP tools it's allowed | Can delegate to |
|---|---|---|---|
| **Boss** (`backend/agents/boss.py`) | `prompts/boss.md` | `get_ticket`, `get_shop_clock`, `list_open_tickets`, `update_ticket_status` | inventory, accounting, facilities, customer_service |
| **Inventory** (`backend/agents/inventory.py`) | `prompts/inventory.md` | `get_ticket`, `get_shop_clock`, `check_inventory`, `list_vendors` | boss, accounting, facilities, customer_service |
| **Accounting** (`backend/agents/accounting.py`) | `prompts/accounting.md` | `get_ticket`, `get_shop_clock`, `get_invoice_status`, `get_cash_balance`, `get_pricing`, `create_purchase_order`, `pay_invoice`, `get_lease_payment_status` | boss, inventory, facilities, customer_service |
| **Facilities** (`backend/agents/facilities.py`) | `prompts/facilities.md` | `get_ticket`, `get_shop_clock`, `get_lease_payment_status` | boss, inventory, accounting, customer_service |
| **Customer Service** (`backend/agents/customer_service.py`) | `prompts/customer_service.md` | `get_ticket`, `get_shop_clock` only — it has no stock/money tools on purpose, so it must delegate for every fact it puts in a draft | boss, inventory, accounting, facilities |

`backend/orchestrator.py` is the agent loop entry point: `python3 -m backend.orchestrator` lists every open ticket (via `list_open_tickets`), hands each one to the Boss agent with a fresh `ShopDeps`, and lets the Boss delegate out and call `update_ticket_status` to close it. A real run against the live database (`gpt-6-luna`, real Portkey calls) resolved all three tickets correctly: #101 and #103 both came back `blocked` on the same unpaid Bulldog Print Co invoice, #102 came back `blocked` pending human approval even though cash covers it, and Customer Service drafted an honest, unsent delay message to Tauhid Zaman for #101.

### All MCP tools, by table

| Tool | Table(s) read/written | Type |
|---|---|---|
| `get_shop_clock` | `desk` | read |
| `check_inventory` | `inventory` | read |
| `get_cash_balance` | `cash_accounts` | read |
| `list_open_tickets` | `tickets` | read |
| `get_ticket` | `tickets` | read |
| `list_vendors` | `vendors` | read |
| `get_pricing` | `pricing` | read |
| `get_invoice_status` | `invoices`, `vendors` (+ `desk` for overdue calc) | read |
| `get_lease_payment_status` | `leases`, `cash_accounts` (+ `desk` for days-until-due) | read |
| `update_ticket_status` | `tickets` | write |
| `create_purchase_order` | `invoices` (+ reads `pricing`, `vendors`) | write |
| `pay_invoice` | `invoices`, `cash_accounts`, `payments` (+ `desk` for paid_at) | write |
| `pay_lease` | `leases`, `cash_accounts`, `payments` (+ `desk` for paid_at) | write |

### Audit trail

Every agent-loop step (prompt in, model request, model response with tool calls + token usage, delegation start/end, end) is appended as one JSON object per line to `output/audit_trail.json` (`backend/agents/tracing.py::run_with_audit`). The file is opened in append mode and is never truncated between runs, so it accumulates a permanent history across every run anyone does against this project.

## Safety: guardrails for real customers and real money

This system is a simulation against a database, but it's built the way a real deployment touching real customers and real cash would need to be:

- **Human approval is a hard gate on payment, enforced in code, not just in a prompt.** `pay_invoice` refuses unless called with `human_approved=True` and a named `approved_by` — and no agent is ever given a reason or a tool to set that itself. The Accounting prompt explicitly forbids it from ever calling `pay_invoice` with approval; its job stops at "ready for a human to approve."
- **No negative balances, enforced in code.** `pay_invoice` checks the checking balance before writing anything and refuses if the payment would take it below zero — there is no override.
- **Vendors can't be re-ordered from while they're owed money.** `create_purchase_order` refuses if the vendor has any non-paid invoice, which is the actual shop rule, not just a prompt instruction the model could ignore.
- **Nothing real goes out.** Customer Service only ever produces draft text — there is no send-email or contact-vendor tool anywhere in the system, so there is nothing for a misbehaving agent to misuse here even in principle.
- **Least-privilege tool access.** Each agent's MCP toolset is filtered down to only the tools its job needs (see the table above); Customer Service, for instance, cannot call `pay_invoice` or even see stock numbers directly, no matter what it's asked.
- **A single source of truth.** All five agents go through the same MCP server against the same database; there's no second, ungoverned path to the data that could drift out of sync with the rules above.
- **Everything is auditable after the fact.** The append-only `output/audit_trail.json` records every model call, every tool call and its arguments, and every delegation, so a human can reconstruct exactly why an agent did what it did.

Guardrails that keep token/cost use in check:
- **A hard per-ticket usage cap.** `backend/orchestrator.py::TICKET_USAGE_LIMITS` sets `request_limit=30`, `tool_calls_limit=40`, and `total_tokens_limit=200_000` via PydanticAI's native `UsageLimits`, and a single shared `RunUsage()` is passed through every nested `.run()` call in a ticket's delegation tree (Boss → any specialist → any other specialist). That means the cap is enforced on the whole tree's combined spend, not per-agent, so five agents bouncing a ticket around can't each get their own separate budget.
- **A hard delegation-count cap**, independent of token usage, so a loop of cheap, low-token delegations still can't run forever (`ShopDeps.max_delegations`, default 8 per ticket).
- **A fixed, single model for every agent.** Every agent is pinned to `gpt-6-luna` in `backend/agents/config.py` — no agent can escalate itself to a more expensive model.
- **A real production system should add:** a per-day or per-ticket dollar budget (not just token count, since $/token varies by model), alerting when a ticket hits its usage cap instead of silently truncating, and a periodic human review of the audit trail rather than relying on guardrails alone.

## Backend API routes (Problem 7)

`backend/main.py` — FastAPI app for the React dashboard, run from `backend/` with `uvicorn main:app --reload --port 8000`. Every route goes through the MCP server (an agent run or a direct tool call via `backend/mcp_client.py`) — nothing talks to the database directly.

- `GET /api/tickets` — the three tickets (101/102/103) with their current status and an `is_open` flag.
- `POST /api/tickets/{ticket_id}/run` — runs the agent team (Boss + whichever specialists it delegates to) on that ticket id.
- `GET /api/events?limit=50&ticket_id=` — the most recent agent-loop events from `output/audit_trail.json` (what each agent said, which tools it called), optionally filtered to one ticket, for the dashboard to poll.
- `POST /api/payments/approve` — body `{kind: "invoice"|"rent", ref_id, approved_by}`; the only route that actually calls `pay_invoice`/`pay_lease` with `human_approved=True`, i.e. the only route that moves cash.
- `GET /api/cash` — the current `checking` balance from `cash_accounts`.
- `POST /api/reset` — copies `data/campus_customs.db` back over `data/campus_customs_new.db` for a fresh run.
- `GET /api/health` — basic liveness check (not one of the six required routes, but cheap and useful for the dashboard to confirm the backend is up).

All seven were tested live against the running server: tickets/cash/health return real data, `/api/events` returns real logged steps, `/api/payments/approve` both refused correctly (missing approval, unknown invoice) and succeeded (paid lease 1's rent, balance dropped from $3,400 to $1,000), `/api/reset` restored it, and `/api/tickets/102/run` drove a real agent run over HTTP. The working database was reset to pristine before handing this off.

## The dashboard (Problem 8)

`frontend/` — React + Vite + TypeScript, run with `npm run dev` (opens on `http://localhost:5173`; the backend's CORS allowlist is scoped to that origin range specifically, not a wildcard). Talks to the backend at the fixed address `http://localhost:8000` (`frontend/src/lib/api.ts`).

- **Ticket queue** (left column, `TicketQueue.tsx`) — all three tickets as "ticket stub" cards with a live status badge; click one to select it.
- **Ticket board** (right column, `TicketBoard.tsx`) — the selected ticket's details, a "Run agent team" button, and once a ticket is no longer open, a rotated **verdict stamp** showing its real status (`BLOCKED`, `ESCALATED`, etc. — whatever the Boss actually chose, never forced to say "RESOLVED").
- **Live agent feed** (`AgentFeed.tsx`) — a color-coded, chat-thread view of every agent-loop step (prompts, tool calls as `🔧 tool(args)` chips, delegation arrows, final answers), fed by polling `GET /api/events` every ~1.1s while a run is in flight, since the run route itself blocks until the whole delegation tree finishes.
- **Per-agent summary** (`AgentSummary.tsx`) — one card per agent that actually participated, holding that agent's own final answer.
- **Approval panel** (`ApprovalPanel.tsx` / `lib/approvals.ts`) — scans the ticket's real tool-call history for payable invoices/leases it already surfaced (`create_purchase_order`, `get_invoice_status`, `get_lease_payment_status` results) and turns each into a one-click "Approve" card wired to `POST /api/payments/approve` — nothing here is invented, it's real tool output turned into a button.
- **Cash ticker** (`CashTicker.tsx`) — the live checking balance in the header, with a flash/bump animation when it changes.

Each of the five agents gets its own accent color (all within the black-and-pink theme) so the feed, delegation arrows, and summary cards all read consistently — see `output/design.md` for the full design rationale, including a real bug the live testing surfaced (a CSS height-chain bug that silently prevented the feed from scrolling, and a multi-minute agent run whose HTTP connection got dropped by a proxy mid-flight, which is why the "is this ticket finished" check trusts the freshly-refetched ticket status rather than this tab's own request outcome).

## Problem 9: the full run, reset to resolved

`data/campus_customs_new.db` was reset via `POST /api/reset` and all three tickets were run end to end. Starting checking balance: **$3,400.00**.

| Ticket | Final status | Cash impact |
|---|---|---|
| #101 | `blocked` | Invoice 501 ($840, Bulldog Print Co) approved by me as the human afterward → balance $2,560.00 |
| #102 | `escalated` | Lease 1 rent ($2,400) approved by me afterward → balance $160.00 |
| #103 | `blocked` | Once 501 was paid, Accounting successfully drafted a *new* purchase order (invoice 502, $264) — I attempted to approve it and the no-negative-balance guardrail correctly refused it (`$160.00` on hand, `$264.00` needed) |

**Ending checking balance: $160.00**, verified directly against `cash_accounts` and `payments` in the working database (see `output/desk_tickets.html`'s Cash tab for the full reconciliation).

Full detail lives in:
- `output/desk_tickets.html` — expected vs. actual plan per ticket, the cash itemization, and a detailed reflection (performance evaluation, single-agent-vs-team comparison, and new problems this team could/couldn't solve).
- `output/resolved_tickets.json` — machine-readable final status, outcome, per-agent contribution, and human approvals for all three tickets.
- `output/resolved_board.html` — real screenshots of the running React dashboard for each resolved ticket.
- `output/audit_trail.json` — the complete, append-only, step-by-step log every run above was reconstructed from.
