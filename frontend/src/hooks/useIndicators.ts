/**
 * TradeAI - Hook: useIndicators (Fase 3)
 * Polling do endpoint /analysis/summary a cada 60 segundos.
 * Retorna indicadores, análise qualitativa, sinal e score V2.
 *
 * Atualiza automaticamente ao trocar símbolo ou timeframe.
 * Fase 4+: adicionar subscrição WebSocket para atualizações em tempo real.
 */

"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import type { AnalysisSummaryResponse } from "@/types";
import { getAnalysisSummary } from "@/lib/api";

const POLL_INTERVAL_MS = 60_000;

export function useIndicators(symbol: string, timeframe: string = "1h") {
  const [data,    setData]    = useState<AnalysisSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);
  const mountedRef = useRef(true);

  const refresh = useCallback(async () => {
    if (!mountedRef.current) return;
    try {
      const result = await getAnalysisSummary(symbol, timeframe);
      if (!mountedRef.current) return;
      if (result) {
        setData(result);
        setError(null);
      } else {
        setError("Indicadores indisponíveis");
      }
    } catch {
      if (mountedRef.current) setError("Falha ao buscar análise");
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [symbol, timeframe]);

  useEffect(() => {
    mountedRef.current = true;
    setLoading(true);
    setData(null);
    refresh();

    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    return () => {
      mountedRef.current = false;
      clearInterval(interval);
    };
  }, [refresh]);

  return { data, loading, error, refresh };
}
