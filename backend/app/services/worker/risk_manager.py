"""
Worker Risk Manager — Circuit Breaker + Sizing Adaptativo (V7)

Regras:
  - 3 perdas consecutivas → sizing reduzido a 50%
  - 5 perdas consecutivas → pausa de 4h
  - Reset automático no próximo dia UTC
  - Por regime: cada regime tem seu próprio contador
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.worker import WorkerRiskDaily, WorkerAccount

logger = logging.getLogger(__name__)

RISK_REDUCE_AFTER = 3    # perdas consecutivas → 50% sizing
RISK_PAUSE_AFTER  = 5    # perdas consecutivas → pausa 4h
RISK_REDUCE_FACTOR = 0.5
REGIMES = ("BULL", "BEAR", "SIDEWAYS", "HIGH_VOLATILITY", "UNKNOWN")


class WorkerRiskManager:
    """Circuit breaker e sizing adaptativo do Worker Agent."""

    def __init__(self):
        self._today_str: str = ""
        self._regime_losses: dict[str, int] = {}
        self._last_reset_day: str = ""
        self._pause_until: Optional[datetime] = None
        self._reset()

    def _reset(self) -> None:
        self._today_str = date.today().isoformat()
        self._regime_losses = {r: 0 for r in REGIMES}
        self._pause_until = None
        logger.debug("[WorkerRisk] Reset diário")

    def _check_reset(self) -> None:
        today = date.today().isoformat()
        if today != self._today_str:
            self._reset()

    def record_trade(self, won: bool, regime: str = "UNKNOWN") -> None:
        """Registra resultado do trade e atualiza contadores."""
        self._check_reset()
        if regime not in self._regime_losses:
            regime = "UNKNOWN"

        if won:
            self._regime_losses[regime] = 0
        else:
            self._regime_losses[regime] = self._regime_losses.get(regime, 0) + 1

        n_losses = self._regime_losses[regime]
        if n_losses >= RISK_PAUSE_AFTER:
            self._pause_until = datetime.now(timezone.utc) + timedelta(hours=4)
            logger.warning(
                f"[WorkerRisk] {regime}: {n_losses} perdas consecutivas → PAUSA até {self._pause_until}"
            )

    @property
    def is_paused(self) -> bool:
        """True se o Worker deve pausar operações."""
        self._check_reset()
        if self._pause_until and datetime.now(timezone.utc) < self._pause_until:
            return True
        self._pause_until = None
        return False

    def sizing_factor(self, regime: str = "UNKNOWN") -> float:
        """Fator de sizing: 1.0 normal, 0.5 se >=3 perdas consecutivas."""
        self._check_reset()
        n = self._regime_losses.get(regime, 0)
        if n >= RISK_REDUCE_AFTER:
            return RISK_REDUCE_FACTOR
        return 1.0

    def can_trade(self, regime: str = "UNKNOWN") -> tuple[bool, str]:
        """
        Verifica se pode abrir novo trade.
        Returns: (pode_trade, motivo)
        """
        self._check_reset()
        if self.is_paused:
            return False, f"PAUSA ativa até {self._pause_until}"
        n = self._regime_losses.get(regime, 0)
        if n >= RISK_PAUSE_AFTER:
            return False, f"{n} perdas consecutivas em {regime}"
        return True, "ok"

    async def load_today(self) -> None:
        """Carrega estado do banco no início."""
        try:
            async with AsyncSessionLocal() as session:
                row = await session.scalar(
                    select(WorkerRiskDaily).where(WorkerRiskDaily.date == date.today().isoformat())
                )
                if row and row.is_blocked:
                    self._pause_until = datetime.now(timezone.utc) + timedelta(hours=4)
        except Exception:
            pass


worker_risk = WorkerRiskManager()
