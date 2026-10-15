# Campus Customs MCP Server

A FastMCP server that gives every agent (Boss, Inventory, Accounting, Facilities,
Customer Service) a shared view into the shop's database. Agents don't query
SQLite directly — they call these MCP tools so all data access and every write
goes through one place, with the same rules applied every time. This is also
the only layer with write access to the database; the agent team in `backend/`
never bypasses it.

**Database:** `data/campus_customs_new.db` (the working copy — the original
backup lives at `data/campus_customs.db` and is never written to).

## Tools

### Read-only
- **`get_shop_clock()`** — the shop's current date and desk notes from `desk`.
- **`check_inventory(sku, size=None)`** — current stock for a SKU (optionally
  one size) from `inventory`.
- **`get_cash_balance(account="checking")`** — current balance from
  `cash_accounts`.
- **`list_open_tickets()`** — every ticket with status `open` from `tickets`.
- **`get_ticket(ticket_id)`** — one ticket's full record from `tickets`.
- **`list_vendors(specialty=None)`** — vendors from `vendors`, optionally
  filtered by specialty.
- **`get_pricing(sku)`** — unit cost, list price, and margin from `pricing`.
- **`get_invoice_status(invoice_id)`** — an invoice plus its vendor from
  `invoices`/`vendors`, with overdue and vendor-shipping-blocked flags
  computed against `desk.date_today`.
- **`get_lease_payment_status(lease_id)`** — a lease from `leases`, checked
  against the `checking` balance in `cash_accounts` and `desk.date_today`.

### Write (guardrailed)
- **`update_ticket_status(ticket_id, status, notes=None)`** — updates a
  ticket's status/notes in `tickets`. Only ever touches the ticket row.
- **`create_purchase_order(vendor_id, sku, qty, notes=None)`** — drafts a
  `pending_approval` invoice in `invoices` (amount computed from `pricing`,
  due date from the vendor's `lead_days`). Refuses if the vendor already has
  any unpaid invoice, per the shop rule that a vendor won't ship while one is
  outstanding.
- **`pay_invoice(invoice_id, approved_by, human_approved=False)`** — pays an
  invoice out of `checking`, updates `invoices` to `paid`, and appends a row
  to `payments`. Refuses unless `human_approved=True` with a named
  `approved_by`, and refuses if the payment would take the balance below
  zero. This is one of the shop's two cash-out paths — there is no cash-in tool.
- **`pay_lease(lease_id, approved_by, human_approved=False)`** — the same
  guardrails as `pay_invoice`, but for rent: pays a lease's `monthly_rent` out
  of `checking`, appends a `payments` row, and advances the lease's
  `next_due` by 30 days. Rent isn't an invoice, so this is its own tool
  rather than overloading `pay_invoice`.

See `output/harness.md` for how each tool ties to tickets 101, 102, and 103,
and for the safety/guardrails section covering real-money and real-customer
risk plus token-use limits.

All tools are checked against the real database — no data is invented;
everything returned or written comes straight from (or lands straight in)
the tables above.

## Running

```bash
cd hw5
python3 -m mcp_server.server
```

Requires `fastmcp` (see the project-root `requirements.txt`). The agent team in `backend/`
spawns this same command over stdio automatically — you don't need to run it
separately to use the agents.
