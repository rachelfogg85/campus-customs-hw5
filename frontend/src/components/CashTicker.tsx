import { useEffect, useRef, useState } from "react";

export function CashTicker({ balance }: { balance: number | null }) {
  const [bump, setBump] = useState(false);
  const prev = useRef<number | null>(null);

  useEffect(() => {
    if (balance === null) return;
    if (prev.current !== null && prev.current !== balance) {
      setBump(true);
      const t = setTimeout(() => setBump(false), 500);
      return () => clearTimeout(t);
    }
    prev.current = balance;
  }, [balance]);

  useEffect(() => {
    if (balance !== null) prev.current = balance;
  }, [balance]);

  return (
    <div className={`cash-ticker${bump ? " bump" : ""}`}>
      <span className="label">Checking</span>
      <span className="amount">
        {balance === null ? "—" : `$${balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
      </span>
    </div>
  );
}
