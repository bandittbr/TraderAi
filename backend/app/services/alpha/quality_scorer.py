"""
Fase 9 — Setup Quality Scorer
Calcula um Setup Quality Score (0-100) para cada sinal emitido.
Componentes:
  - Pattern Score  (0-40): padrões históricos correspondentes
  - Regime Score   (0-25): performance do regime atual
  - Context Score  (0-20): contexto de mercado (F&G, funding, news)
  - Confluence     (0-15): quantidade de critérios simultâneos
Tudo determinístico — sem IA.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Any

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.alpha import AlphaPattern, SetupQualityHistory
from app.models.analytics import SignalHistory, SignalOutcome

logger = logging.getLogger(__name__)

# ── Pesos dos componentes ─────────────────────────────────────────────────────
PATTERN_WEIGHT    = 40.0
REGIME_WEIGHT     = 25.0
CONTEXT_WEIGHT    = 20.0
CONFLUENCE_WEIGHT = 15.0

# ── Regime scores base ────────────────────────────────────────────────────────
REGIME_BASE_SCORE: dict[str, float] = {
    "BULL":            22.0,
    "BEAR":            18.0,
    "SIDEWAYS":        12.0,
    "HIGH_VOLATILITY": 10.0,
    "UNKNOWN":         10.0,
}

# ── Confluence: score por número de critérios simultâneos ─────────────────────
def _confluence_score(n_criteria: int) -> float:
    """Score de confluência baseado em quantos critérios estão presentes."""
    if n_criteria <= 0:
        return 0.0
    if n_criteria == 1:
        return 5.0
    if n_criteria == 2:
        return 9.0
    if n_criteria == 3:
        return 12.0
    return min(15.0, 12.0 + (n_criteria - 3) * 1.0)


class SetupQualityScorer:
    """
    Calcula o Setup Quality Score em tempo real para um sinal.
    Usa padrões históricos do banco (alpha_patterns) + regime + contexto.
    """

    async def score(
        self,
        *,
        symbol:         str,
        timeframe:      str                 = "1h",
        signal:         str,               # BUY | SELL | NEUTRAL
        criteria_met:   Optional[list[str]] = None,
        regime:         Optional[str]       = None,
        context_score:  Optional[float]     = None,   # 0-100 (Phase 5)
        fear_greed:     Optional[float]     = None,   # 0-100
        funding_label:  Optional[str]       = None,   # POSITIVE | NEUTRAL | NEGATIVE
        persist:        bool                = True,
    ) -> float:
        """
        Calcula e opcionalmente persiste o quality score.
        Retorna float 0-100.
        """
        criteria = criteria_met or []
        n_criteria = len(criteria)

        # 1. Pattern Score (0-40)
        pattern_sc = await self._pattern_score(criteria, signal)

        # 2. Regime Score (0-25)
        regime_sc = self._regime_score(regime)

        # 3. Context Score (0-20)
        ctx_sc = self._context_component(context_score, fear_greed, funding_label, signal)

        # 4. Confluence (0-15)
        conf_sc = _confluence_score(n_criteria)

        total = round(min(100.0, pattern_sc + regime_sc + ctx_sc + conf_sc), 2)

        if persist:
            await self._persist(
                symbol=symbol, timeframe=timeframe, signal=signal,
                regime=regime, quality_score=total,
                pattern_score=pattern_sc, regime_score=regime_sc,
                context_score_comp=ctx_sc, confluence_score=conf_sc,
                criteria_met=criteria, criteria_count=n_criteria,
            )

        return total

    def _regime_score(self, regime: Optional[str]) -> float:
        """Score do regime de mercado (0-25)."""
        if not regime:
            return 10.0
        return REGIME_BASE_SCORE.get(str(regime).upper(), 10.0)

    def _context_component(
        self,
        context_score: Optional[float],
        fear_greed:    Optional[float],
        funding_label: Optional[str],
        signal:        str,
    ) -> float:
        """
        Compõe score de contexto (0-20):
          - context_score: 0-100 → contribui até 10 pontos
          - fear_greed: contribui até 6 pontos (condições extremas podem ser contrárias)
          - funding: contribui até 4 pontos
        """
        total = 0.0

        # Context Score (0-10)
        if context_score is not None:
            total += (context_score / 100.0) * 10.0

        # Fear & Greed (0-6)
        if fear_greed is not None:
            sig_up = signal.upper()
            if sig_up == "BUY":
                # Melhor comprar em medo (oportunidade) ou ganância moderada
                if fear_greed < 25:
                    total += 6.0   # medo extremo = oportunidade de compra
                elif fear_greed < 50:
                    total += 4.0
                elif fear_greed < 75:
                    total += 3.0
                else:
                    total += 1.0   # ganância extrema = sinal de compra arriscado
            elif sig_up == "SELL":
                if fear_greed > 75:
                    total += 6.0   # ganância extrema = oportunidade de venda
                elif fear_greed > 50:
                    total += 4.0
                elif fear_greed > 25:
                    total += 3.0
                else:
                    total += 1.0
            else:
                total += 3.0  # neutro

        # Funding Rate (0-4)
        if funding_label:
            fl = funding_label.upper()
            sig_up = signal.upper()
            if sig_up == "BUY" and fl == "NEGATIVE":
                total += 4.0   # funding negativo = longs pagam menos
            elif sig_up == "SELL" and fl == "POSITIVE":
                total += 4.0   # funding positivo = shorts pagam menos
            elif fl == "NEUTRAL":
                total += 2.0
            else:
                total += 1.0   # funding contrário ao sinal

        return round(min(20.0, total), 2)

    async def _pattern_score(self, criteria: list[str], signal: str) -> float:
        """
        Busca padrões históricos que coincidem com os critérios atuais.
        Retorna score 0-40 baseado no melhor alpha_score encontrado.
        """
        if not criteria:
            return 0.0
        try:
            async with AsyncSessionLocal() as db:
                # Buscar padrões com qualquer critério presente
                result = await db.execute(
                    select(AlphaPattern)
                    .where(
                        AlphaPattern.sufficient_data == True,
                        AlphaPattern.is_positive == True,
                    )
                    .order_by(AlphaPattern.alpha_score.desc())
                    .limit(200)
                )
                patterns = result.scalars().all()

            if not patterns:
                return 15.0  # score neutro quando sem histórico

            criteria_set = set(criteria)
            best_score = 0.0

            for p in patterns:
                try:
                    p_criteria = set(json.loads(p.criteria))
                except Exception:
                    continue
                # Overlap ratio: proporção de critérios do padrão presentes
                overlap = len(p_criteria & criteria_set)
                if overlap == 0:
                    continue
                coverage = overlap / max(len(p_criteria), 1)
                # Contribuição = alpha_score do padrão * coverage
                contrib = (p.alpha_score or 0.0) * coverage
                if contrib > best_score:
                    best_score = contrib

            # Normalizar para 0-40
            normalized = min(40.0, best_score * 0.4)
            return round(normalized, 2)

        except Exception as exc:
            logger.error("[alpha] _pattern_score: %s", exc)
            return 10.0  # fallback neutro

    async def _persist(
        self,
        *,
        symbol: str, timeframe: str, signal: str, regime: Optional[str],
        quality_score: float, pattern_score: float, regime_score: float,
        context_score_comp: float, confluence_score: float,
        criteria_met: list[str], criteria_count: int,
    ) -> None:
        try:
            async with AsyncSessionLocal() as db:
                entry = SetupQualityHistory(
                    symbol              = symbol,
                    timeframe           = timeframe,
                    signal              = signal,
                    regime              = regime,
                    quality_score       = quality_score,
                    pattern_score       = pattern_score,
                    regime_score        = regime_score,
                    context_score_comp  = context_score_comp,
                    confluence_score    = confluence_score,
                    criteria_met        = json.dumps(criteria_met),
                    criteria_count      = criteria_count,
                    computed_at         = datetime.utcnow(),
                )
                db.add(entry)
                await db.commit()
        except Exception as exc:
            logger.debug("[alpha] _persist quality: %s", exc)

    async def get_latest(self, symbol: Optional[str] = None, limit: int = 50) -> list:
        """Retorna os últimos quality scores calculados."""
        try:
            async with AsyncSessionLocal() as db:
                q = select(SetupQualityHistory).order_by(
                    SetupQualityHistory.computed_at.desc()
                ).limit(limit)
                if symbol:
                    q = q.where(SetupQualityHistory.symbol == symbol)
                result = await db.execute(q)
                return list(result.scalars().all())
        except Exception as e:
            logger.error("[alpha] get_latest: %s", e)
            return []


# ── Singleton ─────────────────────────────────────────────────────────────────

setup_quality_scorer = SetupQualityScorer()
