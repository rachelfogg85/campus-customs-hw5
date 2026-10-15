import type { Ticket } from "../lib/types";
import { StatusBadge } from "./StatusBadge";

interface Props {
  tickets: Ticket[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}

function ticketLine(t: Ticket): string {
  if (t.sku) return `${t.sku}${t.size ? ` / ${t.size}` : ""}${t.qty ? ` × ${t.qty}` : ""}`;
  if (t.lease_id) return `Lease #${t.lease_id}`;
  return t.type;
}

export function TicketQueue({ tickets, selectedId, onSelect }: Props) {
  return (
    <div className="queue">
      <h2>Desk tickets</h2>
      {tickets.map((t) => (
        <button
          key={t.id}
          type="button"
          className={`ticket-stub${t.id === selectedId ? " selected" : ""}`}
          onClick={() => onSelect(t.id)}
        >
          <div className="stub-top">
            <span className="stub-id">#{t.id}</span>
            <StatusBadge status={t.status} />
          </div>
          <div className="stub-subject">{t.subject}</div>
          <div className="stub-requester">{t.requester}</div>
          <div className="stub-divider" />
          <div className="stub-requester mono">{ticketLine(t)}</div>
        </button>
      ))}
    </div>
  );
}
