import { useEffect, useRef } from "react";
import type { Ticket } from "../lib/types";
import { useTicketRun } from "../hooks/useTicketRun";
import { AgentFeed } from "./AgentFeed";
import { AgentSummary } from "./AgentSummary";
import { ApprovalPanel } from "./ApprovalPanel";
import { StatusBadge, VerdictStamp } from "./StatusBadge";

interface Props {
  ticket: Ticket;
  onSettled: () => void;
}

export function TicketBoard({ ticket, onSettled }: Props) {
  const { events, status, error, run } = useTicketRun(ticket.id, onSettled);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (status === "running" && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, status]);

  const running = status === "running";
  // Trust the freshly-refetched ticket record for "is this actually done,"
  // not just this browser tab's own fetch outcome — a long agent run (these
  // can take several minutes once delegation chains get deep) can finish
  // correctly on the backend even if this tab's own HTTP connection to it
  // drops first, so is_open is the honest source of truth either way.
  const finished = !running && !ticket.is_open;
  const showStaleError = status === "error" && ticket.is_open;

  return (
    <div className="board">
      <div className="board-head">
        <div>
          <h2>
            #{ticket.id} — {ticket.subject}
          </h2>
          <div className="meta">
            <span>
              <span className="k">from</span> {ticket.requester}
            </span>
            <span>
              <span className="k">type</span> {ticket.type}
            </span>
            {ticket.sku && (
              <span>
                <span className="k">item</span> {ticket.sku} {ticket.size} × {ticket.qty}
              </span>
            )}
            {ticket.lease_id && (
              <span>
                <span className="k">lease</span> #{ticket.lease_id}
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {finished ? <VerdictStamp status={ticket.status} /> : <StatusBadge status={ticket.status} />}
          <button className="run-btn" onClick={run} disabled={running}>
            {running ? "Agents working…" : "Run agent team"}
          </button>
        </div>
      </div>

      <div className="board-scroll" ref={scrollRef}>
        {showStaleError && (
          <div className="feed-empty" style={{ borderColor: "var(--bad)", color: "var(--bad)" }}>
            Lost the connection while the agents were working ({error}). They may still be
            finishing up — reopen this ticket in a moment to check, or hit run again.
          </div>
        )}

        <section>
          <p className="section-label">
            {running && <span className="live-dot" />}
            {running ? "Live agent feed" : "Agent feed"}
          </p>
          <AgentFeed events={events} />
        </section>

        <section>
          <p className="section-label">Per-agent summary</p>
          <AgentSummary events={events} />
        </section>

        <section>
          <p className="section-label">Needs human approval</p>
          <ApprovalPanel events={events} onApproved={onSettled} />
        </section>
      </div>
    </div>
  );
}
