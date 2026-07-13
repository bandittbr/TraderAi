"use client";

import { useState } from "react";
import {
  placeBrokerOrder,
  cancelBrokerOrder,
  cancelAllBrokerOrders,
  getBrokerOpenOrders,
  setBrokerLeverage,
  setBrokerMarginType,
  getBrokerTicker,
} from "@/lib/api";
import type { BrokerPosition, BrokerOrderResponse, BrokerOrderRequest, OrderSide, OrderType, PositionSide } from "@/types";

interface BrokerTradeTabProps {
  status: any;
  positions: BrokerPosition[];
  openOrders: BrokerOrderResponse[];
  ticker: any;
  onPlaceOrder: (order: BrokerOrderRequest) => Promise<{ status: string; order: BrokerOrderResponse } | null>;
  onCancelOrder: (order: BrokerOrderResponse) => Promise<void>;
  onCancelAll: (symbol: string) => Promise<void>;
  onSetLeverage: (symbol: string, leverage: number) => Promise<void>;
  onSetMarginType: (symbol: string, marginType: string) => Promise<void>;
  placingOrder: boolean;
  error: string | null;
  success: string | null;
  setError: (e: string | null) => void;
  setSuccess: (s: string | null) => void;
}

const SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "LINKUSDT"];

export function BrokerTradeTab({
  status,
  positions,
  openOrders,
  ticker,
  onPlaceOrder,
  onCancelOrder,
  onCancelAll,
  onSetLeverage,
  onSetMarginType,
  placingOrder,
  error,
  success,
  setError,
  setSuccess,
}: BrokerTradeTabProps) {
  const [orderSymbol, setOrderSymbol] = useState("BTCUSDT");
  const [orderSide, setOrderSide] = useState<OrderSide>("BUY");
  const [orderType, setOrderType] = useState<OrderType>("MARKET");
  const [orderQty, setOrderQty] = useState("");
  const [orderPrice, setOrderPrice] = useState("");
  const [orderStopPrice, setOrderStopPrice] = useState("");
  const [orderPositionSide, setOrderPositionSide] = useState<PositionSide>("BOTH");
  const [orderReduceOnly, setOrderReduceOnly] = useState(false);
  const [levSymbol, setLevSymbol] = useState("BTCUSDT");
  const [levValue, setLevValue] = useState(10);
  const [marginSymbol, setMarginSymbol] = useState("BTCUSDT");
  const [marginType, setMarginType] = useState("ISOLATED");

  function formatNumber(n: number, decimals = 4): string {
    return n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  function pnlColor(pnl: number): string {
    return pnl >= 0 ? "text-emerald-400" : "text-red-400";
  }

  async function handlePlaceOrder() {
    if (!orderQty) {
      setError("Informe a quantidade");
      return;
    }
    if (orderType !== "MARKET" && !orderPrice) {
      setError("Preço obrigatório para ordens LIMIT/STOP");
      return;
    }
    if (orderType === "STOP_MARKET" && !orderStopPrice) {
      setError("Stop price obrigatório para STOP_MARKET");
      return;
    }

    setError(null);
    try {
      const res = await onPlaceOrder({
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
      } else {
        setError("Falha ao enviar ordem");
      }
    } catch (e: any) {
      setError(e.message || "Erro ao enviar ordem");
    }
  }

  async function handleCancelOrder(order: BrokerOrderResponse) {
    try {
      await onCancelOrder(order);
      setSuccess("Ordem cancelada");
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleCancelAll(symbol: string) {
    try {
      await onCancelAll(symbol);
      setSuccess("Todas ordens canceladas");
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleSetLeverage() {
    try {
      await onSetLeverage(levSymbol, levValue);
      setSuccess(`Alavancagem ${levSymbol} = ${levValue}x`);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleSetMarginType() {
    try {
      await onSetMarginType(marginSymbol, marginType);
      setSuccess(`Margem ${marginSymbol} = ${marginType}`);
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Order Form */}
      <div className="lg:col-span-2 space-y-6">
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <span className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center text-amber-400">📈</span>
            Nova Ordem
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-[#9ca3af] mb-1">Símbolo</label>
              <select
                value={orderSymbol}
                onChange={e => setOrderSymbol(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#9ca3af] mb-1">Lado</label>
              <select
                value={orderSide}
                onChange={e => setOrderSide(e.target.value as OrderSide)}
                className="w-full px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="BUY">COMPRAR (LONG)</option>
                <option value="SELL">VENDER (SHORT)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#9ca3af] mb-1">Tipo</label>
              <select
                value={orderType}
                onChange={e => setOrderType(e.target.value as OrderType)}
                className="w-full px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="MARKET">MARKET (a mercado)</option>
                <option value="LIMIT">LIMIT (preço limite)</option>
                <option value="STOP_MARKET">STOP MARKET (stop loss)</option>
                <option value="TAKE_PROFIT_MARKET">TAKE PROFIT MARKET</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#9ca3af] mb-1">Posição</label>
              <select
                value={orderPositionSide}
                onChange={e => setOrderPositionSide(e.target.value as PositionSide)}
                className="w-full px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="BOTH">BOTH (hedge mode off)</option>
                <option value="LONG">LONG</option>
                <option value="SHORT">SHORT</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#9ca3af] mb-1">Quantidade</label>
              <input
                type="number"
                step="0.001"
                value={orderQty}
                onChange={e => setOrderQty(e.target.value)}
                placeholder="Ex: 0.001"
                className="w-full px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white placeholder-[#4b5563] focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-[#9ca3af] mb-1">Preço (LIMIT/STOP)</label>
              <input
                type="number"
                step="0.01"
                value={orderPrice}
                onChange={e => setOrderPrice(e.target.value)}
placeholder="Preço limite"
                      className="w-full px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white placeholder-[#4b5563] focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
            </div>
            <div>
              <label className="block text-xs text-[#9ca3af] mb-1">Stop Price (STOP_MARKET)</label>
              <input
                type="number"
                step="0.01"
                value={orderStopPrice}
                onChange={e => setOrderStopPrice(e.target.value)}
                placeholder="Preço de disparo"
                className="w-full px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white placeholder-[#4b5563] focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={orderReduceOnly}
                  onChange={e => setOrderReduceOnly(e.target.checked)}
                  className="w-4 h-4 rounded border-[#1f2937] bg-[#0a0e1a] text-blue-500 focus:ring-blue-500"
                />
                <span className="text-sm text-[#d1d5db]">Reduce Only (apenas fechar)</span>
              </label>
            </div>
          </div>

          <button
            onClick={handlePlaceOrder}
            disabled={placingOrder}
            className="w-full py-3 rounded-lg font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: "linear-gradient(135deg, #f59e0b, #d97706)" }}
          >
            {placingOrder ? "Enviando..." : orderSide === "BUY" ? "COMPRAR (LONG)" : "VENDER (SHORT)"}
          </button>
        </div>

        {/* Quick Actions */}
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6">
          <h4 className="text-sm font-bold text-white mb-4">Ações Rápidas</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <button
              onClick={() => { setOrderSide("BUY"); setOrderType("MARKET"); setOrderPositionSide("BOTH"); }}
              className="px-4 py-2 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors text-sm font-medium"
            >
              Market Long
            </button>
            <button
              onClick={() => { setOrderSide("SELL"); setOrderType("MARKET"); setOrderPositionSide("BOTH"); }}
              className="px-4 py-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors text-sm font-medium"
            >
              Market Short
            </button>
            <button
              onClick={() => { setOrderType("STOP_MARKET"); }}
              className="px-4 py-2 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 transition-colors text-sm font-medium"
            >
              Stop Loss
            </button>
            <button
              onClick={() => { setOrderType("TAKE_PROFIT_MARKET"); }}
              className="px-4 py-2 rounded-lg bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30 transition-colors text-sm font-medium"
            >
              Take Profit
            </button>
          </div>
        </div>
      </div>

      {/* Market Info */}
      <div className="space-y-6">
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <span className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-400">📊</span>
            Mercado - {orderSymbol}
          </h3>
          {ticker && (
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-[#0a0e1a]">
                <div className="text-xs text-[#9ca3af]">Preço Atual</div>
                <div className="text-2xl font-bold font-mono text-white">${ticker.price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
              </div>
              <div className="p-4 rounded-lg bg-[#0a0e1a]">
                <div className="text-xs text-[#9ca3af]">24h Change</div>
                <div className={`text-2xl font-bold font-mono ${ticker.change_24h >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {ticker.change_24h >= 0 ? "+" : ""}{ticker.change_24h.toFixed(2)}%
                </div>
              </div>
              <div className="p-4 rounded-lg bg-[#0a0e1a]">
                <div className="text-xs text-[#9ca3af]">Volume 24h</div>
                <div className="text-xl font-bold font-mono text-white">${formatNumber(ticker.volume_24h / 1e6, 1)}M</div>
              </div>
              <div className="p-4 rounded-lg bg-[#0a0e1a]">
                <div className="text-xs text-[#9ca3af]">High / Low 24h</div>
                <div className="text-sm font-mono text-white">${formatNumber(ticker.high_24h, 2)} / ${formatNumber(ticker.low_24h, 2)}</div>
              </div>
            </div>
          )}
        </div>

        {/* Leverage / Margin */}
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6">
          <h4 className="text-sm font-bold text-white mb-4">Alavancagem & Margem</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-[#9ca3af] mb-1">Símbolo</label>
              <select
                value={levSymbol}
                onChange={e => setLevSymbol(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex gap-2">
              <input
                type="number"
                min="1"
                max="125"
                value={levValue}
                onChange={e => setLevValue(parseInt(e.target.value) || 1)}
                className="flex-1 px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <button
                onClick={async () => {
                  try {
                    await fetch(`/api/v1/broker/leverage`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ symbol: levSymbol, leverage: levValue }),
                    });
                    setSuccess(`Alavancagem ${levSymbol} = ${levValue}x`);
                  } catch (e: any) {
                    setError(e.message);
                  }
                }}
                className="px-4 py-2.5 rounded-lg bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30 transition-colors font-medium"
              >
                Definir
              </button>
            </div>
            <div>
              <label className="block text-xs text-[#9ca3af] mb-1">Símbolo</label>
              <select
                value={marginSymbol}
                onChange={e => setMarginSymbol(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex gap-2">
              <select
                value={marginType}
                onChange={e => setMarginType(e.target.value)}
                className="flex-1 px-4 py-2.5 rounded-lg bg-[#0a0e1a] border border-[#1f2937] text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="ISOLATED">ISOLATED</option>
                <option value="CROSSED">CROSSED</option>
              </select>
              <button
                onClick={async () => {
                  try {
                    await fetch(`/api/v1/broker/margin-type`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ symbol: marginSymbol, margin_type: marginType }),
                    });
                    setSuccess(`Margem ${marginSymbol} = ${marginType}`);
                  } catch (e: any) {
                    setError(e.message);
                  }
                }}
                className="px-4 py-2.5 rounded-lg bg-purple-500/20 text-purple-400 border border-purple-500/30 hover:bg-purple-500/30 transition-colors font-medium"
              >
                Definir
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}