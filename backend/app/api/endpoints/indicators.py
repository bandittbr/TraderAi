"""
TradeAI - Endpoints: Indicadores e Análise Técnica (Fase 3)

Rotas HTTP:
  GET /api/v1/indicators/latest   → indicadores mais recentes de um ativo
  GET /api/v1/indicators/history  → histórico de indicadores
  GET /api/v1/analysis/summary    → análise completa (indicadores + análise + sinal + score)
"""

from fastapi import APIRouter, Query, HTTPException, status
from app.schemas.indicators import (
    IndicatorData,
    IndicatorResponse,
    AnalysisSummaryResponse,
    AnalysisData,
    SignalData,
    ScoreBreakdown,
)
from app.services.indicators.calculator import indicator_calculator
from app.services.analysis.analysis_engine import analyze
from app.services.analysis.signal_engine   import generate_signal
from app.services.market_data.store        import store
from app.services.market_data.market_score import calculate_market_score
from app.services.market_context.context_engine import context_engine
from app.logger import get_logger

logger = get_logger(__name__)

router          = APIRouter()
analysis_router = APIRouter()

# ── Configuração ──────────────────────────────────────────────────────────────

SUPPORTED_SYMBOLS  = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
VALID_TIMEFRAMES   = {"15m", "30m", "1h"}


def _validate_symbol(symbol: str) -> str:
    sym = symbol.upper()
    if sym not in SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Símbolo '{sym}' não suportado.",
        )
    return sym


def _validate_timeframe(timeframe: str) -> str:
    tf = timeframe.lower()
    if tf not in VALID_TIMEFRAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Timeframe '{tf}' inválido. Use: {sorted(VALID_TIMEFRAMES)}",
        )
    return tf


# ── GET /indicators/latest ────────────────────────────────────────────────────

@router.get(
    "/latest",
    response_model=IndicatorData,
    summary="Indicadores técnicos mais recentes",
)
async def get_latest_indicators(
    symbol:    str = Query("BTCUSDT", description="Ex: BTCUSDT, ETHUSDT"),
    timeframe: str = Query("1h",      description="15m | 30m | 1h"),
) -> IndicatorData:
    """
    Retorna os indicadores técnicos calculados mais recentes para o par informado.
    Os indicadores são atualizados pelo scheduler a cada 60 segundos.
    """
    sym = _validate_symbol(symbol)
    tf  = _validate_timeframe(timeframe)

    ind = await indicator_calculator.get_latest(sym, tf)
    if ind is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Indicadores ainda não calculados. Aguarde a inicialização do sistema.",
        )

    return IndicatorData(
        timestamp      = ind.timestamp,
        rsi            = ind.rsi,
        ema_9          = ind.ema_9,
        ema_21         = ind.ema_21,
        ema_50         = ind.ema_50,
        ema_200        = ind.ema_200,
        macd           = ind.macd,
        macd_signal    = ind.macd_signal,
        macd_histogram = ind.macd_histogram,
        atr            = ind.atr,
    )


# ── GET /indicators/history ───────────────────────────────────────────────────

@router.get(
    "/history",
    response_model=list[IndicatorResponse],
    summary="Histórico de indicadores técnicos",
)
async def get_indicators_history(
    symbol:    str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    limit:     int = Query(100, ge=1, le=500),
) -> list[IndicatorResponse]:
    """Retorna o histórico de indicadores em ordem cronológica crescente."""
    sym = _validate_symbol(symbol)
    tf  = _validate_timeframe(timeframe)

    rows = await indicator_calculator.get_history(sym, tf, limit=limit)

    return [
        IndicatorResponse(
            id             = r.id,
            symbol         = r.symbol,
            timeframe      = r.timeframe,
            timestamp      = r.timestamp,
            rsi            = r.rsi,
            ema_9          = r.ema_9,
            ema_21         = r.ema_21,
            ema_50         = r.ema_50,
            ema_200        = r.ema_200,
            macd           = r.macd,
            macd_signal    = r.macd_signal,
            macd_histogram = r.macd_histogram,
            atr            = r.atr,
        )
        for r in rows
    ]


# ── GET /analysis/summary ─────────────────────────────────────────────────────

@analysis_router.get(
    "/summary",
    response_model=AnalysisSummaryResponse,
    summary="Análise técnica completa (indicadores + análise + sinal + score)",
)
async def get_analysis_summary(
    symbol:    str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
) -> AnalysisSummaryResponse:
    """
    Retorna a análise técnica completa para o ativo/timeframe solicitado:
      • Valores dos indicadores (RSI, EMAs, MACD, ATR)
      • Resumo qualitativo (Trend, Momentum, Volatility)
      • Sinal direcional (BUY/SELL/NEUTRAL) com confiança e justificativas
      • Market Score V2 com breakdown por dimensão
    """
    sym = _validate_symbol(symbol)
    tf  = _validate_timeframe(timeframe)

    # ── Indicadores ───────────────────────────────────────────────────────────
    ind = await indicator_calculator.get_latest(sym, tf)
    if ind is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Indicadores não disponíveis. Aguarde a inicialização do sistema.",
        )

    # ── Preço atual para cálculos de ATR% ─────────────────────────────────────
    stat = await store.get_stats(sym)
    current_price = float(stat.price) if stat else 0.0

    # ── Contexto de mercado (Fase 5) — não bloqueia se falhar ────────────────
    try:
        ctx = await context_engine.calculate(sym)
    except Exception:
        ctx = None

    # ── Análise e sinal com contexto injetado ─────────────────────────────────
    analysis_result = analyze(ind, current_price, context=ctx)
    signal_result   = generate_signal(ind, current_price, context=ctx)

    # ── Market Score V2 ───────────────────────────────────────────────────────
    candles    = await store.get_candles(sym, tf, limit=50)
    score_v2   = calculate_market_score(candles, indicator=ind, symbol=sym)

    return AnalysisSummaryResponse(
        symbol    = sym,
        timeframe = tf,
        indicators = IndicatorData(
            timestamp      = ind.timestamp,
            rsi            = ind.rsi,
            ema_9          = ind.ema_9,
            ema_21         = ind.ema_21,
            ema_50         = ind.ema_50,
            ema_200        = ind.ema_200,
            macd           = ind.macd,
            macd_signal    = ind.macd_signal,
            macd_histogram = ind.macd_histogram,
            atr            = ind.atr,
        ),
        analysis = AnalysisData(
            trend             = analysis_result.trend,
            momentum          = analysis_result.momentum,
            volatility        = analysis_result.volatility,
            news_sentiment    = analysis_result.news_sentiment,
            fear_greed_label  = analysis_result.fear_greed_label,
            fear_greed_value  = analysis_result.fear_greed_value,
            funding_label     = analysis_result.funding_label,
            context_score     = analysis_result.context_score,
            context_label     = analysis_result.context_label,
        ),
        signal = SignalData(
            signal        = signal_result.signal,
            confidence    = signal_result.confidence,
            reasons       = signal_result.reasons,
            context_boost = signal_result.context_boost,
        ),
        score = ScoreBreakdown(
            trend_score      = score_v2.trend_score,
            momentum_score   = score_v2.momentum_score,
            volume_score     = score_v2.volume_score,
            volatility_score = score_v2.volatility_score,
            total_score      = score_v2.total_score,
        ),
    )
