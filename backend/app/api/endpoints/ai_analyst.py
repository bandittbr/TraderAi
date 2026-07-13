"""
TradeAI - AI Analyst Endpoints (Gemini)
Análise inteligente do estado completo do bot via LLM.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from app.services.ai_analyst.analyst import ai_analyst

router = APIRouter()


@router.get(
    "/analyze",
    summary="Análise completa do sistema via Gemini",
    description="Retorna insights, melhorias e aprendizados baseados em todo o contexto do bot (últimos 7 dias).",
)
async def analyze_system(
    days: int = Query(7, ge=1, le=30, description="Dias de histórico para analisar"),
    focus: str = Query("full", description="Foco: full, paper, worker, scalper, groq, market, biel"),
):
    """
    Análise inteligente via Gemini 1.5 Flash.
    
    Coleta contexto de:
    - Paper Trading (trades, PnL, win rate, motivos de fechamento)
    - Worker Agent (trades, regimes, confiança)
    - Scalper (trades, performance)
    - Groq Agent (trades, pensamentos/reasoning dos ciclos)
    - Mercado (regime BTC, Fear & Greed, funding rate)
    - Sinais emitidos (últimos 30)
    - Biel Instagram (posts recentes)
    
    Retorna relatório estruturado em português com:
    - Resumo executivo do portfolio
    - Análise por agente
    - Pontos fortes e fracos
    - Melhorias sugeridas
    - Aprendizados
    - Próximas ações recomendadas
    """
    if not ai_analyst.model:
        raise HTTPException(
            status_code=503,
            detail="Gemini API não configurada. Defina GEMINI_API_KEY no ambiente."
        )

    try:
        result = await ai_analyst.analyze(days=days, focus=focus)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Erro desconhecido"))
        return {
            "status": "success",
            "days_analyzed": days,
            "focus": focus,
            **result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na análise IA: {str(e)}")


@router.get(
    "/context",
    summary="Contexto bruto para debug",
    description="Retorna o contexto coletado sem análise do LLM (útil para debug).",
)
async def get_context(
    days: int = Query(7, ge=1, le=30),
):
    """Contexto bruto coletado de todos os agentes."""
    ctx = await ai_analyst.gather_full_context(days=days)
    return {"status": "success", "days": days, "context": ctx}


@router.get(
    "/health",
    summary="Health check do AI Analyst",
)
async def ai_health():
    """Verifica se Gemini está configurado e acessível."""
    if not ai_analyst.model:
        return {
            "status": "unavailable",
            "reason": "GEMINI_API_KEY não configurada",
            "model": None,
        }
    
    try:
        # Teste rápido
        test = ai_analyst.model.generate_content("Responda apenas: OK")
        return {
            "status": "healthy",
            "model": "gemini-1.5-flash",
            "test_response": test.text.strip() if test.text else "empty",
        }
    except Exception as e:
        return {
            "status": "degraded",
            "reason": str(e),
            "model": "gemini-1.5-flash",
        }