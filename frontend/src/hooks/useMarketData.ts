/**
 * TradeAI - Hook: useMarketData
 * Combina dados REST (polling 30s) para estatísticas de mercado.
 * Os preços em tempo real ficam no hook useWebSocket (WebSocket).
 *
 * Uso:
 *   const { stats, loading, refresh } = useMarketData("BTCUSDT");
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { getMarketStats } from "@/lib/api";
import type { MarketStatsResponse } from "@/types";

const POLL_INTERVAL_MS = 30_000;

export function useMarketData(symbol: string) {
  const [stats,   setStats]   = useState<MarketStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await getMarketStats(symbol);
      setStats(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    setLoading(true);
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refresh]);

  return { stats, loading, error, refresh };
}
