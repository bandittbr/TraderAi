"""
TradeAI - Schemas Pydantic: Dados de Mercado
DTOs de request/response para todos os endpoints de mercado.
Os tipos espelham exatamente os tipos TypeScript em frontend/src/types/index.ts.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ── Candles ───────────────────────────────────────────────────────────────────

class CandleResponse(BaseModel):
    """
    Candle OHLCV formatado para o frontend.
    O campo `time` é em segundos Unix — formato exigido pelo lightweight-charts.
    """
    time: int = Field(..., description="Timestamp Unix em segundos")
    open: float
    high: float
    low: float
    close: float
    volume: float


# ── Estatísticas 24h ──────────────────────────────────────────────────────────

class MarketStatsResponse(BaseModel):
    """
    Estatísticas 24h de um ativo + Market Score V2 com breakdown.
    Fase 3: adicionados trend_score, momentum_score, volume_score, volatility_score.
    """
    symbol:           str
    price:            float
    change_24h:       float   = Field(..., description="Variação percentual em 24h")
    volume_24h:       float
    high_24h:         float
    low_24h:          float
    market_score:     int     = Field(..., ge=0, le=100, description="Score total 0-100")
    trend_score:      float   = Field(default=0.0, description="Score de tendência 0-35")
    momentum_score:   float   = Field(default=0.0, description="Score de momentum 0-25")
    volume_score:     float   = Field(default=0.0, description="Score de volume 0-25")
    volatility_score: float   = Field(default=0.0, description="Score de volatilidade 0-15")
    updated_at:       datetime


# ── Preço simples ─────────────────────────────────────────────────────────────

class PriceResponse(BaseModel):
    """Preço atual de um ativo."""
    symbol: str
    price: float
    timestamp: datetime


# ── Símbolos disponíveis ──────────────────────────────────────────────────────

class SymbolInfo(BaseModel):
    """Metadados de um ativo negociável."""
    symbol: str
    name: str
    active: bool


# ── WebSocket ─────────────────────────────────────────────────────────────────

class WsPriceUpdate(BaseModel):
    """
    Payload enviado via WebSocket ao frontend em tempo real.
    Fase 4+: adicionar bid, ask, funding_rate.
    """
    type: str = "price_update"
    symbol: str
    price: float
    open: float
    high: float
    low: float
    volume: float
    timestamp: int = Field(..., description="Epoch em milissegundos (Binance padrão)")
