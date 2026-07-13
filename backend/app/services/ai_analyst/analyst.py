"""
TradeAI - AI Analyst Service (Gemini)
Analisa todo o contexto do bot e gera insights, melhorias e aprendizados.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import google.generativeai as genai
from app.config import settings
from app.database import AsyncSessionLocal
from app.logger import get_logger
from sqlalchemy import select, desc, func, and_

logger = get_logger(__name__)

# Configura Gemini
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)
    GEMINI_MODEL = genai.GenerativeModel("gemini-1.5-flash")
else:
    GEMINI_MODEL = None
    logger.warning("[ai_analyst] GEMINI_API_KEY não configurada")


class AIAnalyst:
    """
    Analista IA que lê todo o estado do sistema e gera relatórios inteligentes.
    """

    def __init__(self):
        self.model = GEMINI_MODEL

    async def gather_full_context(self, days: int = 7) -> dict[str, Any]:
        """Coleta contexto completo de todos os agentes e mercado."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        ctx = {}

        async with AsyncSessionLocal() as session:
            # ── Paper Trading ──────────────────────────────────────────────
            from app.models.paper_trading import PaperTrade, PaperAccount
            paper_trades = await session.execute(
                select(PaperTrade).where(PaperTrade.opened_at >= cutoff).order_by(desc(PaperTrade.opened_at))
            )
            paper_trades = list(paper_trades.scalars().all())
            paper_acc = await session.scalar(select(PaperAccount))

            ctx["paper"] = {
                "balance": paper_acc.balance if paper_acc else 0,
                "initial_balance": paper_acc.initial_balance if paper_acc else 0,
                "total_trades": len(paper_trades),
                "closed_trades": [t for t in paper_trades if t.status == "CLOSED"],
                "open_trades": [t for t in paper_trades if t.status == "OPEN"],
                "recent_trades": [
                    {
                        "symbol": t.symbol,
                        "side": t.trade_side,
                        "entry": t.entry_price,
                        "exit": t.exit_price,
                        "pnl_pct": t.pnl_percent,
                        "pnl_usd": t.pnl,
                        "status": t.status,
                        "close_reason": t.close_reason,
                        "opened": t.opened_at.isoformat() if t.opened_at else None,
                        "closed": t.closed_at.isoformat() if t.closed_at else None,
                    }
                    for t in paper_trades[:20]
                ],
            }

            # ── Worker Agent ───────────────────────────────────────────────
            from app.models.worker import WorkerTrade, WorkerAccount
            worker_trades = await session.execute(
                select(WorkerTrade).where(WorkerTrade.opened_at >= cutoff).order_by(desc(WorkerTrade.opened_at))
            )
            worker_trades = list(worker_trades.scalars().all())
            worker_acc = await session.scalar(select(WorkerAccount))

            ctx["worker"] = {
                "balance": worker_acc.balance if worker_acc else 0,
                "total_trades": len(worker_trades),
                "recent_trades": [
                    {
                        "symbol": t.symbol,
                        "side": t.trade_side,
                        "entry": t.entry_price,
                        "exit": t.exit_price,
                        "pnl_pct": t.net_pnl_pct,
                        "status": t.status,
                        "close_reason": t.close_reason,
                        "confidence": t.confidence,
                        "regime": t.regime_at_entry,
                    }
                    for t in worker_trades[:15]
                ],
            }

            # ── Scalper ────────────────────────────────────────────────────
            from app.models.scalper import ScalperTrade, ScalperAccount
            scalper_trades = await session.execute(
                select(ScalperTrade).where(ScalperTrade.opened_at >= cutoff).order_by(desc(ScalperTrade.opened_at))
            )
            scalper_trades = list(scalper_trades.scalars().all())
            scalper_acc = await session.scalar(select(ScalperAccount))

            ctx["scalper"] = {
                "balance": scalper_acc.balance if scalper_acc else 0,
                "total_trades": len(scalper_trades),
                "recent_trades": [
                    {
                        "symbol": t.symbol,
                        "side": t.trade_side,
                        "entry": t.entry_price,
                        "exit": t.exit_price,
                        "pnl_pct": t.pnl_pct,
                        "status": t.status,
                        "close_reason": t.close_reason,
                    }
                    for t in scalper_trades[:15]
                ],
            }

            # ── Groq Agent ─────────────────────────────────────────────────
            from app.models.groq_agent import GroqTrade, GroqAccount, GroqThinking
            groq_trades = await session.execute(
                select(GroqTrade).where(GroqTrade.opened_at >= cutoff).order_by(desc(GroqTrade.opened_at))
            )
            groq_trades = list(groq_trades.scalars().all())
            groq_acc = await session.scalar(select(GroqAccount))

            # Últimos pensamentos do Groq
            groq_thoughts = await session.execute(
                select(GroqThinking).order_by(desc(GroqThinking.created_at)).limit(10)
            )
            groq_thoughts = list(groq_thoughts.scalars().all())

            ctx["groq"] = {
                "balance": groq_acc.balance if groq_acc else 0,
                "total_trades": len(groq_trades),
                "recent_trades": [
                    {
                        "symbol": t.symbol,
                        "side": t.trade_side,
                        "entry": t.entry_price,
                        "exit": t.exit_price,
                        "pnl_pct": t.net_pnl_pct,
                        "status": t.status,
                        "confidence": t.confidence,
                        "regime": t.regime_at_entry,
                    }
                    for t in groq_trades[:15]
                ],
                "recent_thoughts": [
                    {
                        "symbol": th.symbol,
                        "action": th.action,
                        "confidence": th.confidence,
                        "reasoning": th.reasoning[:500] if th.reasoning else None,
                        "error": th.error,
                        "created": th.created_at.isoformat() if th.created_at else None,
                    }
                    for th in groq_thoughts
                ],
            }

            # ── Market Context ─────────────────────────────────────────────
            from app.models.market_data import MarketCandle, MarketIndicator, MarketRegime
            from app.models.market_context import FearGreed, FundingRate, OpenInterest

            # Regime atual BTC
            regime = await session.execute(
                select(MarketRegime).where(MarketRegime.symbol == "BTCUSDT").order_by(desc(MarketRegime.timestamp)).limit(1)
            )
            regime = regime.scalar_one_or_none()

            # Fear & Greed
            fg = await session.execute(
                select(FearGreed).order_by(desc(FearGreed.timestamp)).limit(1)
            )
            fg = fg.scalar_one_or_none()

            # Funding rates
            funding = await session.execute(
                select(FundingRate).where(FundingRate.symbol == "BTCUSDT").order_by(desc(FundingRate.timestamp)).limit(1)
            )
            funding = funding.scalar_one_or_none()

            ctx["market"] = {
                "btc_regime": regime.regime if regime else "UNKNOWN",
                "regime_confidence": regime.confidence if regime else 0,
                "fear_greed": fg.value if fg else 50,
                "fear_greed_label": fg.classification if fg else "NEUTRAL",
                "funding_rate": funding.rate_percent if funding else 0,
            }

            # ── Signal History ─────────────────────────────────────────────
            from app.models.signal_analytics import SignalHistory
            signals = await session.execute(
                select(SignalHistory).where(SignalHistory.emitted_at >= cutoff).order_by(desc(SignalHistory.emitted_at)).limit(30)
            )
            signals = list(signals.scalars().all())

            ctx["signals"] = [
                {
                    "symbol": s.symbol,
                    "signal": s.signal,
                    "confidence": s.confidence,
                    "regime": s.regime,
                    "outcome": s.outcome,
                    "pnl_pct": s.pnl_pct,
                    "emitted": s.emitted_at.isoformat() if s.emitted_at else None,
                }
                for s in signals
            ]

            # ── Biel Instagram ─────────────────────────────────────────────
            from app.models.biel import BielPost, BielPostMetrics
            biel_posts = await session.execute(
                select(BielPost).order_by(desc(BielPost.created_at)).limit(10)
            )
            biel_posts = list(biel_posts.scalars().all())

            ctx["biel"] = {
                "total_posts": len(biel_posts),
                "recent_posts": [
                    {
                        "type": p.post_type,
                        "topic": p.topic,
                        "caption": p.caption[:200] if p.caption else None,
                        "published": p.published_at.isoformat() if p.published_at else None,
                    }
                    for p in biel_posts
                ],
            }

        return ctx

    def build_prompt(self, ctx: dict[str, Any], focus: str = "full") -> str:
        """Constrói prompt estruturado para o Gemini."""
        paper = ctx.get("paper", {})
        worker = ctx.get("worker", {})
        scalper = ctx.get("scalper", {})
        groq = ctx.get("groq", {})
        market = ctx.get("market", {})
        signals = ctx.get("signals", [])
        biel = ctx.get("biel", {})

        # Calcula métricas agregadas
        paper_closed = paper.get("closed_trades", [])
        paper_wins = [t for t in paper_closed if (t.get("pnl_pct") or 0) > 0]
        paper_wr = len(paper_wins) / len(paper_closed) * 100 if paper_closed else 0
        paper_avg_pnl = sum(t.get("pnl_pct") or 0 for t in paper_closed) / len(paper_closed) if paper_closed else 0

        prompt = f"""
# TradeAI - Relatório de Análise IA (Gemini 1.5 Flash)
**Período:** Últimos 7 dias | **Foco:** {focus}
**Gerado em:** {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}

---

## 📊 RESUMO EXECUTIVO DO PORTFÓLIO

| Agente | Saldo Atual | Inicial | PnL % | Trades | Win Rate |
|--------|-------------|---------|-------|--------|----------|
| **Paper** | ${paper.get('balance', 0):,.2f} | ${paper.get('initial_balance', 0):,.2f} | {((paper.get('balance', 0) / paper.get('initial_balance', 1)) - 1) * 100:+.2f}% | {paper.get('total_trades', 0)} | {paper_wr:.1f}% |
| **Worker** | ${worker.get('balance', 0):,.2f} | $10,000 | {((worker.get('balance', 0) / 10000) - 1) * 100:+.2f}% | {worker.get('total_trades', 0)} | — |
| **Scalper** | ${scalper.get('balance', 0):,.2f} | $10,000 | {((scalper.get('balance', 0) / 10000) - 1) * 100:+.2f}% | {scalper.get('total_trades', 0)} | — |
| **Groq** | ${groq.get('balance', 0):,.2f} | $10,000 | {((groq.get('balance', 0) / 10000) - 1) * 100:+.2f}% | {groq.get('total_trades', 0)} | — |

**Total Portfolio:** ${sum([paper.get('balance', 0), worker.get('balance', 0), scalper.get('balance', 0), groq.get('balance', 0)]):,.2f}

---

## 🎯 MERCADO ATUAL (BTCUSDT)
- **Regime:** {market.get('btc_regime', 'UNKNOWN')} ({market.get('regime_confidence', 0):.0f}% confiança)
- **Fear & Greed:** {market.get('fear_greed', 50)} ({market.get('fear_greed_label', 'NEUTRAL')})
- **Funding Rate:** {market.get('funding_rate', 0):.4f}%

---

## 📈 PAPER TRADING - Detalhado
- **Trades Fechados:** {len(paper_closed)}
- **Win Rate:** {paper_wr:.1f}%
- **PnL Médio:** {paper_avg_pnl:+.2f}%
- **Melhor Trade:** {max((t.get('pnl_pct') or 0) for t in paper_closed) if paper_closed else 0:+.2f}%
- **Pior Trade:** {min((t.get('pnl_pct') or 0) for t in paper_closed) if paper_closed else 0:+.2f}%
- **Motivos de Fechamento:** {self._count_close_reasons(paper_closed)}

**Últimos 10 Trades:**
{self._format_trades(paper.get('recent_trades', [])[:10])}

---

## ⚙️ WORKER AGENT
- **Trades:** {worker.get('total_trades', 0)}
- **Regime dominante nos trades:** {self._most_common([t.get('regime') for t in worker.get('recent_trades', [])])}
- **Confiança média:** {sum(t.get('confidence', 0) for t in worker.get('recent_trades', [])) / max(len(worker.get('recent_trades', [])), 1):.1f}

**Últimos Trades:**
{self._format_trades(worker.get('recent_trades', [])[:10])}

---

## ⚡ SCALPER
- **Trades:** {scalper.get('total_trades', 0)}
**Últimos:**
{self._format_trades(scalper.get('recent_trades', [])[:10])}

---

## 🧠 GROQ AGENT (LLM Trading)
- **Trades:** {groq.get('total_trades', 0)}
- **Pensamentos recentes:** {len(groq.get('recent_thoughts', []))}

**Últimos Ciclos de Pensamento:**
{self._format_groq_thoughts(groq.get('recent_thoughts', [])[:5])}

**Trades Recentes:**
{self._format_trades(groq.get('recent_trades', [])[:10])}

---

## 📡 SINAIS EMITIDOS (últimos 30)
{self._format_signals(signals[:20])}

---

## 📱 BIEL INSTAGRAM
- **Posts:** {biel.get('total_posts', 0)}
- **Tópicos recentes:** {', '.join([p.get('topic', '') for p in biel.get('recent_posts', [])[:5]])}

---

## 🎯 TAREFA PARA VOCÊ (GEMINI)

Analise TODO o contexto acima e gere um relatório em **português brasileiro** com:

### 1. DIAGNÓSTICO GERAL (3-5 bullets)
- Estado de saúde de cada agente
- Padrões de sucesso/fracasso identificados
- Riscos atuais

### 2. TOP 3 MELHORIAS PRIORITÁRIAS
- Ação concreta | Agente afetado | Impacto esperado | Esforço (baixo/médio/alto)

### 3. APRENDIZADOS DA SEMANA
- O que funcionou
- O que falhou
- Padrões de mercado observados

### 4. AJUSTES DE PARÂMETROS SUGERIDOS
- Parâmetro | Valor Atual | Valor Sugerido | Justificativa

### 5. ALERTAS / RISCOS CRÍTICOS
- Coisas que precisam de atenção imediata

### 6. PRÓXIMOS PASSOS RECOMENDADOS
- Roadmap de 1-2 semanas

---

**Formato:** Use markdown, seja direto e acionável. Números reais, não generalidades.
"""
        return prompt

    def _count_close_reasons(self, trades: list) -> str:
        from collections import Counter
        reasons = [t.get("close_reason", "UNKNOWN") for t in trades if t.get("close_reason")]
        return ", ".join([f"{r}: {c}" for r, c in Counter(reasons).most_common()])

    def _format_trades(self, trades: list) -> str:
        if not trades:
            return "  (nenhum)"
        lines = []
        for t in trades:
            pnl = t.get("pnl_pct")
            pnl_str = f"{pnl:+.2f}%" if pnl is not None else "OPEN"
            side = t.get("side", "?")
            sym = t.get("symbol", "?")
            reason = t.get("close_reason", "")
            lines.append(f"  • {sym} {side} | PnL: {pnl_str} | {reason}")
        return "\n".join(lines)

    def _format_groq_thoughts(self, thoughts: list) -> str:
        if not thoughts:
            return "  (nenhum)"
        lines = []
        for th in thoughts:
            act = th.get("action", "?")
            conf = th.get("confidence", 0)
            reas = th.get("reasoning", "")[:150]
            lines.append(f"  • {act} ({conf:.0f}%) | {reas}...")
        return "\n".join(lines)

    def _format_signals(self, signals: list) -> str:
        if not signals:
            return "  (nenhum)"
        lines = []
        for s in signals:
            outcome = s.get("outcome", "PENDING")
            pnl = s.get("pnl_pct")
            pnl_str = f"{pnl:+.2f}%" if pnl is not None else "—"
            lines.append(f"  • {s.get('symbol')} {s.get('signal')} | Conf: {s.get('confidence', 0):.0f}% | {outcome} | PnL: {pnl_str}")
        return "\n".join(lines)

    def _most_common(self, items: list) -> str:
        from collections import Counter
        filtered = [i for i in items if i]
        if not filtered:
            return "—"
        return Counter(filtered).most_common(1)[0][0]

    async def analyze(self, days: int = 7, focus: str = "full") -> dict[str, Any]:
        """Executa análise completa e retorna resultado estruturado."""
        if not self.model:
            return {
                "error": "GEMINI_API_KEY não configurada",
                "fallback": "Configure a variável de ambiente GEMINI_API_KEY no Railway"
            }

        try:
            ctx = await self.gather_full_context(days)
            prompt = self.build_prompt(ctx, focus)

            logger.info("[ai_analyst] Enviando prompt para Gemini (~%d chars)", len(prompt))
            response = await self.model.generate_content_async(prompt)

            return {
                "success": True,
                "analysis": response.text,
                "context_summary": {
                    "paper_balance": ctx.get("paper", {}).get("balance"),
                    "worker_balance": ctx.get("worker", {}).get("balance"),
                    "scalper_balance": ctx.get("scalper", {}).get("balance"),
                    "groq_balance": ctx.get("groq", {}).get("balance"),
                    "btc_regime": ctx.get("market", {}).get("btc_regime"),
                    "fear_greed": ctx.get("market", {}).get("fear_greed"),
                    "total_trades": sum([
                        ctx.get("paper", {}).get("total_trades", 0),
                        ctx.get("worker", {}).get("total_trades", 0),
                        ctx.get("scalper", {}).get("total_trades", 0),
                        ctx.get("groq", {}).get("total_trades", 0),
                    ]),
                },
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error("[ai_analyst] Erro na análise: %s", e, exc_info=True)
            return {"error": str(e), "success": False}


# Instância singleton
ai_analyst = AIAnalyst()