"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";

type Quote = { sym: string; val: string; chg: string; up: boolean };

// Backend əlçatmaz olarsa göstəriləcək fallback (canlı data gələnə qədər).
const FALLBACK: Quote[] = [
  { sym: "EUR/USD", val: "1.0842", chg: "+0.18%", up: true },
  { sym: "BTC/USD", val: "67,420", chg: "+2.41%", up: true },
  { sym: "DXY", val: "104.32", chg: "-0.22%", up: false },
  { sym: "S&P 500", val: "5,431", chg: "+0.54%", up: true },
  { sym: "NASDAQ", val: "17,210", chg: "+0.77%", up: true },
  { sym: "ETH/USD", val: "3,512", chg: "-1.05%", up: false },
  { sym: "GBP/USD", val: "1.2710", chg: "+0.09%", up: true },
  { sym: "GOLD", val: "2,318", chg: "-0.31%", up: false },
];

const REFRESH_MS = 60_000;

function Row({ quotes }: { quotes: Quote[] }) {
  return (
    <div className="flex shrink-0 items-center">
      {quotes.map((q) => (
        <span
          key={q.sym}
          className="flex items-center gap-2 whitespace-nowrap px-5 text-xs"
        >
          <span className="font-mono font-medium text-text">{q.sym}</span>
          <span className="tabular text-text">{q.val}</span>
          <span className={q.up ? "tabular text-up" : "tabular text-down"}>
            {q.chg}
          </span>
        </span>
      ))}
    </div>
  );
}

/** Canlı bazar lenti. Real qiymətləri backend-dən çəkir (60s-də yenilənir). */
export function Ticker({ compact = false }: { compact?: boolean }) {
  const [quotes, setQuotes] = useState<Quote[]>(FALLBACK);

  useEffect(() => {
    let alive = true;
    const fetchQuotes = async () => {
      try {
        const data = await apiGet<Quote[]>("/market/ticker");
        if (alive && data.length) setQuotes(data);
      } catch {
        /* fallback qalır */
      }
    };
    fetchQuotes();
    const id = setInterval(fetchQuotes, REFRESH_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  if (compact) {
    return (
      <div className="relative w-full overflow-hidden rounded-full border border-border bg-surface/80 py-2 backdrop-blur">
        <div className="ticker-track flex w-max">
          <Row quotes={quotes} />
          <Row quotes={quotes} />
        </div>
        <div className="pointer-events-none absolute inset-y-0 left-0 w-10 rounded-l-full bg-gradient-to-r from-surface to-transparent" />
        <div className="pointer-events-none absolute inset-y-0 right-0 w-10 rounded-r-full bg-gradient-to-l from-surface to-transparent" />
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden border-y border-border bg-surface/60">
      <div className="ticker-track flex w-max">
        <Row quotes={quotes} />
        <Row quotes={quotes} />
      </div>
      <div className="pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-bg to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-bg to-transparent" />
    </div>
  );
}
