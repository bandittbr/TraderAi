/**
 * TradeAI - Dashboard Principal (Fase 3)
 * Fase 3: seletor de ativo, TechnicalIndicators, MarketAnalysis, SignalEngine,
 *         Market Score V2 com breakdown por dimensão.
 */

"use client";

import { useEffect, useState }            from "react";
import { SystemStatus }                   from "@/components/dashboard/SystemStatus";
import { MarketPanel }                    from "@/components/dashboard/MarketPanel";
import { MarketChart }                    from "@/components/dashboard/MarketChart";
import { MarketScore }                    from "@/components/dashboard/MarketScore";
import { TechnicalIndicators }            from "@/components/dashboard/TechnicalIndicators";
import { MarketAnalysis }                 from "@/components/dashboard/MarketAnalysis";
import { SignalEngine }                   from "@/components/dashboard/SignalEngine";
import { NewsPlaceholder }                from "@/components/dashboard/NewsPlaceholder";
import { StatsPlaceholder }               from "@/components/dashboard/StatsPlaceholder";
import { useWebSocket }                   from "@/hooks/useWebSocket";
import { useMarketData }                  from "@/hooks/useMarketData";
import { useIndicators }                  from "@/hooks/useIndicators";
import { StrategyPerformance }            from "@/components/dashboard/StrategyPerformance";
import { Badge }                          from "@/components/ui/Badge";
import { clsx }                           from "clsx";
import { getPaperStats, getNews, getFearGreed, getFundingRates, getOpenInterest, getContextScore } from "@/lib/api";
import Link                               from "next/link";
import { NewsFeed }                        from "@/components/market-context/NewsFeed";
import { FearGreedGauge }                  from "@/components/market-context/FearGreedGauge";
import { FundingRateCard }                 from "@/components/market-context/FundingRateCard";
import { OpenInterestCard }                from "@/components/market-context/OpenInterestCard";
import { MarketContextCard }               from "@/components/market-context/MarketContextCard";
import { MarketStructurePanel }            from "@/components/market-structure/MarketStructurePanel";
import { LiquidityPanel }                  from "@/components/smart-money/LiquidityPanel";
import { SweepMonitor }                    from "@/components/smart-money/SweepMonitor";
import { FVGPanel }                        from "@/components/smart-money/FVGPanel";
import { VolumeProfilePanel }              from "@/components/smart-money/VolumeProfilePanel";
import { OptimizerDashboard }              from "@/components/optimizer/OptimizerDashboard";
import { CriteriaRanking }                from "@/components/optimizer/CriteriaRanking";
import { CombinationRanking }             from "@/components/optimizer/CombinationRanking";
import { RegimePerformance }              from "@/components/optimizer/RegimePerformance";
import type {
  PaperStatsResponse,
  NewsArticle,
  FearGreedData,
  FundingRateData,
  OpenInterestData,
  ContextScoreData,
} from "@/types";

// ── Ativos disponíveis ────────────────────────────────────────────────────────

const SYMBOLS = [
  { symbol: "BTCUSDT",  label: "BTC"  },
  { symbol: "ETHUSDT",  label: "ETH"  },
  { symbol: "SOLUSDT",  label: "SOL"  },
  { symbol: "BNBUSDT",  label: "BNB"  },
  { symbol: "AVAXUSDT", label: "AVAX" },
  { symbol: "LINKUSDT", label: "LINK" },
];

// ── Relógio ───────────────────────────────────────────────────────────────────

function Clock() {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const tick = setInterval(() => setNow(new Date()), 1_000);
    return () => clearInterval(tick);
  }, []);

  if (!now) return null;

  return (
    <div className="text-right">
      <p className="text-2xl font-mono font-semibold text-[#f9fafb] tabular-nums">
        {now.toLocaleTimeString("pt-BR")}
      </p>
      <p className="text-xs text-[#6b7280] mt-0.5">
        {now.toLocaleDateString("pt-BR", {
          weekday: "long", day: "2-digit", month: "long", year: "numeric",
        })}
      </p>
    </div>
  );
}

// ── Seletor de ativo ──────────────────────────────────────────────────────────

function AssetSelector({
  active,
  onChange,
}: {
  active:   string;
  onChange: (symbol: string) => void;
}) {
  return (
    <div className="flex items-center gap-1 bg-[#0f1623] rounded-lg p-1 border border-[#1f2937]">
      {SYMBOLS.map(({ symbol, label }) => (
        <button
          key={symbol}
          onClick={() => onChange(symbol)}
          className={clsx(
            "px-4 py-1.5 rounded-md text-sm font-semibold transition-all",
            active === symbol
              ? "bg-blue-500 text-white shadow-sm"
              : "text-[#9ca3af] hover:text-[#f9fafb] hover:bg-[#1f2937]",
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [activeSymbol, setActiveSymbol] = useState("BTCUSDT");

  // WebSocket: conexão única na raiz — broadcasting de todos os ativos
  const { prices, connected } = useWebSocket();
  const livePrice = prices[activeSymbol];

  // REST polling: stats 24h + market score V2 (30s)
  const { stats, loading: statsLoading } = useMarketData(activeSymbol);

  // Análise técnica: indicadores + sinal + análise qualitativa (60s)
  const { data: analysis, loading: analysisLoading } = useIndicators(activeSymbol, "1h");

  const [paperStats, setPaperStats] = useState<PaperStatsResponse | null>(null);
  useEffect(() => {
    getPaperStats().then(setPaperStats);
    const id = setInterval(() => getPaperStats().then(setPaperStats), 30_000);
    return () => clearInterval(id);
  }, []);

  // Fase 5: Market Context
  const [newsArticles,  setNewsArticles]  = useState<NewsArticle[]>([]);
  const [fearGreed,     setFearGreed]     = useState<FearGreedData | null>(null);
  const [fundingRates,  setFundingRates]  = useState<FundingRateData[]>([]);
  const [openInterest,  setOpenInterest]  = useState<OpenInterestData[]>([]);
  const [contextScore,  setContextScore]  = useState<ContextScoreData | null>(null);
  const [contextLoading, setContextLoading] = useState(true);

  useEffect(() => {
    async function loadContext() {
      const [news, fg, fr, oi, ctx] = await Promise.all([
        getNews(activeSymbol.replace("USDT",""), 20, 48),
        getFearGreed(),
        getFundingRates(),
        getOpenInterest(),
        getContextScore(activeSymbol),
      ]);
      setNewsArticles(news);
      setFearGreed(fg);
      setFundingRates(fr);
      setOpenInterest(oi);
      setContextScore(ctx);
      setContextLoading(false);
    }
    setContextLoading(true);
    loadContext();
    const id = setInterval(loadContext, 60_000);
    return () => clearInterval(id);
  }, [activeSymbol]);

  return (
    <div className="min-h-screen bg-[#0a0e1a]">

      {/* ── Navbar ──────────────────────────────────────────────────────────── */}
      <nav className="border-b border-[#1f2937] bg-[#111827]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-screen-xl mx-auto px-6 py-3 flex items-center justify-between gap-4">

          {/* Logo */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
                <polyline points="16 7 22 7 22 13" />
              </svg>
            </div>
            <div>
              <span className="text-lg font-bold text-[#f9fafb]">TradeAI</span>
              <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 font-mono">
                v9.0.0
              </span>
            </div>
          </div>

          {/* Seletor de ativo */}
          <AssetSelector active={activeSymbol} onChange={setActiveSymbol} />

          {/* Status */}
          <div className="hidden md:flex items-center gap-3 shrink-0">
            <Badge
              level={connected ? "online" : "warning"}
              label={connected ? "Live" : "Reconectando..."}
            />
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#1f2937]">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              <span className="text-xs text-[#9ca3af]">Fase 5 — News Intelligence</span>
            </div>
          </div>
        </div>
      </nav>

      {/* ── Conteúdo ────────────────────────────────────────────────────────── */}
      <main className="max-w-screen-xl mx-auto px-6 py-8 flex flex-col gap-6">

        {/* Cabeçalho */}
        <header className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-[#f9fafb]">Dashboard</h1>
            <p className="text-sm text-[#9ca3af] mt-1">
              Análise técnica em tempo real · Binance ·{" "}
              <span className="text-blue-400 font-semibold">
                {activeSymbol.replace("USDT", "")}/USDT
              </span>
            </p>
          </div>
          <Clock />
        </header>

        {/* Status do sistema */}
        <SystemStatus />

        {/* Market Panel (3/4) + Market Score V2 (1/4) */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <div className="lg:col-span-3">
            <MarketPanel
              symbol={activeSymbol}
              stats={stats}
              livePrice={livePrice}
              loading={statsLoading}
            />
          </div>
          <div className="lg:col-span-1">
            <MarketScore
              stats={stats}
              symbol={activeSymbol}
              loading={statsLoading}
            />
          </div>
        </div>

        {/* Gráfico candlestick */}
        <MarketChart symbol={activeSymbol} livePrice={livePrice} />

        {/* Indicadores Técnicos (full width) */}
        <TechnicalIndicators
          indicators={analysis?.indicators ?? null}
          loading={analysisLoading}
          symbol={activeSymbol}
        />

        {/* Signal Engine + Market Analysis */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SignalEngine
            signal={analysis?.signal ?? null}
            loading={analysisLoading}
            symbol={activeSymbol}
          />
          <MarketAnalysis
            analysis={analysis?.analysis ?? null}
            loading={analysisLoading}
            symbol={activeSymbol}
          />
        </div>

        {/* Fase 5: Market Context Score */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <MarketContextCard data={contextScore} loading={contextLoading} />
          </div>
          <FearGreedGauge data={fearGreed} loading={contextLoading} />
        </div>

        {/* Fase 5: Funding Rate + Open Interest */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <FundingRateCard  rates={fundingRates}  loading={contextLoading} />
          <OpenInterestCard data={openInterest}   loading={contextLoading} />
        </div>

        {/* Fase 5: News Feed */}
        <NewsFeed articles={newsArticles} loading={contextLoading} />

        {/* Fase 6.5: Market Structure */}
        <MarketStructurePanel />

        {/* Fase 7: Smart Money & Liquidity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <LiquidityPanel />
          <SweepMonitor />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <FVGPanel />
          <VolumeProfilePanel />
        </div>

        {/* Fase 8: Adaptive Strategy Optimizer */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <OptimizerDashboard />
          <RegimePerformance />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <CriteriaRanking />
          <CombinationRanking />
        </div>

        {/* Fase 4: Strategy Performance + Paper Trading link */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <StrategyPerformance stats={paperStats} />
          <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col items-center justify-center gap-3">
            <div className="w-10 h-10 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
              <span className="text-amber-400 text-lg">📊</span>
            </div>
            <p className="text-sm font-semibold text-[#f9fafb]">Paper Trading</p>
            <p className="text-xs text-[#6b7280] text-center">
              Validação de sinais com conta virtual. Nenhum risco real.
            </p>
            <Link
              href="/paper-trading"
              className="px-4 py-1.5 text-xs font-semibold rounded-md bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 transition-colors"
            >
              Abrir Paper Trading →
            </Link>
          </div>
        </div>


        {/* Rodapé */}
        <footer className="text-center pt-4 border-t border-[#1f2937]">
          <p className="text-xs text-[#4b5563]">
            TradeAI v12.0.0 — Fase 12: Trade Management Engine · Laboratório Quantitativo.{" "}
            <Link href="/alpha" className="text-blue-400 hover:text-blue-300 underline transition-colors">
              Alpha Discovery →
            </Link>
            {" · "}
            <Link href="/robustness" className="text-purple-400 hover:text-purple-300 underline transition-colors">
              Robustness →
            </Link>
            {" · "}
            <Link href="/strategies" className="text-emerald-400 hover:text-emerald-300 underline transition-colors">
              Strategy Lab →
            </Link>
            {" · "}
            <Link href="/paper-trading" className="text-amber-400 hover:text-amber-300 underline transition-colors">
              Paper Trading →
            </Link>
            {" · "}
            <Link href="/trade-management" className="text-cyan-400 hover:text-cyan-300 underline transition-colors">
              Trade Mgmt →
            </Link>
          </p>
        </footer>
      </main>
    </div>
  );
}
