"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

// ── helpers ──────────────────────────────────────────────────────────────────

function safeNum(v: unknown, fb = 0): number {
  const n = Number(v);
  return isFinite(n) ? n : fb;
}
function safeStr(v: unknown, fb = ""): string {
  return typeof v === "string" ? v : fb;
}
function safeArr<T>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}
function ago(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 0)   return "agora";
    if (diff < 60)  return `${Math.round(diff)}s atrás`;
    if (diff < 3600) return `${Math.round(diff / 60)}m atrás`;
    return `${Math.round(diff / 3600)}h atrás`;
  } catch { return "—"; }
}

// ── types ─────────────────────────────────────────────────────────────────────

type Lvl = "online" | "degraded" | "offline" | "loading";

interface ModuleStatus {
  id:       string;
  label:    string;
  status:   Lvl;
  detail:   string;
  lastSeen: string | null;
}

interface DebugData {
  signals_processed_since_restart?:               number;
  signals_rejected_confidence_since_restart?:     number;
  signals_rejected_existing_trade_since_restart?: number;
  trade_engine_last_execution?:                   string | null;
  trades_open?:                                   number;
  trades_closed?:                                 number;
  signals_generated?:                             number;
  signals_rejected_confidence?:                   number;
  signals_high_confidence?:                       number;
  oldest_open_trade_hours?:                       number;
  oldest_open_trade_info?:                        Record<string, unknown>;
}

interface TmStats {
  total_closed_trades?:   number;
  time_stop_count?:       number;
  break_even_stop_count?: number;
  trailing_stop_count?:   number;
  stop_loss_count?:       number;
  take_profit_count?:     number;
  signal_close_count?:    number;
  exit_score_count?:      number;
  partial_tp_count?:      number;
  avg_exit_score?:        number | null;
  avg_duration_hours?:    number;
}

interface LastSignal {
  signal?:     string;
  symbol?:     string;
  confidence?: number;
  created_at?: string;
  timestamp?:  string;
}

interface MarketData {
  price?:      number;
  updated_at?: string;
}

interface PaperStats {
  current_balance?: number;
  open_trades?:     number;
  total_pnl?:       number;
  win_rate?:        number;
}

// ── sub-components ────────────────────────────────────────────────────────────

const LVL_STYLE: Record<Lvl, { dot: string; text: string; bg: string; border: string }> = {
  online:   { dot: "bg-emerald-500 shadow-[0_0_6px_#10b981]", text: "text-emerald-400", bg: "bg-emerald-500/5",  border: "border-emerald-500/20" },
  degraded: { dot: "bg-amber-500",                             text: "text-amber-400",   bg: "bg-amber-500/5",    border: "border-amber-500/20"   },
  offline:  { dot: "bg-red-500",                               text: "text-red-400",     bg: "bg-red-500/5",      border: "border-red-500/20"     },
  loading:  { dot: "bg-[#1e3050] animate-pulse",               text: "text-[#3d5a80]",   bg: "bg-[#0d1220]",      border: "border-[#141c2e]"      },
};

function ModuleCard({ mod }: { mod: ModuleStatus }) {
  const s = LVL_STYLE[mod.status] ?? LVL_STYLE.loading;
  const label =
    mod.status === "online"   ? "Online"   :
    mod.status === "degraded" ? "Atenção"  :
    mod.status === "offline"  ? "Offline"  : "...";
  return (
    <div className={`rounded-xl p-4 border ${s.bg} ${s.border} transition-all`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-white">{mod.label}</span>
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${s.dot}`} />
          <span className={`text-[10px] font-semibold ${s.text}`}>{label}</span>
        </div>
      </div>
      <p className="text-[10px] text-[#3d5a80] mb-1">{mod.detail}</p>
      {mod.lastSeen && (
        <p className="text-[9px] text-[#2d4060]">Atualizado: {ago(mod.lastSeen)}</p>
      )}
    </div>
  );
}

function DiagRow({ label, value, sub, color = "text-white" }: {
  label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[#0d1835]">
      <span className="text-[11px] text-[#4a6080]">{label}</span>
      <div className="text-right">
        <span className={`text-sm font-bold font-mono ${color}`}>{value}</span>
        {sub && <span className="text-[9px] text-[#2d4060] ml-1.5">{sub}</span>}
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[9px] text-[#1e3050] uppercase tracking-widest mb-3 font-semibold">
      {children}
    </div>
  );
}

// ── main page ─────────────────────────────────────────────────────────────────

export default function SystemHealthPage() {
  const [modules,     setModules]     = useState<ModuleStatus[]>([]);
  const [debug,       setDebug]       = useState<DebugData | null>(null);
  const [tmStats,     setTmStats]     = useState<TmStats | null>(null);
  const [lastSignal,  setLastSignal]  = useState<LastSignal | null>(null);
  const [marketData,  setMarketData]  = useState<MarketData | null>(null);
  const [paperStats,  setPaperStats]  = useState<PaperStats | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string>("");
  const [loading,     setLoading]     = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const mods: ModuleStatus[] = [];

    // 1. Backend API + Database
    let dbOk = false;
    let uptime = 0;
    try {
      const r = await fetch("/api/v1/system/health", { signal: AbortSignal.timeout(4000) });
      if (r.ok) {
        const d = await r.json().catch(() => ({})) as Record<string, unknown>;
        dbOk   = d?.database_connected === true;
        uptime = safeNum(d?.uptime_seconds);
        mods.push({
          id: "backend", label: "Backend API",
          status:   "online",
          detail:   `Uptime: ${Math.round(uptime / 60)}m`,
          lastSeen: new Date().toISOString(),
        });
        mods.push({
          id: "database", label: "Database (SQLite)",
          status:   dbOk ? "online" : "degraded",
          detail:   dbOk ? "Conexão OK" : "Sem conexão",
          lastSeen: new Date().toISOString(),
        });
      } else {
        mods.push({ id: "backend",  label: "Backend API",       status: "degraded", detail: `HTTP ${r.status}`, lastSeen: null });
        mods.push({ id: "database", label: "Database (SQLite)", status: "offline",  detail: "Backend degradado", lastSeen: null });
      }
    } catch {
      mods.push({ id: "backend",  label: "Backend API",       status: "offline", detail: "Sem resposta", lastSeen: null });
      mods.push({ id: "database", label: "Database (SQLite)", status: "offline", detail: "Backend offline", lastSeen: null });
    }

    // 2. Market Data (Binance REST)
    let mktUpdatedAt: string | null = null;
    try {
      const r = await fetch("/api/v1/market/stats?symbol=BTCUSDT", { signal: AbortSignal.timeout(4000) });
      if (r.ok) {
        const d = await r.json().catch(() => ({})) as MarketData;
        mktUpdatedAt = safeStr(d?.updated_at) || null;
        setMarketData(d);
        const ageMs = mktUpdatedAt ? Date.now() - new Date(mktUpdatedAt).getTime() : 9999999;
        const mktStatus: Lvl = ageMs < 120_000 ? "online" : ageMs < 300_000 ? "degraded" : "offline";
        mods.push({
          id: "market", label: "Market Data (REST)",
          status:   mktStatus,
          detail:   `BTC: $${safeNum(d?.price).toLocaleString("en-US", { maximumFractionDigits: 0 })}`,
          lastSeen: mktUpdatedAt,
        });
      } else {
        mods.push({ id: "market", label: "Market Data (REST)", status: "offline", detail: `HTTP ${r.status}`, lastSeen: null });
      }
    } catch {
      mods.push({ id: "market", label: "Market Data (REST)", status: "offline", detail: "Timeout / sem dados", lastSeen: null });
    }

    // 3. Paper Trading debug (scheduler last exec + signal engine)
    let dbgData: DebugData | null = null;
    try {
      const r = await fetch("/api/v1/paper/debug", { signal: AbortSignal.timeout(4000) });
      if (r.ok) {
        dbgData = await r.json().catch(() => null) as DebugData;
        setDebug(dbgData);
        const lastExec = safeStr(dbgData?.trade_engine_last_execution) || null;
        const execAgeMs = lastExec ? Date.now() - new Date(lastExec).getTime() : 9999999;
        const schStatus: Lvl = execAgeMs < 180_000 ? "online" : execAgeMs < 600_000 ? "degraded" : "offline";
        mods.push({
          id: "scheduler", label: "Scheduler",
          status:   schStatus,
          detail:   lastExec ? `Última exec: ${ago(lastExec)}` : "Sem execução registrada",
          lastSeen: lastExec,
        });
        const sigTotal = safeNum(dbgData?.signals_processed_since_restart);
        mods.push({
          id: "signal", label: "Signal Engine",
          status:   sigTotal > 0 ? "online" : (dbgData ? "degraded" : "offline"),
          detail:   `${sigTotal} sinais processados (sessão)`,
          lastSeen: lastExec,
        });
        const tradesOpen = safeNum(dbgData?.trades_open);
        mods.push({
          id: "paper", label: "Paper Trading",
          status:   "online",
          detail:   `${tradesOpen} trades abertos`,
          lastSeen: lastExec,
        });
      } else {
        ["scheduler", "signal", "paper"].forEach(id =>
          mods.push({ id, label: id, status: "degraded", detail: `HTTP ${r.status}`, lastSeen: null })
        );
      }
    } catch {
      ["scheduler", "signal", "paper"].forEach(id =>
        mods.push({ id, label: id, status: "offline", detail: "Sem resposta", lastSeen: null })
      );
    }

    // 4. Trade Management
    try {
      const r = await fetch("/api/v1/trade-management/stats", { signal: AbortSignal.timeout(4000) });
      if (r.ok) {
        const d = await r.json().catch(() => null) as TmStats;
        setTmStats(d);
        mods.push({
          id: "tradeMgmt", label: "Trade Management",
          status:   "online",
          detail:   `${safeNum(d?.total_closed_trades)} trades gerenciados`,
          lastSeen: new Date().toISOString(),
        });
      } else {
        mods.push({ id: "tradeMgmt", label: "Trade Management", status: "degraded", detail: `HTTP ${r.status}`, lastSeen: null });
      }
    } catch {
      mods.push({ id: "tradeMgmt", label: "Trade Management", status: "offline", detail: "Sem resposta", lastSeen: null });
    }

    // 5. Last Signal
    try {
      const r = await fetch("/api/v1/analytics/signals?limit=1", { signal: AbortSignal.timeout(4000) });
      if (r.ok) {
        const d = await r.json().catch(() => ({}));
        const arr = safeArr<LastSignal>(Array.isArray(d) ? d : (d?.signals ?? []));
        if (arr.length > 0) setLastSignal(arr[0]);
      }
    } catch { /* ignore */ }

    // 6. Paper stats
    try {
      const r = await fetch("/api/v1/paper/stats", { signal: AbortSignal.timeout(4000) });
      if (r.ok) {
        const d = await r.json().catch(() => null) as PaperStats;
        if (d) setPaperStats(d);
      }
    } catch { /* ignore */ }

    // Sort modules into fixed order
    const ORDER = ["backend", "database", "market", "scheduler", "signal", "paper", "tradeMgmt"];
    mods.sort((a, b) => ORDER.indexOf(a.id) - ORDER.indexOf(b.id));
    setModules(mods);
    setLastRefresh(new Date().toLocaleTimeString("pt-BR"));
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 30_000);
    return () => clearInterval(id);
  }, [refresh]);

  // ── derived display ────────────────────────────────────────────────────────
  const onlineCount  = modules.filter(m => m.status === "online").length;
  const offlineCount = modules.filter(m => m.status === "offline").length;
  const overallStatus: Lvl =
    offlineCount > 2 ? "offline" :
    offlineCount > 0 ? "degraded" : "online";

  const overallLabel =
    overallStatus === "online"   ? "Todos os sistemas operacionais" :
    overallStatus === "degraded" ? "Atenção: módulos com problema"  : "Sistema com falhas";

  const overallColor =
    overallStatus === "online"   ? "text-emerald-400" :
    overallStatus === "degraded" ? "text-amber-400"   : "text-red-400";

  const sigGenerated  = safeNum(debug?.signals_generated);
  const sigRejConf    = safeNum(debug?.signals_rejected_confidence);
  const sigRejTrade   = safeNum(debug?.signals_rejected_existing_trade_since_restart);
  const sigProcessed  = safeNum(debug?.signals_processed_since_restart);
  const sigHighConf   = safeNum(debug?.signals_high_confidence);

  const tmClosed   = safeNum(tmStats?.total_closed_trades);
  const tmTP       = safeNum(tmStats?.take_profit_count);
  const tmSL       = safeNum(tmStats?.stop_loss_count);
  const tmBE       = safeNum(tmStats?.break_even_stop_count);
  const tmTrail    = safeNum(tmStats?.trailing_stop_count);
  const tmTime     = safeNum(tmStats?.time_stop_count);
  const tmSignal   = safeNum(tmStats?.signal_close_count);
  const tmPartial  = safeNum(tmStats?.partial_tp_count);
  const tmAvgHours = safeNum(tmStats?.avg_duration_hours);

  const lastSigTs   = safeStr(lastSignal?.created_at ?? lastSignal?.timestamp) || null;
  const lastSigInfo = lastSignal
    ? `${safeStr(lastSignal.signal)} ${safeStr(lastSignal.symbol)} conf:${safeNum(lastSignal.confidence).toFixed(0)}%`
    : "—";

  const mktTs = safeStr(marketData?.updated_at) || null;

  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto space-y-8">

      {/* Header */}
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="text-[10px] tracking-widest text-[#2d4060] uppercase mb-1">
            Fase 12.6 · Observabilidade
          </div>
          <h1 className="text-2xl font-bold text-white leading-none">System Health</h1>
          <p className={`text-xs mt-1.5 font-medium ${overallColor}`}>{overallLabel}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-[#2d4060]">
            {lastRefresh ? `Atualizado: ${lastRefresh}` : "Carregando..."}
          </span>
          <button
            onClick={refresh}
            disabled={loading}
            className="text-[10px] px-3 py-1.5 rounded-lg border transition-all disabled:opacity-40"
            style={{ borderColor: "#2d4060", color: "#8aa4c8", background: "#0d1220" }}
          >
            {loading ? "..." : "Atualizar"}
          </button>
          <Link
            href="/"
            className="text-[10px] px-3 py-1.5 rounded-lg border transition-all"
            style={{ borderColor: "#2d4060", color: "#8aa4c8", background: "#0d1220" }}
          >
            ← Control Center
          </Link>
        </div>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-4">
        {([
          ["Módulos Online",  String(onlineCount),               onlineCount  === modules.length ? "text-emerald-400" : "text-amber-400"],
          ["Com Problema",    String(offlineCount),               offlineCount > 0 ? "text-red-400" : "text-emerald-400"],
          ["Total Módulos",   String(modules.length),             "text-white"],
        ] as [string, string, string][]).map(([l, v, c]) => (
          <div key={l} className="rounded-xl px-4 py-3 text-center" style={{ background: "#0d1220", border: "1px solid #141c2e" }}>
            <div className="text-[9px] text-[#2d4060] uppercase tracking-widest mb-1">{l}</div>
            <div className={`text-2xl font-bold font-mono ${c}`}>{v}</div>
          </div>
        ))}
      </div>

      {/* Module status grid */}
      <section>
        <SectionTitle>Status dos Módulos</SectionTitle>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {modules.map(m => <ModuleCard key={m.id} mod={m} />)}
        </div>
      </section>

      {/* Live activity */}
      <section>
        <SectionTitle>Atividade Recente</SectionTitle>
        <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #141c2e" }}>
          <DiagRow
            label="Último dado de mercado (BTC)"
            value={mktTs ? ago(mktTs) : "—"}
            sub={mktTs ? new Date(mktTs).toLocaleTimeString("pt-BR") : undefined}
          />
          <DiagRow
            label="Último sinal gerado"
            value={lastSigTs ? ago(lastSigTs) : "—"}
            sub={lastSigInfo !== "—" ? lastSigInfo : undefined}
          />
          <DiagRow
            label="Última execução do Trade Engine"
            value={debug?.trade_engine_last_execution ? ago(debug.trade_engine_last_execution) : "—"}
          />
          <DiagRow
            label="Trades abertos agora"
            value={safeNum(debug?.trades_open)}
            sub={`${safeNum(debug?.oldest_open_trade_hours).toFixed(1)}h mais antigo`}
          />
          <DiagRow
            label="Total trades fechados (histórico)"
            value={safeNum(debug?.trades_closed)}
          />
          <DiagRow
            label="Saldo Paper Trading"
            value={`$${safeNum(paperStats?.current_balance).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            color={safeNum(paperStats?.total_pnl) >= 0 ? "text-emerald-400" : "text-red-400"}
          />
        </div>
      </section>

      {/* Two columns: Signal diagnostics + Trade management */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Signals */}
        <section>
          <SectionTitle>Diagnóstico de Sinais</SectionTitle>
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #141c2e" }}>
            <DiagRow label="Sinais gerados (DB histórico)"    value={sigGenerated}  />
            <DiagRow label="Alta confiança (≥70%)"           value={sigHighConf}   color="text-emerald-400" />
            <DiagRow label="Rejeitados por confiança"        value={sigRejConf}    color={sigRejConf > 0 ? "text-amber-400" : "text-white"} />
            <DiagRow label="Processados nesta sessão"        value={sigProcessed}  />
            <DiagRow
              label="Rejeitados — trade existente (sessão)"
              value={sigRejTrade}
              color={sigRejTrade > 0 ? "text-amber-400" : "text-white"}
            />
          </div>
        </section>

        {/* Trade Management */}
        <section>
          <SectionTitle>Diagnóstico de Trade Management</SectionTitle>
          <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #141c2e" }}>
            <DiagRow label="Trades fechados (gerenciados)"  value={tmClosed} />
            <DiagRow label="Duração média"                  value={`${tmAvgHours.toFixed(1)}h`} />
            <DiagRow label="Take Profit hits"               value={tmTP}     color="text-emerald-400" />
            <DiagRow label="Stop Loss hits"                 value={tmSL}     color={tmSL > 0 ? "text-red-400" : "text-white"} />
            <DiagRow label="Break Even hits"                value={tmBE}     color="text-blue-400" />
            <DiagRow label="Trailing Stop hits"             value={tmTrail}  color="text-cyan-400" />
            <DiagRow label="Time Stop hits"                 value={tmTime}   color={tmTime > 0 ? "text-amber-400" : "text-white"} />
            <DiagRow label="Signal Close"                   value={tmSignal} />
            <DiagRow label="Partial TP hits"                value={tmPartial} color="text-emerald-400" />
          </div>
        </section>

      </div>

      {/* Endpoints reference */}
      <section>
        <SectionTitle>Endpoints Monitorados</SectionTitle>
        <div className="rounded-xl p-4 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-1.5" style={{ background: "#0d1220", border: "1px solid #141c2e" }}>
          {[
            ["Backend + DB",        "/api/v1/system/health"],
            ["Market Data",         "/api/v1/market/stats?symbol=BTCUSDT"],
            ["Paper Trading Debug", "/api/v1/paper/debug"],
            ["Paper Stats",         "/api/v1/paper/stats"],
            ["Trade Mgmt Stats",    "/api/v1/trade-management/stats"],
            ["Último Sinal",        "/api/v1/analytics/signals?limit=1"],
          ].map(([label, url]) => (
            <div key={url} className="flex gap-2 text-[10px]">
              <span className="text-[#2d4060] shrink-0">{label}:</span>
              <span className="text-[#4a6080] font-mono truncate">{url}</span>
            </div>
          ))}
        </div>
      </section>

      <footer className="pt-4 border-t text-center" style={{ borderColor: "#141c2e" }}>
        <p className="text-[10px] text-[#1e3050] font-mono">
          TradeAI v12.0.0 · Fase 12.6 · System Health & Diagnostics · Atualiza a cada 30s
        </p>
      </footer>

    </div>
  );
}
