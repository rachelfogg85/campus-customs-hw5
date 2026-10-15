import { useCallback, useEffect, useState } from "react";
import "./App.css";
import { api } from "./lib/api";
import type { Ticket } from "./lib/types";
import { CashTicker } from "./components/CashTicker";
import { TicketQueue } from "./components/TicketQueue";
import { TicketBoard } from "./components/TicketBoard";

function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [resetting, setResetting] = useState(false);

  const refreshTickets = useCallback(async () => {
    const t = await api.getTickets();
    setTickets(t);
    return t;
  }, []);

  const refreshCash = useCallback(async () => {
    const c = await api.getCash();
    setBalance(c.balance);
  }, []);

  useEffect(() => {
    refreshTickets().then((t) => {
      if (t.length > 0) setSelectedId(t[0].id);
    });
    refreshCash();
  }, [refreshTickets, refreshCash]);

  const handleSettled = useCallback(() => {
    refreshTickets();
    refreshCash();
  }, [refreshTickets, refreshCash]);

  const handleReset = useCallback(async () => {
    setResetting(true);
    try {
      await api.resetDatabase();
      await refreshTickets();
      await refreshCash();
    } finally {
      setResetting(false);
    }
  }, [refreshTickets, refreshCash]);

  const selected = tickets.find((t) => t.id === selectedId) ?? null;

  return (
    <div className="desk">
      <header className="desk-header">
        <div className="desk-title">
          <h1>
            Campus Customs <span className="accent">Agent Desk</span>
          </h1>
          <p>Boss, Inventory, Accounting, Facilities &amp; Customer Service — watching live.</p>
        </div>
        <div className="header-right">
          <CashTicker balance={balance} />
          <button className="icon-btn" onClick={handleReset} disabled={resetting}>
            {resetting ? "Resetting…" : "↺ Reset data"}
          </button>
        </div>
      </header>

      <div className="desk-body">
        <TicketQueue tickets={tickets} selectedId={selectedId} onSelect={setSelectedId} />
        {selected ? (
          <TicketBoard key={selected.id} ticket={selected} onSettled={handleSettled} />
        ) : (
          <div className="board-empty">Pick a ticket from the queue to get started.</div>
        )}
      </div>
    </div>
  );
}

export default App;
