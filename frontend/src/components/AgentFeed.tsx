import type { ReactNode } from "react";
import type { AgentEvent } from "../lib/types";
import { agentMeta } from "../lib/agents";

function fmtTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString(undefined, { hour12: false });
  } catch {
    return ts;
  }
}

function toolArgsPreview(args: Record<string, unknown>): string {
  const entries = Object.entries(args);
  if (entries.length === 0) return "";
  return entries.map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ");
}

// Delegation rows are connective tissue ("who asked whom, and did they hand
// anything back") — the full answer is already shown a moment later (or
// earlier) in that agent's own styled bubble, so these only need a preview.
function clip(text: string | undefined, limit = 110): string {
  if (!text) return "";
  const trimmed = text.trim();
  return trimmed.length > limit ? `${trimmed.slice(0, limit)}…` : trimmed;
}

// Who does a "handed its answer back" row hand back *to*? We only trust the
// backend's own `to` field for this (set directly from the caller/target
// closure in backend/agents/delegation.py), never a frontend guess. Agents
// sometimes get delegated to concurrently (Boss asking two specialists in
// the same turn), so a simple "call stack" reconstruction over the flat
// event log can't reliably untangle interleaved conversations — it produced
// confidently wrong answers (e.g. "Inventory handed back to Inventory") on
// real multi-branch runs, which is worse than just not naming a recipient.
// Only runs logged after that backend fix will show a name; older history
// honestly shows none rather than guessing.

function FeedBubble({
  event,
  variant,
  children,
}: {
  event: AgentEvent;
  variant: string;
  children: ReactNode;
}) {
  const meta = agentMeta(event.agent);
  return (
    <div className="feed-row">
      <div className="agent-chip" style={{ background: `var(${meta.colorVar})` }}>
        {meta.initial}
      </div>
      <div
        className={`feed-bubble bubble-${variant}`}
        style={{ ["--bubble-accent" as string]: `var(${meta.colorVar})` }}
      >
        <div className="bubble-head">
          <span className="agent-name" style={{ color: `var(${meta.colorVar})` }}>
            {meta.label}
          </span>
          <span className="bubble-time">{fmtTime(event.timestamp)}</span>
        </div>
        {children}
      </div>
    </div>
  );
}

function renderEvent(event: AgentEvent, key: string) {
  switch (event.kind) {
    case "user_prompt":
      return (
        <FeedBubble key={key} event={event} variant="prompt">
          <div className="bubble-text">was asked: “{event.prompt}”</div>
        </FeedBubble>
      );

    case "model_response": {
      const hasText = event.text && event.text.trim().length > 0;
      const hasThinking = event.thinking && event.thinking.trim().length > 0;
      if (!hasText && !hasThinking && (!event.tool_calls || event.tool_calls.length === 0)) {
        return null;
      }
      return (
        <FeedBubble key={key} event={event} variant="response">
          {hasThinking && <div className="bubble-text thinking">{event.thinking}</div>}
          {hasText && <div className="bubble-text">{event.text}</div>}
          {event.tool_calls && event.tool_calls.length > 0 && (
            <div className="tool-chip-row">
              {event.tool_calls.map((tc) => (
                <span className="tool-chip" key={tc.tool_call_id}>
                  🔧 {tc.tool}({toolArgsPreview(tc.args)})
                </span>
              ))}
            </div>
          )}
        </FeedBubble>
      );
    }

    case "delegation_start":
      return (
        <div className="delegation-row" key={key}>
          <span className="arrow">→</span>
          delegating to <strong>{agentMeta(event.to ?? "").label}</strong>: “{clip(event.question)}”
        </div>
      );

    case "delegation_end":
      return (
        <div className="delegation-row" key={key}>
          <span className="arrow">↩</span>
          <strong>{agentMeta(event.agent).label}</strong> handed its answer back
          {event.to ? (
            <>
              {" "}
              to <strong>{agentMeta(event.to).label}</strong>
            </>
          ) : null}{" "}
          (see its reply above)
        </div>
      );

    case "end":
      return (
        <FeedBubble key={key} event={event} variant="end">
          <div className="bubble-text">
            <strong>Final:</strong> {event.output}
          </div>
        </FeedBubble>
      );

    default:
      return null;
  }
}

export function AgentFeed({ events }: { events: AgentEvent[] }) {
  const rendered = events
    .map((e, i) => renderEvent(e, `${e.timestamp}-${i}`))
    .filter(Boolean);

  if (rendered.length === 0) {
    return <div className="feed-empty">No activity yet — run the agent team to see them work.</div>;
  }

  return <div className="feed">{rendered}</div>;
}
