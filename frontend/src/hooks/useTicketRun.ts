import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { AgentEvent } from "../lib/types";

export type RunStatus = "idle" | "loading-history" | "running" | "done" | "error";

interface UseTicketRunResult {
  events: AgentEvent[];
  status: RunStatus;
  outcome: string | null;
  delegations: number | null;
  error: string | null;
  run: () => void;
}

const POLL_MS = 1100;

/**
 * Owns one ticket's event feed: loads its history on selection, and while a
 * run is in flight polls GET /api/events for new rows so the feed updates
 * live (the backend's run route itself blocks until the whole delegation
 * tree finishes, so polling is what makes this feel live without changing
 * the Problem 7 routes).
 */
export function useTicketRun(ticketId: number, onSettled: () => void): UseTicketRunResult {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [status, setStatus] = useState<RunStatus>("loading-history");
  const [outcome, setOutcome] = useState<string | null>(null);
  const [delegations, setDelegations] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const refreshEvents = useCallback(async () => {
    const res = await api.getEvents(ticketId, 300);
    setEvents(res.events);
    return res.events;
  }, [ticketId]);

  // Load this ticket's history whenever a different ticket is selected.
  useEffect(() => {
    let cancelled = false;
    setStatus("loading-history");
    setOutcome(null);
    setDelegations(null);
    setError(null);
    stopPolling();

    api
      .getEvents(ticketId, 300)
      .then((res) => {
        if (cancelled) return;
        setEvents(res.events);
        const lastEnd = [...res.events].reverse().find((e) => e.kind === "ticket_end");
        if (lastEnd) {
          setOutcome(lastEnd.output ?? null);
          setDelegations(lastEnd.delegations ?? null);
        }
        setStatus("idle");
      })
      .catch((err) => {
        if (!cancelled) {
          setError(String(err));
          setStatus("error");
        }
      });

    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [ticketId, stopPolling]);

  const run = useCallback(() => {
    setStatus("running");
    setError(null);
    setOutcome(null);
    setDelegations(null);

    pollRef.current = setInterval(() => {
      refreshEvents().catch(() => {
        /* transient poll errors are fine — next tick retries */
      });
    }, POLL_MS);

    api
      .runTicket(ticketId)
      .then(async (res) => {
        await refreshEvents();
        setOutcome(res.outcome);
        setDelegations(res.delegations);
        setStatus("done");
      })
      .catch((err) => {
        setError(String(err));
        setStatus("error");
      })
      .finally(() => {
        stopPolling();
        onSettled();
      });
  }, [ticketId, refreshEvents, stopPolling, onSettled]);

  useEffect(() => stopPolling, [stopPolling]);

  return { events, status, outcome, delegations, error, run };
}
