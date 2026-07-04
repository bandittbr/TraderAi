"""
Scalper Scheduler (Fase 13)
Loop dedicado independente — roda a cada 60s para sinais 1m.
Sincroniza candles 1m e 5m separadamente do scheduler principal.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from app.logger import logger
from app.services.market_data.store import MarketDataStore
from app.services.market_data.fetcher import MarketDataFetcher
from app.services.scalper.signal_engine import evaluate_scalper_signal, SCALPER_SYMBOLS
from app.services.scalper.trade_engine import scalper_engine
from app.models.scalper import ScalperSignal
from app.database import AsyncSessionLocal

# ── Constantes ────────────────────────────────────────────────────────────────
SCALPER_LOOP_INTERVAL  = 60     # segundos (1 vela 1m)
SCALPER_SYNC_TIMEFRAMES = ["1m", "5m"]
SCALPER_CANDLES_NEEDED  = {
    "1m":  60,    # 60 candles 1m
    "5m":  40,    # 40 candles 5m
    "15m": 60,    # 60 candles 15m (já sincronizados pelo scheduler principal)
}

store   = MarketDataStore()
fetcher = MarketDataFetcher()


# ── Sync de candles 1m e 5m ──────────────────────────────────────────────────
async def _sync_scalper_candles(symbol: str) -> None:
    """Sincroniza 1m e 5m antes de calcular sinal."""
    for tf in SCALPER_SYNC_TIMEFRAMES:
        try:
            raw   = await fetcher.fetch_klines(symbol, tf, limit=10)
            saved = await store.save_candles(symbol, tf, raw)
            if saved:
                logger.debug(f"[Scalper Sync] {symbol} {tf}: +{saved} candles")
        except Exception as exc:
            logger.warning(f"[Scalper Sync] {symbol} {tf}: {exc}")


# ── Salva sinal no DB ─────────────────────────────────────────────────────────
async def _save_signal(sig, acted_on: bool, reject_reason: str = "") -> None:
    try:
        async with AsyncSessionLocal() as session:
            record = ScalperSignal(
                symbol       = sig.symbol,
                direction    = sig.direction,
                trend_15m    = sig.trend_15m,
                confirm_5m   = sig.confirm_5m,
                entry_1m     = sig.entry_1m,
                confidence   = sig.confidence,
                price        = sig.price,
                rsi_1m       = sig.rsi_1m,
                rsi_5m       = sig.rsi_5m,
                ema9_15m     = sig.ema9_15m,
                ema21_15m    = sig.ema21_15m,
                acted_on     = acted_on,
                reject_reason= reject_reason,
            )
            session.add(record)
            await session.commit()
    except Exception as exc:
        logger.warning(f"[Scalper] Erro ao salvar sinal {sig.symbol}: {exc}")


# ── Loop principal ────────────────────────────────────────────────────────────
async def scalper_main_loop() -> None:
    """
    Roda a cada 60s.
    Para cada símbolo: sync 1m/5m → avalia MTF → processa trade.
    """
    logger.info("[Scalper] Aguardando 30s para sistema estabilizar...")
    await asyncio.sleep(30)

    logger.info("[Scalper] Loop iniciado.")
    while True:
        loop_start = datetime.now(timezone.utc)

        for symbol in SCALPER_SYMBOLS:
            try:
                # 1. Sync candles rápido
                await _sync_scalper_candles(symbol)

                # 2. Busca candles
                c15 = await store.get_candles(symbol, "15m", limit=60)
                c5  = await store.get_candles(symbol, "5m",  limit=40)
                c1  = await store.get_candles(symbol, "1m",  limit=60)

                if len(c15) < 55 or len(c5) < 25 or len(c1) < 36:
                    logger.debug(
                        f"[Scalper] {symbol}: candles insuficientes "
                        f"15m={len(c15)} 5m={len(c5)} 1m={len(c1)}"
                    )
                    continue

                # 3. Avalia sinal MTF
                sig = evaluate_scalper_signal(symbol, c15, c5, c1)

                # 4. Processa no trade engine (inclui gestão de trades abertos)
                await scalper_engine.process_signal(sig)

                # 5. Salva sinal no histórico
                acted = sig.direction in ("LONG", "SHORT")
                await _save_signal(sig, acted_on=acted)

            except Exception as exc:
                logger.warning(f"[Scalper] {symbol}: {exc}")

        # Aguarda até completar 60s
        elapsed = (datetime.now(timezone.utc) - loop_start).total_seconds()
        sleep   = max(0.0, SCALPER_LOOP_INTERVAL - elapsed)
        await asyncio.sleep(sleep)


async def start_scalper() -> list[asyncio.Task]:
    """Chamado no lifespan do FastAPI para iniciar o loop do scalper."""
    tasks = [
        asyncio.create_task(scalper_main_loop(), name="scalper_main"),
    ]
    logger.info("[Scalper] Background task iniciada.")
    return tasks
