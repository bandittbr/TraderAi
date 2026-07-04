"""
TradeAI - Schemas Pydantic: Indicadores e Análise Técnica (Fase 3)
DTOs de request/response para os endpoints de indicadores e análise.
Espelham os tipos TypeScript em frontend/src/types/index.ts.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional


# ── Indicadores ───────────────────────────────────────────────────────────────

class IndicatorData(BaseModel):
    """Valores calculados de todos os indicadores técnicos para um candle."""
    timestamp:      int           = Field(..., description="Epoch seconds")
    rsi:            Optional[float] = None
    ema_9:          Optional[float] = None
    ema_21:         Optional[float] = None
    ema_50:         Optional[float] = None
    ema_200:        Optional[float] = None
    macd:           Optional[float] = None
    macd_signal:    Optional[float] = None
    macd_histogram: Optional[float] = None
    atr:            Optional[float] = None


class IndicatorResponse(IndicatorData):
    """IndicatorData com campos de identificação para o endpoint de histórico."""
    id:        int
    symbol:    str
    timeframe: str


# ── Análise ───────────────────────────────────────────────────────────────────

TrendLabel      = Literal["Strong Bullish", "Bullish", "Sideways", "Bearish", "Strong Bearish"]
MomentumLabel   = Literal["Strong", "Neutral", "Weak"]
VolatilityLabel = Literal["Low", "Medium", "High"]
SignalType      = Literal["BUY", "SELL", "NEUTRAL"]


class AnalysisData(BaseModel):
    """Resumo qualitativo da análise técnica."""
    trend:      TrendLabel
    momentum:   MomentumLabel
    volatility: VolatilityLabel


class SignalData(BaseModel):
    """Sinal direcional gerado pelo Signal Engine."""
    signal:     SignalType
    confidence: int   = Field(..., ge=0, le=100)
    reasons:    list[str]


class ScoreBreakdown(BaseModel):
    """Market Score V2 com detalhamento por dimensão."""
    trend_score:      float = Field(..., ge=0, le=35)
    momentum_score:   float = Field(..., ge=0, le=25)
    volume_score:     float = Field(..., ge=0, le=25)
    volatility_score: float = Field(..., ge=0, le=15)
    total_score:      int   = Field(..., ge=0, le=100)


class AnalysisSummaryResponse(BaseModel):
    """
    Resposta completa do endpoint GET /analysis/summary.
    Agrega indicadores, análise qualitativa, sinal e score V2.
    """
    symbol:     str
    timeframe:  str
    indicators: IndicatorData
    analysis:   AnalysisData
    signal:     SignalData
    score:      ScoreBreakdown


# ── Schema atualizado para /market/stats (V2) ─────────────────────────────────

class MarketStatsResponse(BaseModel):
    """Estatísticas 24h + Market Score V2 com breakdown."""
    symbol:           str
    price:            float
    change_24h:       float = Field(..., description="Variação percentual em 24h")
    volume_24h:       float
    high_24h:         float
    low_24h:          float
    market_score:     int   = Field(..., ge=0, le=100, description="Score total 0-100")
    trend_score:      float = Field(default=0.0, ge=0, le=35)
    momentum_score:   float = Field(default=0.0, ge=0, le=25)
    volume_score:     float = Field(default=0.0, ge=0, le=25)
    volatility_score: float = Field(default=0.0, ge=0, le=15)
    updated_at:       str   # ISO 8601
