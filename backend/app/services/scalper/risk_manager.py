"""
Scalper Risk Manager (Fase 13)
Controla:
  - Máximo 5 perdas consecutivas por dia → bloqueia
  - Máxima perda diária de 3% → bloqueia
  - Reset automático no próximo dia UTC
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.scalper import ScalperRiskDaily
from app.logger import logger

# ── Limites ───────────────────────────────────────────────────────────────────
MAX_CONSECUTIVE_LOSSES = 5
MAX_DAILY_LOSS_PCT     = 3.0   # %


class ScalperRiskManager:

    # ── Estado em memória (espelho do DB para velocidade) ─────────────────────
    _today_str:           str   = ""
    _consecutive_losses:  int   = 0
    _daily_pnl_pct:       float = 0.0
    _is_blocked:          bool  = False
    _block_reason:        str   = ""

    def _today(self) -> str:
        return date.today().isoformat()

    def _reset_if_new_day(self, today: str) -> None:
        if today != self._today_str:
            self._today_str          = today
            self._consecutive_losses = 0
            self._daily_pnl_pct      = 0.0
            self._is_blocked         = False
            self._block_reason       = ""
            logger.info(f"[Scalper Risk] Novo dia {today}: contadores zerados.")

    # ── Carrega estado do DB ──────────────────────────────────────────────────
    async def load_today(self) -> ScalperRiskDaily:
        today = self._today()
        self._reset_if_new_day(today)
        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ScalperRiskDaily).where(ScalperRiskDaily.date == today)
            )
            if row is None:
                row = ScalperRiskDaily(date=today)
                session.add(row)
                await session.commit()
                await session.refresh(row)
            # Espelha em memória
            self._consecutive_losses = row.consecutive_losses
            self._daily_pnl_pct      = row.daily_pnl_pct
            self._is_blocked         = row.is_blocked
            self._block_reason       = row.block_reason or ""
            return row

    # ── Verifica se pode operar ───────────────────────────────────────────────
    async def can_trade(self) -> tuple[bool, str]:
        """Limites desativados — opera todas as oportunidades."""
        await self.load_today()
        return True, ""

    # ── Registra resultado de trade ───────────────────────────────────────────
    async def record_trade(self, pnl_pct: float, won: bool) -> None:
        """Chamado após fechar um trade."""
        today = self._today()
        self._reset_if_new_day(today)

        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ScalperRiskDaily).where(ScalperRiskDaily.date == today)
            )
            if row is None:
                row = ScalperRiskDaily(date=today)
                session.add(row)

            row.daily_pnl_pct  += pnl_pct
            row.daily_pnl_usd  += 0.0   # atualizado pelo trade_engine
            row.total_trades   += 1
            row.updated_at      = datetime.now(timezone.utc)

            if won:
                row.winning_trades      += 1
                row.consecutive_losses   = 0
            else:
                row.losing_trades       += 1
                row.consecutive_losses  += 1

            # Verifica limites após atualizar
            if row.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
                row.is_blocked    = True
                row.block_reason  = f"5 perdas consecutivas ({row.consecutive_losses})"
                logger.warning(f"[Scalper Risk] BLOQUEADO: {row.block_reason}")

            if row.daily_pnl_pct <= -MAX_DAILY_LOSS_PCT:
                row.is_blocked   = True
                row.block_reason = f"Perda diária máxima ({row.daily_pnl_pct:.2f}%)"
                logger.warning(f"[Scalper Risk] BLOQUEADO: {row.block_reason}")

            await session.commit()

            # Atualiza memória
            self._consecutive_losses = row.consecutive_losses
            self._daily_pnl_pct      = row.daily_pnl_pct
            self._is_blocked         = row.is_blocked
            self._block_reason       = row.block_reason or ""

    # ── Bloqueia ──────────────────────────────────────────────────────────────
    async def _block(self, reason: str) -> None:
        today = self._today()
        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ScalperRiskDaily).where(ScalperRiskDaily.date == today)
            )
            if row:
                row.is_blocked   = True
                row.block_reason = reason
                row.updated_at   = datetime.now(timezone.utc)
                await session.commit()
        self._is_blocked   = True
        self._block_reason = reason

    # ── Status atual ─────────────────────────────────────────────────────────
    @property
    def is_blocked(self) -> bool:
        return self._is_blocked

    @property
    def consecutive_losses(self) -> int:
        return self._consecutive_losses

    @property
    def daily_pnl_pct(self) -> float:
        return self._daily_pnl_pct


scalper_risk = ScalperRiskManager()
