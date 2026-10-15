from datetime import date, timedelta

from fastmcp import FastMCP

from mcp_server.db import get_connection

mcp = FastMCP("campus-customs")


def _today() -> str:
    conn = get_connection()
    row = conn.execute("SELECT date_today FROM desk").fetchone()
    conn.close()
    return row["date_today"]


@mcp.tool
def check_inventory(sku: str, size: str | None = None) -> dict:
    """Look up live stock for a SKU (optionally one size) from the inventory table.

    Used for ticket 101 (customer order for CC-TEE-WHITE size S — confirms
    whether there's stock to fill the order) and ticket 103 (Yale AI Club
    bulk order for 20x CC-HOOD-NAVY size M — confirms current qty against
    the requested qty so a shortfall can be sized).
    """
    conn = get_connection()
    if size:
        rows = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ?",
            (sku,),
        ).fetchall()
    conn.close()
    return {"sku": sku, "size": size, "matches": [dict(r) for r in rows]}


@mcp.tool
def get_invoice_status(invoice_id: int) -> dict:
    """Look up an invoice and its vendor from the invoices/vendors tables.

    Used for ticket 101: the ticket's invoice_id (501) points to an invoice
    from Bulldog Print Co. This tool reports the invoice's amount, due date,
    and status, compares due_date to desk.date_today to flag it overdue, and
    reports that the vendor cannot ship a restock while that invoice is
    unpaid (per the no-ship-with-unpaid-invoice rule).
    """
    conn = get_connection()
    row = conn.execute(
        """
        SELECT invoices.id, invoices.vendor_id, invoices.amount, invoices.due_date,
               invoices.status, invoices.description,
               vendors.name AS vendor_name, vendors.specialty AS vendor_specialty,
               vendors.lead_days AS vendor_lead_days
        FROM invoices
        JOIN vendors ON vendors.id = invoices.vendor_id
        WHERE invoices.id = ?
        """,
        (invoice_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return {"invoice_id": invoice_id, "found": False}

    today = _today()
    is_unpaid = row["status"] != "paid"
    is_overdue = is_unpaid and row["due_date"] < today

    return {
        "found": True,
        "invoice_id": row["id"],
        "vendor_id": row["vendor_id"],
        "vendor_name": row["vendor_name"],
        "vendor_specialty": row["vendor_specialty"],
        "vendor_lead_days": row["vendor_lead_days"],
        "amount": row["amount"],
        "due_date": row["due_date"],
        "status": row["status"],
        "description": row["description"],
        "date_today": today,
        "is_overdue": is_overdue,
        "vendor_blocked_from_shipping": is_unpaid,
    }


@mcp.tool
def get_lease_payment_status(lease_id: int) -> dict:
    """Look up a lease and check it against cash on hand and today's date.

    Used for ticket 102: the ticket's lease_id (1) points to the Chapel
    Street shop lease. This tool reports the monthly rent and next_due date,
    compares next_due to desk.date_today for days remaining, and compares
    the rent amount to the checking account balance so Accounting knows
    whether cash can cover it before requesting human approval to pay.
    """
    conn = get_connection()
    lease = conn.execute(
        "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
        (lease_id,),
    ).fetchone()
    cash = conn.execute(
        "SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'"
    ).fetchone()
    conn.close()
    if lease is None:
        return {"lease_id": lease_id, "found": False}

    today = _today()
    days_until_due = (date.fromisoformat(lease["next_due"]) - date.fromisoformat(today)).days

    return {
        "found": True,
        "lease_id": lease["id"],
        "space_name": lease["space_name"],
        "landlord": lease["landlord"],
        "monthly_rent": lease["monthly_rent"],
        "next_due": lease["next_due"],
        "notes": lease["notes"],
        "date_today": today,
        "days_until_due": days_until_due,
        "cash_account": cash["name"],
        "cash_balance": cash["balance"],
        "cash_covers_rent": cash["balance"] >= lease["monthly_rent"],
    }


@mcp.tool
def get_shop_clock() -> dict:
    """Return the shop's current date and desk notes from the desk table.

    Every agent should treat the returned date as "today" when deciding if a
    lease, invoice, or restock lead time is overdue — never today's real-world
    calendar date.
    """
    conn = get_connection()
    row = conn.execute("SELECT date_today, notes FROM desk").fetchone()
    conn.close()
    return {"date_today": row["date_today"], "notes": row["notes"]}


@mcp.tool
def get_cash_balance(account: str = "checking") -> dict:
    """Return the current balance for a cash account from cash_accounts.

    Used by Accounting to confirm funds before recommending a payment or
    purchase order, independent of any specific invoice or lease.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,)
    ).fetchone()
    conn.close()
    if row is None:
        return {"account": account, "found": False}
    return {"found": True, "account": row["name"], "balance": row["balance"], "as_of": row["date"]}


@mcp.tool
def list_open_tickets() -> list[dict]:
    """List every ticket with status 'open' from the tickets table.

    This is the Boss agent's inbox — the starting point for deciding who
    should work each ticket (currently tickets 101, 102, and 103).
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, notes, created_at "
        "FROM tickets WHERE status = 'open' ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Look up one ticket's full record from the tickets table by id.

    Used whenever an agent is handed a specific ticket id (e.g. by the Boss)
    and needs the ticket's sku/size/qty/lease_id/invoice_id to know which
    other tools to call next.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, notes, created_at "
        "FROM tickets WHERE id = ?",
        (ticket_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return {"ticket_id": ticket_id, "found": False}
    return {"found": True, **dict(row)}


@mcp.tool
def update_ticket_status(ticket_id: int, status: str, notes: str | None = None) -> dict:
    """Update a ticket's status (and optionally append a note) in the tickets table.

    This is how the Boss agent records the final call on a ticket (e.g.
    'resolved', 'blocked', 'escalated') once the right specialist has weighed
    in. It only ever touches the ticket row — it never pays anyone or moves
    inventory, so it's safe for the Boss to call directly.
    """
    conn = get_connection()
    existing = conn.execute("SELECT id, notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if existing is None:
        conn.close()
        return {"ticket_id": ticket_id, "found": False, "updated": False}

    combined_notes = existing["notes"] or ""
    if notes:
        combined_notes = f"{combined_notes}\n{notes}".strip()

    conn.execute(
        "UPDATE tickets SET status = ?, notes = ? WHERE id = ?",
        (status, combined_notes, ticket_id),
    )
    conn.commit()
    conn.close()
    return {"found": True, "updated": True, "ticket_id": ticket_id, "status": status, "notes": combined_notes}


@mcp.tool
def list_vendors(specialty: str | None = None) -> list[dict]:
    """List vendors from the vendors table, optionally filtered by specialty.

    Used by Inventory to find who can restock a shortfall (e.g. specialty
    'apparel reprint' for hoodies/tees) and to read each candidate's
    lead_days before recommending a restock plan.
    """
    conn = get_connection()
    if specialty:
        rows = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE specialty = ?",
            (specialty,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT id, name, specialty, lead_days FROM vendors").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@mcp.tool
def get_pricing(sku: str) -> dict:
    """Look up unit cost and list price for a SKU from the pricing table.

    Used by Accounting to check margin (list_price - unit_cost) before
    approving a discount or price override, such as ticket 103's bulk
    hoodie request.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
    ).fetchone()
    conn.close()
    if row is None:
        return {"sku": sku, "found": False}
    return {
        "found": True,
        "sku": row["sku"],
        "unit_cost": row["unit_cost"],
        "list_price": row["list_price"],
        "margin_per_unit": round(row["list_price"] - row["unit_cost"], 2),
    }


@mcp.tool
def create_purchase_order(vendor_id: int, sku: str, qty: int, notes: str | None = None) -> dict:
    """Draft a purchase order to a vendor as a new row in the invoices table.

    Used by Accounting to prepare a restock order for human approval (e.g.
    reordering CC-TEE-WHITE/S for ticket 101, or CC-HOOD-NAVY/M for ticket
    103). The amount is computed from qty x unit_cost in the pricing table,
    and due_date is today + the vendor's lead_days. Refuses to draft the PO
    if the vendor already has an open/unpaid invoice, since per the shop
    rules a vendor will not ship new product while they have an unpaid
    invoice — that invoice must be paid first.
    """
    conn = get_connection()
    vendor = conn.execute(
        "SELECT id, name, lead_days FROM vendors WHERE id = ?", (vendor_id,)
    ).fetchone()
    pricing = conn.execute(
        "SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)
    ).fetchone()
    blocking_invoice = conn.execute(
        "SELECT id, amount, due_date FROM invoices WHERE vendor_id = ? AND status != 'paid'",
        (vendor_id,),
    ).fetchone()

    if vendor is None:
        conn.close()
        return {"created": False, "reason": f"No vendor with id {vendor_id}."}
    if pricing is None:
        conn.close()
        return {"created": False, "reason": f"No pricing row for sku {sku}."}
    if blocking_invoice is not None:
        conn.close()
        return {
            "created": False,
            "reason": (
                f"Vendor {vendor['name']} has an unpaid invoice "
                f"(id {blocking_invoice['id']}, ${blocking_invoice['amount']}, "
                f"due {blocking_invoice['due_date']}) and will not ship until it is paid."
            ),
            "blocking_invoice_id": blocking_invoice["id"],
        }

    today = _today()
    due_date = (date.fromisoformat(today) + timedelta(days=vendor["lead_days"])).isoformat()
    amount = round(pricing["unit_cost"] * qty, 2)
    description = f"Purchase order: {qty}x {sku}" + (f" — {notes}" if notes else "")

    cur = conn.execute(
        "INSERT INTO invoices (vendor_id, amount, due_date, status, description) VALUES (?, ?, ?, 'pending_approval', ?)",
        (vendor_id, amount, due_date, description),
    )
    conn.commit()
    invoice_id = cur.lastrowid
    conn.close()

    return {
        "created": True,
        "invoice_id": invoice_id,
        "vendor_id": vendor_id,
        "vendor_name": vendor["name"],
        "sku": sku,
        "qty": qty,
        "amount": amount,
        "due_date": due_date,
        "status": "pending_approval",
    }


@mcp.tool
def pay_invoice(invoice_id: int, approved_by: str, human_approved: bool = False) -> dict:
    """Pay an invoice out of the checking account and record it in payments.

    This is the shop's pay tool, and it only ever sends cash out (there is no
    cash-in path in this system). It enforces the hard rules: it refuses
    unless human_approved is explicitly True and approved_by names the human
    who approved it (no agent may set this itself — an agent should always
    stop and ask a human before calling this), and it refuses if paying would
    take the checking balance below zero — no negative balances are allowed.
    On success it updates the invoice to 'paid', deducts the amount from
    cash_accounts, and appends an audit row to payments.
    """
    if not human_approved or not approved_by.strip():
        return {
            "paid": False,
            "reason": "Payment requires explicit human approval (human_approved=True and a named approved_by).",
        }

    conn = get_connection()
    invoice = conn.execute(
        "SELECT id, vendor_id, amount, status FROM invoices WHERE id = ?", (invoice_id,)
    ).fetchone()
    if invoice is None:
        conn.close()
        return {"paid": False, "reason": f"No invoice with id {invoice_id}."}
    if invoice["status"] == "paid":
        conn.close()
        return {"paid": False, "reason": f"Invoice {invoice_id} is already paid."}

    cash = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()
    if cash["balance"] - invoice["amount"] < 0:
        conn.close()
        return {
            "paid": False,
            "reason": (
                f"Paying ${invoice['amount']} would take checking below zero "
                f"(balance is ${cash['balance']}). No negative balances allowed."
            ),
        }

    today = _today()
    new_balance = round(cash["balance"] - invoice["amount"], 2)
    conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = 'checking'", (new_balance, today))
    conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (invoice_id,))
    conn.execute(
        "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES ('invoice', ?, ?, 'checking', ?, ?)",
        (invoice_id, invoice["amount"], today, approved_by),
    )
    conn.commit()
    conn.close()

    return {
        "paid": True,
        "invoice_id": invoice_id,
        "amount": invoice["amount"],
        "approved_by": approved_by,
        "paid_at": today,
        "new_checking_balance": new_balance,
    }


@mcp.tool
def pay_lease(lease_id: int, approved_by: str, human_approved: bool = False) -> dict:
    """Pay a lease's monthly rent out of the checking account and record it in payments.

    Rent isn't an invoice — it lives in the leases table — so this is the
    lease equivalent of pay_invoice, with the same hard rules: it refuses
    unless human_approved is explicitly True and approved_by names the human
    who approved it, and it refuses if paying would take the checking
    balance below zero. On success it deducts monthly_rent from
    cash_accounts, appends a 'rent' row to payments, and advances the
    lease's next_due by 30 days so the next cycle's due date is in the
    future again.
    """
    if not human_approved or not approved_by.strip():
        return {
            "paid": False,
            "reason": "Payment requires explicit human approval (human_approved=True and a named approved_by).",
        }

    conn = get_connection()
    lease = conn.execute(
        "SELECT id, space_name, monthly_rent, next_due FROM leases WHERE id = ?", (lease_id,)
    ).fetchone()
    if lease is None:
        conn.close()
        return {"paid": False, "reason": f"No lease with id {lease_id}."}

    cash = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()
    if cash["balance"] - lease["monthly_rent"] < 0:
        conn.close()
        return {
            "paid": False,
            "reason": (
                f"Paying ${lease['monthly_rent']} would take checking below zero "
                f"(balance is ${cash['balance']}). No negative balances allowed."
            ),
        }

    today = _today()
    new_balance = round(cash["balance"] - lease["monthly_rent"], 2)
    new_next_due = (date.fromisoformat(lease["next_due"]) + timedelta(days=30)).isoformat()
    conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = 'checking'", (new_balance, today))
    conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (new_next_due, lease_id))
    conn.execute(
        "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES ('rent', ?, ?, 'checking', ?, ?)",
        (lease_id, lease["monthly_rent"], today, approved_by),
    )
    conn.commit()
    conn.close()

    return {
        "paid": True,
        "lease_id": lease_id,
        "space_name": lease["space_name"],
        "amount": lease["monthly_rent"],
        "approved_by": approved_by,
        "paid_at": today,
        "new_checking_balance": new_balance,
        "new_next_due": new_next_due,
    }


if __name__ == "__main__":
    mcp.run()
