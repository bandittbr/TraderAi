"""
Base Agent — Interface abstrata para todos os agentes de trading.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AgentSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


@dataclass
class AgentSignal:
    """
    Sinal de trading gerado por um agente.
    """
    agent_name:       str
    symbol:           str
    direction:        AgentSide
    confidence:       float          # 0–100
    entry_price:      float
    stop_loss:        float
    take_profit:      Optional[float] = None
    take_profit2:     Optional[float] = None
    take_profit3:     Optional[float] = None
    leverage:         int            = 1
    reason:           str            = ""
    regime:           str            = "UNKNOWN"
    atr_pct:          float          = 0.0
    metadata:         dict           = field(default_factory=dict)
    is_valid:         bool           = True


@dataclass
class AgentResult:
    """
    Resultado completo da análise de um agente.
    """
    agent_name:       str
    symbol:           str
    signal:           AgentSignal
    module_scores:    dict           = field(default_factory=dict)
    raw_data:         dict           = field(default_factory=dict)
    execution_time_ms: float         = 0.0
    error:            Optional[str]  = None


class BaseAgent(ABC):
    """
    Classe base abstrata para todos os agentes de trading.
    Cada agente implementa sua própria lógica de análise.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._last_execution: datetime | None = None
        self._enabled: bool = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    @property
    def last_execution(self) -> datetime | None:
        return self._last_execution

    @abstractmethod
    async def analyze(
        self,
        symbol:      str,
        price_1h:    Optional[Any],   # MarketIndicator 1h
        price_15m:   Optional[Any],   # MarketIndicator 15m
        regime:      Optional[Any] = None,
        context:     Optional[Any] = None,
        structure:   Optional[Any] = None,
        smc:         Optional[Any] = None,
        current_price: Optional[float] = None,
        **kwargs,
    ) -> AgentResult:
        """
        Analisa o mercado e retorna um sinal de trading.
        """
        ...

    def get_config(self) -> dict:
        """Retorna configuração do agente para exibição."""
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self._enabled,
            "last_execution": self._last_execution.isoformat() if self._last_execution else None,
        }

    def __repr__(self) -> str:
        return f"<Agent {self.name} enabled={self._enabled}>"
