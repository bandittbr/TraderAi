/**
 * TradeAI - Componente: Placeholder de Gráfico
 * Área reservada para integração futura com TradingView ou Recharts.
 * Fase 2: substituir pelo gráfico real de candles/linha.
 */

export function ChartPlaceholder() {
  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6 flex flex-col gap-4">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Gráfico de Mercado</h3>
          <p className="text-xs text-[#6b7280] mt-0.5">TradingView — Fase 2</p>
        </div>
        <div className="flex gap-2">
          {["1m", "5m", "1h", "1d"].map((tf) => (
            <button
              key={tf}
              disabled
              className="px-2.5 py-1 text-xs rounded-md bg-[#1f2937] text-[#6b7280] cursor-not-allowed"
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Área do gráfico */}
      <div className="relative h-64 rounded-lg bg-[#0a0e1a] border border-dashed border-[#1f2937] flex flex-col items-center justify-center gap-3">
        {/* Grade decorativa */}
        <svg
          className="absolute inset-0 w-full h-full opacity-10"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#3b82f6" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>

        {/* Candles decorativos */}
        <svg width="120" height="60" viewBox="0 0 120 60" className="opacity-20">
          {[
            { x: 10, open: 40, close: 20, high: 15, low: 50 },
            { x: 30, open: 20, close: 35, high: 10, low: 45 },
            { x: 50, open: 35, close: 15, high: 8,  low: 52 },
            { x: 70, open: 15, close: 30, high: 5,  low: 40 },
            { x: 90, open: 30, close: 10, high: 3,  low: 55 },
          ].map((c, i) => (
            <g key={i}>
              <line x1={c.x + 5} y1={c.high} x2={c.x + 5} y2={c.low} stroke="#9ca3af" strokeWidth="1" />
              <rect
                x={c.x}
                y={Math.min(c.open, c.close)}
                width="10"
                height={Math.abs(c.close - c.open)}
                fill={c.close < c.open ? "#10b981" : "#ef4444"}
              />
            </g>
          ))}
        </svg>

        <p className="text-sm font-medium text-[#6b7280] z-10">
          Gráfico disponível na Fase 2
        </p>
        <p className="text-xs text-[#4b5563] z-10">
          Integração com TradingView Lightweight Charts
        </p>
      </div>
    </div>
  );
}
