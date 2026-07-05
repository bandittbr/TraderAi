"""
TradeAI - Roteador Principal da API
Agrega todos os sub-roteadores dos endpoints.
"""

from fastapi import APIRouter
from app.api.endpoints import (
    health, market, indicators, paper_trading, market_context,
    analytics, market_structure, smart_money, optimizer, alpha,
    robustness, strategies, trade_management, scalper, biel,
)

# Roteador raiz -- prefixo /api/v1 aplicado no main.py
router = APIRouter()

# -- Fase 1: Sistema -------------------------------------------------------
router.include_router(health.router,           prefix="/system",     tags=["Sistema"])

# -- Fase 2: Mercado (HTTP) ------------------------------------------------
router.include_router(market.router,           prefix="/market",     tags=["Mercado"])

# -- Fase 2: WebSocket (sem prefixo /market) --------------------------------
router.include_router(market.ws_router,        prefix="",            tags=["WebSocket"])

# -- Fase 3: Indicadores e Analise -----------------------------------------
router.include_router(indicators.router,          prefix="/indicators", tags=["Indicadores"])
router.include_router(indicators.analysis_router, prefix="/analysis",   tags=["Analise"])

# -- Fase 4: Paper Trading e Backtest ---------------------------------------
router.include_router(paper_trading.router,          prefix="/paper",   tags=["Paper Trading"])
router.include_router(paper_trading.backtest_router, prefix="/backtest", tags=["Backtest"])

# -- Fase 5: Market Context (Noticias, F&G, Funding, OI) -------------------
router.include_router(market_context.router, prefix="/context", tags=["Market Context"])

# -- Fase 6: Signal Analytics ----------------------------------------------
router.include_router(analytics.router, tags=["Analytics"])

# -- Fase 6.5: Market Structure --------------------------------------------
router.include_router(market_structure.router, prefix="/structure", tags=["Market Structure"])

# -- Fase 7: Smart Money & Liquidity ---------------------------------------
router.include_router(smart_money.router, prefix="/smc", tags=["Smart Money"])

# -- Fase 8: Adaptive Optimizer --------------------------------------------
router.include_router(optimizer.router, prefix="/optimizer", tags=["Optimizer"])

# -- Fase 9: Alpha Discovery Engine ----------------------------------------
router.include_router(alpha.router, prefix="/alpha", tags=["Alpha"])

# -- Fase 10: Walk Forward Validation Engine --------------------------------
router.include_router(robustness.router, prefix="/robustness", tags=["Robustness"])

# -- Fase 11: Strategy Evolution Engine ------------------------------------
router.include_router(strategies.router, prefix="/strategies", tags=["Strategies"])

# -- Fase 12: Trade Management Engine --------------------------------------
router.include_router(trade_management.router, prefix="/trade-management", tags=["Trade Management"])

# -- Fase 13: Scalper Engine ------------------------------------------
router.include_router(scalper.router, prefix="/scalper", tags=["Scalper"])

# -- Fase 14: Biel Instagram Agent ------------------------------------
router.include_router(biel.router, prefix="/biel", tags=["Biel"])

# -- Placeholders ----------------------------------------------------------
# router.include_router(broker.router,   prefix="/broker",   tags=["Corretora"])
# router.include_router(ai.router,       prefix="/ai",       tags=["IA"])
