"use client";

import { motion } from "framer-motion";

const news = [
  { title: "BTC ultrapassa resistência de $65k com volume acima da média", source: "CoinDesk", sentiment: "positive" as const, impact: 8 },
  { title: "ETF de ETH registra maior entrada em 3 meses", source: "Reuters", sentiment: "positive" as const, impact: 7 },
  { title: "Federal Reserve mantém juros, mercado reage positivamente", source: "Bloomberg", sentiment: "positive" as const, impact: 9 },
  { title: "Regulador europeu sinaliza novas regras para stablecoins", source: "FT", sentiment: "negative" as const, impact: 6 },
  { title: "Adoção institucional de crypto atinge novo recorde", source: "CNBC", sentiment: "positive" as const, impact: 7 },
];

const sentimentConfig = {
  positive: { label: "Positiva", color: "#22c55e", bg: "#22c55e10" },
  negative: { label: "Negativa", color: "#ef4444", bg: "#ef444410" },
  neutral:  { label: "Neutra",   color: "#8aa4c8", bg: "#8aa4c810" },
};

export default function SentimentGauge() {
  const fearGreedValue = 72;
  const classification = fearGreedValue > 60 ? "GANÂNCIA" : fearGreedValue > 40 ? "NEUTRO" : "MEDO";
  const labelColor = fearGreedValue > 60 ? "text-emerald-400" : fearGreedValue > 40 ? "text-[#8aa4c8]" : "text-red-400";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.5 }}
      className="rounded-xl p-3"
      style={{ background: "#080c14", border: "1px solid #1a2540" }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] font-bold text-white">📰</span>
        <span className="text-[10px] font-bold text-white uppercase tracking-wider">Sentimento + Notícias</span>
      </div>

      <div className="flex gap-3">
        {/* Fear & Greed Gauge */}
        <div className="w-[120px] shrink-0">
          <div className="rounded-lg p-2.5 text-center" style={{ background: "#050816", border: "1px solid #1a2540" }}>
            <div className="text-[8px] text-[#2d4060] uppercase tracking-wider mb-1">Fear & Greed</div>
            {/* Gauge */}
            <div className="relative h-16 flex items-center justify-center mb-1">
              <svg width="80" height="64" viewBox="0 0 80 64">
                <path
                  d="M 5 56 A 38 38 0 0 1 75 56"
                  fill="none"
                  stroke="#1a2540"
                  strokeWidth="8"
                  strokeLinecap="round"
                />
                {/* Gradient arc */}
                <defs>
                  <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#ef4444" />
                    <stop offset="30%" stopColor="#f59e0b" />
                    <stop offset="60%" stopColor="#8aa4c8" />
                    <stop offset="100%" stopColor="#22c55e" />
                  </linearGradient>
                </defs>
                <path
                  d="M 5 56 A 38 38 0 0 1 75 56"
                  fill="none"
                  stroke="url(#gaugeGrad)"
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={`${(fearGreedValue / 100) * 140} 140`}
                  opacity="0.6"
                />
                {/* Needle */}
                <line
                  x1={40} y1={56}
                  x2={40 + 30 * Math.sin((fearGreedValue / 100) * Math.PI)}
                  y2={56 - 30 * Math.cos((fearGreedValue / 100) * Math.PI)}
                  stroke="white"
                  strokeWidth="1.5"
                  opacity="0.8"
                />
                <circle cx={40} cy={56} r="3" fill="white" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center mt-4">
                <span className="text-lg font-bold font-mono text-white">{fearGreedValue}</span>
              </div>
            </div>
            <div className={`text-[9px] font-bold ${labelColor}`}>{classification}</div>
          </div>
        </div>

        {/* News list */}
        <div className="flex-1 min-w-0">
          <div className="space-y-1.5">
            {news.map((item, i) => {
              const cfg = sentimentConfig[item.sentiment];
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-start gap-2 py-1.5 px-2 rounded-lg hover:bg-[#0a0e1a40] transition-colors"
                >
                  <span className="text-[9px] mt-0.5 shrink-0">
                    {item.sentiment === "positive" ? "📈" : item.sentiment === "negative" ? "📉" : "➡"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[9px] text-[#8aa4c8] leading-tight truncate">{item.title}</div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[7px] text-[#2d4060]">{item.source}</span>
                      <span className="text-[7px] text-[#2d4060]">•</span>
                      <span className="text-[7px] text-[#2d4060]">Impacto: {item.impact}/10</span>
                    </div>
                  </div>
                  <div
                    className="w-1.5 h-1.5 rounded-full mt-1 shrink-0"
                    style={{ background: cfg.color, boxShadow: `0 0 4px ${cfg.color}` }}
                  />
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
