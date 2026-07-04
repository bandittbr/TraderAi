/**
 * TradeAI - Componente: Badge de Status
 * Exibe um indicador visual (ponto + texto) para status de componentes.
 */

import { clsx } from "clsx";
import type { StatusLevel } from "@/types";

interface BadgeProps {
  level: StatusLevel;
  label: string;
  className?: string;
}

const levelConfig: Record<StatusLevel, { dot: string; text: string; bg: string }> = {
  online:  { dot: "status-dot-online",  text: "text-emerald-400", bg: "bg-emerald-400/10" },
  offline: { dot: "status-dot-offline", text: "text-red-400",     bg: "bg-red-400/10"     },
  loading: { dot: "status-dot-loading", text: "text-gray-400",    bg: "bg-gray-400/10"    },
  warning: { dot: "status-dot-warning", text: "text-amber-400",   bg: "bg-amber-400/10"   },
};

export function Badge({ level, label, className }: BadgeProps) {
  const config = levelConfig[level];

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium",
        config.bg,
        config.text,
        className
      )}
    >
      <span
        className={clsx("w-1.5 h-1.5 rounded-full", config.dot)}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}
