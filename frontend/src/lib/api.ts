import type {
  ApprovePaymentRequest,
  ApprovePaymentResponse,
  CashResponse,
  EventsResponse,
  ResetResponse,
  RunTicketResponse,
  Ticket,
} from "./types";

// The dashboard talks to the FastAPI backend from Problem 7, always at this
// fixed address — the backend's CORS allowlist is set up for the Vite dev
// origin specifically to make this pairing work.
export const API_BASE = "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ ok: boolean; db: string }>("/api/health"),

  getTickets: () => request<{ tickets: Ticket[] }>("/api/tickets").then((r) => r.tickets),

  runTicket: (ticketId: number) =>
    request<RunTicketResponse>(`/api/tickets/${ticketId}/run`, { method: "POST" }),

  getEvents: (ticketId?: number, limit = 200) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (ticketId !== undefined) params.set("ticket_id", String(ticketId));
    return request<EventsResponse>(`/api/events?${params.toString()}`);
  },

  approvePayment: (body: ApprovePaymentRequest) =>
    request<ApprovePaymentResponse>("/api/payments/approve", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getCash: () => request<CashResponse>("/api/cash"),

  resetDatabase: () => request<ResetResponse>("/api/reset", { method: "POST" }),
};
