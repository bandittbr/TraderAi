"""
Scalper Risk Manager (Fase 13 / V7)
- Monitoramento estatístico
- Circuit Breaker por regime (BULL/BEAR/SIDEWAYS)
  * 3 consecutivas no regime → posição reduz 50%
  * 5 consecutivas no regime → pausa (NONE) até próxima entrada vitoriosa
NÃO bloqueia trades globalmente — apenas ajusta sizing por regime.
Reset automático no próximo dia UTC.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.scalper import ScalperRiskDaily
from app.logger import logger

# ── V7: Parâmetros do Circuit Breaker ────────────────────────────────────────
REGIME_REDUCE_AFTER   = 3   # perdas consecutivas no regime → sizing 50%
REGIME_PAUSE_AFTER    = 5   # perdas consecutivas no regime → pausa
REGIME_REDUCE_FACTOR  = 0.5 # multiplicador de posição quando reduz
REGIMES               = ("BULL", "BEAR", "SIDEWAYS")


class ScalperRiskManager:

    # ── Estado em memória ────────────────────────────────────────────────────
    _today_str:           str   = ""
    _consecutive_losses:  int   = 0
    _daily_pnl_pct:       float = 0.0

    # V7: Circuit Breaker por regime (reset diário)
    _regime_losses: dict[str, int] = None  # {"BULL": 0, "BEAR": 0, ...}
    _regime_paused:  dict[str, bool] = None # regimes pausados até win reset

    def __init__(self):
        self._reset_regime_state()

    def _reset_regime_state(self) -> None:
        self._regime_losses = {r: 0 for r in REGIMES}
        self._regime_paused = {r: False for r in REGIMES}

    def _today(self) -> str:
        return date.today().isoformat()

    def _reset_if_new_day(self, today: str) -> None:
        if today != self._today_str:
            self._today_str          = today
            self._consecutive_losses = 0
            self._daily_pnl_pct      = 0.0
            self._reset_regime_state()
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
            return row

    # ── Verifica se pode operar ───────────────────────────────────────────────
    async def can_trade(self) -> tuple[bool, str]:
        """Sempre True — nenhum limite de perda diária global."""
        await self.load_today()
        return True, ""

    # ── V7: Retorna fator de sizing para regime ───────────────────────────────
    def regime_sizing_multiplier(self, regime: str) -> float:
        """
        1.0  normal
        0.5  após REGIME_REDUCE_AFTER perdas consecutivas
        0.0  se pausado (REGIME_PAUSE_AFTER+ perdas)
        """
        losses = self._regime_losses.get(regime, 0)
        if self._regime_paused.get(regime, False) or losses >= REGIME_PAUSE_AFTER:
            return 0.0
        if losses >= REGIME_REDUCE_AFTER:
            return REGIME_REDUCE_FACTOR
        return 1.0

    # ── V7: Verifica se regime específico está pausado ────────────────────────
    def is_regime_paused(self, regime: str) -> bool:
        return self._regime_paused.get(regime, False) or \
               self._regime_losses.get(regime, 0) >= REGIME_PAUSE_AFTER

    # ── Registra resultado de trade (V7: circuit breaker por regime) ──────────
    async def record_trade(self, pnl_pct: float, won: bool,
                           regime: str | None = None) -> None:
        """
        Registra resultado e atualiza circuit breaker.
        regime: "BULL" | "BEAR" | "SIDEWAYS" — para rastreio por regime.
        """
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

            await session.commit()

            # Atualiza memória
            self._consecutive_losses = row.consecutive_losses
            self._daily_pnl_pct      = row.daily_pnl_pct

        # ── V7: Circuit Breaker por regime ────────────────────────────────────
        if regime and regime in self._regime_losses:
            if won:
                self._regime_losses[regime] = 0
                if self._regime_paused.get(regime, False):
                    self._regime_paused[regime] = False
                    logger.info(f"[Scalper Risk] Regime {regime} reativado após vitória.")
            else:
                self._regime_losses[regime] += 1
                los = self._regime_losses[regime]
                if los == REGIME_REDUCE_AFTER:
                    logger.info(f"[Scalper Risk] Regime {regime}: {los} consecutivas → sizing 50%")
                if los >= REGIME_PAUSE_AFTER:
                    self._regime_paused[regime] = True
                    logger.info(f"[Scalper Risk] Regime {regime}: {los} consecutivas → PAUSADO")
        else:
            # Fallback: se regime não for informado, rastreio global (legado)
            if regime not in self._regime_losses and regime is not None:
                logger.warning(f"[Scalper Risk] Regime {regime} desconhecido — ignorado.")

    # ── Status atual ─────────────────────────────────────────────────────────
    @property
    def is_blocked(self) -> bool:
        return False

    @property
    def consecutive_losses(self) -> int:
        return self._consecutive_losses

    @property
    def daily_pnl_pct(self) -> float:
        return self._daily_pnl_pct


scalper_risk = ScalperRiskManager()
