# Análise Profunda: Métricas para Trade — TradeAI

> **Data:** 2026-07-08
> **Última atualização:** 2026-07-08 — V7 implementada
> **Escopo:** Scalper Engine (Fase 13) + Signal Engine V7 + Paper Trading Engine (Fases 4–12)
> **Objetivo:** Mapear todos os indicadores, thresholds, fórmulas e lógicas; identificar vulnerabilidades, pontos fortes e fracos; propor melhorias para aumentar a consistência dos resultados.

---

## Sumário

1. [Visão Geral dos Dois Sistemas](#1-visão-geral-dos-dois-sistemas)
2. [Scalper Engine — Análise Completa](#2-scalper-engine--análise-completa)
3. [Paper Trading Engine — Análise Completa](#3-paper-trading-engine--análise-completa)
4. [Trade Management (Fase 12) — Análise](#4-trade-management-fase-12--análise)
5. [Análise Comparativa: Scalper vs Paper](#5-análise-comparativa-scalper-vs-paper)
6. [Vulnerabilidades Críticas Transversais](#6-vulnerabilidades-críticas-transversais)
7. [Recomendações Prioritárias](#7-recomendações-prioritárias)
8. [Roteiro de Melhorias Sugerido](#8-roteiro-de-melhorias-sugerido)

---

## 1. Visão Geral dos Dois Sistemas

| Aspecto | Scalper (Fase 13) | Paper Trading (Fases 4–12) |
|---|---|---|
| **Timeframes** | 1m · 5m · 15m | 15m · 1h (pelo scheduler) |
| **Símbolos** | BTC, ETH, SOL, AVAX | Mesmo + qualquer no scheduler |
| **Abordagem** | Multi-timeframe estrita (3 estágios) | 13 critérios paralelos com pesos adaptativos |
| **Indicadores base** | EMA(9,21,50), RSI(14), MACD(12,26,9) | EMA(9,21,50,200), RSI(14), MACD(12,26,9) |
| **Complexidade** | Baixa (~262 linhas) | Muito alta (6+ módulos, 13+ critérios, ML-free) |
| **Gestão de risco** | SL 0.25%, TP 0.50%, Trailing, BE, Time Stop 2h | SL 2%, TP 4%, Trailing, BE, Time Stop 48h, Exit Score |
| **Adaptabilidade** | Nenhuma (fixo) | Pesos adaptativos por critério (otimizador Fase 8) |
| **Contexto externo** | Não usa | Fear & Greed, Funding Rate, News, OI |
| **SMC (Smart Money)** | Não usa | Sweep, FVG, Volume Profile, Liquidity Score |

---

## 2. Scalper Engine — Análise Completa

### 2.1 Signal Engine — Métricas e Thresholds

#### Estágio 1: Tendência 15m

| Métrica | Fórmula | Threshold |
|---|---|---|
| EMA(9) > EMA(21) > EMA(50) | Comparação direta | **Estritamente ordenado** |
| Preço > EMA(21) | Preço atual vs EMA(21) | **Acima** |

**Pontos fortes:**
- ❄️ Filtro de tendência rigoroso — só opera alinhado com o macro local
- 🔄 Três EMAs dá mais robustez que apenas duas (evita falso crossover em 9/21)

**Pontos fracos:**
- 🚫 **SIDEWAYS = descarte total** — Perde oportunidades em mercados laterais com micro-movimentos
- 📏 **Ordem estrita** — EMA9 > EMA21 > EMA50 é muito rígido; EMA9 > EMA21 já bastaria se EMA50 for neutra
- 🔇 **Sem análise de volume** — Tendência medida apenas por preço, sem confirmação de volume
- 📊 **Apenas 55 velas** — Pode pegar uma tendência recente curta (poucas horas) como se fosse estrutural

#### Estágio 2: Confirmação 5m

| Métrica | Condição LONG | Condição SHORT |
|---|---|---|
| RSI(14) | 30–58 | 42–70 |
| EMA9 vs EMA21 | EMA9 > EMA21 (micro_bull) | EMA9 < EMA21 (micro_bear) |
| Proximidade do EMA9 | `abs(price - EMA9)/EMA9 ≤ 0.005` (0.5%) | Idem |
| Fallback | price < EMA9 × 1.001 | price > EMA9 × 0.999 |

**Pontos fortes:**
- ✅ RSI com ranges diferentes para LONG vs SHORT (assimétrico) — reconhece que momentum de alta e baixa têm características diferentes
- ✅ Exige proximidade do EMA9 (pullback/bounce) — evita entrar em fuga vertical
- ✅ Combina micro-tendência + RSI + preço relativo = 3 fatores independentes

**Pontos fracos/vulnerabilidades:**
- 🚩 **RSI 30–58 para LONG é muito baixo** — Exige RSI abaixo de 58, o que significa que só entra em LONG quando o momentum ainda está fraco ou negativo. Isso pode filtrar entradas boas, mas também faz perder o início de movimentos fortes.
- 🚩 **RSI 42–70 para SHORT é muito amplo** — 42–70 significa que entra em SHORT mesmo com RSI em zona neutra-alta (até 70), o que contradiz a lógica de "exaurimento de alta".
- 🚩 **Sem convergência/divergência** — Não verifica divergência RSI-preço (um dos sinais mais fortes para reversão)
- 🚩 **Fallback muito permissivo** — `price < EMA9 * 1.001` significa "pode estar até 0.1% acima do EMA9" — essencialmente remove a exigência de proximidade

#### Estágio 3: Gatilho 1m

| Métrica | Condição LONG | Condição SHORT |
|---|---|---|
| Candle atual | Bullish (close > open) | Bearish (close < open) |
| MACD Histograma |  `prev < 0 ≤ curr` OU `curr > 0` | `prev > 0 ≥ curr` OU `curr < 0` |
| RSI(14) | 35–70 | 30–65 |

**Pontos fortes:**
- ✅ Gatilho de candle + MACD + RSI — três confirmações independentes no timeframe mais granular
- ✅ MACD cross é um dos indicadores mais rápidos e confiáveis para entrada

**Pontos fracos/vulnerabilidades:**
- 🚩 **RSI 35–70 para LONG é redundante** — Se o RSI da 5m já está em 30–58, o RSI da 1m em 35–70 adiciona pouco; quando um está OK e o outro não, cria inconsistência
- 🚩 **MACD cross único** — Um único cruzamento pode ser ruído; exigir 2 candles consecutivos pós-cruzamento reduziria falsos sinais
- 🚩 **Candle bullish/bearish individual** — Vela individual tem baixo poder preditivo (especialmente em 1m com micro-ruído)
- 🚩 **Apenas 36 velas para MACD** — Mínimo de 36 velas = 36 minutos de dados. MACD com apenas 36 amostras em 1m é instável

#### Score de Confiança (0–100)

| Componente | Pontos |
|---|---|
| Base (confirm + entry OK) | 65 |
| RSI 5m ideal (LONG: 38–52, SHORT: 48–62) | +10 |
| RSI 1m ideal (40–60) | +10 |
| **Máximo** | **100** |

**Vulnerabilidade:** O score é extremamente binário — ou tem 65 (se passou nos filtros) ou 0 (se não passou). O bônus de RSI ideal (+10 cada) é pequeno demais para criar diferenciação significativa. Isso significa que **todos os trades aprovados são essencialmente iguais** (confiança 65–85), sem hierarquia real de qualidade.

### 2.2 Scalper Trade Engine — Gestão de Posição

| Parâmetro | Valor V7 | R:R |
|---|---|---|---|
| SL | `max(0.25%, ATR_1m × 1.5)` | — |
| TP | SL × 2.0 (R:R 1:2) | 1:2 |
| SL_ATR_MULTIPLIER | 1.5 | — |
| TP_RR | 2.0 | — |
| BE Trigger | 0.20% | — |
| Trailing Start | 0.40% | — |
| Trailing Distance | 0.15% | — |
| Time Stop | 120 min | — |
| Risk base/trade | $10 | — |
| **Sizing: confidence** | `risk × max(25%, conf/100)` | V7 |
| **Sizing: regime** | `risk × regime_sizing()` | V7 |

**Melhorias V7:**
- ✅ **SL adaptativo por ATR** — SL = `max(0.25%, ATR_1m × 1.5)`. Se ATR da 1m é 0.30%, SL = 0.45%. Se ATR é 0.10%, SL = 0.25% (mínimo). Protege contra volatilidade anormal sem perder proteção mínima.
- ✅ **Position sizing por confiança** — `risk = $10 × max(25%, confidence/100)`. Trade com confiança 80% arrisca $8; confiança 50% arrisca $5. Escala proporcional à qualidade do setup.
- ✅ **R:R 1:2 mantido via TP_RR** — TP = SL × 2.0. Se SL adaptativo muda para 0.45%, TP automaticamente vai para 0.90%. Proporcionalidade preservada.

**Vulnerabilidades remanescentes:**
- 🚩 **BE +0.20% com SL mínimo 0.25%** — A distância entre o SL original e o BE é de apenas 0.05%. O preço precisa se mover apenas 0.20% para ativar BE.
- 🚩 **Trailing Distance 0.15% com Start 0.40%** — Após ativar o trailing, o stop fica a 0.15% do pico. Muito apertado para 1m.
- 🚩 **Time Stop de 2h em scalper de 1m** — Trade aberto por 2h sem atingir SL/TP indica que o setup quebrou.

### 2.3 Scalper Risk Manager

**Estado V7:** Estatístico + Circuit Breaker por regime de mercado.

| Métrica | Rastreada? | Bloqueia global? | Bloqueia por regime? |
|---|---|---|---|
| Perdas consecutivas | ✅ Sim | ❌ Não | ✅ Sim (V7) |
| PnL diário % | ✅ Sim | ❌ Não | ❌ |
| Total de trades/dia | ✅ Sim | ❌ Não | ❌ |

**Circuit Breaker V7 (por regime):**
- **3 perdas consecutivas** em um regime (ex: BULL) → **sizing reduzido para 50%** nesse regime
- **5 perdas consecutivas** em um regime → **regime pausado** (trades ignorados) até próxima vitória no regime
- **Vitória reseta** o contador do regime e reativa se pausado
- Regimes monitorados: BULL, BEAR, SIDEWAYS (HIGH_VOL mapeado via _regime_losses)
- **Não bloqueia globalmente** — trades em regimes saudáveis continuam normalmente

**Vulnerabilidade:**
- 🚩 Ainda **sem limite de perda diária global**. Uma sequência de perdas distribuídas entre regimes (ex: 3 perdas em BULL, 3 em BEAR, 3 em SIDEWAYS) não ativa o circuit breaker de nenhum regime individual.

---

## 3. Paper Trading Engine — Análise Completa

### 3.1 Signal Engine V7 — 13 Critérios + Decisão por Score Ponderado

#### Categorias dos Critérios

| Categoria | Critérios | Peso Máximo |
|---|---|---|
| **Técnicos (6)** | EMA Cross, EMA Macro, EMA Price, MACD Trend, MACD Signal, RSI | 6 × 20 = 120 |
| **Estruturais (3)** | Structure, BOS, S/R Zone | 3 × 20 = 60 |
| **SMC (4)** | Liquidity Sweep, FVG, Volume Profile, Liquidity Score | 4 × 20 = 80 |
| **Total** | **13** | **260** |

#### Regime-Adaptive RSI e Mínimos

| Regime | RSI Buy Range | RSI Sell Range | Min Buy | Min Sell |
|---|---|---|---|---|
| **BULL** | 40–78 | 28–60 | 3/13 | 4/13 |
| **BEAR** | 25–50 | 40–70 | 5/13 | 2/13 |
| **SIDEWAYS** | 45–65 | 35–55 | 4/13 | 4/13 |
| **HIGH_VOL** | 40–68 | 32–60 | 4/13 | 4/13 |

#### ✅ V7: Decisão por Score Ponderado (substituiu Majority Vote)

**Antes (V5/V6):** `BUY se buy_count >= min_buy AND buy_count > sell_count` — ignorava pesos.

**Agora (V7):**
```python
if weighted_score_buy - weighted_score_sell >= NEUTRAL_ZONE:  # 10
    direction = BUY
elif weighted_score_sell - weighted_score_buy >= NEUTRAL_ZONE:
    direction = SELL
else:
    direction = NEUTRAL
```

- `NEUTRAL_ZONE = 10` — evita whiplash em diferenças marginais
- Pesos dos critérios finalmente importam na decisão binária
- Backward compatible: se weights não disponíveis, usa V5 (count)

**Pontos fortes:**
- ✅ **Regime-adaptativo** — O RSI muda conforme o regime de mercado
- ✅ **Mínimos assimétricos** — Em BULL, exige menos critérios para BUY que para SELL
- ✅ **V7: Decisão por score ponderado** — Pesos finalmente impactam a direção do trade
- ✅ **13 critérios paralelos** — Diversificação de fatores reduz overfitting
- ✅ **Separação técnica + estrutural + SMC** — Abordagem holística

**Vulnerabilidades remanescentes:**
- 🚩 **Sem verificação de divergência** — Nenhum critério captura divergência RSI/MACD
- 🚩 **SIDEWAYS exige 4 critérios mínimos** — Pode ser difícil de atingir em mercado lateral
- 🚩 **HIGH_VOL: sem adaptação de SL/TP** — Apenas muda RSI/mínimos
- 🚩 **Min BULL = 3/13** — Possível entrar sem estrutura nem SMC

### 3.2 Score de Confiança V6

**Raw Score (backward):**
```
raw = (count / total_max) × 100
```
Onde `total_max` depende de quais módulos estão disponíveis (6 a 13).

**Weighted Score (V6 atual):**
```
weighted = min(100, (sum_weights / (total_max × 10.0)) × 100)
```

**Vulnerabilidades:**
- 🚩 **Normalização problemática** — `total_max × 10.0` assume que cada critério pode ter peso 10.0, mas os pesos variam de 1.0 a 20.0. Se um critério muito relevante tem peso 20, a conta `sum_weights / (total_max × 10.0)` pode dar >1.0 e ser truncada. Isso achata a diferenciação.
- 🚩 **Context Boost é frágil** — Adiciona ±5–10 pontos baseado em notícias/F&G, mas o impacto no resultado final depende de quantos critérios foram aprovados. Um contexto contrário pode anular um setup tecnicamente forte sem proporcionalidade.
- 🚩 **Sem calibração histórica** — O score não é calibrado contra resultados passados. Um score de 72 não tem significado intrínseco — não sabemos se trades com score 72+ têm win rate de 60% ou 40%.

### 3.3 Regime Classifier

| Métrica | Threshold |
|---|---|
| High Vol | ATR% ≥ 3.0% |
| BULL | EMA Score ≥ +3 E preço > EMA200 |
| BEAR | EMA Score ≤ -3 E preço < EMA200 |
| SIDEWAYS | Restante |

**Fórmula EMA Score (-4 a +4):**
- EMA9 > EMA21 → +1 / -1
- EMA21 > EMA50 → +1 / -1
- EMA50 > EMA200 → +1 / -1
- EMA9 > EMA200 → +1 / -1

**Vulnerabilidades:**
- 🚩 **Alinhamento de EMAs é lento** — O EMA Score muda devagar (precisa de 4 cruzamentos). O regime pode ficar classificado como BULL por horas depois de o mercado já ter virado, gerando sinais contra a nova tendência.
- 🚩 **High Vol detectado apenas por ATR%** — Um mercado pode estar extremamente volátil sem que o ATR% ultrapasse 3% (ex: gap de abertura seguido de range estreito). Além disso, ATR é um indicador defasado.
- 🚩 **SIDEWAYS é catch-all** — Qualquer coisa que não é BULL, BEAR ou HIGH_VOL cai em SIDEWAYS. Não há detecção real de sideway (compressão, baixa volatilidade relativa, etc.)
- 🚩 **Confiança do regime não é usada no signal engine** — O regime tem `ema_confidence` (0–100), mas o signal engine só usa o label, não a confiança. Um regime "BULL" com confiança 51% trata igual a "BULL" com confiança 99%.

### 3.4 Market Structure + SMC (Fases 6.5 e 7)

#### Structure Classifier

| Componente | Parâmetro | Valor |
|---|---|---|
| Swing Detection | `swing_length` | 5 candles |
| BOS Tolerance | `bos_tolerance` | 0.1% |
| S/R Cluster | `cluster_tolerance` | 0.5% |
| S/R Proximity | `proximity_pct` | 1.5% |

**Vulnerabilidades:**
- 🚩 **swing_length fixo em 5** — Em timeframe de 15m, 5 velas = 75min. Em 1h, 5 velas = 5h. O mesmo parâmetro não serve para todos os timeframes.
- 🚩 **BOS tolerance de 0.1% é muito pequeno** — Qualquer micro-quebra de estrutura já conta como BOS. Gera muitos falsos positivos.
- 🚩 **S/R zones usam apenas pivots (swing highs/lows)** — Não incorpora volume (order flow), liquidez ou zonas institucionais (eleições de opções, etc.)
- 🚩 **Apenas 5 zonas máximas** — Pode perder suportes/resistências importantes em mercados com muitos níveis

#### Liquidity Sweep Detector

| Parâmetro | Valor |
|---|---|
| `sweep_tolerance` | 0.1% |
| `reversal_pct` | 0.3% |
| `lookback_candles` | 10 |
| `stop_hunt_mult` | 2.0× |

**Vulnerabilidades:**
- 🚩 **reversal_pct de 0.3%** — Em mercados de alta volatilidade (BTC), 0.3% pode ser atingido por ruído. Deveria ser adaptativo à volatilidade atual (ex: 0.5× ATR).
- 🚩 **Falso sweep comum** — Preço que penetra 0.1% além de um swing high e fecha 0.3% abaixo é classificado como sweep legítimo. Em mercados rápidos, isso acontece por acaso em ~20% das velas.
- 🚩 **Não valida sweep com volume** — Sweep verdadeiro tipicamente tem volume acima da média. O detector não usa volume.

#### Fair Value Gap Engine

| Parâmetro | Valor |
|---|---|
| `proximity_pct` | 2.0% |
| `max_age_candles` | 50 |
| `min_gap_pct` | 0.05% |

**Vulnerabilidades:**
- 🚩 **min_gap_pct de 0.05% é minúsculo** — Qualquer gap de 0.05% (em BTC: ~$5) é considerado FVG. A maioria é ruído de spread.
- 🚩 **max_age_candles fixo** — Em timeframe variável, 50 velas significa durações diferentes. Deveria ser baseado em tempo real (ex: 4h).
- 🚩 **Não mede profundidade do gap** — Um FVG de $100 tem o mesmo peso que um de $5 na classificação.

#### Volume Profile Lite

| Parâmetro | Valor |
|---|---|
| `n_bins` | 50 |
| `value_area_pct` | 70% |
| `hvn_threshold` | 1.5× média |
| `lvn_threshold` | 0.4× média |

**Vulnerabilidades:**
- 🚩 **Apenas 50 bins** — Em mercados com grande amplitude de preço, 50 bins podem ser muito poucos, agrupando níveis distintos no mesmo bin.
- 🚩 **Value Area de 70% é arbitrário** — O padrão da indústria é 70%, mas não há validação de que este valor otimiza os resultados para os ativos negociados.
- 🚩 **Volume Profile é "lite"** — A distribuição proporcional de volume por range é uma aproximação (volume é distribuído igualmente no range da vela, não no perfil real de ticks).

### 3.5 Context Engine

| Componente | Peso |
|---|---|
| Fear & Greed | 35 |
| News Sentiment | 30 |
| Funding Rate | 20 |
| Open Interest | 15 |

**Vulnerabilidades:**
- 🚩 **Peso de 35 no F&G é excessivo** — Fear & Greed é um índice diário, defasado e genérico (todo o mercado crypto). Dar 35% do contexto de entrada para ele é arriscado.
- 🚩 **Funding Rate normalização** — Mapeia [-0.1%, +0.1%] → [0, 100]. Funding de 0% vira score 50. Funding de -0.05% vira score 25. Não há assimetria — funding negativo pode ser alcista (longs pagando shorts) mas o modelo trata como baixista.
- 🚩 **OI Change normalização** — [-10%, +10%] → [0, 100]. OI subindo 2% vira score 60. OI caindo 2% vira score 40. Não há validação de que OI subindo é realmente altista (pode ser acúmulo de shorts).

### 3.6 Optimizer / Adaptive Weights (Fase 8)

| Parâmetro | Valor |
|---|---|
| `DEFAULT_WEIGHT` | 10.0 |
| `MIN_WEIGHT` | 1.0 |
| `MAX_WEIGHT` | 20.0 |
| `MAX_DELTA` | 1.0/ciclo |
| `SCALE_FACTOR` | 5.0 |
| `MIN_SAMPLE` | 5 |
| `LOOKBACK_DAYS` | 90 |

**Fórmula de atualização de peso:**
```
perf_delta  = (wr_delta + pf_delta)/2 - dd_penalty
raw_adj     = perf_delta × 5.0
clamped_adj = clamp(raw_adj, -1.0, +1.0)
new_weight  = clamp(cur + clamped_adj, 1.0, 20.0)
```

**Vulnerabilidades:**
- 🚩 **Mudança máxima de ±1.0 por ciclo** — Para ir de 10.0 → 20.0 precisa de 10 ciclos de acertos consecutivos. Isso torna o sistema muito lento para se adaptar a mudanças de regime.
- 🚩 **dd_penalty = max(0, drawdown/10)** — Um drawdown de 5% gera penalidade de 0.5. Com SCALE_FACTOR=5, um drawdown pequeno pode anular o wr_delta e pf_delta. Penalidade muito alta.
- 🚩 **Baseline WR e PF fixos** — Usa a média geral histórica como baseline. Se o mercado mudou, a baseline está desatualizada. Um critério que performa bem no novo regime mas mal no histórico geral seria prejudicado.
- 🚩 **MIN_SAMPLE = 5** — Apenas 5 trades para ajustar um peso. Em 5 trades, uma única aberração estatística pode mudar o peso significativamente.
- 🟢 **✅ V7: Pesos por regime implementados** — Pesos agora são mantidos separadamente por regime (GLOBAL, BULL, BEAR, SIDEWAYS, HIGH_VOL). O otimizador ajusta cada conjunto independentemente usando os dados do RegimePerformanceAnalyzer.

---

## 4. Trade Management (Fase 12) — Análise

### 4.1 Exit Score

| Componente | Peso | Faixa |
|---|---|---|
| Context Score | 25% | ±25 |
| Regime | 25% |  -20 a +20 |
| Structure | 25% | -30 a +15 |
| SMC/Liquidity | 15% | -13 a +5 |
| Momentum (PnL) | 10% | ±10 |

**Threshold:** `paper_exit_score_threshold = 30.0`

**Pontos fortes:**
- ✅ Dashboard completo de fatores para decidir saída
- ✅ Inversão correta para SHORT (context score positivo reduz score de SHORT)
- ✅ Penalidade de regime: LONG em BEAR = -20 (grande penalidade)
- ✅ Momentum/PnL dá peso ao fato consumado

**Vulnerabilidades:**
- 🚩 **Estrutura pode dar mais dano (-30) que contexto de mercado (+25)** — Structure domina o score. Uma estrutura bearish (-20) + BOS adverso (-10) = -30. Isso pode estourar o trade mesmo com regime BULL (+20) e contexto positivo (+25).
- 🚩 **Momentum dá ±10 para ±10% de PnL** — Um trade com -1% de PnL perde 1 ponto. Com +8% de PnL ganha 8 pontos. Mas o threshold é 30, e o score começa em 50. O momentum sozinho quase nunca leva à saída.
- 🚩 **Break-even não aumenta o exit score** — Depois que o BE ativa, o trade está sem risco de perda (stop na entrada). Mas o Exit Score não leva isso em conta — poderia reduzir o limiar de saída ou adicionar bônus.
- 🚩 **Não há peso para tempo aberto** — Um trade que está há 40h aberto deveria ter maior propensão a sair (mesmo que não tenha atingido o time stop de 48h).
- 🚩 **SWEEP BIAS penaliza com -8 pontos** — Se sweep_bias é BEARISH e estamos LONG, perde 8 pontos. Mas o liq_score pode dar +5. Efeito líquido pequeno.

### 4.2 Partial TP1 e TP2

| Parâmetro | Valor |
|---|---|
| TP1 (50% saída) | +2.0% |
| TP2 (100% saída) | +4.0% |

**Análise:**
- ✅ TP1 cedo (+2%) garante lucro parcial na maioria dos trades que atingem o alvo
- ✅ Saldo atualizado imediatamente no TP1

**✅ V7: Overlap corrigido:**

| Parâmetro | V6 | V7 | Motivo |
|---|---|---|---|
| BE Trigger | +1.5% | **+1.0%** | Protege capital mais cedo (antes do TP1) |
| Trailing Start | +2.0% | **+2.5%** | Após TP1 (+2.0%), evita overlap |
| TP1 | +2.0% | +2.0% | Mantido |
| TP2 | +4.0% | +4.0% | Mantido |

**Ordem de eventos V7:**
1. Preço +1.0% → BE ativa, stop move para entrada (trade sem risco)
2. Preço +2.0% → TP1 fecha 50% com lucro (R:R 1:1 nesta parcela)
3. Preço +2.5% → Trailing ativa, stop a 1.0% do pico
4. Preço +4.0% → TP2 fecha o restante (R:R 2:1 nesta parcela)

**Vulnerabilidade remanescente:**
- 🚩 **R:R real é menor que 1:2 nominal** — Metade fecha em 1:1 (TP1), metade em 2:1 (TP2). Eficiência = (0.5 × 1 + 0.5 × 2) / 2 = 1.5:1 na prática.

### 4.3 Break Even + Trailing + Time Stop

| Mecanismo | Ativa em (V7) | Distância |
|---|---|---|
| Break Even | **+1.0%** (era 1.5%) | Stop move para entry |
| Trailing Start | **+2.5%** (era 2.0%) | 1.0% do pico |
| Time Stop | 48h | — |

**✅ V7: Overlap resolvido:**
- BE ativa em +1.0% (antes do TP1 de +2.0%)
- Trailing ativa em +2.5% (depois do TP1)
- Range de overlap reduzido de 0.5% para 0%

**Vulnerabilidade remanescente:**
- 🚩 **Trailing distance 1% com Time Stop 48h** — 1% de distância em timeframe 1h é apertado. Pullback normal de 1–2% pode estopar o trailing.

---

## 5. Análise Comparativa: Scalper vs Paper

| Métrica | Scalper | Paper Trading |
|---|---|---|
| **Win rate estimado** | Precisa ser >50% (R:R 1:2) | Precisa ser >33% (R:R 1:2) |
| **Frequência de trades** | Muito alta (1m) | Baixa (15m/1h) |
| **Qualidade dos sinais** | Alta (filtro multi-estágio) | Variável (13 critérios adaptativos) |
| **Robustez do sistema** | Baixa (poucos indicadores) | Média-alta (muitos indicadores) |
| **Resistência a ruído** | Baixa (1m + 0.25% SL) | Alta (15m/1h + 2% SL) |
| **Adaptabilidade** | Nula (parâmetros fixos) | Média (pesos adaptativos, regime) |
| **Exposição a fatores externos** | Nula (só preço) | Alta (F&G, Funding, News, OI) |
| **Complexidade de manutenção** | Baixa (3 arquivos) | Muito alta (15+ módulos) |
| **Drenagem por comissão** | Alta (muitos trades) | Baixa (poucos trades) |

---

## 6. Vulnerabilidades Críticas Transversais

### 🔴 6.1 Ausência de Validação Estatística

Não há um sistema que:
- Calibre o score de confiança contra resultados históricos reais
- Valide que RSI 30–58 realmente produz melhores trades que RSI 40–65
- Meça o impacto real de cada critério no resultado líquido (PnL real, não win rate)

**Impacto:** Os parâmetros atuais são escolhas arbitrárias ou baseadas em "sabedoria popular" de trading, não em dados do próprio sistema.

### 🟢 6.2 ✅ RESOLVIDO — Ajuste de Posição por Confiança (V7)

**Antes:** Ambos os sistemas usavam posição fixa ($10/scalper, $10/paper).
**Depois (V7):**
- **Scalper:** `risk = $10 × max(25%, confidence/100) × regime_sizing()`
- **Paper:** `quantity = risk_effective / price` onde `risk_effective = $10 × max(25%, confidence/100)`

Trades com confiança 90% arriscam $9 (vs $10 máximo). Trades com confiança 50% arriscam $5. O fator `regime_sizing()` em scalper reduz ainda mais em regimes problemáticos.

**Pendente:** Aumento de posição para sinais de altíssima convicção (ex: confidence > 85 → bonus × 1.25).

### 🟡 6.3 Performance por Regime — Parcialmente Resolvido

**Antes:** Pesos globais, sem adaptação por regime.
**Depois (V7):**
- ✅ **Pesos por regime** — 4 conjuntos independentes de pesos, ajustados separadamente
- ✅ **Circuit breaker** — Pausa automática por regime no scalper (3 perdas → 50%, 5 perdas → pausa)
- ⬜ **Adaptação de SL/TP por volatilidade** — Ainda não implementado no paper trading
- ⬜ **Pausa automática para paper trading** — Circuit breaker existe apenas no scalper

**Impacto residual:** Sistema de paper trading ainda não tem circuit breaker por regime. SL/TP não adaptam por volatilidade (exceto scalper com ATR-adaptativo).

### 🟢 6.4 ✅ RESOLVIDO — Decisão por Score Ponderado (V7)

**Antes:** `BUY se buy_count >= min_buy AND buy_count > sell_count` — votação por maioria ignorando pesos.

**Depois (V7):**
```python
NEUTRAL_ZONE = 10
BUY  se weighted_buy - weighted_sell >= NEUTRAL_ZONE
SELL se weighted_sell - weighted_buy >= NEUTRAL_ZONE
```

Os pesos de cada critério (1–20) agora determinam a direção. Um trade com 4 critérios de peso 20 (score=80) vence 5 critérios de peso 1 (score=5). O sistema de pesos adaptativos finalmente tem efeito na decisão.

### 🔴 6.5 Sem Tratamento de Comissões e Slippage

Nenhum dos sistemas modela:
- Taxa de exchange (maker/taker)
- Spread bid-ask
- Slippage de execução (especialmente relevante para scalper em 1m)

**Impacto:** O PnL reportado é maior que o real. Trades marginalmente lucrativos podem ser perdedores na vida real.

### 🔴 6.6 Sem Coleta de Métricas de Performance por Configuração

O sistema não correlaciona mudanças de parâmetros com resultados. Se você muda SL de 0.25% para 0.30% no scalper, não há um dashboard que mostre "antes: 55% WR, depois: 58% WR".

**Impacto:** Melhorias são feitas "no escuro" — não há como saber se uma mudança realmente melhorou o sistema.

---

## 7. Recomendações Prioritárias

### ✅ JÁ IMPLEMENTADAS (V7)

#### 7.1 ✅ Decisão por Score Ponderado — IMPLEMENTADO

**Status:** Signal Engine V7 agora usa `weighted_score_buy - weighted_score_sell >= NEUTRAL_ZONE (10)` para decisão. Pesos de critérios (1–20) finalmente impactam a direção. Backward compatible com V5/V6.

**Arquivo:** `backend/app/services/analysis/signal_engine.py`

#### 7.2 ✅ Dimensionamento de Posição por Confiança — IMPLEMENTADO

**Status:** Ambos os sistemas agora escalam posição por confiança:
- **Scalper:** `risk = $10 × max(25%, confidence/100) × regime_sizing()`
- **Paper:** `quantity = (paper_risk_per_trade × max(25%, confidence/100)) / price`

**Arquivos:** `scalper/trade_engine.py`, `paper_trading/trade_engine.py`

#### 7.4 ✅ SL Adaptativo por ATR (Scalper) — IMPLEMENTADO

**Status:** SL = `max(0.25%, ATR_1m × 1.5%)` com TP mantendo R:R 1:2 via `TP_RR=2.0`. Protege contra volatilidade anormal.

**Arquivo:** `scalper/trade_engine.py`

#### 7.5 ✅ Overlap BE/Trailing/TP1 — IMPLEMENTADO

**Status:** BE=+1.0% (antes 1.5%), Trailing Start=+2.5% (antes 2.0%). Range de overlap eliminado.

**Arquivo:** `backend/app/config.py`

#### 7.7 ✅ Conflito Majority Vote × Weighted Score — IMPLEMENTADO

**Status:** `7.1` já resolveu o conflito. Majority vote substituído por weighted score com NEUTRAL_ZONE=10. `7.1` e `7.7` são a mesma alteração.

#### 7.8 ✅ Volume/OBV no Scalper — IMPLEMENTADO

**Status:** OBV (On-Balance Volume) adicionado no estágio 5m do scalper:
- `obv_trend`: BULL/BEAR/NEUTRAL baseado na EMA(14) vs EMA(28) do OBV
- `volume_spike`: último candle 5m com volume > 1.5× média de 20 períodos
- OBV contraditório → NONE (invalida confirmação)
- OBV favorável + volume spike → +5 na confidence

**Arquivo:** `scalper/signal_engine.py`

#### 7.10 ✅ Circuit Breaker por Regime — IMPLEMENTADO

**Status:** ScalperRiskManager agora rastreia perdas consecutivas por regime (BULL/BEAR/SIDEWAYS):
- 3 perdas → sizing 50% no regime
- 5 perdas → regime pausado (trades ignorados)
- Vitória reseta e reativa o regime

**Arquivo:** `scalper/risk_manager.py`, `scalper/trade_engine.py`

### 🥇 Próximas Alta Prioridade (Pendentes)

#### 7.3 ✅ Pesos por Regime de Mercado — IMPLEMENTADO

**Status:** Pesos agora são mantidos separadamente por regime (GLOBAL, BULL, BEAR, SIDEWAYS, HIGH_VOL).

**O que mudou:**
- **DB:** `criterion_weights` agora tem coluna `regime` + unique(regime, criterion)
- **WeightEngine:** `load_weights(regime)`, `save_weights(weights, regime)`, `compute_new_weights_from_stats()`, `load_all_regime_weights()`
- **OptimizerEngine:** Após o ciclo GLOBAL, itera por regime → usa `RegimeData.criteria_stats` para ajustar pesos específicos do regime
- **Scheduler:** Mantém `_cached_regime_weights: dict[str, dict[str, float]]` → seleciona pesos pelo regime atual via `_resolve_weights_for_regime()`
- **SignalEngine:** Continua recebendo `weights` dict — o scheduler passa o conjunto correto

**Fluxo:** RegimeClassifier → regime_label → scheduler seleciona pesos → generate_signal(weights=regime_weights)

#### 7.6 Validação Estatística Cross-Validation

Implementar módulo que divide dados históricos em treino/teste (80/20) e mede win rate/PF por parâmetro calibrado.

### 🥈 Média Prioridade (Futuras)

#### 7.9 Métricas de Qualidade do Sinal

Armazenar score individual por critério, contribuição por módulo, distância do threshold, expected value por perfil de sinal.

#### 7.11 Modelar Comissões e Slippage

Adicionar taxa 0.05–0.10% por perna, slippage 0.01–0.05%, spread bid-ask.

---

## 8. Roteiro de Melhorias Sugerido

```
Fase 1 (Imediata — CONCLUÍDA V7):
├── ✅ 7.1 Decisão por score ponderado (V7 signal engine)
├── ✅ 7.4 SL adaptativo por ATR (scalper)
├── ✅ 7.5 Overlap BE/Trailing/TP1 corrigido (paper)
├── ✅ 7.7 Conflito majority vote × weighted score removido
├── ✅ 7.2 Position sizing por confiança (ambos os sistemas)
├── ✅ 7.8 Volume/OBV no scalper 5m
└── ✅ 7.10 Circuit breaker por regime (scalper risk manager)

Fase 2 (Próximo — 1 semana):
├── ✅ 7.3 Pesos separados por regime de mercado
├── ⬜ 7.6 Validação estatística cross-validation
└── ⬜ 7.9 Métricas de qualidade do sinal

Fase 3 (Médio prazo — 2-4 semanas):
├── ⬜ 7.11 Modelar comissões e slippage
├── ⬜ Dashboard de performance por configuração
└── ⬜ Refinar ranges RSI calibrados por dados históricos
```

---

## Apêndice A: Todos os Parâmetros Atuais (Cheat Sheet)

### Scalper (V7)

| Parâmetro | Valor V7 | Arquivo |
|---|---|---|
| EMA períodos | 9, 21, 50 | signal_engine.py |
| RSI período | 14 | signal_engine.py |
| MACD | 12, 26, 9 | signal_engine.py |
| RSI 5m LONG | 30–58 | signal_engine.py |
| RSI 5m SHORT | 42–70 | signal_engine.py |
| RSI 1m LONG | 35–70 | signal_engine.py |
| RSI 1m SHORT | 30–65 | signal_engine.py |
| Proximity EMA9 | 0.5% | signal_engine.py |
| **ATR período** | **14** **(V7)** | signal_engine.py |
| **OBV período** | **14/28 (V7)** | signal_engine.py |
| **Volume spike** | **1.5× média 20** **(V7)** | signal_engine.py |
| SL | `max(0.25%, ATR_1m × 1.5)` **(V7)** | trade_engine.py |
| TP | SL × 2.0 **(V7)** | trade_engine.py |
| SL_ATR_MULTIPLIER | 1.5 **(V7)** | trade_engine.py |
| TP_RR | 2.0 **(V7)** | trade_engine.py |
| BE Trigger | 0.20% | trade_engine.py |
| Trailing Start | 0.40% | trade_engine.py |
| Trailing Dist | 0.15% | trade_engine.py |
| Time Stop | 120 min | trade_engine.py |
| Risco base/trade | $10 | trade_engine.py |
| **Sizing confidence** | `risk × max(25%, conf/100)` **(V7)** | trade_engine.py |
| **Sizing regime** | `risk × regime_sizing()` **(V7)** | trade_engine.py |
| **Circuit breaker** | **3→50%, 5→pausa** **(V7)** | risk_manager.py |

### Paper Trading (V7)

| Parâmetro | Valor | Arquivo |
|---|---|---|
| RSI BULL Buy | 40–78 | signal_engine.py |
| RSI BULL Sell | 28–60 | signal_engine.py |
| RSI BEAR Buy | 25–50 | signal_engine.py |
| RSI BEAR Sell | 40–70 | signal_engine.py |
| Min Buy BULL | 3/13 | signal_engine.py |
| Min Sell BULL | 4/13 | signal_engine.py |
| Min Buy BEAR | 5/13 | signal_engine.py |
| Min Sell BEAR | 2/13 | signal_engine.py |
| Peso default | 10.0 | weight_engine.py |
| Peso min/max | 1.0/20.0 | weight_engine.py |
| Max delta/ciclo | 1.0 | weight_engine.py |
| **Regimes (V7)** | **GLOBAL, BULL, BEAR, SIDEWAYS, HIGH_VOL** | weight_engine.py |
| **Seleção V7** | **regime atual → resolve_weights_for_regime()** | scheduler.py |
| **Decisão V7** | **score ponderado, NEUTRAL_ZONE=10** | signal_engine.py |
| SL | 2.0% | config.py |
| TP (TP2) | 4.0% | config.py |
| **BE Trigger** | **1.0% (V7: era 1.5%)** | config.py |
| **Trailing Start** | **2.5% (V7: era 2.0%)** | config.py |
| Trailing Dist | 1.0% | config.py |
| TP1 | 2.0% | config.py |
| Time Stop | 48h | config.py |
| Exit Threshold | 30.0 | config.py |
| **Sizing confiança** | **`risk × max(25%, conf/100)` (V7)** | trade_engine.py |
| Risco/trade | $10 | config.py |
| Saldo inicial | $200 | config.py |
| Context: F&G peso | 35% | context_engine.py |
| Context: News peso | 30% | context_engine.py |
| Context: Funding peso | 20% | context_engine.py |
| Context: OI peso | 15% | context_engine.py |
| Swing length | 5 | swing_detector.py |
| Sweep tolerance | 0.1% | liquidity_sweep.py |
| Reversal pct | 0.3% | liquidity_sweep.py |
| FVG min gap | 0.05% | fvg_engine.py |
| FVG max age | 50 velas | fvg_engine.py |
| FVG proximity | 2.0% | fvg_engine.py |
| S/R cluster | 0.5% | sr_zones.py |
| S/R proximity | 1.5% | sr_zones.py |

---

*Documento gerado em 2026-07-08 por análise estática do código-fonte do TradeAI.*
