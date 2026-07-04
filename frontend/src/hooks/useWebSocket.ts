/**
 * TradeAI - Hook: useWebSocket
 * Mantém uma conexão WebSocket persistente com o backend.
 * Reconecta automaticamente em caso de falha ou perda de conexão.
 *
 * Retorna:
 *   prices    → mapa { BTCUSDT: WsPriceUpdate, ETHUSDT: ..., ... }
 *   connected → estado da conexão
 *
 * Fase 3+: adicionar suporte a canais por símbolo, autenticação JWT.
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { WsPriceUpdate, PriceMap } from "@/types";

// URL direta ao backend — WebSocket não passa pelo proxy Next.js
const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://127.0.0.1:8000/api/v1/ws/market";

const RECONNECT_DELAY_MS = 5_000;

export function useWebSocket() {
  const [prices, setPrices]       = useState<PriceMap>({});
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
        const data = JSON.parse(event.data as string) as WsPriceUpdate;
        if (data.type === "price_update" && data.symbol) {
          setPrices(prev => ({ ...prev, [data.symbol]: data }));
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

  return { prices, connected };
}
