import type { AgentEvent } from "../lib/types";
import { agentMeta, SPECIALIST_ROLES } from "../lib/agents";

/** One card per agent that actually participated, showing its own final word. */
export function AgentSummary({ events }: { events: AgentEvent[] }) {
  const lastEndByAgent = new Map<string, string>();
  for (const e of events) {
    if (e.kind === "end" && e.output) {
      lastEndByAgent.set(e.agent, e.output);
    }
  }

  const participants = SPECIALIST_ROLES.filter((role) => lastEndByAgent.has(role));

  if (participants.length === 0) {
    return <div className="no-approvals">No agent has reported in on this ticket yet.</div>;
  }

  return (
    <div className="summary-grid">
      {participants.map((role) => {
        const meta = agentMeta(role);
        return (
          <div className="summary-card" key={role} style={{ ["--card-accent" as string]: `var(${meta.colorVar})` }}>
            <div className="summary-head">
              <div className="agent-chip" style={{ background: `var(${meta.colorVar})` }}>
                {meta.initial}
              </div>
              <span className="agent-name" style={{ color: `var(${meta.colorVar})` }}>
                {meta.label}
              </span>
            </div>
            <div className="summary-text">{lastEndByAgent.get(role)}</div>
          </div>
        );
      })}
    </div>
  );
}
