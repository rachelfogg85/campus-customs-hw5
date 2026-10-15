import type { AgentRole } from "./types";

export interface AgentMeta {
  label: string;
  initial: string;
  colorVar: string;
  blurb: string;
}

export const AGENT_META: Record<string, AgentMeta> = {
  boss: {
    label: "Boss",
    initial: "B",
    colorVar: "--agent-boss",
    blurb: "Triages the ticket and makes the final call.",
  },
  inventory: {
    label: "Inventory",
    initial: "I",
    colorVar: "--agent-inventory",
    blurb: "Stock, shortfalls, and vendors.",
  },
  accounting: {
    label: "Accounting",
    initial: "A",
    colorVar: "--agent-accounting",
    blurb: "Cash, invoices, margin, payments.",
  },
  facilities: {
    label: "Facilities",
    initial: "F",
    colorVar: "--agent-facilities",
    blurb: "Lease and shop space.",
  },
  customer_service: {
    label: "Customer Service",
    initial: "C",
    colorVar: "--agent-customer-service",
    blurb: "Drafts (never sends) customer messages.",
  },
  orchestrator: {
    label: "Desk",
    initial: "D",
    colorVar: "--agent-orchestrator",
    blurb: "The run itself — start and finish markers.",
  },
};

export function agentMeta(role: string): AgentMeta {
  return (
    AGENT_META[role] ?? {
      label: role,
      initial: role.slice(0, 1).toUpperCase(),
      colorVar: "--agent-orchestrator",
      blurb: "",
    }
  );
}

export const SPECIALIST_ROLES: AgentRole[] = [
  "boss",
  "inventory",
  "accounting",
  "facilities",
  "customer_service",
];
