/**
 * TradeAI - Componente: Painel de Status do Sistema
 * Consome a API /system/status e exibe o estado de cada componente.
 * Atualização automática a cada 30 segundos.
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { StatusCard } from "./StatusCard";
import { getSystemStatus } from "@/lib/api";
import type { SystemStatusResponse, StatusLevel } from "@/types";

function toLevel(status: string | null | undefined): StatusLevel {
  if (!status) return "loading";
  if (status === "online" || status === "connected" || status === "healthy")
    return "online";
  if (status === "offline" || status === "disconnected" || status === "unhealthy")
    return "offline";
  return "warning";
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return h > 0
    ? `${h}h ${m}m ${s}s`
    : m > 0
    ? `${m}m ${s}s`
    : `${s}s`;
}

export function SystemStatus() {
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [elapsedUptime, setElapsedUptime] = useState(0);

  const fetchStatus = useCallback(async () => {
    const data = await getSystemStatus();
    setStatus(data);
    setLoading(false);
    setLastUpdate(new Date());
  }, []);

  // Busca inicial e polling a cada 30s
  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30_000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // Contador de uptime local (incrementa a cada segundo)
  useEffect(() => {
    const tick = setInterval(() => setElapsedUptime((v) => v + 1), 1_000);
    return () => clearInterval(tick);
  }, []);

  const backendLevel: StatusLevel = loading
    ? "loading"
    : status
    ? toLevel(status.backend_status)
    : "offline";

  const dbLevel: StatusLevel = loading
    ? "loading"
    : status
    ? toLevel(status.database_status)
    : "offline";

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-[#9ca3af] uppercase tracking-widest">
          Status dos Componentes
        </h2>
        {lastUpdate && (
          <span className="text-xs text-[#6b7280]">
            Atualizado: {lastUpdate.toLocaleTimeString("pt-BR")}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Backend */}
        <StatusCard
          title="Backend API"
          value={loading ? "—" : status ? "Online" : "Offline"}
          subtitle={`v${status?.app_version ?? "—"}`}
          level={backendLevel}
          icon={<ServerIcon />}
        />

        {/* Banco de dados */}
        <StatusCard
          title="Banco de Dados"
          value={loading ? "—" : status?.database_status === "connected" ? "Conectado" : "Desconectado"}
          subtitle="SQLite"
          level={dbLevel}
          icon={<DatabaseIcon />}
        />

        {/* IA — Fase 2 */}
        <StatusCard
          title="Módulo de IA"
          value="Em breve"
          subtitle="Fase 2"
          level="loading"
          icon={<AIIcon />}
        />

        {/* Corretora — Fase 2 */}
        <StatusCard
          title="Corretora"
          value="Em breve"
          subtitle="Fase 2"
          level="loading"
          icon={<BrokerIcon />}
        />
      </div>
    </section>
  );
}

// ── Ícones inline (SVG) ───────────────────────────────────────────────────────

function ServerIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2" y="2" width="20" height="8" rx="2" />
      <rect x="2" y="14" width="20" height="8" rx="2" />
      <line x1="6" y1="6" x2="6.01" y2="6" />
      <line x1="6" y1="18" x2="6.01" y2="18" />
    </svg>
  );
}

function DatabaseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.657-4.03 3-9 3S3 13.657 3 12" />
      <path d="M3 5v14c0 1.657 4.03 3 9 3s9-1.343 9-3V5" />
    </svg>
  );
}

function AIIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M12 2a10 10 0 1 0 10 10" />
      <path d="M12 6v6l4 2" />
      <circle cx="19" cy="5" r="3" />
    </svg>
  );
}

function BrokerIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  );
}
