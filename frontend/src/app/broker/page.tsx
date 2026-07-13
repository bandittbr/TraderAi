"use client";

import { useEffect, useState } from "react";
import {
  connectBroker,
  disconnectBroker,
  getBrokerStatus,
  getBrokerBalance,
  getBrokerPositions,
  placeBrokerOrder,
  cancelBrokerOrder,
  cancelAllBrokerOrders,
  getBrokerOpenOrders,
  setBrokerLeverage,
  setBrokerMarginType,
  getBrokerTicker,
} from "@/lib/api";
import type { BrokerStatusResponse, BrokerPosition, BrokerOrderResponse, BrokerConnectResponse, OrderSide, OrderType, PositionSide } from "@/types";
import { BrokerConnectTab } from "@/components/broker/BrokerConnectTab";
import { BrokerTradeTab } from "@/components/broker/BrokerTradeTab";
import BrokerPositionsTab from "@/components/broker/BrokerPositionsTab";
import BrokerOrdersTab from "@/components/broker/BrokerOrdersTab";
import BrokerAccountTab from "@/components/broker/BrokerAccountTab";

const SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "LINKUSDT"];

export default function BrokerPage() {
  const [status, setStatus] = useState<BrokerStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Trade tab state
  const [orderSymbol, setOrderSymbol] = useState("BTCUSDT");
  const [orderSide, setOrderSide] = useState<OrderSide>("BUY");
  const [orderType, setOrderType] = useState<OrderType>("MARKET");
  const [orderQty, setOrderQty] = useState("");
  const [orderPrice, setOrderPrice] = useState("");
  const [orderStopPrice, setOrderStopPrice] = useState("");
  const [orderPositionSide, setOrderPositionSide] = useState<PositionSide>("BOTH");
  const [orderReduceOnly, setOrderReduceOnly] = useState(false);
  const [placingOrder, setPlacingOrder] = useState(false);

  // Leverage/Margin
  const [levSymbol, setLevSymbol] = useState("BTCUSDT");
  const [levValue, setLevValue] = useState(10);
  const [marginSymbol, setMarginSymbol] = useState("BTCUSDT");
  const [marginType, setMarginType] = useState("ISOLATED");

  // Data
  const [positions, setPositions] = useState<any[]>([]);
  const [openOrders, setOpenOrders] = useState<any[]>([]);
  const [balances, setBalances] = useState<any[]>([]);
  const [ticker, setTicker] = useState<any>(null);

  // Tabs
  const [activeTab, setActiveTab] = useState<"connect" | "trade" | "positions" | "orders" | "account">("connect");

  // Helpers
  function formatNumber(n: number, decimals = 4): string {
    return n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  function pnlColor(pnl: number): string {
    return pnl >= 0 ? "text-emerald-400" : "text-red-400";
  }

  // Load status on mount
  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 10_000);
    return () => clearInterval(interval);
  }, []);

  async function loadStatus() {
    try {
      const data = await getBrokerStatus();
      if (data) {
        setStatus(data);
        if (data.connected) {
          await loadData();
        }
      }
    } catch (e) {
      console.error("[Broker] loadStatus error:", e);
    } finally {
      setLoading(false);
    }
  }

  async function loadData() {
    try {
      const [pos, ord, bal, tk] = await Promise.all([
        getBrokerPositions(),
        getBrokerOpenOrders(),
        getBrokerBalance(),
        getBrokerTicker("BTCUSDT"),
      ]);
      if (pos) setPositions(pos.positions);
      if (ord) setOpenOrders(ord.orders);
      if (bal) setBalances(bal.balances.filter((b: any) => b.total > 0).sort((a: any, b: any) => b.total - a.total));
      if (tk) setTicker(tk);
    } catch (e) {
      console.error("[Broker] loadData error:", e);
    }
  }

  async function handleConnect(apiKey: string, apiSecret: string, testnet: boolean): Promise<BrokerConnectResponse | null> {
    if (!apiKey || !apiSecret) {
      setError("Preencha API Key e Secret");
      return null;
    }
    setConnecting(true);
    setError(null);
    try {
      const res = await connectBroker(apiKey, apiSecret, testnet);
      if (res?.status === "connected") {
        setSuccess("Conectado com sucesso!");
        setError(null);
        await loadStatus();
      } else {
        setError(res?.message || "Falha ao conectar");
      }
      return res;
    } catch (e: any) {
      setError(e.message || "Erro de conexão");
      return null;
    } finally {
      setConnecting(false);
    }
  }

  async function handleDisconnect() {
    try {
      await disconnectBroker();
      setSuccess("Desconectado");
      await loadStatus();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleAutoMode(enabled: boolean) {
    try {
      await fetch("/api/v1/broker/auto-mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      setSuccess(enabled ? "Modo AUTO ativado" : "Modo AUTO desativado");
      await loadStatus();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleSelectAgent(agent: string) {
    try {
      await fetch("/api/v1/broker/select-agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent }),
      });
      setSuccess(`Agente ${agent.toUpperCase()} selecionado`);
      await loadStatus();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handlePlaceOrder(): Promise<{ status: string; order: BrokerOrderResponse } | null> {
    if (!orderQty) {
      setError("Informe a quantidade");
      return null;
    }
    if (orderType !== "MARKET" && !orderPrice) {
      setError("Preço obrigatório para ordens LIMIT/STOP");
      return null;
    }
    if (orderType === "STOP_MARKET" && !orderStopPrice) {
      setError("Stop price obrigatório para STOP_MARKET");
      return null;
    }

    setPlacingOrder(true);
    setError(null);
    try {
      const res = await placeBrokerOrder({
        symbol: orderSymbol,
        side: orderSide,
        order_type: orderType,
        quantity: parseFloat(orderQty),
        price: orderPrice ? parseFloat(orderPrice) : undefined,
        stop_price: orderStopPrice ? parseFloat(orderStopPrice) : undefined,
        position_side: orderPositionSide,
        reduce_only: orderReduceOnly,
      });
      if (res?.status === "success") {
        setSuccess(`Ordem ${res.order.order_id} enviada!`);
        setOrderQty("");
        setOrderPrice("");
        setOrderStopPrice("");
        await loadData();
      } else {
        setError("Falha ao enviar ordem");
      }
      return res;
    } catch (e: any) {
      setError(e.message || "Erro ao enviar ordem");
      return null;
    } finally {
      setPlacingOrder(false);
    }
  }

  async function handleCancelOrder(order: any) {
    try {
      await cancelBrokerOrder(order.symbol, parseInt(order.order_id));
      setSuccess("Ordem cancelada");
      await loadData();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleCancelAll(symbol: string) {
    try {
      await cancelAllBrokerOrders(symbol);
      setSuccess("Todas ordens canceladas");
      await loadData();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleSetLeverage() {
    try {
      await setBrokerLeverage(levSymbol, levValue);
      setSuccess(`Alavancagem ${levSymbol} = ${levValue}x`);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleSetMarginType() {
    try {
      await setBrokerMarginType(marginSymbol, marginType);
      setSuccess(`Margem ${marginSymbol} = ${marginType}`);
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-[#9ca3af]">Carregando módulo Corretora...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0e1a]">
      {/* Header */}
      <header className="border-b border-[#1f2937] bg-[#111827]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-screen-xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                <rect x="2" y="5" width="20" height="14" rx="2" />
                <path d="M6 12h12M10 5v7M14 5v7" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Corretora</h1>
              <p className="text-xs text-[#9ca3af]">Binance Futures · Trading Real</p>
            </div>
          </div>

          {status?.connected && (
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                status.auto_mode ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"
              }`}>
                {status.auto_mode ? "AUTO" : "MANUAL"}
              </span>
              {status.selected_agent && (
                <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400">
                  {status.selected_agent.toUpperCase()}
                </span>
              )}
              <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#1f2937] text-[#9ca3af]">
                {status.testnet ? "TESTNET" : "MAINNET"}
              </span>
              <button
                onClick={handleDisconnect}
                className="px-4 py-2 text-sm font-medium text-red-400 hover:text-red-300 border border-red-500/30 rounded-lg transition-colors"
              >
                Desconectar
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Tabs */}
      <nav className="border-b border-[#1f2937] bg-[#111827] sticky top-16 z-40">
        <div className="max-w-screen-xl mx-auto px-6">
          <div className="flex gap-1 overflow-x-auto pb-1">
            {[
              { id: "connect", label: "Conectar", icon: "🔗" },
              { id: "trade", label: "Operar", icon: "📈" },
              { id: "positions", label: "Posições", icon: "📊" },
              { id: "orders", label: "Ordens", icon: "📋" },
              { id: "account", label: "Conta", icon: "💰" },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  activeTab === tab.id
                    ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    : "text-[#9ca3af] hover:text-white hover:bg-[#1f2937]"
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-screen-xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-300">✕</button>
          </div>
        )}
        {success && (
          <div className="mb-6 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm flex items-center justify-between">
            <span>{success}</span>
            <button onClick={() => setSuccess(null)} className="text-emerald-500 hover:text-emerald-300">✕</button>
          </div>
        )}

        {/* CONNECT TAB */}
        {activeTab === "connect" && (
          <BrokerConnectTab
            status={status}
            onConnect={handleConnect}
            onDisconnect={handleDisconnect}
            connecting={connecting}
            error={error}
            success={success}
            setError={setError}
            setSuccess={setSuccess}
          />
        )}

        {/* TRADE TAB */}
        {activeTab === "trade" && status?.connected && (
          <BrokerTradeTab
            status={status}
            positions={positions}
            openOrders={openOrders}
            ticker={ticker}
            onPlaceOrder={async (order) => {
              const res = await handlePlaceOrder();
              await loadData();
              return res;
            }}
            onCancelOrder={async (order) => {
              await handleCancelOrder(order);
              await loadData();
            }}
            onCancelAll={async (symbol) => {
              await handleCancelAll(symbol);
              await loadData();
            }}
            onSetLeverage={async (symbol, leverage) => {
              await handleSetLeverage();
              await loadData();
            }}
            onSetMarginType={async (symbol, marginType) => {
              await handleSetMarginType();
              await loadData();
            }}
            placingOrder={placingOrder}
            error={error}
            success={success}
            setError={setError}
            setSuccess={setSuccess}
          />
        )}

        {/* POSITIONS TAB */}
        {activeTab === "positions" && status?.connected && (
          <BrokerPositionsTab
            positions={positions}
            onRefresh={loadData}
          />
        )}

        {/* ORDERS TAB */}
        {activeTab === "orders" && status?.connected && (
          <BrokerOrdersTab
            openOrders={openOrders}
            onRefresh={loadData}
          />
        )}

        {/* ACCOUNT TAB */}
        {activeTab === "account" && status?.connected && (
          <BrokerAccountTab
            status={status}
            onRefresh={loadData}
          />
        )}

        {/* NOT CONNECTED */}
        {activeTab !== "connect" && !status?.connected && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">🔗</div>
            <h3 className="text-xl font-bold text-white mb-2">Não conectado</h3>
            <p className="text-[#9ca3af] mb-6">Vá na aba "Conectar" e insira suas credenciais da Binance</p>
            <button
              onClick={() => setActiveTab("connect")}
              className="px-6 py-3 rounded-lg bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30 transition-colors font-medium"
            >
              Ir para Conectar
            </button>
          </div>
        )}
      </main>
    </div>
  );
}