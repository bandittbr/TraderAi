"""
Biel — Brain (Gemini 2.0 Flash ou Groq LLaMA 3)
Detecção automática pelo prefixo da chave:
  gsk_...  → Groq  (api.groq.com)
  AIza/AQ. → Gemini (generativelanguage.googleapis.com)
"""

import httpx
from app.logger import get_logger

logger = get_logger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GROQ_API_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "llama-3.3-70b-versatile"

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
    "market":  "Comente sobre o estado atual do mercado com base nos dados fornecidos.",
    "trade":   "Compartilhe os resultados recentes dos trades, incluindo wins e losses com honestidade.",
    "insight": "Compartilhe um aprendizado ou insight sobre trading baseado nos dados do sistema.",
    "news":    "Comente sobre as notícias recentes de cripto e como elas podem impactar o mercado.",
}

# Prompt extra para gerar dados visuais estruturados (INSIGHTS e NOTÍCIA)
# O LLM deve retornar UM ÚNICO JSON contendo: caption (post Instagram) + visual data
STRUCTURED_PROMPTS = {
    "insight": """
IMPORTANTE: Sua resposta deve ser APENAS UM OBJETO JSON válido (sem markdown, sem ```, sem texto extra).

O JSON deve conter:
1. "caption": o post completo para Instagram (seguindo personalidade Biel, máx 300 chars + hashtags)
2. "question": pergunta provocativa sobre o mercado (máx 80 chars)
3. "insights": array com 3 objetos, cada um com "icon" (emoji), "title" (máx 30 chars), "desc" (máx 100 chars)
4. "ai_summary": resumo final (máx 120 chars)

Exemplo de formato:
{"caption": "O mercado está esquentando...\\n\\n#BTC #Crypto", "question": "Será que vem alta?", "insights": [{"icon": "📊", "title": "Acumulação", "desc": "Baleias comprando..."}, {"icon": "💧", "title": "Liquidez", "desc": "Fluxo crescendo..."}, {"icon": "📈", "title": "Tendência", "desc": "Estrutura altista..."}], "ai_summary": "Cenário misto mas construtivo."}

Ícones relevantes: 📊 💧 📈 📉 🔥 🛡️ ⚡ 🧠 🏦 🔗 🌐 💎 🎯
""",
    "news": """
IMPORTANTE: Sua resposta deve ser APENAS UM OBJETO JSON válido (sem markdown, sem ```, sem texto extra).

O JSON deve conter:
1. "caption": o post completo para Instagram (seguindo personalidade Biel, máx 300 chars + hashtags)
2. "headline": manchete principal (máx 80 chars)
3. "summary": resumo curto (máx 120 chars)
4. "news_symbol": símbolo do ativo principal (ex: BTC, ETH, SOL)
5. "impacts": array com 3 arrays [label, valor] — ex: ["Preço ETH", "+8.5%"]
6. "source": Fonte da notícia (ex: CoinDesk, Reuters)

Exemplo de formato:
{"caption": "ETF de ETH aprovado!...\\n\\n#Ethereum #Crypto", "headline": "SEC Aprova ETFs Spot de Ethereum", "summary": "Marco histórico para o mercado cripto.", "news_symbol": "ETH", "impacts": [["Preço ETH", "+8.5%"], ["Preço BTC", "+2.1%"], ["Volume DEX", "+$420M"]], "source": "CoinDesk"}
""",
}


def _detect_provider(api_key: str) -> str:
    """Detecta o provider pelo prefixo da chave."""
    if api_key.startswith("gsk_"):
        return "groq"
    return "gemini"


async def generate_post(context: dict, topic: str, api_key: str) -> dict:
    """
    Gera um post para o Instagram.
    
    Retorna dict:
      {"caption": "texto do post"} — para market/trade
      {"caption": "texto", "visual": {...}} — para insight/news (com dados estruturados)
    """
    provider = _detect_provider(api_key)
    logger.info(f"[biel/brain] Provider detectado: {provider}")

    topic_instruction = TOPIC_PROMPTS.get(topic, TOPIC_PROMPTS["market"])
    context_text = _format_context(context)

    structured_instruction = STRUCTURED_PROMPTS.get(topic, "")

    max_tokens = 800 if topic in ("insight", "news") else 400

    prompt = f"""{topic_instruction}

CONTEXTO ATUAL DO TRADEAI:
{context_text}

Gere um post para o Instagram seguindo as instruções de personalidade.
{structured_instruction}
"""

    if provider == "groq":
        raw = await _generate_groq(api_key, prompt, max_tokens)
    else:
        raw = await _generate_gemini(api_key, prompt, max_tokens)

    # Tentar extrair JSON do retorno (para insight/news)
    if topic in ("insight", "news"):
        result = _try_extract_structured(raw, topic)
        if result:
            logger.info(f"[biel/brain] JSON estruturado extraído para {topic}")
            return result
        # Fallback: se não conseguir parsear, retorna só caption
        logger.warning(f"[biel/brain] Falha ao extrair JSON para {topic}, retornando só caption")

    return {"caption": raw.strip()}


def _try_extract_structured(raw: str, topic: str = "") -> dict | None:
    """
    Tenta extrair um JSON estruturado da resposta da IA.
    O JSON pode estar no formato:
      { "caption": "...", "visual": { ... } }
    Ou iniciar direto com { "question": ... } (insight) ou { "headline": ... } (news).
    """
    import json
    import re

    text = raw.strip()

    # Remove ```json ... ``` se existir
    code_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if code_match:
        text = code_match.group(1).strip()

    # Encontra o primeiro { e último }
    brace_start = text.find('{')
    brace_end = text.rfind('}')
    if brace_start == -1 or brace_end == -1:
        return None

    json_str = text[brace_start:brace_end + 1]

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # Tentar limpar caracteres problemáticos
        cleaned = re.sub(r',\s*}', '}', json_str)  # trailing commas
        cleaned = re.sub(r',\s*]', ']', cleaned)
        cleaned = re.sub(r'[\u201c\u201d]', '"', cleaned)  # smart quotes
        cleaned = re.sub(r"[\u2018\u2019]", "'", cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    # Se já veio no formato { caption, ... }
    if "caption" in data:
        # Extrair campos visuais (tudo exceto caption) para dentro de "visual"
        visual_keys = [k for k in data if k != "caption"]
        if visual_keys:
            data["visual"] = {k: data.pop(k) for k in visual_keys}
        else:
            data["visual"] = {}
        return data

    # Se veio só os dados visuais sem caption, tenta extrair caption do resto do texto
    if topic in ("insight", "news") and ("question" in data or "headline" in data):
        caption = text[:brace_start].strip() + text[brace_end + 1:].strip()
        if not caption:
            caption = f"Confira nossa análise de {data.get('news_symbol', 'mercado')}!"
        return {"caption": caption, "visual": data}

    return None


async def _generate_groq(api_key: str, prompt: str, max_tokens: int = 400) -> str:
    """Gera texto via Groq (OpenAI-compatible API)."""
    # Garantir que o prompt é string (não lista/dict)
    if not isinstance(prompt, str):
        logger.error(f"[biel/brain] prompt não é string! type={type(prompt).__name__}, repr={repr(prompt)[:200]}")
        prompt = str(prompt)

    # Usar formato explícito de array de texto — elimina qualquer ambiguidade
    # com image_url no payload enviado ao Groq
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": [{"type": "text", "text": BIEL_SYSTEM_PROMPT.strip()}]},
            {"role": "user",   "content": [{"type": "text", "text": prompt}]},
        ],
        "temperature": 0.8,
        "max_tokens": max_tokens,
        "top_p": 0.9,
    }

    logger.info(f"[biel/brain] Groq content type: {type(payload['messages'][1]['content']).__name__}")
    logger.info(f"[biel/brain] Groq prompt preview (100 chars): {prompt[:100]}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
            )
            response.raise_for_status()
            data = response.json()

            text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

            if not text:
                raise ValueError("Groq retornou resposta vazia")

            logger.info(f"[biel/brain] Post gerado via Groq ({len(text)} chars)")
            return text

    except httpx.HTTPStatusError as e:
        error_body = e.response.text
        logger.error(f"[biel/brain] Groq HTTP error {e.response.status_code}: {error_body}")

        # Se Groq rejeitou por imagem (model text-only), sugerir trocar a chave
        if "does not support image input" in error_body:
            msg = (
                "Groq rejeitou o request porque o modelo llama-3.3-70b-versatile é text-only. "
                "Troque a chave API para uma chave Gemini (AIza...) no setup do Biel. "
                f"Detalhes: {error_body[:200]}"
            )
            logger.error(f"[biel/brain] {msg}")
            raise ValueError(msg)

        raise
    except Exception as e:
        logger.error(f"[biel/brain] Erro Groq: {e}")
        raise


async def _generate_gemini(api_key: str, prompt: str, max_tokens: int = 400) -> str:
    """Gera texto via Gemini 2.0 Flash."""
    payload = {
        "system_instruction": {
            "parts": [{"text": BIEL_SYSTEM_PROMPT}]
        },
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": max_tokens,
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

            logger.info(f"[biel/brain] Post gerado via Gemini ({len(text)} chars)")
            return text

    except httpx.HTTPStatusError as e:
        logger.error(f"[biel/brain] Gemini HTTP error {e.response.status_code}: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"[biel/brain] Erro Gemini: {e}")
        raise


def _format_context(ctx: dict) -> str:
    """Formata o contexto em texto legível."""
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
