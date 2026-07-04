"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface MonteCarloData {
  n_simulations: number;
  n_trades: number;
  dd_median: number;
  dd_p95: number;
  dd_p99: number;
  dd_max_observed: number;
  ret_median: number;
  ret_p5: number;
  ret_p95: number;
  ruin_probability: number;
  expected_wr: number;
  wr_std: number;
  dd_histogram: { bins: number[]; counts: number[] };
}

function StatRow({ label, value, unit = "%", warn }: { label: string; value: number; unit?: string; warn?: boolean }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-[#1f2937]">
      <span className="text-xs text-[#9ca3af]">{label}</span>
      <span className={`text-xs font-mono font-semibold ${warn ? "text-red-400" : "text-[#f9fafb]"}`}>
        {value.toFixed(2)}{unit}
      </span>
    </div>
  );
}

export function MonteCarloPanel({ refresh }: { refresh?: number }) {
  const [data, setData] = useState<MonteCarloData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/robustness/monte-carlo`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [refresh]);

  // Histograma simples com barras SVG
  function renderHistogram() {
    if (!data?.dd_histogram?.counts?.length) return null;
    const counts  = data.dd_histogram.counts;
    const bins    = data.dd_histogram.bins;
    const maxC    = Math.max(...counts, 1);
    const barW    = 100 / counts.length;
    return (
      <div className="mt-3">
        <p className="text-[10px] text-[#6b7280] mb-1">Distribuição de Drawdowns (5000 simulações)</p>
        <svg viewBox={`0 0 100 40`} className="w-full" preserveAspectRatio="none" style={{ height: 56 }}>
          {counts.map((c, i) => {
            const h = (c / maxC) * 38;
            const x = i * barW + 0.3;
            return (
              <rect key={i} x={x} y={40 - h} width={barW - 0.6} height={h}
                fill="#a78bfa" fillOpacity={0.7} rx="0.5" />
            );
          })}
        </svg>
        <div className="flex justify-between text-[9px] text-[#4b5563] mt-0.5">
          <span>{bins[0]?.toFixed(1)}%</span>
          <span>{bins[Math.floor(bins.length / 2)]?.toFixed(1)}%</span>
          <span>{bins[bins.length - 1]?.toFixed(1)}%</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[#f9fafb]">Monte Carlo</h2>
          <p className="text-xs text-[#6b7280] mt-0.5">
            {data ? `${data.n_simulations.toLocaleString()} simulações · ${data.n_trades} trades` : "—"}
          </p>
        </div>
        {data && (
          <span className={`text-xs px-2 py-0.5 rounded font-bold ${
            data.ruin_probability < 5 ? "bg-green-500/20 text-green-400"
            : data.ruin_probability < 20 ? "bg-amber-500/20 text-amber-400"
            : "bg-red-500/20 text-red-400"}`}>
            Ruína: {data.ruin_probability.toFixed(1)}%
          </span>
        )}
      </div>

      {loading ? (
        <p className="text-xs text-[#4b5563] text-center py-4">Simulando...</p>
      ) : !data || data.n_trades === 0 ? (
        <p className="text-xs text-[#4b5563] text-center py-4">Trades insuficientes</p>
      ) : (
        <>
          <div>
            <p className="text-[10px] text-[#6b7280] font-semibold mb-1 uppercase tracking-wider">Drawdown</p>
            <StatRow label="Mediana" value={data.dd_median} />
            <StatRow label="Percentil 95" value={data.dd_p95} warn={data.dd_p95 > 20} />
            <StatRow label="Percentil 99" value={data.dd_p99} warn={data.dd_p99 > 30} />
            <StatRow label="Máximo observado" value={data.dd_max_observed} warn={data.dd_max_observed > 40} />
          </div>
          <div>
            <p className="text-[10px] text-[#6b7280] font-semibold mb-1 uppercase tracking-wider">Retorno</p>
            <StatRow label="Mediano" value={data.ret_median} />
            <StatRow label="Pior 5%" value={data.ret_p5} warn={data.ret_p5 < 0} />
            <StatRow label="Melhor 5%" value={data.ret_p95} />
          </div>
          <div>
            <p className="text-[10px] text-[#6b7280] font-semibold mb-1 uppercase tracking-wider">Win Rate</p>
            <StatRow label="WR esperado" value={data.expected_wr} />
            <StatRow label="Desvio padrão" value={data.wr_std} />
          </div>
          {renderHistogram()}
        </>
      )}
    </div>
  );
}
