"use client";

interface RegimeData {
  symbol: string;
  timeframe: string;
  current: {
    regime: string;
    confidence: number;
    ema_alignment_score: number | null;
    atr_pct: number | null;
    price_vs_ema200_pct: number | null;
    rsi: number | null;
    timestamp: string;
  } | null;
}

const REGIME_CONFIG: Record<string, { label: string; color: string; bg: string; description: string }> = {
  BULL:            { label: "Bull Market",      color: "text-green-400",  bg: "bg-green-900/30 border-green-700",   description: "Tendência de alta" },
  BEAR:            { label: "Bear Market",      color: "text-red-400",    bg: "bg-red-900/30 border-red-700",       description: "Tendência de baixa" },
  SIDEWAYS:        { label: "Lateral",          color: "text-yellow-400", bg: "bg-yellow-900/30 border-yellow-700", description: "Sem tendência clara" },
  HIGH_VOLATILITY: { label: "Alta Volatilidade",color: "text-orange-400", bg: "bg-orange-900/30 border-orange-700", description: "Volatilidade elevada" },
  UNKNOWN:         { label: "Indefinido",       color: "text-gray-400",   bg: "bg-gray-800 border-gray-700",        description: "Aguardando dados" },
};

interface Props {
  data: RegimeData | null;
}

export function RegimeIndicator({ data }: Props) {
  const current = data?.current;
  const regime  = current?.regime ?? "UNKNOWN";
  const cfg     = REGIME_CONFIG[regime] ?? REGIME_CONFIG.UNKNOWN;

  return (
    <div className={`rounded-lg border p-4 ${cfg.bg}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-400">Regime de Mercado</h3>
        <span className="text-xs text-gray-500">{data?.symbol ?? "—"}</span>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div>
          <div className={`text-xl font-bold ${cfg.color}`}>{cfg.label}</div>
          <div className="text-xs text-gray-400">{cfg.description}</div>
        </div>
        {current && (
          <div className="ml-auto text-right">
            <div className="text-lg font-semibold text-white">
              {current.confidence.toFixed(0)}%
            </div>
            <div className="text-xs text-gray-500">confiança</div>
          </div>
        )}
      </div>

      {current && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          {current.ema_alignment_score !== null && (
            <div className="bg-black/20 rounded p-2">
              <div className="text-gray-500">EMA Score</div>
              <div className={`font-semibold ${current.ema_alignment_score >= 0 ? "text-green-400" : "text-red-400"}`}>
                {current.ema_alignment_score > 0 ? "+" : ""}{current.ema_alignment_score}/4
              </div>
            </div>
          )}
          {current.atr_pct !== null && (
            <div className="bg-black/20 rounded p-2">
              <div className="text-gray-500">ATR%</div>
              <div className="text-white font-semibold">{current.atr_pct.toFixed(2)}%</div>
            </div>
          )}
          {current.price_vs_ema200_pct !== null && (
            <div className="bg-black/20 rounded p-2">
              <div className="text-gray-500">vs EMA200</div>
              <div className={`font-semibold ${current.price_vs_ema200_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                {current.price_vs_ema200_pct > 0 ? "+" : ""}{current.price_vs_ema200_pct.toFixed(2)}%
              </div>
            </div>
          )}
          {current.rsi !== null && (
            <div className="bg-black/20 rounded p-2">
              <div className="text-gray-500">RSI</div>
              <div className="text-white font-semibold">{current.rsi.toFixed(1)}</div>
            </div>
          )}
        </div>
      )}

      {!current && (
        <div className="text-center text-gray-500 text-sm py-2">
          Aguardando classificação...
        </div>
      )}
    </div>
  );
}
