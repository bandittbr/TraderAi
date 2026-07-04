"use client";

interface Metrics {
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  profit_factor: number;
  expectancy: number;
  sharpe_ratio: number;
  calmar_ratio: number;
  max_drawdown: number;
  avg_pnl_pct: number;
  avg_win_pct: number;
  avg_loss_pct: number;
  avg_duration_min: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
}

interface Props {
  metrics: Metrics | null;
  loading?: boolean;
}

interface Stat {
  label: string;
  value: string;
  color: string;
  tooltip?: string;
}

function formatNumber(n: number, decimals = 2): string {
  return n.toFixed(decimals);
}

function formatDuration(min: number): string {
  if (min < 60) return `${min.toFixed(0)}m`;
  return `${(min / 60).toFixed(1)}h`;
}

export function MetricsDashboard({ metrics: m, loading }: Props) {
  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <div className="text-center text-gray-500 py-8 text-sm">Calculando métricas...</div>
      </div>
    );
  }

  if (!m || m.total_trades === 0) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-4">Métricas de Performance</h3>
        <div className="text-center text-gray-600 py-6 text-sm">
          Nenhum trade resolvido ainda.
          <br />
          <span className="text-xs">As métricas aparecem após fechar posições.</span>
        </div>
      </div>
    );
  }

  const stats: Stat[] = [
    {
      label: "Win Rate",
      value: `${formatNumber(m.win_rate)}%`,
      color: m.win_rate >= 55 ? "text-green-400" : m.win_rate >= 45 ? "text-yellow-400" : "text-red-400",
      tooltip: "Percentual de trades positivos",
    },
    {
      label: "Profit Factor",
      value: formatNumber(m.profit_factor),
      color: m.profit_factor >= 1.5 ? "text-green-400" : m.profit_factor >= 1.0 ? "text-yellow-400" : "text-red-400",
      tooltip: "Ganhos totais / Perdas totais (>1.5 = ótimo)",
    },
    {
      label: "Expectância",
      value: `${m.expectancy >= 0 ? "+" : ""}${formatNumber(m.expectancy)}%`,
      color: m.expectancy > 0 ? "text-green-400" : "text-red-400",
      tooltip: "Retorno esperado por trade (>0 = edge positivo)",
    },
    {
      label: "Sharpe Ratio",
      value: formatNumber(m.sharpe_ratio),
      color: m.sharpe_ratio >= 1.5 ? "text-green-400" : m.sharpe_ratio >= 0.5 ? "text-yellow-400" : "text-red-400",
      tooltip: "Retorno ajustado ao risco anualizado (>1.5 = excelente)",
    },
    {
      label: "Calmar Ratio",
      value: formatNumber(m.calmar_ratio),
      color: m.calmar_ratio >= 2.0 ? "text-green-400" : m.calmar_ratio >= 1.0 ? "text-yellow-400" : "text-red-400",
      tooltip: "Retorno anual / Max Drawdown (>2 = excelente)",
    },
    {
      label: "Max Drawdown",
      value: `${formatNumber(m.max_drawdown)}%`,
      color: m.max_drawdown > -5 ? "text-green-400" : m.max_drawdown > -15 ? "text-yellow-400" : "text-red-400",
      tooltip: "Maior sequência de perdas acumuladas",
    },
    {
      label: "Média Ganho",
      value: `+${formatNumber(m.avg_win_pct)}%`,
      color: "text-green-400",
    },
    {
      label: "Média Perda",
      value: `${formatNumber(m.avg_loss_pct)}%`,
      color: "text-red-400",
    },
    {
      label: "Duração Média",
      value: formatDuration(m.avg_duration_min),
      color: "text-gray-300",
    },
    {
      label: "Seq. Vitórias",
      value: String(m.max_consecutive_wins),
      color: "text-green-400",
      tooltip: "Maior sequência consecutiva de wins",
    },
    {
      label: "Seq. Perdas",
      value: String(m.max_consecutive_losses),
      color: "text-red-400",
      tooltip: "Maior sequência consecutiva de losses",
    },
    {
      label: "Total Trades",
      value: String(m.total_trades),
      color: "text-gray-300",
    },
  ];

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-400">Métricas de Performance</h3>
        <div className="flex gap-3 text-xs">
          <span className="text-green-400 font-semibold">{m.wins}W</span>
          <span className="text-red-400 font-semibold">{m.losses}L</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="bg-gray-800/50 rounded p-2.5"
            title={stat.tooltip}
          >
            <div className="text-xs text-gray-500 mb-1">{stat.label}</div>
            <div className={`text-base font-bold ${stat.color}`}>{stat.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
