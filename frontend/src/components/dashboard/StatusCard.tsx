/**
 * TradeAI - Componente: Card de Status
 * Card reutilizável para exibir métricas e status do sistema.
 */

import { clsx } from "clsx";
import { Badge } from "@/components/ui/Badge";
import type { StatusLevel } from "@/types";

interface StatusCardProps {
  title: string;
  value: string;
  subtitle?: string;
  level?: StatusLevel;
  icon?: React.ReactNode;
  className?: string;
}

export function StatusCard({
  title,
  value,
  subtitle,
  level,
  icon,
  className,
}: StatusCardProps) {
  return (
    <div
      className={clsx(
        "bg-[#111827] border border-[#1f2937] rounded-xl p-5",
        "flex flex-col gap-3 transition-all duration-200 hover:border-[#374151]",
        className
      )}
    >
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-[#9ca3af] uppercase tracking-wider">
          {title}
        </span>
        {icon && (
          <span className="text-[#6b7280]">{icon}</span>
        )}
      </div>

      {/* Valor principal */}
      <p className="text-2xl font-semibold text-[#f9fafb] font-mono leading-none">
        {value}
      </p>

      {/* Rodapé */}
      {(subtitle || level) && (
        <div className="flex items-center justify-between mt-auto pt-1 border-t border-[#1f2937]">
          {subtitle && (
            <span className="text-xs text-[#6b7280]">{subtitle}</span>
          )}
          {level && (
            <Badge
              level={level}
              label={
                level === "online"  ? "Online"    :
                level === "offline" ? "Offline"   :
                level === "warning" ? "Atenção"   : "Aguardando"
              }
            />
          )}
        </div>
      )}
    </div>
  );
}
