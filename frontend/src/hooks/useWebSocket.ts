/**
 * TradeAI - Hook: useWebSocket
 * Mantém uma conexão WebSocket persistente com o backend.
 * Reconecta automaticamente em caso de falha ou perda de conexão.
 *
 * Retorna:
 *   prices    → mapa { BTCUSDT: WsPriceUpdate, ETHUSDT: ..., ... }
 *   trades    → array de TradeActivity (últimas atividades dos agentes)
 *   connected → estado da conexão
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { WsPriceUpdate, PriceMap } from "@/types";

// ── Types ────────────────────────────────────────────────────────────────────

export interface TradeActivity {
  type: "trade_activity";
  agent: string;
  event: string;
  symbol: string;
  trade_id: number | null;
  price: number;
  quantity: number | null;
  side: string | null;
  pnl: number | null;
  pnl_pct: number | null;
  reason: string | null;
  confidence: number | null;
  regime: string | null;
  balance_after: number | null;
  timestamp: number | null;
}

// URL direta ao backend — WebSocket não passa pelo proxy Next.js
const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://127.0.0.1:8000/api/v1/ws/market";

const RECONNECT_DELAY_MS = 5_000;
const MAX_TRADE_HISTORY = 50;

export function useWebSocket() {
  const [prices, setPrices]       = useState<PriceMap>({});
  const [trades, setTrades]       = useState<TradeActivity[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef                     = useRef<WebSocket | null>(null);
  const reconnectRef              = useRef<ReturnType<typeof setTimeout>>();
  const mountedRef                = useRef(true);

  const connect = useCallback(() => {
    // Não reconecta se o componente foi desmontado ou já conectado
    if (!mountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setConnected(true);
    };

    ws.onmessage = (event: MessageEvent) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(event.data as string);
        
        if (data.type === "price_update" && data.symbol) {
          setPrices(prev => ({ ...prev, [data.symbol]: data }));
        } else if (data.type === "trade_activity") {
          setTrades(prev => {
            const next = [data as TradeActivity, ...prev];
            return next.slice(0, MAX_TRADE_HISTORY);
          });
        }
      } catch {
        // Mensagem malformada — ignorar silenciosamente
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setConnected(false);
      // Agenda reconexão automática
      reconnectRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
    };

    ws.onerror = () => {
      // onerror sempre é seguido de onclose — a reconexão é feita lá
      ws.close();
    };
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { prices, trades, connected };
}
