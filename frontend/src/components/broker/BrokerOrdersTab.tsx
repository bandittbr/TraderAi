"use client";

import React from "react";
import { useState } from "react";

interface BrokerOrdersTabProps {
  openOrders: any[];
  onRefresh: () => Promise<void>;
}

export default function BrokerOrdersTab({ openOrders, onRefresh }: BrokerOrdersTabProps) {
  const [cancellingOrder, setCancellingOrder] = useState<string | null>(null);

  function formatNumber(n: number, decimals = 4): string {
    return n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  async function handleCancelOrder(order: any) {
    try {
      await fetch(`/api/v1/broker/order/${order.symbol}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ order_id: parseInt(order.order_id) }),
      });
      alert("Ordem cancelada");
    } catch (e: any) {
      alert(e.message);
    }
  }

  async function handleCancelAll(symbol: string) {
    if (!confirm(`Cancelar TODAS as ordens de ${symbol}?`)) return;
    try {
      await fetch(`/api/v1/broker/orders/${symbol}`, { method: "DELETE" });
      alert("Todas as ordens canceladas");
    } catch (e: any) {
      alert(e.message);
    }
  }

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden">
      <div className="p-4 border-b border-[#1f2937] flex items-center justify-between">
        <h3 className="text-lg font-bold text-white">Ordens Abertas</h3>
        <span className="px-3 py-1 text-xs font-medium bg-blue-500/20 text-blue-400 rounded-full">
          {openOrders.length}
        </span>
      </div>
      {openOrders.length === 0 ? (
        <div className="p-12 text-center text-[#4b5563]">
          <div className="text-4xl mb-2">📋</div>
          <p>Nenhuma ordem aberta</p>
        </div>
       ) : (
        <>
         <div className="overflow-x-auto">
           <table className="w-full">
             <thead>
               <tr className="text-left text-xs text-[#4b5563] border-b border-[#1f2937]">
                 <th className="p-3">Símbolo</th>
                 <th className="p-3">Lado</th>
                 <th className="p-3">Tipo</th>
                 <th className="p-3">Qtd</th>
                 <th className="p-3">Preço</th>
                 <th className="p-3">Status</th>
                 <th className="p-3">Preenchido</th>
                 <th className="p-3">Ações</th>
               </tr>
             </thead>
             <tbody>
               {openOrders.map((order) => (
                 <tr key={order.order_id} className="border-b border-[#1f2937] hover:bg-[#0a0e1a]">
                   <td className="p-3 font-mono text-white">{order.symbol}</td>
                   <td className="p-3">
                     <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                       order.side === "BUY" ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"
                     }`}>
                       {order.side}
                     </span>
                   </td>
                   <td className="p-3 text-[#9ca3af]">{order.type}</td>
                   <td className="p-3 font-mono text-white">{order.quantity.toLocaleString("en-US", { minimumFractionDigits: 6, maximumFractionDigits: 6 })}</td>
                   <td className="p-3 font-mono text-[#9ca3af]">${order.price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                   <td className="p-3">
                     <span className={`px-2 py-0.5 rounded text-xs ${
                       order.status === "NEW" ? "bg-blue-500/20 text-blue-400" :
                       order.status === "PARTIALLY_FILLED" ? "bg-amber-500/20 text-amber-400" :
                       "bg-[#1f2937] text-[#9ca3af]"
                     }`}>
                       {order.status}
                     </span>
                   </td>
                   <td className="p-3 font-mono text-[#9ca3af]">{order.filled_qty.toLocaleString("en-US", { minimumFractionDigits: 6, maximumFractionDigits: 6 })}</td>
                   <td className="p-3">
                     <button
                       onClick={() => handleCancelOrder(order)}
                       className="px-3 py-1 text-xs rounded bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors"
                     >
                       Cancelar
                     </button>
                   </td>
                 </tr>
               ))}
             </tbody>
           </table>
         </div>
         {openOrders.length > 0 && (
           <div className="p-4 border-t border-[#1f2937]">
             <button
               onClick={() => handleCancelAll(openOrders[0].symbol)}
               className="w-full py-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors font-medium"
             >
               Cancelar Todas as Ordens de {openOrders[0].symbol}
             </button>
           </div>
         )}
        </>
       )}
  </div>
  );
}
