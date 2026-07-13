"""
Groq Agent — Signal Engine (V1)
Coleta dados de mercado e usa o Groq API (Llama 3.3 70B) para decidir trades.

Fluxo:
  1. Coleta indicadores, regime, preço, histórico de trades
  2. Monta prompt estruturado com contexto completo
  3. Envia para Groq API
  4. Parseia resposta JSON (direção, SL, TP, reasoning)
  5. Valida e retorna GroqSignalResult
"""
from __future__ import annotations

import json
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from groq import Groq, RateLimitError, APIConnectionError

logger = logging.getLogger(__name__)

# ── Configuração ──────────────────────────────────────────────────────────────

GROQ_MODEL = "llama-3.3-70b-versatile"  # Mais inteligente free tier
MAX_TOKENS = 1024
TEMPERATURE = 0.3  # Baixo = mais consistente

SYSTEM_PROMPT = """Você é GROQ, um agente de trading autônomo e altamente inteligente.
Você opera com ALAVANCAGEM 10x em timeframe de 15 MINUTOS.

LIBERDADE TOTAL: Use qualquer estratégia, fórmula ou abordagem que achar melhor.
Você pode combinar indicadores técnicos de qualquer forma, criar modelos customizados,
usar padrões de price action, harmonics, Fibonacci, volume profile, Order Flow, ou
qualquer outro método. O único limite é sua criatividade e os dados fornecidos.

REGRAS OBRIGATÓRIAS:
1. Responda SEMPRE em JSON válido, sem texto antes ou depois.
2. ALAVANCAGEM: 10x — o P&L é multiplicado por 10. SL/TP de 1% = 10% no resultado.
3. Stop Loss deve ser entre 0.1% e 1.5% do preço de entrada (com 10x, 1% = 10% de perda real).
4. Take Profit deve ser entre 0.2% e 3.0% do preço de entrada.
5. Risco/Retorno mínimo 1:1.5 (TP >= SL × 1.5).
6. Máximo 2% do saldo arriscado por trade (= 0.2% preço × 10x = exposição controlada).
7. Considere o histórico recente — não repita erros.
8. Se tiver 3+ perdas consecutivas, seja mais conservador (SL mais apertado).
9. Timeframe é 15 minutos — pense em movimentos de curto prazo.
10. Você pode usar QUALQUER combinação de indicadores para gerar seu sinal.

DICA: Para scalping 15min com 10x, considere:
- RSI extremes para entries de reversão
- Cruzamento de EMAs curtas (9/21) para momentum
- MACD histogram para confirmação
- ATR para calibrar SL dinamicamente
- Volume para confirmar breaks
- Price action (suportes/resistências, pin bars, engulfing)
- Qualquer outro padrão que identifique

FORMATO DE RESPOSTA:
{
  "action": "BUY" | "SELL" | "HOLD",
  "confidence": 0-100,
  "stop_loss_pct": 0.1-1.5,
  "take_profit_pct": 0.2-3.0,
  "reasoning": "Explicação da sua estratégia e lógica em português",
  "strategy_used": "Nome da estratégia/fórmula que você está aplicando",
  "market_assessment": "bullish" | "bearish" | "neutral",
  "risk_level": "low" | "medium" | "high"
}"""


@dataclass
class GroqSignalResult:
    symbol:       str
    action:       str            # "BUY" | "SELL" | "HOLD"
    confidence:   float          # 0-100
    stop_loss_pct: float         # % do preço (0.1-1.5% com 10x)
    take_profit_pct: float       # % do preço (0.2-3.0% com 10x)
    reasoning:    str = ""
    strategy_used: str = ""      # Nome da estratégia/fórmula usada
    market_assessment: str = "neutral"
    risk_level:   str = "medium"
    price:        float = 0.0
    raw_response: str = ""
    prompt_tokens: int = 0
    output_tokens: int = 0
    latency_ms:   float = 0.0
    error:        str = ""
    is_valid:     bool = True


class GroqSignalEngine:
    """
    Engine que usa Groq API para decisões de trading.
    Coleta dados do mercado e envia para o LLM analisar.
    """

    def __init__(self):
        self._client: Optional[Groq] = None
        self._last_call_time: float = 0
        self._min_interval: float = 2.0  # Mínimo 2s entre calls (safety)

    @property
    def client(self) -> Groq:
        if self._client is None:
            import os
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY não configurada nas variáveis de ambiente")
            self._client = Groq(api_key=api_key, max_retries=2, timeout=30.0)
        return self._client

    async def analyze(
        self,
        symbol: str,
        price: float,
        indicators: dict,
        regime: str = "UNKNOWN",
        recent_trades: list[dict] = None,
        account_balance: float = 10000.0,
        open_position: dict = None,
    ) -> GroqSignalResult:
        """
        Analisa o mercado e decide a ação.
        
        Args:
            symbol: Par de trading (ex: BTCUSDT)
            price: Preço atual
            indicators: Dict com RSI, EMA, MACD, ATR, etc.
            regime: Regime de mercado
            recent_trades: Últimos 10 trades para contexto
            account_balance: Saldo atual
            open_position: Posição aberta atual (se houver)
        """
        # Rate limiting básico
        now = time.time()
        wait = self._min_interval - (now - self._last_call_time)
        if wait > 0:
            time.sleep(wait)

        # Montar prompt com dados do mercado
        user_prompt = self._build_prompt(
            symbol, price, indicators, regime,
            recent_trades, account_balance, open_position,
        )

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )

            latency = (time.time() - start_time) * 1000
            self._last_call_time = time.time()

            raw_text = response.choices[0].message.content.strip()
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            # Parse JSON
            result = self._parse_response(
                raw_text, symbol, price, prompt_tokens, output_tokens, latency,
            )

            logger.info(
                f"[Groq] {symbol} action={result.action} conf={result.confidence:.0f}% "
                f"SL={result.stop_loss_pct:.2f}% TP={result.take_profit_pct:.2f}% "
                f"latency={latency:.0f}ms"
            )

            return result

        except RateLimitError:
            logger.warning("[Groq] Rate limit atingido — usando fallback HOLD")
            return GroqSignalResult(
                symbol=symbol, action="HOLD", confidence=0, price=price,
                stop_loss_pct=0.5, take_profit_pct=1.0,
                reasoning="Rate limit da API Groq — aguardando próximo ciclo",
                error="rate_limit", is_valid=False,
                latency_ms=(time.time() - start_time) * 1000,
            )
        except APIConnectionError:
            logger.warning("[Groq] Falha de conexão — usando fallback HOLD")
            return GroqSignalResult(
                symbol=symbol, action="HOLD", confidence=0, price=price,
                stop_loss_pct=0.5, take_profit_pct=1.0,
                reasoning="Falha de conexão com a API Groq",
                error="connection_error", is_valid=False,
                latency_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            logger.error(f"[Groq] Erro inesperado: {e}")
            return GroqSignalResult(
                symbol=symbol, action="HOLD", confidence=0, price=price,
                stop_loss_pct=0.5, take_profit_pct=1.0,
                reasoning=f"Erro: {str(e)}",
                error=str(e), is_valid=False,
                latency_ms=(time.time() - start_time) * 1000,
            )

    def _build_prompt(
        self,
        symbol: str,
        price: float,
        indicators: dict,
        regime: str,
        recent_trades: list[dict],
        account_balance: float,
        open_position: dict,
    ) -> str:
        """Monta o prompt estruturado com todos os dados do mercado."""

        # Indicadores formatados
        rsi = indicators.get("rsi", 50)
        ema9 = indicators.get("ema_9", 0)
        ema21 = indicators.get("ema_21", 0)
        ema50 = indicators.get("ema_50", 0)
        ema200 = indicators.get("ema_200", 0)
        macd = indicators.get("macd", 0)
        macd_signal = indicators.get("macd_signal", 0)
        macd_hist = indicators.get("macd_histogram", 0)
        atr = indicators.get("atr", 0)
        atr_pct = (atr / price * 100) if price > 0 and atr > 0 else 0

        prompt = f"""## DADOS DE MERCADO — {symbol}

### Preço Atual: ${price:,.2f}

### Indicadores Técnicos:
- RSI(14): {rsi:.1f}
- EMA9: ${ema9:,.2f}
- EMA21: ${ema21:,.2f}
- EMA50: ${ema50:,.2f}
- EMA200: ${ema200:,.2f}
- MACD: {macd:.4f} | Sinal: {macd_signal:.4f} | Histograma: {macd_hist:.4f}
- ATR(14): ${atr:.2f} ({atr_pct:.3f}%)

### Regime de Mercado: {regime}

### Configuração:
- ALAVANCAGEM: 10x
- Timeframe: 15 minutos
- Saldo: ${account_balance:,.2f}
- Risco máximo por trade: 2% (${account_balance * 0.02:,.2f})
"""

        # Posição aberta
        if open_position:
            side = open_position.get("side", "LONG")
            entry = open_position.get("entry_price", 0)
            sl = open_position.get("stop_loss", 0)
            tp = open_position.get("take_profit", 0)
            pnl_pct = ((price - entry) / entry * 100) if side == "LONG" else ((entry - price) / entry * 100)
            prompt += f"""
### Posição Aberta:
- Lado: {side}
- Entrada: ${entry:,.2f}
- Stop Loss: ${sl:,.2f}
- Take Profit: ${tp:,.2f}
- P&L Atual: {pnl_pct:+.2f}%
"""
        else:
            prompt += "\n### Posição Aberta: NENHUMA\n"

        # Últimos trades
        if recent_trades:
            prompt += "\n### Últimos 5 Trades:\n"
            for t in recent_trades[-5:]:
                result = "WIN" if (t.get("pnl_pct", 0) or 0) > 0 else "LOSS"
                prompt += (
                    f"- {t.get('side', '?')} {t.get('symbol', '?')} "
                    f"| P&L: {t.get('pnl_pct', 0):+.2f}% ({result}) "
                    f"| Motivo: {t.get('close_reason', '?')}\n"
                )

        # Instrução final
        if open_position:
            prompt += "\nVocê tem uma posição ABERTA (10x alavancada, 15min). Deve decidir se MANTÉM, FECHA (SELL para LONG / BUY para SHORT), ou ajusta o SL/TP."
        else:
            prompt += "\nNão há posição aberta. Analise os dados e decida se ABRE uma nova posição (BUY/SELL com 10x) ou fica em HOLD."

        prompt += "\nUse QUALQUER estratégia que quiser. Não há restrição de método."
        prompt += "\n\nResponda APENAS com o JSON. Sem texto adicional."

        return prompt

    def _parse_response(
        self,
        raw_text: str,
        symbol: str,
        price: float,
        prompt_tokens: int,
        output_tokens: int,
        latency_ms: float,
    ) -> GroqSignalResult:
        """Parse da resposta JSON do LLM com validação."""

        # Limpar possíveis marcadores de código
        clean = raw_text.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        try:
            data = json.loads(clean)
        except json.JSONDecodeError as e:
            logger.warning(f"[Groq] JSON inválido: {e}\nRaw: {raw_text[:200]}")
            return GroqSignalResult(
                symbol=symbol, action="HOLD", confidence=0, price=price,
                stop_loss_pct=0.5, take_profit_pct=1.0,
                reasoning="Resposta do LLM não é JSON válido",
                raw_response=raw_text, error=f"json_parse: {e}",
                is_valid=False, prompt_tokens=prompt_tokens,
                output_tokens=output_tokens, latency_ms=latency_ms,
            )

        # Extrair campos com validação (ranges para 10x leverage)
        action = str(data.get("action", "HOLD")).upper()
        if action not in ("BUY", "SELL", "HOLD"):
            action = "HOLD"

        confidence = max(0, min(100, float(data.get("confidence", 50))))
        sl_pct = max(0.1, min(1.5, float(data.get("stop_loss_pct", 0.3))))
        tp_pct = max(0.2, min(3.0, float(data.get("take_profit_pct", 0.6))))

        # Validar R:R mínimo 1:1.5
        if tp_pct < sl_pct * 1.5:
            tp_pct = sl_pct * 1.5
            tp_pct = min(tp_pct, 3.0)

        reasoning = str(data.get("reasoning", ""))[:500]
        strategy_used = str(data.get("strategy_used", ""))[:100]
        market_assessment = str(data.get("market_assessment", "neutral"))
        risk_level = str(data.get("risk_level", "medium"))

        return GroqSignalResult(
            symbol=symbol,
            action=action,
            confidence=confidence,
            stop_loss_pct=sl_pct,
            take_profit_pct=tp_pct,
            reasoning=reasoning,
            strategy_used=strategy_used,
            market_assessment=market_assessment,
            risk_level=risk_level,
            price=price,
            raw_response=raw_text,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            is_valid=True,
        )


# Singleton
groq_signal_engine = GroqSignalEngine()
