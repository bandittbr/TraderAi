/**
 * TradeAI - Componente: Placeholder de Estatísticas de Desempenho
 * Área reservada para KPIs de trading: P&L, win rate, drawdown etc.
 * Fase 2: conectar ao módulo de gestão de risco e carteira.
 */

export function StatsPlaceholder() {
  const mockStats = [
    { label: "Retorno Total",    value: "+24,3%", trend: "up",     unit: ""   },
    { label: "Win Rate",         value: "68%",    trend: "up",     unit: ""   },
    { label: "Max. Drawdown",    value: "-8,1%",  trend: "down",   unit: ""   },
    { label: "Operações Hoje",   value: "0",      trend: "neutral", unit: ""  },
  ];

  const trendStyle: Record<string, string> = {
    up:      "text-emerald-400",
    down:    "text-red-400",
    neutral: "text-[#9ca3af]",
  };

  const trendArrow: Record<string, string> = {
    up: "↑", down: "↓", neutral: "─",
  };

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Estatísticas de Desempenho</h3>
          <p className="text-xs text-[#6b7280] mt-0.5">KPIs de trading — Fase 2</p>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-[#1f2937] text-[#6b7280]">
          Preview
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {mockStats.map((stat) => (
          <div
            key={stat.label}
            className="p-3 rounded-lg bg-[#0a0e1a] border border-[#1f2937] opacity-50 cursor-not-allowed"
          >
            <p className="text-xs text-[#6b7280] mb-1">{stat.label}</p>
            <div className="flex items-baseline gap-1.5">
              <span className="text-lg font-mono font-semibold text-[#f9fafb]">
                {stat.value}
              </span>
              <span className={`text-sm font-medium ${trendStyle[stat.trend]}`}>
                {trendArrow[stat.trend]}
              </span>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-center text-[#4b5563] pt-2 border-t border-[#1f2937]">
        Estatísticas reais disponíveis após integração com corretora na Fase 2
      </p>
    </div>
  );
}
