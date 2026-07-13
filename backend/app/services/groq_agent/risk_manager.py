"""
Groq Agent — Risk Manager (V2 — 10x Leverage)
Circuit breaker + sizing adaptativo para operações alavancadas 10x.

Com 10x alavancagem:
- 1% de movimento no preço = 10% no resultado
- SL de 0.5% = 5% de perda real
- Risco de 2% do saldo = exposição bruta de 20%
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.groq_agent import GroqRiskDaily
from app.logger import get_logger

logger = get_logger(__name__)

# Parâmetros (ajustados para 10x leverage)
REDUCE_AFTER = 3   # perdas consecutivas → sizing 50%
PAUSE_AFTER = 5    # perdas consecutivas → pausa 2h
REDUCE_FACTOR = 0.5
MAX_RISK_PCT = 0.02  # 2% do saldo por trade (exposição bruta = 20% com 10x)


class GroqRiskManager:
    """Circuit breaker do Groq Agent."""

    def __init__(self):
        self._today_str: str = ""
        self._consecutive_losses: int = 0
        self._regime_losses: dict[str, int] = {}
        self._pause_until: datetime | None = None

    def _check_reset(self) -> None:
        today = date.today().isoformat()
        if today != self._today_str:
            self._today_str = today
            self._consecutive_losses = 0
            self._regime_losses = {}
            self._pause_until = None

    def can_trade(self) -> tuple[bool, str]:
        self._check_reset()
        if self._pause_until and datetime.now(timezone.utc) < self._pause_until:
            return False, f"Pausa ativa até {self._pause_until}"
        if self._consecutive_losses >= PAUSE_AFTER:
            return False, f"{self._consecutive_losses} perdas consecutivas"
        return True, "ok"

    def sizing_factor(self) -> float:
        self._check_reset()
        if self._consecutive_losses >= REDUCE_AFTER:
            return REDUCE_FACTOR
        return 1.0

    def max_risk_usd(self, balance: float) -> float:
        """Retorna o máximo em USD que pode arriscar."""
        factor = self.sizing_factor()
        return balance * MAX_RISK_PCT * factor

    def record_trade(self, won: bool) -> None:
        self._check_reset()
        if won:
            self._consecutive_losses = 0
            self._pause_until = None
        else:
            self._consecutive_losses += 1
            if self._consecutive_losses >= PAUSE_AFTER:
                from datetime import timedelta
                self._pause_until = datetime.now(timezone.utc) + timedelta(hours=2)
                logger.warning(
                    f"[GroqRisk] {self._consecutive_losses} perdas → pausa 2h"
                )

    @property
    def is_paused(self) -> bool:
        self._check_reset()
        if self._pause_until and datetime.now(timezone.utc) < self._pause_until:
            return True
        self._pause_until = None
        return False

    @property
    def consecutive_losses(self) -> int:
        self._check_reset()
        return self._consecutive_losses


groq_risk = GroqRiskManager()
