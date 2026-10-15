// Mirrors backend/models.py — kept by hand since this is a small, stable API surface.

export type TicketType = "customer_order" | "rent_notice" | "price_override" | string;

export interface Ticket {
  id: number;
  type: TicketType;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  status: string;
  notes: string | null;
  created_at: string;
  is_open: boolean;
}

export interface RunTicketResponse {
  ticket_id: number;
  outcome: string;
  delegations: number;
}

export type AgentRole = "boss" | "inventory" | "accounting" | "facilities" | "customer_service";

export type EventKind =
  | "user_prompt"
  | "model_request"
  | "model_response"
  | "delegation_start"
  | "delegation_end"
  | "end"
  | "ticket_start"
  | "ticket_end";

export interface ToolCall {
  tool: string;
  tool_call_id: string;
  args: Record<string, unknown>;
}

export interface ToolReturn {
  tool: string;
  tool_call_id: string;
  content: string;
}

export interface UsageDict {
  requests: number;
  input_tokens: number;
  output_tokens: number;
  tool_calls: number;
}

// Loosely typed: the audit trail is a flat dict with kind-specific extra
// fields spread in (see backend/models.py::AuditEvent.to_dict).
export interface AgentEvent {
  timestamp: string;
  ticket_id: number | null;
  agent: string;
  step: number;
  kind: EventKind;
  prompt?: string;
  parts?: string[];
  tool_returns?: ToolReturn[];
  retries?: string[];
  model?: string;
  text?: string;
  thinking?: string;
  tool_calls?: ToolCall[];
  usage?: UsageDict;
  output?: string;
  from?: string;
  to?: string;
  question?: string;
  delegations?: number;
}

export interface EventsResponse {
  count: number;
  events: AgentEvent[];
}

export type PaymentKind = "invoice" | "rent";

export interface ApprovePaymentRequest {
  kind: PaymentKind;
  ref_id: number;
  approved_by: string;
}

export interface ApprovePaymentResponse {
  paid: boolean;
  reason?: string;
  invoice_id?: number;
  lease_id?: number;
  amount?: number;
  approved_by?: string;
  paid_at?: string;
  new_checking_balance?: number;
  [key: string]: unknown;
}

export interface CashResponse {
  account: string;
  balance: number;
  as_of: string;
}

export interface ResetResponse {
  reset: boolean;
  message: string;
}
