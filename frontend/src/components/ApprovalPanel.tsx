import { useMemo, useState } from "react";
import { deriveApprovalSuggestions } from "../lib/approvals";
import { api } from "../lib/api";
import type { AgentEvent } from "../lib/types";

interface Props {
  events: AgentEvent[];
  onApproved: () => void;
}

export function ApprovalPanel({ events, onApproved }: Props) {
  const suggestions = useMemo(() => deriveApprovalSuggestions(events), [events]);
  const [names, setNames] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, { ok: boolean; message: string }>>({});

  if (suggestions.length === 0) {
    return <div className="no-approvals">Nothing is waiting on a human yet.</div>;
  }

  async function approve(key: string, kind: "invoice" | "rent", refId: number) {
    const approvedBy = (names[key] ?? "").trim();
    if (!approvedBy) {
      setResults((r) => ({ ...r, [key]: { ok: false, message: "Enter your name to approve." } }));
      return;
    }
    setBusy(key);
    try {
      const res = await api.approvePayment({ kind, ref_id: refId, approved_by: approvedBy });
      setResults((r) => ({
        ...r,
        [key]: { ok: true, message: `Paid $${res.amount} — new balance $${res.new_checking_balance}.` },
      }));
      onApproved();
    } catch (err) {
      setResults((r) => ({ ...r, [key]: { ok: false, message: String(err) } }));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="approvals">
      {suggestions.map((s) => {
        const result = results[s.key];
        const paidOk = result?.ok;
        return (
          <div className="approval-card" key={s.key}>
            <div className="approval-info">
              <div className="label">{s.label}</div>
              <div className="detail">{s.detail}</div>
              {result && <div className={`approval-result ${result.ok ? "ok" : "err"}`}>{result.message}</div>}
            </div>
            {!paidOk && (
              <div className="approval-actions">
                <input
                  placeholder="Your name"
                  value={names[s.key] ?? ""}
                  onChange={(e) => setNames((n) => ({ ...n, [s.key]: e.target.value }))}
                />
                <button
                  className="approve-btn"
                  disabled={busy === s.key}
                  onClick={() => approve(s.key, s.kind, s.ref_id)}
                >
                  {busy === s.key ? "Approving…" : "Approve"}
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
