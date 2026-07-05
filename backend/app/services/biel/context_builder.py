"""
Biel — Context Builder
Coleta dados reais do TradeAI para alimentar o cérebro do Biel.
"""

from datetime import datetime, timezone
from sqlalchemy import select, desc
from app.database import AsyncSessionLocal
from app.models.paper_trading import PaperAccount, PaperTrade
from app.models.market import MarketCandle
from app.models.market_context import FearGreedIndex, MarketNews
from app.models.analytics import MarketRegime
from app.logger import get_logger

logger = get_logger(__name__)


async def build_context() -> dict:
    """
    Retorna um dicionário com o estado atual do TradeAI
    para ser usado como contexto na geração de posts do Biel.
    """
    async with AsyncSessionLocal() as session:
        ctx = {}

        # ── Conta paper trading ────────────────────────────────────────────
        try:
            result = await session.execute(select(PaperAccount).limit(1))
            account = result.scalar_one_or_none()
            if account:
                ctx["saldo"]          = round(account.balance, 2)
                ctx["saldo_inicial"]  = round(account.initial_balance, 2)
                ctx["pnl_total"]      = round(account.total_pnl, 2)
                ctx["pnl_pct"]        = round(
                    (account.total_pnl / account.initial_balance) * 100, 2
                ) if account.initial_balance else 0
        except Exception as e:
            logger.warning(f"[biel/context] Conta: {e}")

        # ── Últimos trades ─────────────────────────────────────────────────
        try:
            result = await session.execute(
                select(PaperTrade)
                .where(PaperTrade.status == "closed")
                .order_by(desc(PaperTrade.closed_at))
                .limit(5)
            )
            trades = result.scalars().all()
            ctx["ultimos_trades"] = [
                {
                    "symbol":    t.symbol,
                    "side":      t.trade_side,
                    "pnl":       round(t.pnl or 0, 2),
                    "pnl_pct":   round(t.pnl_pct or 0, 2),
                    "resultado": "WIN" if (t.pnl or 0) > 0 else "LOSS",
                }
                for t in trades
            ]
            wins  = sum(1 for t in trades if (t.pnl or 0) > 0)
            ctx["win_rate_recente"] = round(wins / len(trades) * 100) if trades else 0
        except Exception as e:
            logger.warning(f"[biel/context] Trades: {e}")

        # ── Regime de mercado ──────────────────────────────────────────────
        try:
            result = await session.execute(
                select(MarketRegime)
                .order_by(desc(MarketRegime.timestamp))
                .limit(1)
            )
            regime = result.scalar_one_or_none()
            if regime:
                ctx["regime"]        = regime.regime
                ctx["regime_symbol"] = regime.symbol
        except Exception as e:
            logger.warning(f"[biel/context] Regime: {e}")

        # ── Fear & Greed ───────────────────────────────────────────────────
        try:
            result = await session.execute(
                select(FearGreedIndex)
                .order_by(desc(FearGreedIndex.timestamp))
                .limit(1)
            )
            fg = result.scalar_one_or_none()
            if fg:
                ctx["fear_greed_value"]       = fg.value
                ctx["fear_greed_label"]       = fg.value_classification
        except Exception as e:
            logger.warning(f"[biel/context] FearGreed: {e}")

        # ── Notícias recentes ──────────────────────────────────────────────
        try:
            result = await session.execute(
                select(MarketNews)
                .order_by(desc(MarketNews.published_at))
                .limit(3)
            )
            news = result.scalars().all()
            ctx["noticias"] = [
                {"titulo": n.title, "sentimento": n.sentiment}
                for n in news
            ]
        except Exception as e:
            logger.warning(f"[biel/context] News: {e}")

        # ── Preço atual BTC ────────────────────────────────────────────────
        try:
            result = await session.execute(
                select(MarketCandle)
                .where(MarketCandle.symbol == "BTCUSDT")
                .where(MarketCandle.timeframe == "1h")
                .order_by(desc(MarketCandle.open_time))
                .limit(1)
            )
            candle = result.scalar_one_or_none()
            if candle:
                ctx["btc_price"] = round(candle.close, 2)
        except Exception as e:
            logger.warning(f"[biel/context] BTC price: {e}")

        ctx["timestamp"] = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        return ctx
