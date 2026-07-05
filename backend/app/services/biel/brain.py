"""
Biel — Brain (Gemini 2.0 Flash)
Gera textos com a personalidade do Biel usando Google Gemini API.
"""

import httpx
from app.logger import get_logger

logger = get_logger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

BIEL_SYSTEM_PROMPT = """
Você é Biel, um agente de trading autônomo especialista em criptomoedas e futuros.
Você controla o TradeAI, uma plataforma quantitativa de trading algorítmico.

Personalidade:
- Direto e confiante, mas honesto sobre riscos
- Usa linguagem descontraída mas profissional, sem ser informal demais
- Compartilha aprendizados reais dos trades (wins e losses)
- Não vende sonhos — fala de resultados reais com contexto
- Usa emojis com moderação (máximo 3 por post)
- Escreve em português brasileiro
- Posts curtos: máximo 300 caracteres para o Instagram (mais hashtags)

Formato do post:
1. Frase de abertura impactante (1 linha)
2. Dados reais do contexto
3. Reflexão ou aprendizado
4. Call to action sutil
5. 5-8 hashtags relevantes no final

Nunca invente dados — use apenas o que foi fornecido no contexto.
"""

TOPIC_PROMPTS = {
    "market": "Comente sobre o estado atual do mercado com base nos dados fornecidos.",
    "trade":  "Compartilhe os resultados recentes dos trades, incluindo wins e losses com honestidade.",
    "insight": "Compartilhe um aprendizado ou insight sobre trading baseado nos dados do sistema.",
    "news":   "Comente sobre as notícias recentes de cripto e como elas podem impactar o mercado.",
}


async def generate_post(context: dict, topic: str, api_key: str) -> str:
    """
    Gera um post para o Instagram usando o Gemini 2.0 Flash.
    Retorna o texto do post.
    """
    topic_instruction = TOPIC_PROMPTS.get(topic, TOPIC_PROMPTS["market"])

    context_text = _format_context(context)

    prompt = f"""{topic_instruction}

CONTEXTO ATUAL DO TRADEAI:
{context_text}

Gere um post para o Instagram seguindo as instruções de personalidade.
"""

    payload = {
        "system_instruction": {
            "parts": [{"text": BIEL_SYSTEM_PROMPT}]
        },
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 400,
            "topP": 0.9,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GEMINI_API_URL}?key={api_key}",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()

            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )

            if not text:
                raise ValueError("Gemini retornou resposta vazia")

            logger.info(f"[biel/brain] Post gerado ({len(text)} chars) — tópico: {topic}")
            return text

    except httpx.HTTPStatusError as e:
        logger.error(f"[biel/brain] Gemini HTTP error {e.response.status_code}: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"[biel/brain] Erro ao gerar post: {e}")
        raise


def _format_context(ctx: dict) -> str:
    """Formata o contexto em texto legível para o Gemini."""
    lines = []

    if "btc_price" in ctx:
        lines.append(f"- BTC atual: ${ctx['btc_price']:,.2f}")
    if "regime" in ctx:
        lines.append(f"- Regime de mercado: {ctx['regime']} ({ctx.get('regime_symbol', 'BTC')})")
    if "fear_greed_value" in ctx:
        lines.append(f"- Fear & Greed: {ctx['fear_greed_value']} ({ctx.get('fear_greed_label', '')})")
    if "saldo" in ctx:
        pnl = ctx.get("pnl_total", 0)
        pnl_pct = ctx.get("pnl_pct", 0)
        sinal = "+" if pnl >= 0 else ""
        lines.append(f"- Saldo virtual: ${ctx['saldo']:,.2f}")
        lines.append(f"- P&L total: {sinal}${pnl:,.2f} ({sinal}{pnl_pct:.1f}%)")
    if "win_rate_recente" in ctx:
        lines.append(f"- Win rate recente: {ctx['win_rate_recente']}% (últimos 5 trades)")
    if "ultimos_trades" in ctx and ctx["ultimos_trades"]:
        trades_str = ", ".join(
            f"{t['symbol']} {t['side']} {'+' if t['pnl'] >= 0 else ''}{t['pnl']:.2f} ({t['resultado']})"
            for t in ctx["ultimos_trades"][:3]
        )
        lines.append(f"- Últimos trades: {trades_str}")
    if "noticias" in ctx and ctx["noticias"]:
        for n in ctx["noticias"][:2]:
            lines.append(f"- Notícia: {n['titulo']} (sentimento: {n['sentimento']})")
    if "timestamp" in ctx:
        lines.append(f"- Data/hora: {ctx['timestamp']}")

    return "\n".join(lines) if lines else "Nenhum dado disponível no momento."
