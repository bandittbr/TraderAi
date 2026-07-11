"""
TradeAI - Scheduler de Dados de Mercado (Phase 6)
Background tasks:
  1. Sincronizacao inicial de candles historicos (Binance REST).
  2. Loop periodico de atualizacao de candles (1 min).
  3. Loop periodico de estatisticas 24h (30s).
  4. WebSocket Binance -> broadcast para clientes frontend.
  5. [Fase 3] Loop de calculo de indicadores tecnicos (60s).
  6. [Fase 5] Noticias RSS (15min), Fear & Greed (1h), Funding/OI (5min).
  7. [Phase 6] Classificacao de regime + signal tracking + expire loop.
"""

import asyncio
import json
import websockets
from app.services.market_data.fetcher import fetcher
from app.services.market_data.store import store
from app.services.indicators.calculator import indicator_calculator
from app.services.websocket.manager import ws_manager
from app.services.analysis.analysis_engine import analyze
from app.services.analysis.signal_engine   import generate_signal
from app.services.paper_trading.trade_engine import trade_engine, SignalInput
from app.services.news.news_fetcher          import news_fetcher
from app.services.news.news_store            import news_store
from app.services.market_context.fear_greed  import fear_greed_service
from app.services.market_context.funding_rate import funding_rate_service
from app.services.market_context.open_interest import open_interest_service
# Phase 6
from app.services.signal_analytics.regime_classifier import classify_regime
from app.services.signal_analytics.signal_tracker    import signal_tracker
from app.logger import get_logger

logger = get_logger(__name__)

# ── Configuracao ──────────────────────────────────────────────────────────────

SYMBOLS              = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "LINKUSDT"]
SYNC_TIMEFRAMES      = ["15m", "30m", "1h"]
INDICATOR_TIMEFRAMES = ["15m", "1h"]

# WebSocket streams construídos dinamicamente a partir de SYMBOLS
_WS_STREAMS = "/".join(f"{s.lower()}@miniTicker" for s in SYMBOLS)
BINANCE_WS_URL = f"wss://data-stream.binance.vision/stream?streams={_WS_STREAMS}"

CANDLE_SYNC_INTERVAL_SECS    = 60
STATS_SYNC_INTERVAL_SECS     = 30
INDICATOR_SYNC_INTERVAL_SECS = 60
BINANCE_WS_RECONNECT_SECS    = 5
NEWS_SYNC_INTERVAL_SECS      = 900
FEAR_GREED_INTERVAL_SECS     = 3600
FUNDING_OI_INTERVAL_SECS     = 300
SIGNAL_EXPIRE_INTERVAL_SECS  = 3600   # Phase 6
INDICATOR_15M_INTERVAL_SECS  = 900    # Phase 13: sync a cada nova vela 15m
INDICATOR_1H_INTERVAL_SECS   = 60     # Phase 13: 1h mais frequente para capturar variações


# ── Sincronizacao REST ────────────────────────────────────────────────────────

async def _sync_candles_for_symbol(symbol: str, limit: int = 5) -> None:
    for tf in SYNC_TIMEFRAMES:
        try:
            raw   = await fetcher.fetch_klines(symbol, tf, limit=limit)
            saved = await store.save_candles(symbol, tf, raw)
            if saved:
                logger.debug(f"[candles] {symbol} {tf}: +{saved} novos candles")
        except Exception as exc:
            logger.warning(f"[candles] Falha {symbol} {tf}: {exc}")


async def _sync_stats_for_symbol(symbol: str) -> None:
    try:
        ticker = await fetcher.fetch_ticker_24h(symbol)
        await store.save_stats(symbol, ticker)
        logger.debug(f"[stats] {symbol}: ${float(ticker.get('lastPrice', 0)):,.2f}")
    except Exception as exc:
        logger.warning(f"[stats] Falha {symbol}: {exc}")


async def _sync_indicators_for_symbol(symbol: str) -> None:
    for tf in INDICATOR_TIMEFRAMES:
        try:
            candles = await store.get_candles(symbol, tf, limit=220)
            if len(candles) < 15:
                logger.debug(f"[indicators] {symbol} {tf}: candles insuficientes ({len(candles)})")
                continue

            ind = await indicator_calculator.calculate_and_save(symbol, tf, candles)
            if ind:
                logger.debug(f"[indicators] {symbol}/{tf} OK")
                await _process_signal_for_paper_trading(symbol, tf, ind)
        except Exception as exc:
            logger.warning(f"[indicators] Falha {symbol} {tf}: {exc}")


# ── Background loops ──────────────────────────────────────────────────────────

async def initial_sync_task() -> None:
    logger.info("Iniciando sincronizacao historica de candles...")
    for symbol in SYMBOLS:
        for tf in SYNC_TIMEFRAMES:
            try:
                raw   = await fetcher.fetch_klines(symbol, tf, limit=220)
                saved = await store.save_candles(symbol, tf, raw)
                logger.info(f"[init] {symbol} {tf}: {saved} candles salvos")
            except Exception as exc:
                logger.warning(f"[init] Falha {symbol} {tf}: {exc}")
        await _sync_stats_for_symbol(symbol)

    logger.info("Sync historico concluido. Calculando indicadores iniciais...")
    for symbol in SYMBOLS:
        await _sync_indicators_for_symbol(symbol)
    logger.info("Indicadores iniciais calculados.")
    # Phase 8: carregar pesos adaptativos salvos (se existirem)
    await _load_optimizer_weights()


async def candle_sync_loop() -> None:
    await initial_sync_task()
    while True:
        await asyncio.sleep(CANDLE_SYNC_INTERVAL_SECS)
        for symbol in SYMBOLS:
            await _sync_candles_for_symbol(symbol, limit=5)


async def stats_sync_loop() -> None:
    await asyncio.sleep(10)
    while True:
        for symbol in SYMBOLS:
            await _sync_stats_for_symbol(symbol)
        await asyncio.sleep(STATS_SYNC_INTERVAL_SECS)


async def indicator_1h_loop() -> None:
    """Phase 13: indicadores 1h — dispara a cada 60s para capturar variações intra-hora."""
    await asyncio.sleep(90)
    while True:
        for symbol in SYMBOLS:
            try:
                candles = await store.get_candles(symbol, "1h", limit=220)
                if len(candles) < 50:
                    continue
                ind = await indicator_calculator.calculate_and_save(symbol, "1h", candles)
                if ind:
                    await _process_signal_for_paper_trading(symbol, "1h", ind)
            except Exception as exc:
                logger.warning(f"[1h-loop] {symbol}: {exc}")
        await asyncio.sleep(INDICATOR_1H_INTERVAL_SECS)


async def indicator_15m_loop() -> None:
    """Phase 13: indicadores 15m — dispara a cada 900s (1 vela = 15 min)."""
    await asyncio.sleep(150)  # offset para não colidir com 1h
    while True:
        for symbol in SYMBOLS:
            try:
                candles = await store.get_candles(symbol, "15m", limit=220)
                if len(candles) < 50:
                    continue
                ind = await indicator_calculator.calculate_and_save(symbol, "15m", candles)
                if ind:
                    await _process_signal_for_paper_trading(symbol, "15m", ind)
            except Exception as exc:
                logger.warning(f"[15m-loop] {symbol}: {exc}")
        await asyncio.sleep(INDICATOR_15M_INTERVAL_SECS)


async def indicator_sync_loop() -> None:
    """Mantido para compatibilidade — delega aos loops especializados."""
    await asyncio.sleep(90)
    while True:
        for symbol in SYMBOLS:
            await _sync_indicators_for_symbol(symbol)
        await asyncio.sleep(INDICATOR_SYNC_INTERVAL_SECS)


async def binance_ws_loop() -> None:
    while True:
        try:
            logger.info("Conectando ao WebSocket da Binance...")
            async with websockets.connect(BINANCE_WS_URL, ping_interval=20) as ws:
                logger.info("WebSocket Binance: conectado.")
                async for raw_message in ws:
                    try:
                        data   = json.loads(raw_message)
                        ticker = data.get("data", {})
                        if ticker.get("e") != "24hrMiniTicker":
                            continue
                        payload = {
                            "type":      "price_update",
                            "symbol":    ticker["s"],
                            "price":     float(ticker["c"]),
                            "open":      float(ticker["o"]),
                            "high":      float(ticker["h"]),
                            "low":       float(ticker["l"]),
                            "volume":    float(ticker["v"]),
                            "timestamp": ticker["E"],
                        }
                        await ws_manager.broadcast(payload)
                    except (json.JSONDecodeError, KeyError, ValueError) as exc:
                        logger.debug(f"[binance-ws] Mensagem invalida: {exc}")
        except asyncio.CancelledError:
            logger.info("WebSocket Binance: encerrado.")
            break
        except Exception as exc:
            logger.error(
                f"WebSocket Binance: desconectado ({exc}). "
                f"Reconectando em {BINANCE_WS_RECONNECT_SECS}s..."
            )
            await asyncio.sleep(BINANCE_WS_RECONNECT_SECS)


# ── Fase 5: Market Context loops ──────────────────────────────────────────────

async def news_sync_loop() -> None:
    await asyncio.sleep(30)
    while True:
        try:
            articles = await news_fetcher.fetch_all()
            saved    = await news_store.save_articles(articles)
            if saved:
                logger.info(f"[news] {saved} novas noticias salvas")
        except Exception as exc:
            logger.warning(f"[news] Falha no sync: {exc}")
        await asyncio.sleep(NEWS_SYNC_INTERVAL_SECS)


async def fear_greed_sync_loop() -> None:
    await asyncio.sleep(20)
    while True:
        try:
            await fear_greed_service.fetch_and_save()
        except Exception as exc:
            logger.warning(f"[fear_greed] Falha no sync: {exc}")
        await asyncio.sleep(FEAR_GREED_INTERVAL_SECS)


async def funding_oi_sync_loop() -> None:
    await asyncio.sleep(40)
    while True:
        try:
            await funding_rate_service.fetch_and_save_all()
            await open_interest_service.fetch_and_save_all()
        except Exception as exc:
            logger.warning(f"[funding/oi] Falha no sync: {exc}")
        await asyncio.sleep(FUNDING_OI_INTERVAL_SECS)


# ── Phase 6: Signal expire loop ───────────────────────────────────────────────

async def signal_expire_loop() -> None:
    """[Phase 6] Expira sinais OPEN mais velhos que MAX_OPEN_HOURS."""
    await asyncio.sleep(60)
    while True:
        try:
            expired = await signal_tracker.expire_old_open_signals()
            if expired:
                logger.info(f"[signal_expire] {expired} sinais marcados MISSED")
        except Exception as exc:
            logger.warning(f"[signal_expire] Falha: {exc}")
        await asyncio.sleep(SIGNAL_EXPIRE_INTERVAL_SECS)


# ── Phase 6: _process_signal_for_paper_trading (atualizado) ──────────────────

async def _save_regime_to_db(symbol: str, tf: str, regime_result) -> None:
    """Persiste regime classificado no banco de dados."""
    from app.database import AsyncSessionLocal
    from app.models.analytics import MarketRegime
    async with AsyncSessionLocal() as db:
        record = MarketRegime(
            symbol              = symbol,
            timeframe           = tf,
            regime              = regime_result.regime,
            confidence          = regime_result.confidence,
            ema_alignment_score = regime_result.ema_alignment_score,
            atr_pct             = regime_result.atr_pct,
            price_vs_ema200_pct = regime_result.price_vs_ema200_pct,
            ema9_vs_ema21_pct   = regime_result.ema9_vs_ema21_pct,
            rsi                 = regime_result.rsi,
        )
        db.add(record)
        await db.commit()


async def _process_signal_for_paper_trading(symbol: str, tf: str, ind) -> None:
    """
    Phase 6: classifica regime, gera sinal adaptativo,
    grava em signal_history e envia ao TradeEngine.
    """
    try:
        from app.services.market_data.store import store as _store
        stat = await _store.get_stats(symbol)
        if stat is None:
            return

        price = stat.price

        # Phase 6: Classificar regime
        regime_result = classify_regime(ind, price)
        try:
            await _save_regime_to_db(symbol, tf, regime_result)
        except Exception:
            pass

        # Context (Phase 5 -- opcional)
        context = None
        try:
            from app.services.market_context.context_engine import context_engine
            context = await context_engine.get_context(symbol)
        except Exception:
            pass

        # Market Structure V4 (Phase 6.5 — graceful degradation)
        structure = None
        try:
            from app.services.market_structure.engine import market_structure_engine
            structure = await market_structure_engine.analyze(symbol, tf)
            # Persiste snapshot assincronamente sem bloquear o sinal
            asyncio.create_task(market_structure_engine.save_snapshot(structure))
        except Exception as _se:
            logger.debug("[phase6.5] structure skip: %s", _se)

        # Smart Money V5 (Phase 7 — graceful degradation)
        smc = None
        try:
            from app.services.smart_money.engine import smart_money_engine
            smc = await smart_money_engine.analyze(symbol, tf, structure=structure)
            asyncio.create_task(smart_money_engine.save_snapshot(smc))
        except Exception as _smce:
            logger.debug("[phase7] smc skip: %s", _smce)

        # Phase 8 / V7: Pesos adaptativos por regime (fallback GLOBAL)
        regime_raw   = getattr(regime_result, 'regime', None)
        regime_label = regime_raw.value if hasattr(regime_raw, 'value') else str(regime_raw or "GLOBAL")
        weights      = _resolve_weights_for_regime(regime_label)

        # Analise e Sinal V6 (regime + structure + SMC + weights)
        analysis = analyze(ind, price, context=context)
        signal   = generate_signal(
            ind, price, context=context, regime=regime_result,
            structure=structure, smc=smc, weights=weights,
        )

        # Phase 6/7/8: Gravar sinal no histórico com contexto SMC + V6 scores
        try:
            await signal_tracker.record_signal(
                symbol         = symbol,
                timeframe      = tf,
                signal         = signal.signal,
                confidence     = float(signal.confidence),
                indicator      = ind,
                current_price  = price,
                regime         = regime_result,
                context        = context,
                criteria_met   = signal.criteria_met,
                context_boost  = signal.context_boost,
                smc            = smc,
                structure      = structure,
                raw_score      = signal.raw_score,
                weighted_score = signal.weighted_score,
                weights_version= _weights_version,
            )
        except Exception:
            pass

        # Paper Trading — Phase 12: passa contexto completo ao TradeManager
        await trade_engine.process_signal(SignalInput(
            symbol     = symbol,
            timeframe  = tf,
            signal     = signal.signal,
            confidence = signal.confidence,
            trend      = analysis.trend,
            price      = price,
            context    = context,
            regime     = regime_result,
            structure  = structure,
            smc        = smc,
        ))

        # V7 — Worker Agent 24/7 (quando timeframe = 1h)
        if tf == "1h":
            try:
                from app.services.worker.trade_engine import worker_engine
                # Worker usa 1h para direção + 15m para entrada
                # FIX: store.get_indicator_15m não existia — o Worker sempre caía
                # no fallback e usava o indicador 1h como se fosse 15m.
                ind_15m = None
                try:
                    ind_15m = await indicator_calculator.get_latest(symbol, "15m")
                except Exception:
                    pass
                await worker_engine.process_signal(
                    symbol=symbol, price_1h=ind, price_15m=ind_15m or ind,
                    regime=regime_result, context=context,
                    structure=structure, smc=smc, weights=weights,
                    current_price=price,  # FIX: MarketIndicator não tem .close/.price
                )
            except Exception as _we:
                logger.debug("[worker] skip: %s", _we)

        struct_label = structure.structure_label if structure else "N/A"
        liq_score    = smc.liquidity_score if smc else 0
        logger.debug(
            f"[phase8] {symbol}/{tf} regime={regime_result.regime.value} "
            f"struct={struct_label} liq={liq_score:.0f} "
            f"signal={signal.signal} conf={signal.confidence}% "
            f"engine={signal.engine_version} raw={signal.raw_score:.1f} w={signal.weighted_score:.1f}"
        )

    except Exception as exc:
        logger.warning(f"[paper_trading] Falha ao processar sinal {symbol}: {exc}")


# ── Entry point ───────────────────────────────────────────────────────────────

async def start_background_tasks() -> list:
    """
    Inicia todas as tarefas de background.
    Chamado no lifespan do FastAPI (main.py).
    """
    tasks = [
        asyncio.create_task(candle_sync_loop(),       name="candle_sync"),
        asyncio.create_task(stats_sync_loop(),        name="stats_sync"),
        asyncio.create_task(binance_ws_loop(),        name="binance_ws"),
        # Phase 13: loops especializados de indicadores (1h + 15m)
        # NOTA: indicator_sync_loop (antigo) foi removido — coberto pelos especializados
        asyncio.create_task(indicator_1h_loop(),      name="indicator_1h"),
        asyncio.create_task(indicator_15m_loop(),     name="indicator_15m"),  # Phase 13
        asyncio.create_task(news_sync_loop(),         name="news_sync"),
        asyncio.create_task(fear_greed_sync_loop(),   name="fear_greed_sync"),
        asyncio.create_task(funding_oi_sync_loop(),   name="funding_oi_sync"),
        asyncio.create_task(signal_expire_loop(),     name="signal_expire"),  # Phase 6
        asyncio.create_task(optimizer_sync_loop(),    name="optimizer_sync"),  # Phase 8
        asyncio.create_task(alpha_sync_loop(),         name="alpha_sync"),        # Phase 9
        asyncio.create_task(robustness_sync_loop(),   name="robustness_sync"),   # Phase 10
        asyncio.create_task(strategy_sync_loop(),    name="strategy_sync"),     # Phase 11
    ]
    logger.info(f"Background tasks iniciadas: {[t.get_name() for t in tasks]}")
    return tasks

# ── Phase 8: Optimizer sync loop ─────────────────────────────────────────────

OPTIMIZER_SYNC_INTERVAL_SECS = 21600   # 6 horas

# Cache de pesos em memória (recarregado a cada ciclo do optimizer)
# V7: {regime: {criterion: weight}} — permite selecionar por regime
_cached_regime_weights: dict[str, dict[str, float]] = {}
_cached_weights_fallback: dict[str, float] = {}   # GLOBAL fallback
_weights_version: int = 0


async def _load_optimizer_weights() -> dict:
    """Carrega pesos adaptativos do banco (Phase 8 / V7: por regime)."""
    global _cached_regime_weights, _cached_weights_fallback, _weights_version
    try:
        from app.services.optimizer.weight_engine import weight_engine
        regime_weights = await weight_engine.load_all_regime_weights()
        _cached_regime_weights  = regime_weights
        _cached_weights_fallback = regime_weights.get("GLOBAL", {})
        _weights_version += 1
        n_regimes = len(regime_weights)
        n_total   = sum(len(w) for w in regime_weights.values())
        logger.info("[phase8] Pesos V7 carregados: %d regimes, %d critérios total", n_regimes, n_total)
        return _cached_weights_fallback
    except Exception as e:
        logger.debug("[phase8] weight load skip: %s", e)
        _cached_regime_weights = {}
        _cached_weights_fallback = {}
        return {}


def _resolve_weights_for_regime(regime_value: str) -> dict[str, float] | None:
    """
    V7: Retorna os pesos apropriados para o regime dado.
    Busca no cache por regime; fallback para GLOBAL.
    """
    if not _cached_regime_weights:
        return _cached_weights_fallback or None
    # Tenta o regime exato (ex: "BULL", "BEAR", "HIGH_VOLATILITY")
    regime_key = str(regime_value)
    if regime_key in _cached_regime_weights:
        return _cached_regime_weights[regime_key]
    # UNKNOWN fallback para SIDEWAYS
    if regime_key == "UNKNOWN" and "SIDEWAYS" in _cached_regime_weights:
        return _cached_regime_weights["SIDEWAYS"]
    # Fallback para GLOBAL
    return _cached_regime_weights.get("GLOBAL", _cached_weights_fallback) or None


async def optimizer_sync_loop() -> None:
    """[Phase 8] Roda ciclo de otimização a cada 6h."""
    await asyncio.sleep(120)  # aguarda dados iniciais
    while True:
        try:
            from app.services.optimizer.optimizer_engine import optimizer_engine
            await optimizer_engine.run(save_snapshot=True)
            await _load_optimizer_weights()
            logger.info("[phase8] Ciclo de otimização concluído.")
        except Exception as exc:
            logger.warning("[phase8] optimizer_sync_loop: %s", exc)
        await asyncio.sleep(OPTIMIZER_SYNC_INTERVAL_SECS)


async def alpha_sync_loop() -> None:
    """[Phase 9] Roda ciclo do Alpha Discovery Engine a cada 12h."""
    await asyncio.sleep(180)  # aguarda dados consolidados
    while True:
        try:
            from app.services.alpha.alpha_engine import alpha_engine
            result = await alpha_engine.run(lookback_days=90)
            logger.info("[phase9] alpha_sync concluído: %d padrões", result.get("n_patterns", 0) if isinstance(result, dict) else 0)
        except Exception as exc:
            logger.warning("[phase9] alpha_sync_loop: %s", exc)
        await asyncio.sleep(43200)  # 12 horas




ROBUSTNESS_SYNC_INTERVAL_SECS = 86400   # 24 horas


async def robustness_sync_loop() -> None:
    """[Phase 10] Roda ciclo de robustez a cada 24h."""
    await asyncio.sleep(300)
    while True:
        try:
            from app.services.robustness.robustness_engine import robustness_engine
            report = await robustness_engine.run(persist=True)
            logger.info(
                "[phase10] robustness_sync concluido: score=%.1f (%s)",
                report.robustness_score, report.interpretation,
            )
        except Exception as exc:
            logger.warning("[phase10] robustness_sync_loop: %s", exc)
        await asyncio.sleep(ROBUSTNESS_SYNC_INTERVAL_SECS)


STRATEGY_SYNC_INTERVAL_SECS = 86400   # 24 horas


async def strategy_sync_loop() -> None:
    """[Phase 11] Roda ciclo de descoberta de estrategias a cada 24h."""
    await asyncio.sleep(600)
    while True:
        try:
            from app.services.strategy.strategy_engine import strategy_engine
            report = await strategy_engine.run(
                generate_new=True, evolve=True, validate_rob=False, batch=200,
            )
            logger.info(
                "[phase11] strategy_sync concluido: gen=%d eval=%d evo=%d top=%.1f",
                report.n_generated, report.n_evaluated,
                report.n_evolved, report.top_score,
            )
        except Exception as exc:
            logger.warning("[phase11] strategy_sync_loop: %s", exc)
        await asyncio.sleep(STRATEGY_SYNC_INTERVAL_SECS)
