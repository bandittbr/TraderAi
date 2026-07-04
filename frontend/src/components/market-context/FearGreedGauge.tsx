"use client";

import type { FearGreedData } from "@/types";

interface Props {
  data:    FearGreedData | null;
  loading?: boolean;
}

function getColor(value: number): string {
  if (value <= 24) return "#ef4444";   // Extreme Fear — vermelho
  if (value <= 44) return "#f97316";   // Fear — laranja
  if (value <= 55) return "#eab308";   // Neutral — amarelo
  if (value <= 75) return "#84cc16";   // Greed — verde claro
  return "#10b981";                    // Extreme Greed — verde
}

function getLabel(value: number): string {
  if (value <= 24) return "Medo Extremo";
  if (value <= 44) return "Medo";
  if (value <= 55) return "Neutro";
  if (value <= 75) return "Ganância";
  return "Ganância Extrema";
}

export function FearGreedGauge({ data, loading }: Props) {
  const value = data?.value ?? 50;
  const color = getColor(value);
  const label = data ? getLabel(value) : "Carregando...";

  // Arc SVG: semicírculo de 180° mapeado para 0-100
  const RADIUS = 52;
  const CX = 70, CY = 70;
  const startAngle = 180; // graus
  const endAngle   = 0;
  const angle = startAngle - (value / 100) * 180;
  const rad   = (angle * Math.PI) / 180;
  const needleX = CX + RADIUS * Math.cos(rad);
  const needleY = CY - RADIUS * Math.sin(rad);

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#f9fafb]">Fear &amp; Greed</h3>
        <span className="text-xs text-[#4b5563]">alternative.me</span>
      </div>

      {loading || !data ? (
        <div className="h-36 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="flex flex-col items-center">
          {/* SVG gauge */}
          <svg width="140" height="80" viewBox="0 0 140 80">
            {/* Track */}
            <path
              d={`M 18 70 A 52 52 0 0 1 122 70`}
              fill="none"
              stroke="#1f2937"
              strokeWidth="10"
              strokeLinecap="round"
            />
            {/* Filled arc */}
            {(() => {
              const sweepAngle = (value / 100) * 180;
              const rad2 = ((180 - sweepAngle) * Math.PI) / 180;
              const ex = CX + RADIUS * Math.cos(rad2);
              const ey = CY - RADIUS * Math.sin(rad2);
              const large = sweepAngle > 180 ? 1 : 0;
              return (
                <path
                  d={`M 18 70 A 52 52 0 ${large} 1 ${ex.toFixed(1)} ${ey.toFixed(1)}`}
                  fill="none"
                  stroke={color}
                  strokeWidth="10"
                  strokeLinecap="round"
                />
              );
            })()}
            {/* Needle */}
            <line
              x1={CX} y1={CY}
              x2={needleX.toFixed(1)}
              y2={needleY.toFixed(1)}
              stroke={color}
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <circle cx={CX} cy={CY} r="4" fill={color} />
            {/* Value */}
            <text x={CX} y={CY + 20} textAnchor="middle" fill={color} fontSize="18" fontWeight="bold">
              {value}
            </text>
          </svg>

          <p className="text-sm font-semibold mt-1" style={{ color }}>
            {label}
          </p>
          <p className="text-xs text-[#4b5563] mt-0.5">
            {new Date(data.timestamp * 1000).toLocaleDateString("pt-BR")}
          </p>

          {/* Escala */}
          <div className="flex justify-between w-full mt-3 text-[10px] text-[#4b5563]">
            <span className="text-red-500">Medo</span>
            <span className="text-yellow-500">Neutro</span>
            <span className="text-emerald-500">Ganância</span>
          </div>
        </div>
      )}
    </div>
  );
}
