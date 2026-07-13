"use client";

import { useState } from "react";
import { connectBroker, disconnectBroker, getBrokerStatus } from "@/lib/api";
import type { BrokerStatusResponse, BrokerConnectResponse } from "@/types";

interface BrokerConnectTabProps {
  status: BrokerStatusResponse | null;
  onConnect: (apiKey: string, apiSecret: string, testnet: boolean) => Promise<BrokerConnectResponse | null>;
  onDisconnect: () => Promise<void>;
  connecting: boolean;
  error: string | null;
  success: string | null;
  setError: (e: string | null) => void;
  setSuccess: (s: string | null) => void;
}

export function BrokerConnectTab({
  status,
  onConnect,
  onDisconnect,
  connecting,
  error,
  success,
  setError,
  setSuccess,
}: BrokerConnectTabProps) {
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [testnet, setTestnet] = useState(true);

  function formatNumber(n: number, decimals = 4): string {
    return n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  async function handleConnect() {
    if (!apiKey || !apiSecret) {
      setError("Preencha API Key e Secret");
      return;
    }
    setError(null);
    try {
      const res = await onConnect(apiKey, apiSecret, testnet);
      if (res?.status === "connected") {
        setSuccess("Conectado com sucesso!");
        setApiKey("");
        setApiSecret("");
      } else {
        setError(res?.message || "Falha ao conectar");
      }
    } catch (e: any) {
      setError(e.message || "Erro de conexão");
    }
  }

  async function handleDisconnect() {
    try {
      await onDisconnect();
      setSuccess("Desconectado");
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Connect Form */}
      <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <span className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-400">🔗</span>
          Conexão Binance
        </h2>
        <p className="text-sm text-[#9ca3af] mb-6">
          Insira suas credenciais da API da Binance Futures.
          <strong className="text-amber-400"> Use Testnet para testes.</strong>
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-xs text-[#9ca3af] mb-1">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="Sua API Key"
              className="w-full px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white placeholder-[#4b5563] focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-[#9ca3af] mb-1">API Secret</label>
            <input
              type="password"
              value={apiSecret}
              onChange={e => setApiSecret(e.target.value)}
              placeholder="Sua API Secret"
              className="w-full px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white placeholder-[#4b5563] focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={testnet}
                onChange={e => setTestnet(e.target.checked)}
                className="w-4 h-4 rounded border-[#1f2937] bg-[#0a0e1a] text-blue-500 focus:ring-blue-500"
              />
              <span className="text-sm text-[#d1d5db]">Usar Testnet (recomendado)</span>
            </label>
          </div>
          <button
            onClick={handleConnect}
            disabled={connecting || !apiKey || !apiSecret}
            className="w-full py-3 rounded-lg font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: connecting ? "#374151" : "linear-gradient(135deg, #2563eb, #7c3aed)" }}
          >
            {connecting ? "Conectando..." : "Conectar à Binance"}
          </button>
        </div>

        {status?.connected && (
          <div className="mt-6 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
            <div className="flex items-center gap-2 text-emerald-400 mb-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="font-medium">Conectado</span>
              <span className="px-2 py-0.5 text-xs rounded bg-emerald-500/20">
                {status.testnet ? "TESTNET" : "MAINNET"}
              </span>
            </div>
            <div className="text-sm text-[#9ca3af]">
              Saldo USDT: <span className="font-mono text-white">{status.balance_usdt?.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </div>
          </div>
        )}
      </div>

      {/* Quick Status */}
      <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6">
        <h3 className="text-lg font-bold text-white mb-4">Status Rápido</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0e1a]">
            <span className="text-[#9ca3af]">Modo</span>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              status?.auto_mode ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"
            }`}>
              {status?.auto_mode ? "AUTO (IA decide)" : "MANUAL (você escolhe)"}
            </span>
          </div>
          <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0e1a]">
            <span className="text-[#9ca3af]">Agente Selecionado</span>
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400">
              {status?.selected_agent?.toUpperCase() || "—"}
            </span>
          </div>
          <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0e1a]">
            <span className="text-[#9ca3af]">Rede</span>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              status?.testnet ? "bg-amber-500/20 text-amber-400" : "bg-red-500/20 text-red-400"
            }`}>
              {status?.testnet ? "TESTNET" : "MAINNET"}
            </span>
          </div>
          <div className="flex items-center justify-between p-3 rounded-lg bg-[#0a0e1a]">
            <span className="text-[#9ca3af]">Saldo USDT</span>
            <span className="font-mono text-white">{formatNumber(status?.balance_usdt || 0, 2)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}