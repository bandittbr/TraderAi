"""
TradeAI - Multi-Agent Trading System
====================================
Sistema de 10 agentes de trading com estratégias diferentes,
cada um rodando em modo simulado (paper) com $100.000 de capital inicial.
"""
from __future__ import annotations

import logging

from app.services.agents.base import BaseAgent, AgentSignal, AgentSide, AgentResult
from app.services.agents.registry import AgentRegistry, agent_registry
from app.services.agents.trade_engine import MultiAgentEngine, multi_agent_engine

# Agentes
from app.services.agents.agent_momentum_rsi import MomentumRSIAgent
from app.services.agents.agent_high_vol import HighVolContinuationAgent
from app.services.agents.agent_ai_combined import AICombinedAnalysisAgent
from app.services.agents.agent_social_sentiment import SocialSentimentAgent
from app.services.agents.agent_portfolio_cycle import PortfolioCycleAgent
from app.services.agents.agent_grid_scalper import GridScalperAgent
from app.services.agents.agent_mean_reversion import MeanReversionAgent
from app.services.agents.agent_trend_follower import TrendFollowerAgent
from app.services.agents.agent_multi_asset import MultiAssetAgent
from app.services.agents.agent_breakout import BreakoutAgent

logger = logging.getLogger(__name__)


def register_all_agents():
    """Registra todos os agentes no registry."""
    agents = [
        MomentumRSIAgent(),
        HighVolContinuationAgent(),
        AICombinedAnalysisAgent(),
        SocialSentimentAgent(),
        PortfolioCycleAgent(),
        GridScalperAgent(),
        MeanReversionAgent(),
        TrendFollowerAgent(),
        MultiAssetAgent(),
        BreakoutAgent(),
    ]
    for agent in agents:
        agent_registry.register(agent)
    logger.info(f"[Agents] {len(agents)} agentes registrados: {[a.name for a in agents]}")


__all__ = [
    "BaseAgent", "AgentSignal", "AgentSide", "AgentResult",
    "AgentRegistry", "agent_registry",
    "MultiAgentEngine", "multi_agent_engine",
    "register_all_agents",
]
