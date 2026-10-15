import type { AgentEvent, PaymentKind } from "./types";

export interface ApprovalSuggestion {
  key: string;
  kind: PaymentKind;
  ref_id: number;
  label: string;
  detail: string;
  amount: number;
}

function parseToolReturn(content: string): Record<string, unknown> | null {
  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
}

/**
 * Scan a ticket's real audit events for tool calls that surfaced something
 * payable, and turn them into concrete "approve this" suggestions.
 *
 * This only ever reads what a tool actually returned (create_purchase_order,
 * get_invoice_status, get_lease_payment_status) — nothing here is invented;
 * it's just turning facts already in the trail into a one-click action.
 */
export function deriveApprovalSuggestions(events: AgentEvent[]): ApprovalSuggestion[] {
  const suggestions = new Map<string, ApprovalSuggestion>();

  for (const event of events) {
    if (event.kind !== "model_request" || !event.tool_returns) continue;

    for (const ret of event.tool_returns) {
      const data = parseToolReturn(ret.content);
      if (!data) continue;

      if (ret.tool === "create_purchase_order" && data.created === true) {
        const key = `invoice:${data.invoice_id}`;
        suggestions.set(key, {
          key,
          kind: "invoice",
          ref_id: data.invoice_id as number,
          label: `Pay invoice ${data.invoice_id}`,
          detail: `${data.vendor_name ?? "vendor"} — ${data.qty ?? "?"}x ${data.sku ?? "item"}, $${data.amount}`,
          amount: Number(data.amount ?? 0),
        });
      }

      if (ret.tool === "get_invoice_status" && data.found === true && data.status !== "paid") {
        const key = `invoice:${data.invoice_id}`;
        suggestions.set(key, {
          key,
          kind: "invoice",
          ref_id: data.invoice_id as number,
          label: `Pay invoice ${data.invoice_id}`,
          detail: `${data.vendor_name ?? "vendor"} — $${data.amount}${data.is_overdue ? " (overdue)" : ""}`,
          amount: Number(data.amount ?? 0),
        });
      }

      if (ret.tool === "get_lease_payment_status" && data.found === true) {
        const key = `rent:${data.lease_id}`;
        suggestions.set(key, {
          key,
          kind: "rent",
          ref_id: data.lease_id as number,
          label: `Pay rent — lease ${data.lease_id}`,
          detail: `${data.space_name ?? "lease"} — $${data.monthly_rent}, due ${data.next_due}`,
          amount: Number(data.monthly_rent ?? 0),
        });
      }
    }
  }

  return Array.from(suggestions.values());
}
