"use client";

import { motion } from "framer-motion";

const analysisItems = [
  { label: "EMA alinhadas", status: "pass" as const, detail: "9 > 21 > 50 > 200" },
  { label: "RSI saudável", status: "pass" as const, detail: "54.2 (neutro)" },
  { label: "MACD positivo", status: "pass" as const, detail: "Linha > Sinal" },
  { label: "Volume aumentando", status: "warn" as const, detail: "+12% vs média" },
  { label: "Suporte testado", status: "pass" as const, detail: "$64.200 hold" },
  { label: "Resistência próxima", status: "warn" as const, detail: "$65.800" },
];

export default function AIInsights() {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="rounded-xl p-4"
      style={{ background: "#080c14", border: "1px solid #1a2540" }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xs">
          🧠
        </div>
        <div>
          <div className="text-[11px] font-bold text-white">AI Market Analyst</div>
          <div className="text-[8px] text-[#2d4060] uppercase tracking-wider">Análise em tempo real</div>
        </div>
        <div className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[9px] text-emerald-400 font-mono">LIVE</span>
        </div>
      </div>

      {/* Market Status */}
      <div className="flex items-center justify-between p-3 rounded-lg mb-3" style={{ background: "#050816", border: "1px solid #1a2540" }}>
        <div>
          <div className="text-[9px] text-[#2d4060] uppercase tracking-wider">Mercado</div>
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-bold text-emerald-400">ALTISTA</span>
            <span className="text-sm">🚀</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[9px] text-[#2d4060] uppercase tracking-wider">Confiança</div>
          <div className="text-lg font-bold font-mono text-emerald-400">92%</div>
        </div>
      </div>

      {/* Analysis items */}
      <div className="space-y-1.5 mb-3">
        {analysisItems.map((item, i) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 + i * 0.05 }}
            className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-[#0a0e1a40] transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className={item.status === "pass" ? "text-emerald-400" : "text-amber-400"}>
                {item.status === "pass" ? "✓" : "⚠"}
              </span>
              <span className="text-[11px] text-[#8aa4c8]">{item.label}</span>
            </div>
            <span className="text-[9px] font-mono text-[#3d5a80]">{item.detail}</span>
          </motion.div>
        ))}
      </div>

      {/* Support / Resistance */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2.5 rounded-lg" style={{ background: "#050816", border: "1px solid #1a2540" }}>
          <div className="text-[9px] text-[#2d4060] uppercase tracking-wider">Suporte</div>
          <div className="text-sm font-bold font-mono text-emerald-400">$64,200</div>
        </div>
        <div className="p-2.5 rounded-lg" style={{ background: "#050816", border: "1px solid #1a2540" }}>
          <div className="text-[9px] text-[#2d4060] uppercase tracking-wider">Resistência</div>
          <div className="text-sm font-bold font-mono text-red-400">$65,800</div>
        </div>
      </div>

      {/* Key levels */}
      <div className="mt-3 pt-3 border-t border-[#1a2540]">
        <div className="text-[9px] text-[#2d4060] uppercase tracking-wider mb-2">Níveis-chave</div>
        <div className="space-y-1">
          {[
            { label: "TP1", price: 66200, color: "text-emerald-400" },
            { label: "TP2", price: 68100, color: "text-emerald-400" },
            { label: "SL",  price: 63900, color: "text-red-400" },
          ].map(lv => (
            <div key={lv.label} className="flex items-center justify-between text-[10px]">
              <span className="text-[#2d4060] font-mono">{lv.label}</span>
              <span className={`font-mono font-bold ${lv.color}`}>${lv.price.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
