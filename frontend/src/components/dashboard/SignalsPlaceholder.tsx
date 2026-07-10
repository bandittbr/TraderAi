/**
 * TradeAI - Componente: Placeholder de Sinais de Trading
 * Área reservada para exibição de sinais gerados pela IA.
 * Fase 2: conectar ao endpoint /api/v1/signals.
 */

export function SignalsPlaceholder() {
  // Sinais fictícios apenas para ilustrar o layout futuro
  const mockSignals = [
    { asset: "PETR4",  direction: "BUY",  confidence: 87 },
    { asset: "VALE3",  direction: "SELL", confidence: 72 },
    { asset: "ITUB4",  direction: "HOLD", confidence: 61 },
  ];

  const directionStyle: Record<string, string> = {
    BUY:  "text-emerald-400 bg-emerald-400/10",
    SELL: "text-red-400 bg-red-400/10",
    HOLD: "text-amber-400 bg-amber-400/10",
  };

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Sinais de Trading</h3>
          <p className="text-xs text-[#6b7280] mt-0.5">Gerados por IA — Fase 2</p>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-[#1f2937] text-[#6b7280]">
          Preview
        </span>
      </div>

      <div className="flex flex-col gap-2">
        {mockSignals.map((signal) => (
          <div
            key={signal.asset}
            className="flex items-center justify-between p-3 rounded-lg bg-[#0a0e1a] border border-[#1f2937] opacity-50 cursor-not-allowed"
          >
            <span className="text-sm font-mono font-medium text-[#f9fafb]">
              {signal.asset}
            </span>
            <div className="flex items-center gap-3">
              <div className="w-24 h-1.5 rounded-full bg-[#1f2937]">
                <div
                  className="h-full rounded-full bg-blue-500"
                  style={{ width: `${signal.confidence}%` }}
                />
              </div>
              <span className="text-xs text-[#9ca3af] w-8 text-right">
                {signal.confidence}%
              </span>
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded ${directionStyle[signal.direction]}`}
              >
                {signal.direction}
              </span>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-center text-[#4b5563] pt-2 border-t border-[#1f2937]">
        Sinais reais disponíveis após integração com módulo de IA na Fase 2
      </p>
    </div>
  );
}
