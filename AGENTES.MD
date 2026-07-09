# AGENTES AI — TradeAI

Este documento descreve a personalidade, estratégia e métricas de cada agente
de trading disponível na plataforma TradeAI.

---

## 📋 Índice

1. [Paper — O Conservador](#paper--o-conservador)
2. [Scalper — O Agressivo](#scalper--o-agressivo)
3. [Worker — O Estrategista](#worker--o-estrategista)

---

## Paper — O Conservador

### Personalidade

- **Perfil:** Conservador / Defensivo
- **Estilo:** Position trading com viés de médio prazo
- **Timeframe principal:** 1h
- **Aversão a risco:** Alta
- **Alavancagem:** Não utiliza (1x)

### Modo de pensar

O Paper é o **guardião do capital**. Ele só entra em posições quando o sinal
tem alta convicção (confidence ≥ 70%) e o mercado está alinhado com a
tendência principal. Prefere perder uma oportunidade a tomar um stop loss
desnecessário.

Filosofia: _É melhor ficar de fora de um bom trade do que entrar em um ruim._

### Estratégia de entrada

1. **Filtro principal:** Signal Engine da plataforma gera BUY/SELL/NEUTRAL com
   score ponderado (V6/V7) e zona neutra (diferença mínima de 10 pontos entre
   os scores BUY e SELL)
2. **Confiança mínima:** 70% para abrir posição
3. **Sentido:** LONG em sinal BUY, SHORT em sinal SELL
4. **Tamanho da posição:** Dimensionado por score de confiança (7.2) — quanto
   maior a confiança, maior o sizing, dentro de limites conservadores

### Gerenciamento de risco

| Parâmetro | Valor |
|---|---|
| Stop Loss | 2% fixo |
| Take Profit 1 | R:R 2.0 (4%) |
| Break Even | Após +2% (BE_TRIGGER) |
| Trailing Stop | Ativa após +2% (TRAILING_TRIGGER), distância 1.5% |
| Max posições simultâneas | Ilimitado (por símbolo) |
| Circuit breaker por regime | 3 perdas consecutivas → sizing 50%, 5 → pausa |

### Estratégia de saída

- **TP1 + Trailing:** Quando atinge +4%, metade da posição realiza lucro.
  A outra metade fica com trailing stop para capturar tendências maiores.
- **Break Even:** Se o preço andar +2% a favor, o SL sobe para o preço de
  entrada — trade passa a ter risco zero.
- **SL fixo:** Em -2% o trade é fechado sem hesitação.

### Métricas que monitora

- Win rate (gross e net)
- Profit factor
- Expectancy (média ponderada)
- Sharpe ratio (anualizado)
- Max drawdown
- Média de ganho/perda por trade
- Net profit factor (após taxas)

---

## Scalper — O Agressivo

### Personalidade

- **Perfil:** Agressivo / Intensivo
- **Estilo:** Scalping de alta frequência
- **Timeframe principal:** 1m e 5m
- **Aversão a risco:** Baixa
- **Alavancagem:** Não utiliza (1x)

### Modo de pensar

O Scalper é o **caçador de micro-movimentos**. Ele vive no curto prazo,
entrando e saindo do mercado rapidamente para capturar pequenas variações
de preço. Não está interessado na tendência macro — quer ticks.

Filosofia: _Muitos pequenos lucros constroem um grande resultado._

### Estratégia de entrada

1. **Triggers de entrada (5m):**
   - EMA9 > EMA21 (tendência de curto prazo)
   - Volume spike + OBV confirmation (7.8)
   - RSI dentro de zona ajustada por regime
   - Estrutura de micro-mercado (HH/HL ou LH/LL)
2. **Confirmação adicional (1m):** Sinal reverso é usado como fechamento
   (SIGNAL_CLOSE), não como entrada
3. **Sinais SMC:** Sweep de liquidez + FVG no direção do trade aumentam
   a confiança

### Gerenciamento de risco

| Parâmetro | Valor |
|---|---|
| Stop Loss | Adaptativo por ATR: `max(0.25%, ATR_1m × 1.5)` |
| Take Profit | R:R 2.0 (SL × 2) |
| Break Even | Após +0.20% |
| Trailing Stop | Ativa após +0.40%, distância 0.15% |
| Max tempo | 120 minutos (time stop) |
| Circuit breaker (7.10) | 3 perdas consecutivas → sizing 50%, 5 → pausa |
| Risco USD por trade | $10.00 fixo |

### Estratégia de saída

- **TP:** Assim que atinge R:R 2.0, realiza lucro total.
- **Trailing:** Se o preço andar +0.40%, ativa trailing stop a 0.15% de
  distância para capturar extensões.
- **Break Even:** Em +0.20% o SL sobe para o preço de entrada.
- **Time Stop:** 2h no máximo — se não atingiu TP nem SL, fecha por tempo.
- **Sinal reverso:** Se o motor de sinais emitir direção oposta, fecha
  imediatamente.

### Métricas que monitora

- Win rate (gross e net)
- Profit factor (gross e net)
- Média de ganho/perda percentual
- Total PnL (USD e %)
- Maximum win / loss %
- Net win rate e net profit factor (após taxas de 0.16%)
- Por side (LONG vs SHORT)
- Por símbolo
- Por motivo de saída (TP, SL, BE, TRAILING, TIME_STOP)

---

## Worker — O Estrategista

### Personalidade

- **Perfil:** Estrategista / Adaptativo
- **Estilo:** Swing trading com gestão profissional
- **Timeframe principal:** 1h (direção) + 15m (entrada)
- **Aversão a risco:** Moderada (ajustável)
- **Alavancagem:** Adaptativa 1x–3x

### Modo de pensar

O Worker é o **arquiteto de posições**. Ele não olha para ticks nem para
tendências de semanas — ele busca o **ponto de confluência ideal** onde
múltiplos timeframes e módulos de análise concordam. É o mais sofisticado
dos três agentes, combinando todas as ferramentas da plataforma.

Filosofia: _Quando todos os módulos apontam na mesma direção, a probabilidade
está ao seu favor._

### Estratégia de entrada

O Worker usa um sistema de **score multi-módulo**:

1. **Direção primária (timeframe 1h) — peso 35% no score final:**
   - EMA alignment (bull perfeito = +40, bear perfeito = -40)
   - MACD (bullish/bearish)
   - Market structure (HH+HL = +20, LH+LL = -20)
   - Regime de mercado (BULL = +5, BEAR = -5)

2. **Entrada (timeframe 15m) — confluência de 5 módulos:**

   | Módulo | Peso | Sinais de alta | Sinais de baixa |
   |---|---|---|---|
   | **Technical** | 30% | RSI < 30, MACD > signal, EMA9 > 21 | RSI 70+, MACD < signal, EMA9 < 21 |
   | **Structure** | 20% | HH+HL uptrend | LH+LL downtrend |
   | **SMC** | 20% | Sell sweep, FVG bullish, HVN | Buy sweep, FVG bearish, LVN |
   | **Context** | 15% | Extreme fear, news positivo | Extreme greed, news negativo |
   | **Regime** | 15% | BULL regime | BEAR regime |

3. **Condições para entrada:**
   - `confidence >= 65` (score de direção mínimo)
   - `confluence >= 70%` (pelo menos 70% dos módulos concordam)
   - Circuit breaker não está ativo
   - Máximo de 3 posições abertas simultaneamente

### Alavancagem adaptativa

| Condição | Alavancagem |
|---|---|
| Alta volatilidade (ATR > 2%) | 1x |
| Confidence >= 85 | 3x |
| Confidence >= 75 | 2x |
| Demais casos | 1x |

### Gerenciamento de risco

| Parâmetro | Valor |
|---|---|
| Stop Loss | Adaptativo: `max(0.5%, ATR_15m × 1.5)`, expandido 1.3× em alta vol |
| Take Profit 1 (50%) | R:R 1.5 |
| Take Profit 2 (30%) | R:R 3.0 |
| Take Profit 3 (20%) | R:R 5.0 |
| Break Even | Após +0.50% |
| Trailing Stop | Ativa após TP1 (distância 0.5%) |
| Max tempo | 480 minutos (8h) |
| Circuit breaker | 3 perdas consecutivas → sizing 50%, 5 → pausa 4h |
| Risco por trade | 1% do saldo |

### Estratégia de saída (3 níveis)

O Worker é o único agente com **saída parcial em múltiplos níveis**:

1. **TP1 (R:R 1.5):** 50% da posição realiza lucro. Ativa trailing stop.
2. **TP2 (R:R 3.0):** 30% da posição realiza lucro.
3. **TP3 (R:R 5.0):** 20% restante captura grandes movimentos.
4. **Trailing Stop:** Se o preço continuar andando após TP1, o trailing garante
   que o lucro não desaparece.
5. **Break Even:** Posição protegida após +0.50%.
6. **Time Stop:** 8h sem atingir alvos → fecha.

### Métricas que monitora

**Métricas de execução:**
- Win rate (gross e net)
- Profit factor (gross e net)
- Leverage utilizado por trade
- Taxa de acerto por regime de mercado
- Score de direção médio nas entradas

**Métricas de qualidade (7.9):**
- Module scores: % de acerto por módulo (technical, structure, smc)
- Threshold distance: quantos critérios acima do mínimo do regime
- Correlação entre confidence e resultado

**Métricas financeiras:**
- PnL total (USD e %) — gross e net
- Max drawdown
- Sharpe ratio
- Média de duração dos trades
- Por símbolo e por motivo de saída

---

## 🏆 Comparativo rápido

| Característica | Paper | Scalper | Worker |
|---|---|---|---|
| **Perfil** | Conservador | Agressivo | Estrategista |
| **TF principal** | 1h | 1m / 5m | 1h + 15m |
| **Alavancagem** | 1x | 1x | 1x–3x |
| **SL** | 2% fixo | ATR adaptativo | ATR adaptativo + regime |
| **TPs** | 1 nível + trailing | 1 nível + trailing | 3 níveis parciais |
| **Break Even** | +2% | +0.20% | +0.50% |
| **Circuit breaker** | Sim | Sim | Sim |
| **Fee modeling** | 0.16% | 0.16% | 0.16% |
| **Max posições** | Ilimitado | 1 por símbolo | 3 total |
| **Score multi-módulo** | Parcial | Parcial | Completo (5 módulos) |
| **SMC** | ✅ | ✅ | ✅ |
| **Contexto** | ✅ | ❌ | ✅ |
| **Structure** | ✅ | ✅ | ✅ |
| **Regime** | ✅ | ✅ | ✅ |
| **Volume/OBV** | ❌ | ✅ | ❌ |

---

## 🔄 Fluxo de decisão

```
                            Dados de Mercado
                                   │
                                   ▼
                         ┌─────────────────┐
                         │   Regime Classifier │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  Signal   │ │  Market  │ │  Smart   │
              │  Engine   │ │Structure │ │  Money   │
              └─────┬─────┘ └────┬─────┘ └────┬─────┘
                    │            │            │
                    └────────────┼────────────┘
                                 ▼
                    ┌─────────────────────┐
                    │  Weight Engine (V6)  │
                    │  Pesos por regime    │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
   ┌───────────┐       ┌───────────┐       ┌───────────┐
   │   PAPER   │       │  SCALPER  │       │  WORKER   │
   │  1h only  │       │  1m/5m    │       │ 1h + 15m  │
   │ conf≥70%  │       │  ticks    │       │ conf≥65%  │
   │ SL 2%     │       │ SL ATR    │       │ SL ATR+   │
   │ 1 TP      │       │ 1 TP      │       │ 3 TPs     │
   │ 1x        │       │ 1x        │       │ 1x-3x     │
   └───────────┘       └───────────┘       └───────────┘
```

---

> _TradeAI — Sistema Multi-Agente. Cada agente tem sua personalidade,
> mas todos compartilham a mesma base de dados e o mesmo motor de análise.
> A diferença está no timeframe, na agressividade e na gestão de posição._
