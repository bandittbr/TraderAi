# TradeAI — Roadmap Completo (Fases 1–14+)

> **Fase atual:** 14 — Biel Agent  
> **Última atualização:** 06/07/2026

## Legenda de status

| Ícone | Significado |
|-------|-------------|
| ✅ | Concluído e operacional |
| 🔄 | Em andamento / manutenção |
| 📋 | Planejado / documentado |

---

## Fase 1 — Sistema Base ✅

**Objetivo:** API FastAPI funcional + dashboard Next.js estático.

### Concluído

- [x] API FastAPI com roteamento versionado (`/api/v1/`)
- [x] Configuração via pydantic-settings (`.env`)
- [x] Logger estruturado com rotação de arquivos
- [x] Banco SQLite com SQLAlchemy Async
- [x] Health check (`/health`) e status (`/status`)
- [x] Dashboard Next.js 14 com Tailwind
- [x] Placeholders para fases futuras
- [x] Rewrite via `next.config.js` (sem CORS em dev)
- [x] Deploy na Vercel + Railway

### Serviços criados

- `config.py` — settings centralizados
- `logger.py` — logging estruturado
- `database.py` — engine + sessões

---

## Fase 2 — Dados de Mercado ✅

**Objetivo:** Ingestão de dados OHLCV da Binance em tempo real.

### Concluído

- [x] Modelo `MarketData` (candles OHLCV + timeframe)
- [x] Cliente Binance REST (`/api/v3/klines`)
- [x] WebSocket de preços em tempo real (`/api/v1/ws/market`)
- [x] Endpoint `GET /api/v1/market/candles`
- [x] Endpoint `GET /api/v1/market/price`
- [x] Endpoint `GET /api/v1/market/stats`
- [x] Endpoint `GET /api/v1/market/symbols`
- [x] Sincronização automática a cada 60s
- [x] Cache das candles em banco SQLite

### Serviços criados

- `services/market_data/` — cliente Binance + WS + sync
- `services/websocket/` — gerenciador de conexões WS + broadcast

---

## Fase 3 — Indicadores Técnicos ✅

**Objetivo:** Cálculo de indicadores (RSI, EMA, MACD, ATR) sobre dados de mercado.

### Concluído

- [x] Módulo de indicadores desacoplado
- [x] RSI, EMA, MACD, ATR implementados
- [x] Modelo `MarketIndicator` + histórico em banco
- [x] Sincronização a cada vela nova
- [x] Endpoint `GET /api/v1/indicators/latest`
- [x] Análise técnica consolidada (`/api/v1/analysis/summary`)
- [x] Registro de regime de mercado (volatility regime)

### Serviços criados

- `services/indicators/` — cálculo matemático dos indicadores
- `services/analysis/` — análise técnica consolidada + sinais V6
- `models/market_indicator.py`

---

## Fase 4 — Paper Trading ✅

**Objetivo:** Simulador de trades LONG/SHORT com gestão de risco.

### Concluído

- [x] Conta virtual com saldo inicial configurável
- [x] Execução simulada LONG e SHORT
- [x] Gestão de risco (stop loss, take profit)
- [x] Histórico completo de trades
- [x] Métricas de performance (Win Rate, Sharpe, Profit Factor)
- [x] Backtest histórico sobre dados reais
- [x] Endpoint `GET /api/v1/paper/account`
- [x] Endpoint `GET /api/v1/paper/trades`
- [x] Endpoint `GET /api/v1/paper/stats`
- [x] Endpoint `POST /api/v1/backtest/run`

### Serviços criados

- `services/paper_trading/` — simulador + gestão de risco
- `services/backtesting/` — motor de backtest
- `models/paper_account.py`
- `models/paper_trade.py`
- `models/signal_history.py`

---

## Fase 5 — Contexto de Mercado ✅

**Objetivo:** Notícias, Fear & Greed, Funding Rate, Open Interest.

### Concluído

- [x] Feed de notícias com análise de sentimento (VADER)
- [x] Índice Fear & Greed (Alternative.me API)
- [x] Taxas de funding (Binance)
- [x] Open Interest (Binance)
- [x] Market Context Score consolidado
- [x] Endpoints REST para cada fonte
- [x] Sincronização automática

### Serviços criados

- `services/news/` — RSS fetcher + sentimento
- `services/sentiment/` — VADER NLP
- `services/market_context/` — contexto consolidado + score
- `models/news_article.py`
- `models/fear_greed.py`
- `models/funding_rate.py`
- `models/open_interest.py`

---

## Fase 6 — Signal Analytics ✅

**Objetivo:** Classificador de regime de mercado + trackeamento de sinais.

### Concluído

- [x] Regime classifier (tendência, range, volatilidade)
- [x] Signal tracker (acompanhamento de acertos/erros)
- [x] Métricas por ativo e timeframe
- [x] Endpoints REST

### Serviços criados

- `services/signal_analytics/` — analytics + regime + tracker
- `models/market_regime.py`

---

## Fase 6.5 — Market Structure ✅

**Objetivo:** Detecção de BOS, swings, zonas de suporte/resistência.

### Concluído

- [x] Break of Structure (BOS) detection
- [x] Swing High/Low detection
- [x] Zonas de suporte e resistência (SR)
- [x] Endpoints REST

### Serviços criados

- `services/market_structure/` — estrutura de mercado

---

## Fase 7 — Smart Money Concepts ✅

**Objetivo:** FVG, Liquidez, Sweep, Volume Profile.

### Concluído

- [x] Fair Value Gap (FVG) detection
- [x] Zonas de liquidez
- [x] Sweep detection
- [x] Volume Profile (VPOC, High Volume Nodes)
- [x] Endpoints REST

### Serviços criados

- `services/smart_money/` — conceitos de Smart Money

---

## Fase 8 — Optimizer ✅

**Objetivo:** Pesos adaptativos + análise de combinação de critérios.

### Concluído

- [x] Pesos adaptativos baseados em performance histórica
- [x] Combination analyzer (que combinação de setups performa melhor)
- [x] Endpoints REST

### Serviços criados

- `services/optimizer/` — otimizador + combinador

---

## Fase 9 — Alpha Discovery ✅

**Objetivo:** Pattern engine + qualidade de setup + meta-analytics.

### Concluído

- [x] Pattern engine (descoberta de padrões)
- [x] Quality scorer (qualidade do setup)
- [x] Meta-analytics (estatísticas agregadas)
- [x] Endpoints REST

### Serviços criados

- `services/alpha/` — alpha discovery

---

## Fase 10 — Robustness ✅

**Objetivo:** Walk Forward Analysis, Monte Carlo, estabilidade.

### Concluído

- [x] Walk Forward Analysis (WFA)
- [x] Monte Carlo simulation
- [x] Stability metrics
- [x] Endpoints REST

### Serviços criados

- `services/robustness/` — robustez + validação

---

## Fase 11 — Strategy Lab ✅

**Objetivo:** Evolution engine, gerador e avaliador de estratégias.

### Concluído

- [x] Evolution engine (evolução de parâmetros)
- [x] Strategy generator (geração de novas estratégias)
- [x] Strategy evaluator (avaliação de performance)
- [x] Endpoints REST

### Serviços criados

- `services/strategy/` — laboratório de estratégias

---

## Fase 12 — Trade Management ✅

**Objetivo:** Break Even, Trailing Stop, Partial TP, Exit Score.

### Concluído

- [x] Break Even automático
- [x] Trailing Stop dinâmico
- [x] Partial Take Profit (múltiplos alvos)
- [x] Exit Score (qualidade da saída)
- [x] Endpoints REST
- [x] UX Layer — dashboard interativo no frontend

### Serviços criados

- `services/trade_management/` — gerenciamento avançado de trades

---

## Fase 13 — Scalper ✅

**Objetivo:** MTF scalping (1m/5m/15m) + sinais rápidos.

### Concluído

- [x] Motor MTF (análise em 3 timeframes simultâneos)
- [x] Sinais de scalping com confirmação
- [x] Endpoints REST

### Serviços criados

- `services/scalper/` — motor de scalping MTF

---

## Fase 14 — Biel Agent ✅

**Objetivo:** Agente autônomo de Instagram usando IA generativa.

### Concluído

- [x] **Brain**: Geração de texto via Groq (LLaMA 3.3-70B) ou Gemini 2.0 Flash
- [x] **Visual Generator**: Imagens para post com matplotlib
- [x] **Scheduler**: 4 posts/dia (8h, 12h, 18h, 22h UTC)
- [x] **Token Manager**: Renovação automática 7 dias antes de expirar
- [x] **Publisher**: Publicação via Instagram Graph API
- [x] **Context Builder**: BTC price, regime, P&L, notícias + sentimento
- [x] **Influencer Dashboard**: Métricas completas no frontend
- [x] Endpoints REST (setup, status, metrics, posts, tokens)
- [x] Auto-detecção de provider (Groq vs Gemini pelo prefixo da chave)
- [x] Endpoints de verificação e atualização de token sem refazer setup

### Serviços criados

- `services/biel/brain.py` — geração de texto via API
- `services/biel/scheduler.py` — agendamento de posts
- `services/biel/post_engine.py` — motor de criação + publicação
- `services/biel/token_manager.py` — renovação de tokens
- `services/biel/context_builder.py` — coleta de contexto de mercado
- `services/biel/visual_generator.py` — geração de imagem
- `services/biel/setup_service.py` — configuração inicial
- `models/biel_post.py`
- `models/biel_token.py`
- `models/biel_config.py`

---

## Próximas Fases (Planejadas)

| Fase | Tema | Descrição |
|------|------|-----------|
| 15 | **Realtime v2** | WebSocket bidirecional + streaming de trades ao vivo |
| 16 | **Multi-Exchange** | Suporte a Bybit, OKX, Kraken |
| 17 | **Risk Manager** | Drawdown máximo, position sizing avançado |
| 18 | **Social Trading** | Copy trade, comunidade, ranking público |
| 19 | **API Pública** | API aberta para terceiros (API keys, rate limit) |
| 20 | **PostgreSQL** | Migração oficial para PostgreSQL Railway |
| 21 | **Mobile App** | React Native ou PWA avançado |
| 22 | **Auto-Tuning** | ML para ajuste fino de parâmetros |

---

## Diagrama de Evolução

```
Fase  1          Fase  2-5      Fase  6-11      Fase 12-14         Futuro
──────────────   ────────────   ─────────────   ───────────────   ──────────
FastAPI base  →  Dados +      →  Analytics +   →  Gestão de +    →  Multi-
Next.js base     Indicadores     Smart Money      Trades/Scalper     Exchange
SQLite           Paper Trad.     Alpha Lab        Biel Agent         PWA
Sem auth         Contexto        Strategy Lab     Trade Mgmt         PostgreSQL
```

---

## Pré-requisitos para desenvolvimento local

- Python 3.11+
- Node.js 18+
- `.env` configurado (ver `.env.example`)
- Conta Binance (opcional — dados públicos via REST)
- Chave Groq ou Gemini (para Fase 14 — Biel Agent)

```bash
# Backend
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```
