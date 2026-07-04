"""
TradeAI - Endpoints: Dados de Mercado + WebSocket
Todos os endpoints públicos de mercado e o handler WebSocket para o frontend.

Rotas HTTP:
  GET /api/v1/market/symbols   → lista de ativos suportados
  GET /api/v1/market/price     → preço atual de um símbolo
  GET /api/v1/market/stats     → estatísticas 24h + market score
  GET /api/v1/market/candles   → candles OHLCV paginados

WebSocket:
  WS  /api/v1/ws/market        → stream em tempo real (atualizações de preço)
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, HTTPException, status
from app.schemas.market import (
    CandleResponse,
    MarketStatsResponse,
    PriceResponse,
    SymbolInfo,
)
from app.services.market_data.fetcher import fetcher
from app.services.market_data.store import store
from app.services.market_data.market_score import calculate_market_score
from app.services.indicators.calculator import indicator_calculator
from app.services.websocket.manager import ws_manager
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# ── Configuração ──────────────────────────────────────────────────────────────

# Metadados dos ativos suportados na Fase 2
SUPPORTED_SYMBOLS: dict[str, SymbolInfo] = {
    "BTCUSDT": SymbolInfo(symbol="BTCUSDT", name="Bitcoin",   active=True),
    "ETHUSDT": SymbolInfo(symbol="ETHUSDT", name="Ethereum",  active=True),
    "SOLUSDT": SymbolInfo(symbol="SOLUSDT", name="Solana",    active=True),
    "BNBUSDT": SymbolInfo(symbol="BNBUSDT", name="BNB",       active=True),
    "AVAXUSDT": SymbolInfo(symbol="AVAXUSDT", name="Avalanche", active=True),
    "LINKUSDT": SymbolInfo(symbol="LINKUSDT", name="Chainlink", active=True),
}

# Timeframes disponíveis (45m é calculado internamente por resampling)
VALID_TIMEFRAMES = {"15m", "30m", "45m", "1h"}


def _validate_symbol(symbol: str) -> str:
    sym = symbol.upper()
    if sym not in SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Símbolo '{sym}' não suportado. Disponíveis: {list(SUPPORTED_SYMBOLS.keys())}",
        )
    return sym


def _validate_timeframe(timeframe: str) -> str:
    tf = timeframe.lower()
    if tf not in VALID_TIMEFRAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Timeframe '{tf}' inválido. Disponíveis: {sorted(VALID_TIMEFRAMES)}",
        )
    return tf


# ── HTTP Endpoints ────────────────────────────────────────────────────────────

@router.get(
    "/symbols",
    response_model=list[SymbolInfo],
    summary="Lista ativos suportados",
)
async def get_symbols() -> list[SymbolInfo]:
    """Retorna todos os ativos monitorados na plataforma."""
    return list(SUPPORTED_SYMBOLS.values())


@router.get(
    "/price",
    response_model=PriceResponse,
    summary="Preço atual de um ativo",
)
async def get_price(
    symbol: str = Query("BTCUSDT", description="Ex: BTCUSDT, ETHUSDT"),
) -> PriceResponse:
    """
    Busca o preço atual direto da Binance (endpoint leve /ticker/price).
    Sem cache — sempre retorna o valor mais recente.
    """
    sym = _validate_symbol(symbol)
    try:
        price = await fetcher.fetch_price(sym)
        return PriceResponse(
            symbol=sym,
            price=price,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.error(f"Erro ao buscar preço de {sym}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Falha ao buscar preço na Binance. Tente novamente.",
        )


@router.get(
    "/stats",
    response_model=MarketStatsResponse,
    summary="Estatísticas 24h + Market Score",
)
async def get_stats(
    symbol: str = Query("BTCUSDT", description="Ex: BTCUSDT, ETHUSDT"),
) -> MarketStatsResponse:
    """
    Retorna estatísticas de 24h do banco + Market Score calculado em tempo real.
    Fonte primária: banco SQLite (atualizado a cada 30s pelo scheduler).
    Fallback: Binance REST API (se banco estiver vazio).
    """
    sym = _validate_symbol(symbol)

    # Tenta o banco primeiro (mais rápido)
    stat = await store.get_stats(sym)

    if stat is None:
        # Banco ainda não populado — busca direto da Binance como fallback
        try:
            ticker = await fetcher.fetch_ticker_24h(sym)
            await store.save_stats(sym, ticker)
            stat = await store.get_stats(sym)
        except Exception as exc:
            logger.error(f"Fallback Binance falhou para {sym}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Dados indisponíveis. O sistema está inicializando.",
            )

    # Market Score V2: usa indicadores se disponíveis, senão fallback por candles
    candles   = await store.get_candles(sym, "1h", limit=50)
    indicator = await indicator_calculator.get_latest(sym, "1h")
    score_v2  = calculate_market_score(candles, indicator=indicator, symbol=sym)

    return MarketStatsResponse(
        symbol           = stat.symbol,
        price            = stat.price,
        change_24h       = stat.change_24h,
        volume_24h       = stat.volume_24h,
        high_24h         = stat.high_24h,
        low_24h          = stat.low_24h,
        market_score     = score_v2.total_score,
        trend_score      = score_v2.trend_score,
        momentum_score   = score_v2.momentum_score,
        volume_score     = score_v2.volume_score,
        volatility_score = score_v2.volatility_score,
        updated_at       = stat.updated_at,
    )


@router.get(
    "/candles",
    response_model=list[CandleResponse],
    summary="Candles OHLCV históricos",
)
async def get_candles(
    symbol: str    = Query("BTCUSDT", description="Ex: BTCUSDT, ETHUSDT"),
    timeframe: str = Query("1h",      description="15m | 30m | 45m | 1h"),
    limit: int     = Query(100,       ge=1, le=500, description="Número de candles (máx 500)"),
) -> list[CandleResponse]:
    """
    Retorna candles OHLCV do banco de dados.
    Se o banco estiver vazio para o par solicitado, busca da Binance e armazena.
    Os candles retornados estão em ordem cronológica crescente (exigido pelo frontend).
    O campo `time` está em segundos Unix (padrão lightweight-charts).
    """
    sym = _validate_symbol(symbol)
    tf  = _validate_timeframe(timeframe)

    candles = await store.get_candles(sym, tf, limit=limit)

    # Fallback: banco vazio → busca na Binance
    if not candles:
        logger.info(f"Banco vazio para {sym} {tf}. Buscando da Binance...")
        try:
            raw = await fetcher.fetch_klines(sym, tf, limit=limit)
            await store.save_candles(sym, tf, raw)
            candles = await store.get_candles(sym, tf, limit=limit)
        except Exception as exc:
            logger.error(f"Fallback Binance falhou: {exc}")
            return []

    return [
        CandleResponse(
            time=c.timestamp,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume,
        )
        for c in candles
    ]


# ── WebSocket ─────────────────────────────────────────────────────────────────
# Router separado para o WebSocket — evita conflito com o prefixo /market
ws_router = APIRouter()


@ws_router.websocket("/ws/market")
async def websocket_market(websocket: WebSocket) -> None:
    """
    WebSocket de mercado em tempo real.
    O cliente conecta e recebe atualizações de preço a cada tick da Binance.

    Payload recebido pelo frontend:
    {
      "type": "price_update",
      "symbol": "BTCUSDT",
      "price": 65432.10,
      "open": 65000.00,
      "high": 66000.00,
      "low": 64800.00,
      "volume": 12345.67,
      "timestamp": 1704067200000
    }

    URL de conexão: ws://127.0.0.1:8000/api/v1/ws/market
    Reconexão: responsabilidade do cliente (hook useWebSocket).
    """
    await ws_manager.connect(websocket)
    # Envia snapshot inicial com preços atuais do banco
    try:
        stats_list = await store.get_all_stats()
        for stat in stats_list:
            await ws_manager.send_to(websocket, {
                "type":      "price_update",
                "symbol":    stat.symbol,
                "price":     stat.price,
                "open":      stat.price,
                "high":      stat.high_24h,
                "low":       stat.low_24h,
                "volume":    stat.volume_24h,
                "timestamp": int(stat.updated_at.timestamp() * 1000),
            })
    except Exception as exc:
        logger.warning(f"Falha ao enviar snapshot inicial: {exc}")

    try:
        # Mantém a conexão aberta — aguarda mensagens do cliente (ping/pong)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
