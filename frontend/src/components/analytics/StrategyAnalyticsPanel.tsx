"use client";

interface IndicatorWinRate {
  criterion: string;
  win_rate: number;
  label: string;
}

interface AssetPerformance {
  symbol: string;
  win_rate: number;
  total: number;
  avg_pnl: number;
}

interface RegimePerformance {
  regime: string;
  win_rate: number;
  total: number;
  avg_pnl: number;
}

interface StrategyData {
  indicator_win_rates: IndicatorWinRate[];
  best_combination: string[];
  per_asset: AssetPerformance[];
  per_regime: RegimePerformance[];
  total_signals: number;
  resolved_signals: number;
}

const REGIME_LABELS: Record<string, string> = {
  BULL:            "Bull Market",
  BEAR:            "Bear Market",
  SIDEWAYS:        "Lateral",
  HIGH_VOLATILITY: "Alta Volatilidade",
  UNKNOWN:         "Indefinido",
};

function ProgressBar({ value, max = 100, color }: { value: number; max?: number; color: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="w-full bg-gray-700 rounded-full h-1.5 mt-1">
      <div
        className={`h-1.5 rounded-full ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

interface Props {
  data: StrategyData | null;
  loading?: boolean;
}

export function StrategyAnalyticsPanel({ data, loading }: Props) {
  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <div className="text-center text-gray-500 py-8 text-sm">Analisando estratégia...</div>
      </div>
    );
  }

  const hasData = data && data.resolved_signals > 0;

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 p-4 space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-400">Strategy Analytics</h3>
        {data && (
          <span className="text-xs text-gray-500">
            {data.resolved_signals} resolvidos / {data.total_signals} total
          </span>
        )}
      </div>

      {!hasData ? (
        <div className="text-center text-gray-600 py-6 text-sm">
          Dados insuficientes para análise.
          <br />
          <span className="text-xs">Necessário ao menos 3 trades por critério.</span>
        </div>
      ) : (
        <>
          {/* Melhor combinação */}
          {data.best_combination.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-2">Melhor Combinação de Critérios</div>
              <div className="flex flex-wrap gap-1">
                {data.best_combination.map((c) => (
                  <span key={c} className="px-2 py-0.5 bg-blue-900/40 border border-blue-700 text-blue-300 text-xs rounded">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Ranking de indicadores */}
          {data.indicator_win_rates.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-2">Win Rate por Indicador</div>
              <div className="space-y-2">
                {data.indicator_win_rates.slice(0, 8).map((ind) => (
                  <div key={ind.criterion}>
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-300">{ind.label}</span>
                      <span className={`font-semibold ${
                        ind.win_rate >= 60 ? "text-green-400" :
                        ind.win_rate >= 50 ? "text-yellow-400" : "text-red-400"
                      }`}>
                        {ind.win_rate.toFixed(1)}%
                      </span>
                    </div>
                    <ProgressBar
                      value={ind.win_rate}
                      color={
                        ind.win_rate >= 60 ? "bg-green-500" :
                        ind.win_rate >= 50 ? "bg-yellow-500" : "bg-red-500"
                      }
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Performance por ativo */}
          {data.per_asset.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-2">Performance por Ativo</div>
              <div className="space-y-1.5">
                {data.per_asset.map((a) => (
                  <div key={a.symbol} className="flex items-center gap-2 text-xs">
                    <span className="text-gray-300 w-12">{a.symbol.replace("USDT", "")}</span>
                    <div className="flex-1">
                      <ProgressBar
                        value={a.win_rate}
                        color={a.win_rate >= 55 ? "bg-green-500" : a.win_rate >= 45 ? "bg-yellow-500" : "bg-red-500"}
                      />
                    </div>
                    <span className={`font-semibold w-12 text-right ${
                      a.win_rate >= 55 ? "text-green-400" : a.win_rate >= 45 ? "text-yellow-400" : "text-red-400"
                    }`}>
                      {a.win_rate.toFixed(1)}%
                    </span>
                    <span className="text-gray-600 w-10 text-right">{a.total}t</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Performance por regime */}
          {data.per_regime.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-2">Performance por Regime</div>
              <div className="space-y-1.5">
                {data.per_regime.map((r) => (
                  <div key={r.regime} className="flex items-center gap-2 text-xs">
                    <span className="text-gray-300 w-20">{REGIME_LABELS[r.regime] ?? r.regime}</span>
                    <div className="flex-1">
                      <ProgressBar
                        value={r.win_rate}
                        color={r.win_rate >= 55 ? "bg-green-500" : r.win_rate >= 45 ? "bg-yellow-500" : "bg-red-500"}
                      />
                    </div>
                    <span className={`font-semibold w-12 text-right ${
                      r.win_rate >= 55 ? "text-green-400" : r.win_rate >= 45 ? "text-yellow-400" : "text-red-400"
                    }`}>
                      {r.win_rate.toFixed(1)}%
                    </span>
                    <span className="text-gray-600 w-10 text-right">{r.total}t</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
