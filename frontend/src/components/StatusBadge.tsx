function statusClass(status: string): string {
  const s = status.toLowerCase();
  if (s === "open") return "status-open";
  if (s === "resolved") return "status-resolved";
  if (s === "escalated") return "status-escalated";
  return "status-blocked";
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`status-badge ${statusClass(status)}`}>
      <span className="dot" />
      {status}
    </span>
  );
}

export function VerdictStamp({ status }: { status: string }) {
  return <span className={`verdict-stamp ${statusClass(status)}`}>{status}</span>;
}
