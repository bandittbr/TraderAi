"""
TradeAI - IndicatorCalculator (Fase 3)
Orquestra o cálculo de todos os indicadores técnicos a partir de candles
e persiste os resultados na tabela market_indicators (upsert).

Uso:
    from app.services.indicators.calculator import indicator_calculator
    indicator = await indicator_calculator.calculate_and_save("BTCUSDT", "1h", candles)
    latest    = await indicator_calculator.get_latest("BTCUSDT", "1h")
"""

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.indicators import MarketIndicator
from app.models.market import MarketCandle
from app.services.indicators.rsi  import calculate_rsi
from app.services.indicators.ema  import calculate_ema
from app.services.indicators.macd import calculate_macd
from app.services.indicators.atr  import calculate_atr
from app.logger import get_logger

logger = get_logger(__name__)


class IndicatorCalculator:
    """Calcula, persiste e recupera indicadores técnicos."""

    # ── Cálculo e persistência ────────────────────────────────────────────────

    async def calculate_and_save(
        self,
        symbol:    str,
        timeframe: str,
        candles:   list[MarketCandle],
    ) -> MarketIndicator | None:
        """
        Calcula todos os indicadores para a lista de candles e faz upsert no banco.

        Exigências mínimas de candles:
          • RSI-14: 15 candles
          • EMA-200: 200 candles
          • MACD (12/26/9): 34 candles
          • ATR-14: 15 candles

        Para cálculos robustos, recomenda-se 210+ candles.
        Retorna o registro mais recente persistido, ou None em caso de erro.
        """
        if not candles:
            return None

        closes = [float(c.close)  for c in candles]
        highs  = [float(c.high)   for c in candles]
        lows   = [float(c.low)    for c in candles]
        ts     = int(candles[-1].timestamp)

        # ── Cálculos ─────────────────────────────────────────────────────────
        rsi_val         = calculate_rsi(closes)
        ema9_val        = calculate_ema(closes, 9)
        ema21_val       = calculate_ema(closes, 21)
        ema50_val       = calculate_ema(closes, 50)
        ema200_val      = calculate_ema(closes, 200)
        macd_val, signal_val, histogram_val = calculate_macd(closes)
        atr_val         = calculate_atr(highs, lows, closes)

        logger.debug(
            f"[{symbol}/{timeframe}] RSI={rsi_val:.1f} "
            f"EMA9={ema9_val:.2f} MACD={macd_val:.2f} ATR={atr_val:.2f}"
            if all(v is not None for v in [rsi_val, ema9_val, macd_val, atr_val])
            else f"[{symbol}/{timeframe}] Indicadores calculados (dados parciais)"
        )

        # ── Upsert ───────────────────────────────────────────────────────────
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(MarketIndicator).where(
                        MarketIndicator.symbol    == symbol,
                        MarketIndicator.timeframe == timeframe,
                        MarketIndicator.timestamp == ts,
                    )
                )
                existing = result.scalar_one_or_none()

                values: dict = {
                    "symbol":         symbol,
                    "timeframe":      timeframe,
                    "timestamp":      ts,
                    "rsi":            rsi_val,
                    "ema_9":          ema9_val,
                    "ema_21":         ema21_val,
                    "ema_50":         ema50_val,
                    "ema_200":        ema200_val,
                    "macd":           macd_val,
                    "macd_signal":    signal_val,
                    "macd_histogram": histogram_val,
                    "atr":            atr_val,
                }

                if existing:
                    for key, val in values.items():
                        setattr(existing, key, val)
                else:
                    session.add(MarketIndicator(**values))

                await session.commit()

        except Exception as exc:
            logger.error(f"[{symbol}/{timeframe}] Erro ao salvar indicadores: {exc}")
            return None

        return await self.get_latest(symbol, timeframe)

    # ── Leitura ───────────────────────────────────────────────────────────────

    async def get_latest(
        self,
        symbol:    str,
        timeframe: str,
    ) -> MarketIndicator | None:
        """Retorna o indicador mais recente para o par símbolo/timeframe."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MarketIndicator)
                .where(
                    MarketIndicator.symbol    == symbol,
                    MarketIndicator.timeframe == timeframe,
                )
                .order_by(MarketIndicator.timestamp.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_history(
        self,
        symbol:    str,
        timeframe: str,
        limit:     int = 100,
    ) -> list[MarketIndicator]:
        """Retorna histórico de indicadores em ordem cronológica crescente."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MarketIndicator)
                .where(
                    MarketIndicator.symbol    == symbol,
                    MarketIndicator.timeframe == timeframe,
                )
                .order_by(MarketIndicator.timestamp.desc())
                .limit(limit)
            )
            rows = list(result.scalars().all())
            return list(reversed(rows))


# Singleton
indicator_calculator = IndicatorCalculator()
