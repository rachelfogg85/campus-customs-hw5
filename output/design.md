# Dashboard Design — Campus Customs Agent Desk

`frontend/` — React + Vite + TypeScript, talking to the FastAPI backend from Problem 7 at `http://localhost:8000`.

**Note on color:** this document originally described a black-and-pink theme (the project's default house style). Partway through, you explicitly asked for a white background with blue accents instead — first for the static report pages, then, when I checked, for everything including this dashboard. Everything below describes the current, actual white-and-blue version; the design history section at the bottom records that pivot honestly rather than pretending it was blue from the start.

## The concept: a desk, not a dashboard

Most agent demos look like a chat window or a log viewer. I wanted this to feel like an actual **desk** someone sits at for a shift — a physical metaphor, not a generic admin panel. That drove three concrete choices:

- **Ticket queue reads like a stack of paper stubs**, not a table. Each ticket card (`.ticket-stub` in `App.css`) has a dashed perforation line with little circular "punch holes" cut into the edges — like tearing a ticket off a roll. You pick one up (click it) to work it.
- **A verdict stamp, not just a status chip.** While a ticket is open, its status shows as a small pill badge. The moment it's no longer open, the board head renders a rotated, thick-bordered `VERDICT STAMP` (`BLOCKED` / `RESOLVED` / `ESCALATED`) — like a rubber stamp slapped on a case file. That's the single biggest "this feels satisfying" moment in the UI: a ticket visibly gets *closed out*, and the word stamped on it is whatever the Boss actually decided, in whatever real language it used (`blocked`, `escalated`, etc.) — I did not force everything to say "RESOLVED" just to look tidy, because that would misrepresent what actually happened.
- **The cash balance is a glowing LED ticker** in the header, not a line item — tabular-numeral monospace, and a one-shot "bump" animation (flash + scale) the instant it changes. Since the whole point of Problem 7's payment route is "this is the one thing that really moves money," the UI makes that moment visually loud on purpose.

## Color system: white background, blue accents

The whole UI is white with a single blue accent (`index.css` `:root` variables) — no pink anywhere. The only exceptions are semantic, not decorative: green for "paid/good" and red for "refused/bad," since overloading one accent color for both success and failure would make the approval flow confusing. Within that constraint, each of the five agents still gets its own shade, now in the blue family instead of pink:

| Agent | Color | Why this shade |
|---|---|---|
| Boss | strong brand blue | The central, authoritative voice — gets the boldest, most "default" blue. |
| Inventory | soft sky blue | Lightest, friendliest — it's just reporting numbers. |
| Accounting | indigo | Noticeably cooler and more saturated — money talk reads as more serious. |
| Facilities | teal-blue | Between Boss and Inventory in weight. |
| Customer Service | pale blue | Deliberately the softest — it's the one agent whose words a human (the customer) would actually read. |

Every agent gets a small circular initial badge (`B`/`I`/`A`/`F`/`C`) in its color, used identically in three places — the live feed, the delegation arrows, and the summary cards — so a user learns "blue circle with a C = Customer Service" once and can then scan the whole board at a glance without rereading labels. This mapping (which shade means which agent) didn't change when the palette flipped from pink to blue — only the hues themselves did.

## Layout

Two-column desk: a fixed **ticket queue** on the left (always visible, so you never lose your place), and a **ticket board** on the right that's entirely about the ticket you're currently holding:

1. **Board head** — ticket subject/requester/type/item, the verdict stamp or status pill, and the single "Run agent team" button (feature #2).
2. **Live agent feed** (feature #3) — a chat-thread-style log. Each turn is a colored bubble with the agent's name, its text, and its tool calls rendered as inline `🔧 tool_name(args)` chips so you can see *what it did*, not just what it said. Delegations render as their own compact arrow rows — `→ delegating to Inventory: "..."` when one agent asks another for help, and `↩ Inventory handed its answer back to Boss` when it replies — rather than full bubbles, so a ticket with deep cross-agent delegation (ticket 101 bounced Boss → Inventory → Accounting → Inventory → Customer Service → Inventory/Accounting again) stays readable instead of turning into a wall of identical-looking cards. Both of those arrow rows only ever show a short preview or a plain name, never the agent's full answer a second time — that used to be a real bug (see the design iteration log below). While a run is active, a small pulsing dot next to "Live agent feed" makes clear this is updating in real time, and the pane auto-scrolls to the newest line.
3. **Per-agent summary** (feature #5) — one card per agent that actually participated, holding that agent's own final answer (not a reinterpretation of it). This directly answers "what did each agent conclude" without having to re-read the whole feed.
4. **Needs human approval** (feature #6) — this is the one section that isn't just a read-out. It scans the ticket's real tool call history for `create_purchase_order` / `get_invoice_status` / `get_lease_payment_status` results that are still payable, and turns each into a concrete "Pay invoice 501 — Bulldog Print Co — $840 (overdue)" card with a name field and an Approve button. Nothing here is invented — every suggestion is parsed straight out of a tool's actual JSON return in that ticket's audit trail; the UI is just turning a fact the agents already surfaced into a one-click action. Approving calls `POST /api/payments/approve`, and on success the card shows the real new balance inline and the header's cash ticker flashes and drops (feature #7).

## How "live" actually works

`POST /api/tickets/{id}/run` blocks until the whole delegation tree finishes — sometimes for several minutes once a ticket goes several layers deep. Rather than changing the Problem 7 routes, the dashboard fakes "live" the honest way: it fires the run request and, in parallel, polls `GET /api/events?ticket_id=` every ~1.1s for the duration, so the feed fills in as the real audit trail grows. One thing this surfaced during testing: a single long-lived POST is fragile against any proxy or connection timeout sitting between the browser and the backend — in one run here, the backend finished and correctly set the ticket to `blocked`, but this tab's own fetch to `/run` dropped first. So the "has this ticket finished" decision in `TicketBoard` deliberately trusts the freshly-refetched ticket's real `status`/`is_open` from the database, not just this tab's own request outcome — if the connection drops but the ticket is in fact no longer open, the UI still shows the correct verdict stamp instead of a false error.

## Small touches worth calling out

- The header's cash ticker has a faint diagonal light-sweep gradient behind it (`.cash-ticker::before`) — a subtle "display case" feel without being gaudy.
- Monospace is used specifically for anything that's a real system value (ticket IDs, tool calls, the cash figure, timestamps) and regular type for anything conversational (agent text) — a quiet way to signal "this is data" vs. "this is prose" without labeling everything.
- The verdict stamp used to rely on `mix-blend-mode: screen` for its glow, which only works against a dark background — on white it would have washed the stamp out to invisible. That got caught and removed as part of the repaint.

## Design iteration log

The design went through a few real, requested changes after the initial build, each one driven by actually using the thing, not hypothetical polish:

1. **Initial build:** black background, pink accents, per-agent pink/rose/magenta shades — the project's default house style.
2. **"White background, plain language" request:** first scoped to the static report pages (`output/desk_tickets.html`, `output/resolved_board.html`) — white background, no jargon, no code snippets, plain English descriptions of what each agent did.
3. **Scope widened to the dashboard itself:** on request, the same white-background treatment was applied to the live React dashboard too, including re-deriving the whole agent color palette in blue instead of pink, and removing a dark-theme-only CSS effect (`mix-blend-mode: screen`) that would have broken on white.
4. **A real duplication bug, found by using it:** the live feed was showing an agent's full answer twice — once in its own styled bubble, once again as a raw, unstyled wall of text in the "handed back" row underneath. Fixed by truncating that row to a short preview/connector instead of repeating the whole paragraph.
5. **An attempted fix that was itself wrong, caught and reverted:** to show *who* an answer was handed back to, I first tried reconstructing it in the frontend by walking the event log like a call stack. That looked right at first but broke on tickets where the Boss delegates to two specialists in the same turn — real concurrent conversations interleave in the log, which a single stack can't untangle, and it started confidently printing things like "Inventory handed its answer back to Inventory." That guess was removed entirely. The actual fix was on the backend (`backend/agents/delegation.py`): each delegation already knows its own caller and target directly, with no ambiguity, so that's now recorded straight into the log and the frontend just displays it — accurate for every run made after that fix, and honestly silent (no name shown) for older runs logged before it existed, rather than guessing.

## Running it

```bash
cd frontend
npm run dev
```

Opens on `http://localhost:5173` (CORS on the backend is scoped to `localhost:5173`–`5177`, not a wildcard, specifically so this pairing works without opening the API to every origin).
