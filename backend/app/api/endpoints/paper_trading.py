"""
TradeAI - Endpoints: Paper Trading e Backtest (Fase 4)

Rotas HTTP:
  GET  /api/v1/paper/account         → estado da conta virtual
  GET  /api/v1/paper/trades          → lista de trades (com filtro de status)
  GET  /api/v1/paper/stats           → métricas de performance
  POST /api/v1/backtest/run          → executa backtest e retorna resultado
  GET  /api/v1/backtest/results      → último resultado de backtest em cache
"""

from fastapi import APIRouter, Query, HTTPException, status
from app.schemas.paper_trading import (
    PaperAccountResponse,
    PaperTradeResponse,
    PaperStatsResponse,
    BacktestRequest,
    BacktestResultResponse,
    BacktestTradeItem,
)
from app.services.paper_trading.trade_engine  import trade_engine
from app.services.backtesting.backtest_engine import backtest_engine
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

router          = APIRouter()
backtest_router = APIRouter()

# Cache em memória do último resultado de backtest (por chave symbol+days)
_backtest_cache: dict[str, BacktestResultResponse] = {}

VALID_SYMBOLS  = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
VALID_PERIODS  = {7, 30, 90, 180}


# ── Paper Trading ─────────────────────────────────────────────────────────────

@router.get(
    "/account",
    response_model=PaperAccountResponse,
    summary="Estado da conta virtual de paper trading",
)
async def get_paper_account() -> PaperAccountResponse:
    account = await trade_engine.get_account()
    if account is None:
        # Cria conta na primeira consulta
        from app.database import AsyncSessionLocal
        from app.models.paper_trading import PaperAccount
        async with AsyncSessionLocal() as session:
            acc = PaperAccount(
                balance=settings.paper_initial_balance,
                initial_balance=settings.paper_initial_balance,
            )
            session.add(acc)
            await session.commit()
            await session.refresh(acc)
            account = acc

    pnl_total = account.balance - account.initial_balance
    pnl_pct   = ((account.balance / account.initial_balance) - 1) * 100 if account.initial_balance else 0.0

    return PaperAccountResponse(
        id              = account.id,
        balance         = account.balance,
        initial_balance = account.initial_balance,
        pnl_total       = round(pnl_total, 4),
        pnl_pct         = round(pnl_pct, 4),
        created_at      = account.created_at,
        updated_at      = account.updated_at,
    )


@router.get(
    "/trades",
    response_model=list[PaperTradeResponse],
    summary="Lista de trades simulados",
)
async def get_paper_trades(
    status: str  = Query("ALL", description="ALL | OPEN | CLOSED"),
    limit:  int  = Query(100, ge=1, le=500),
) -> list[PaperTradeResponse]:
    all_trades = await trade_engine.get_all_trades(limit=limit)
    st = status.upper()
    if st in ("OPEN", "CLOSED"):
        all_trades = [t for t in all_trades if t.status == st]
    return [PaperTradeResponse.model_validate(t) for t in all_trades]


@router.get(
    "/stats",
    response_model=PaperStatsResponse,
    summary="Métricas de performance do paper trading",
)
async def get_paper_stats() -> PaperStatsResponse:
    m = await trade_engine.get_metrics()
    return PaperStatsResponse(
        total_trades    = m.total_trades,
        open_trades     = m.open_trades,
        closed_trades   = m.closed_trades,
        long_trades     = m.long_trades,
        short_trades    = m.short_trades,
        win_rate        = m.win_rate,
        win_rate_long   = m.win_rate_long,
        win_rate_short  = m.win_rate_short,
        profit_factor   = m.profit_factor,
        avg_gain        = m.avg_gain,
        avg_loss        = m.avg_loss,
        max_drawdown    = m.max_drawdown,
        total_pnl       = m.total_pnl,
        total_pnl_pct   = m.total_pnl_pct,
        current_balance = m.current_balance,
    )


# ── Backtest ──────────────────────────────────────────────────────────────────

@backtest_router.post(
    "/run",
    response_model=BacktestResultResponse,
    summary="Executa backtest sobre candles históricos",
)
async def run_backtest(req: BacktestRequest) -> BacktestResultResponse:
    sym = req.symbol.upper()
    if sym not in VALID_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Símbolo inválido. Disponíveis: {sorted(VALID_SYMBOLS)}",
        )
    if req.period_days not in VALID_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Período inválido. Disponíveis: {sorted(VALID_PERIODS)} dias",
        )

    logger.info(f"[Backtest] Iniciando {sym} {req.period_days}d")
    result = await backtest_engine.run(sym, req.period_days)

    response = BacktestResultResponse(
        symbol         = result.symbol,
        timeframe      = result.timeframe,
        period_days    = result.period_days,
        candles_used   = result.candles_used,
        total_trades   = result.total_trades,
        winning_trades = result.winning_trades,
        losing_trades  = result.losing_trades,
        win_rate       = result.win_rate,
        long_trades    = result.long_trades,
        short_trades   = result.short_trades,
        win_rate_long  = result.win_rate_long,
        win_rate_short = result.win_rate_short,
        pnl_long       = result.pnl_long,
        pnl_short      = result.pnl_short,
        total_pnl      = result.total_pnl,
        total_pnl_pct  = result.total_pnl_pct,
        avg_gain       = result.avg_gain,
        avg_loss       = result.avg_loss,
        profit_factor  = result.profit_factor,
        max_drawdown   = result.max_drawdown,
        started_at     = result.started_at,
        finished_at    = result.finished_at,
        trades         = [BacktestTradeItem(**t) for t in result.trades],
    )

    cache_key = f"{sym}_{req.period_days}"
    _backtest_cache[cache_key] = response
    return response


@router.get(
    "/debug",
    summary="Diagnóstico completo do Paper Trading — gargalos e contadores",
)
async def get_paper_debug() -> dict:
    return await trade_engine.get_debug_stats()


@backtest_router.get(
    "/results",
    response_model=list[BacktestResultResponse],
    summary="Resultados de backtest em cache (última execução por símbolo/período)",
)
async def get_backtest_results(
    symbol:      str = Query(None, description="Filtra por símbolo (opcional)"),
    period_days: int = Query(None, description="Filtra por período (opcional)"),
) -> list[BacktestResultResponse]:
    results = list(_backtest_cache.values())
    if symbol:
        results = [r for r in results if r.symbol == symbol.upper()]
    if period_days:
        results = [r for r in results if r.period_days == period_days]
    return results
