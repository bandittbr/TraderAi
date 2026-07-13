"""
Biel — Context Builder (v2)
Coleta dados reais do TradeAI para alimentar o cérebro do Biel e os modelos visuais.
Inclui dados enriquecidos para os 4 temas (market, trade, insight, news).
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import select, desc
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.paper_trading import PaperAccount, PaperTrade
from app.models.market import MarketCandle, MarketStat
from app.models.market_context import FearGreedIndex, MarketNews
from app.models.analytics import MarketRegime
from app.logger import get_logger

logger = get_logger(__name__)


async def build_context() -> dict:
    """
    Retorna um dicionário com o estado atual do TradeAI
    para ser usado como contexto na geração de posts do Biel.
    Inclui dados enriquecidos para os 4 modelos visuais.
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
                # PaperAccount não tem coluna total_pnl — calcular de balance
                pnl = account.balance - account.initial_balance
                ctx["pnl_total"]      = round(pnl, 2)
                ctx["pnl_pct"]        = round(
                    (pnl / account.initial_balance) * 100, 2
                ) if account.initial_balance else 0
        except Exception as e:
            logger.warning(f"[biel/context] Conta: {e}")

        # ── Últimos trades (enriquecido) ──────────────────────────────────
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
                    "symbol":     t.symbol,
                    "side":       t.trade_side,
                    "entry_price": round(t.entry_price, 2),
                    "exit_price":  round(t.exit_price, 2) if t.exit_price else None,
                    "pnl":        round(t.pnl or 0, 2),
                    "pnl_pct":    round(t.pnl_percent or 0, 2),
                    "resultado":  "WIN" if (t.pnl or 0) > 0 else "LOSS",
                    "close_reason": t.close_reason or "",
                    "tp1_hit":    bool(t.tp1_hit),
                }
                for t in trades
            ]
            wins  = sum(1 for t in trades if (t.pnl or 0) > 0)
            ctx["win_rate_recente"] = round(wins / len(trades) * 100) if trades else 0
        except Exception as e:
            logger.warning(f"[biel/context] Trades: {e}")

        # ── Ideia de trade (modelo TRADE) ───────────────────────────────────
        # PaperTrade não guarda tp1/tp2/sl como colunas — são calculados em
        # runtime pelo trade_engine a partir dos percentuais reais de config.
        # Usa a posição aberta mais recente; se não houver, cai para a última
        # fechada (mesma fórmula, apenas ilustrativa sobre um trade já feito).
        try:
            result = await session.execute(
                select(PaperTrade)
                .where(PaperTrade.status == "open")
                .order_by(desc(PaperTrade.opened_at))
                .limit(1)
            )
            base_trade = result.scalar_one_or_none()
            is_open = base_trade is not None
            if base_trade is None and trades:
                base_trade = trades[0]

            if base_trade is not None:
                entry = base_trade.entry_price
                side = (base_trade.trade_side or "LONG").upper()
                sign = 1 if side == "LONG" else -1

                tp1 = entry * (1 + sign * settings.paper_tp1_pct / 100)
                tp2 = entry * (1 + sign * settings.paper_take_profit_percent / 100)
                sl  = entry * (1 - sign * settings.paper_stop_loss_percent / 100)

                risk = abs(entry - sl)
                reward = abs(tp2 - entry)
                rr = reward / risk if risk > 0 else 0

                ctx["trade_idea"] = {
                    "symbol": base_trade.symbol,
                    "side": side,
                    "entry": round(entry, 2),
                    "tp1": round(tp1, 2),
                    "tp2": round(tp2, 2),
                    "sl": round(sl, 2),
                    "rr": round(rr, 1),
                    "confidence": round(base_trade.confidence or 70, 0),
                    "is_open": is_open,
                }
        except Exception as e:
            logger.warning(f"[biel/context] Trade idea: {e}")

        # ── Regime de mercado ──────────────────────────────────────────────
        try:
            result = await session.execute(
                select(MarketRegime)
                .order_by(desc(MarketRegime.timestamp))
                .limit(1)
            )
            regime = result.scalar_one_or_none()
            if regime:
                # regime.regime é um Enum (MarketRegimeType). Enum.__str__ dá
                # "MarketRegimeType.SIDEWAYS" em vez do valor puro (mesmo sendo
                # um str Enum) — usar .value explicitamente evita isso vazar
                # cru pro texto do post.
                ctx["regime"]        = regime.regime.value if hasattr(regime.regime, "value") else regime.regime
                ctx["regime_symbol"] = regime.symbol
        except Exception as e:
            logger.warning(f"[biel/context] Regime: {e}")

        # ── Fear & Greed (+ variação real vs ~24h atrás) ────────────────────
        try:
            result = await session.execute(
                select(FearGreedIndex)
                .order_by(desc(FearGreedIndex.timestamp))
                .limit(1)
            )
            fg = result.scalar_one_or_none()
            if fg:
                ctx["fear_greed_value"] = fg.value
                ctx["fear_greed_label"] = fg.classification

                # Ponto mais próximo de 24h atrás (índice é atualizado de hora em hora)
                cutoff_24h = fg.timestamp - timedelta(hours=24)
                result_prev = await session.execute(
                    select(FearGreedIndex)
                    .where(FearGreedIndex.timestamp <= cutoff_24h)
                    .order_by(desc(FearGreedIndex.timestamp))
                    .limit(1)
                )
                fg_prev = result_prev.scalar_one_or_none()
                if fg_prev:
                    ctx["fear_greed_change_24h"] = fg.value - fg_prev.value
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

        # ── BTC: Preço atual + variação 24h + histórico (MERCADO) ─────────
        try:
            result = await session.execute(
                select(MarketStat)
                .where(MarketStat.symbol == "BTCUSDT")
                .limit(1)
            )
            stat = result.scalar_one_or_none()
            if stat:
                ctx["btc_price"]     = round(stat.price, 2)
                ctx["btc_change_24h"] = round(stat.change_24h, 2)
                ctx["volume_24h"]    = stat.volume_24h
        except Exception as e:
            logger.warning(f"[biel/context] MarketStat: {e}")

        # Fallback: se MarketStat não existir, tenta pelo último candle
        if "btc_price" not in ctx:
            try:
                result = await session.execute(
                    select(MarketCandle)
                    .where(MarketCandle.symbol == "BTCUSDT")
                    .where(MarketCandle.timeframe == "1h")
                    .order_by(desc(MarketCandle.timestamp))
                    .limit(1)
                )
                candle = result.scalar_one_or_none()
                if candle:
                    ctx["btc_price"] = round(candle.close, 2)
            except Exception as e:
                logger.warning(f"[biel/context] BTC candle fallback: {e}")

        # ── Histórico de preços BTC (últimas 24h → sparkline) ────────────
        try:
            cutoff = int((datetime.now(timezone.utc) - timedelta(hours=24)).timestamp())
            result = await session.execute(
                select(MarketCandle)
                .where(MarketCandle.symbol == "BTCUSDT")
                .where(MarketCandle.timeframe == "1h")
                .where(MarketCandle.timestamp >= cutoff)
                .order_by(MarketCandle.timestamp)
            )
            candles = result.scalars().all()
            if candles:
                ctx["btc_price_history"] = [round(c.close, 2) for c in candles]
                ctx["candle_history"] = [
                    {
                        "open":   round(c.open, 2),
                        "high":   round(c.high, 2),
                        "low":    round(c.low, 2),
                        "close":  round(c.close, 2),
                        "volume": c.volume,
                    }
                    for c in candles[-24:]  # máximo 24 candles
                ]
        except Exception as e:
            logger.warning(f"[biel/context] BTC history: {e}")

        # ── Resumo de mercado (MERCADO cards) ──────────────────────────────
        try:
            result = await session.execute(
                select(MarketStat)
                .where(MarketStat.symbol == "BTCUSDT")
                .limit(1)
            )
            stat = result.scalar_one_or_none()
            if stat:
                vol_str = f"${stat.volume_24h:,.1f}" if stat.volume_24h >= 1_000_000_000 else f"${stat.volume_24h:,.0f}"
                ctx["resumo"] = {
                    "volume_24h": vol_str,
                }
        except Exception as e:
            logger.warning(f"[biel/context] Resumo: {e}")

        # ── Variação real de volume: últimas 24h vs 24h anteriores ─────────
        # (compara soma de volume dos candles 1h — nada inventado, só derivado
        # do candle_history já coletado pela app)
        try:
            cutoff_48h = int((datetime.now(timezone.utc) - timedelta(hours=48)).timestamp())
            cutoff_24h = int((datetime.now(timezone.utc) - timedelta(hours=24)).timestamp())
            result = await session.execute(
                select(MarketCandle)
                .where(MarketCandle.symbol == "BTCUSDT")
                .where(MarketCandle.timeframe == "1h")
                .where(MarketCandle.timestamp >= cutoff_48h)
                .order_by(MarketCandle.timestamp)
            )
            candles_48h = result.scalars().all()
            recent_vol   = sum(c.volume for c in candles_48h if c.timestamp >= cutoff_24h)
            previous_vol = sum(c.volume for c in candles_48h if c.timestamp < cutoff_24h)
            if previous_vol > 0:
                ctx["volume_24h_change_pct"] = round(
                    (recent_vol - previous_vol) / previous_vol * 100, 1
                )
        except Exception as e:
            logger.warning(f"[biel/context] Volume change: {e}")

        # ── Candle mais recente (TRADE model) ─────────────────────────────
        try:
            result = await session.execute(
                select(MarketCandle)
                .where(MarketCandle.symbol == "BTCUSDT")
                .where(MarketCandle.timeframe == "1h")
                .order_by(desc(MarketCandle.timestamp))
                .limit(1)
            )
            c = result.scalar_one_or_none()
            if c:
                ctx["last_candle"] = {
                    "open":   round(c.open, 2),
                    "high":   round(c.high, 2),
                    "low":    round(c.low, 2),
                    "close":  round(c.close, 2),
                    "volume": c.volume,
                }
        except Exception as e:
            logger.warning(f"[biel/context] Last candle: {e}")

        ctx["timestamp"] = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        return ctx
