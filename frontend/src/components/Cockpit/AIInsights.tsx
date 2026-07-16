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
      style={{ background: "#0a0f1e", border: "1px solid #1a2a4a" }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-neon-blue to-neon-purple flex items-center justify-center text-xs">🧠</div>
        <div>
          <div className="text-[11px] font-bold text-text-primary">AI Market Analyst</div>
          <div className="text-[8px] text-text-dim uppercase tracking-wider">Análise em tempo real</div>
        </div>
        <div className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded-full" style={{ background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.2)" }}>
          <span className="w-1.5 h-1.5 rounded-full bg-neon-green animate-pulse" />
          <span className="text-[9px] text-neon-green font-mono">LIVE</span>
        </div>
      </div>

      {/* Market Status */}
      <div className="flex items-center justify-between p-3 rounded-lg mb-3" style={{ background: "#050816", border: "1px solid #1a2a4a" }}>
        <div>
          <div className="text-[9px] text-text-dim uppercase tracking-wider">Mercado</div>
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-bold text-neon-green">ALTISTA</span>
            <span className="text-sm">🚀</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[9px] text-text-dim uppercase tracking-wider">Confiança</div>
          <div className="text-lg font-bold font-mono text-neon-green">92%</div>
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
            className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-white/2 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className={item.status === "pass" ? "text-neon-green" : "text-neon-amber"}>
                {item.status === "pass" ? "✓" : "⚠"}
              </span>
              <span className="text-[11px] text-text-secondary">{item.label}</span>
            </div>
            <span className="text-[9px] font-mono text-text-dim">{item.detail}</span>
          </motion.div>
        ))}
      </div>

      {/* Support / Resistance */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2.5 rounded-lg" style={{ background: "#050816", border: "1px solid #1a2a4a" }}>
          <div className="text-[9px] text-text-dim uppercase tracking-wider">Suporte</div>
          <div className="text-sm font-bold font-mono text-neon-green">$64,200</div>
        </div>
        <div className="p-2.5 rounded-lg" style={{ background: "#050816", border: "1px solid #1a2a4a" }}>
          <div className="text-[9px] text-text-dim uppercase tracking-wider">Resistência</div>
          <div className="text-sm font-bold font-mono text-neon-red">$65,800</div>
        </div>
      </div>

      {/* Key levels */}
      <div className="mt-3 pt-3 border-t" style={{ borderColor: "#1a2a4a" }}>
        <div className="text-[9px] text-text-dim uppercase tracking-wider mb-2">Níveis-chave</div>
        <div className="space-y-1">
          {[
            { label: "TP1", price: 66200, color: "text-neon-green" },
            { label: "TP2", price: 68100, color: "text-neon-green" },
            { label: "SL", price: 63900, color: "text-neon-red" },
          ].map(lv => (
            <div key={lv.label} className="flex items-center justify-between text-[10px]">
              <span className="text-text-dim font-mono">{lv.label}</span>
              <span className={`font-mono font-bold ${lv.color}`}>${lv.price.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}