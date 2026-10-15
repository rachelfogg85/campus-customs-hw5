# Campus Customs — Multi-Agent Shop

A five-agent team (Boss, Inventory, Accounting, Facilities, Customer Service) that works real customer-service, rent, and pricing tickets for a campus merch shop — built on an MCP server, a FastAPI backend, and a React dashboard. See `output/harness.md` for the full technical writeup (database tables, MCP tools, agents, API routes, the dashboard, and safety rules), `output/design.md` for the dashboard's design rationale, and `AI_prompts.md` for a verbatim log of every prompt used to build this.

## Setup

1. **Python deps** (from `hw5/`):
   ```bash
   pip install -r requirements.txt
   ```
2. **Frontend deps**:
   ```bash
   cd frontend
   npm install
   ```
3. **API key**: copy `.env.example` to `.env` in this folder and fill in a real Portkey key:
   ```bash
   cp .env.example .env
   ```
   Every agent uses `gpt-6-luna` routed through Portkey (hardcoded in `backend/agents/config.py` — nothing else to configure). Without a real key, the dashboard and API routes that only read data (tickets, cash, events) still work; anything that actually runs the agent team needs it.

## The database

- `data/campus_customs.db` — the **original**, untouched reference copy. Never written to.
- `data/campus_customs_new.db` — the **working copy** every tool and route actually reads/writes.

To start from a clean slate (e.g. before a full three-ticket run), copy the original back over the working copy:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

The dashboard's "Reset data" button and the backend's `POST /api/reset` route do exactly this for you — you don't have to run the command by hand unless you want to.

## Running it

You need two things running at once: the backend (which spawns the MCP server itself, on demand, per tool call — you don't need to start it separately) and the frontend.

**1. Start the FastAPI backend** (from `hw5/backend/`):
```bash
cd backend
uvicorn main:app --reload --port 8000
```
Docs at `http://localhost:8000/docs`.

**2. Start the React board** (from `hw5/frontend/`, in a separate terminal):
```bash
cd frontend
npm run dev
```
Opens at `http://localhost:5173`. Pick a ticket, hit "Run agent team," watch the live feed, and approve any payment the team surfaces.

**3. (Optional) Run the MCP server standalone**, e.g. to smoke-test a tool without the agents:
```bash
python3 -m mcp_server.server
```

**4. Reset before a full three-ticket run**, either by clicking "Reset data" on the dashboard, calling the API directly:
```bash
curl -X POST http://localhost:8000/api/reset
```
or by copying the database file as shown above — then run tickets 101, 102, and 103 from the dashboard (or `POST /api/tickets/{id}/run`) in any order.

## Layout

```
hw5/
├── requirements.txt       # Python deps for mcp_server/ + backend/
├── .env.example           # copy to .env and fill in PORTKEY_API_KEY
├── .mcp.json              # MCP server registration (for Claude Code / compatible clients)
├── data/
│   ├── campus_customs.db       # original, read-only
│   └── campus_customs_new.db   # working copy the app uses
├── mcp_server/            # FastMCP server: 13 tools over the shop database
├── backend/               # FastAPI app + the 5-agent PydanticAI team
│   ├── main.py            # API routes
│   ├── models.py          # shared data types
│   ├── agents/            # agent definitions, delegation, tracing, config
│   └── prompts/           # one system prompt per agent
├── frontend/              # React + Vite + TypeScript dashboard
└── output/                # all graded deliverables (see harness.md for the index)
```
