"""Append-only audit trail for the agent team.

Every agent-loop step (prompt in, model request, model response with tool
calls + token usage, end) and every inter-agent delegation gets appended as
one JSON object per line to output/audit_trail.json. The file is opened in
append mode and is never truncated or rewritten, so a history of every run
accumulates across the whole project — exactly what a human would need to
audit later what the agents actually did with real customers and real money.

Format is JSON Lines (one JSON object per line) rather than a single JSON
array, specifically so appending never requires reading the whole file back
into memory and rewriting it.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import RetryPromptPart, TextPart, ThinkingPart, ToolCallPart, ToolReturnPart

from backend.models import AuditEvent

AUDIT_TRAIL_PATH = Path(__file__).resolve().parents[2] / "output" / "audit_trail.json"
_write_lock = threading.Lock()


def clip(value: Any, limit: int = 800) -> str:
    text = value if isinstance(value, str) else str(value)
    return text if len(text) <= limit else text[: limit] + f"... (+{len(text) - limit} chars)"


def _usage_dict(usage: Any) -> dict:
    return {
        "requests": getattr(usage, "requests", 0) or 0,
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "tool_calls": getattr(usage, "tool_calls", 0) or 0,
    }


def append_audit_event(event: AuditEvent) -> None:
    AUDIT_TRAIL_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event.to_dict(), default=str)
    with _write_lock:
        with AUDIT_TRAIL_PATH.open("a") as f:
            f.write(line + "\n")


def _describe_node(node: Any) -> tuple[str, dict] | None:
    if Agent.is_user_prompt_node(node):
        return "user_prompt", {"prompt": clip(node.user_prompt)}

    if Agent.is_model_request_node(node):
        parts = node.request.parts
        returns = [
            {"tool": p.tool_name, "tool_call_id": p.tool_call_id, "content": clip(p.model_response_str(), 500)}
            for p in parts
            if isinstance(p, ToolReturnPart)
        ]
        retries = [clip(p.model_response(), 300) for p in parts if isinstance(p, RetryPromptPart)]
        return "model_request", {"parts": [type(p).__name__ for p in parts], "tool_returns": returns, "retries": retries}

    if Agent.is_call_tools_node(node):
        resp = node.model_response
        text = "".join(p.content for p in resp.parts if isinstance(p, TextPart))
        thinking = "".join(p.content for p in resp.parts if isinstance(p, ThinkingPart))
        calls = [
            {"tool": p.tool_name, "tool_call_id": p.tool_call_id, "args": p.args_as_dict()}
            for p in resp.parts
            if isinstance(p, ToolCallPart)
        ]
        return "model_response", {
            "model": resp.model_name,
            "text": clip(text),
            "thinking": clip(thinking, 400) if thinking else "",
            "tool_calls": calls,
            "usage": _usage_dict(resp.usage),
        }

    if Agent.is_end_node(node):
        return "end", {"output": clip(node.data.output)}

    return None


async def run_with_audit(
    agent: Agent,
    prompt: str,
    *,
    agent_name: str,
    ticket_id: int | None,
    deps: Any = None,
    usage: Any = None,
    usage_limits: Any = None,
) -> Any:
    """Run `agent`, appending one AuditEvent per agent-loop node, and return its output."""
    async with agent.iter(prompt, deps=deps, usage=usage, usage_limits=usage_limits) as run:
        step = 0
        async for node in run:
            described = _describe_node(node)
            if described is None:
                continue
            step += 1
            kind, data = described
            append_audit_event(AuditEvent(ticket_id=ticket_id, agent=agent_name, step=step, kind=kind, data=data))
    return run.result.output
