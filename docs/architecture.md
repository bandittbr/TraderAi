# TradeAI — Documentação de Arquitetura

> **Versão:** 12.5.0 | **Status:** Fase 14 — Biel Agent | **Última atualização:** 06/07/2026

## Visão Geral

O TradeAI é uma plataforma de trading algorítmico com inteligência artificial, construída
sobre uma arquitetura cliente-servidor desacoplada. O backend expõe uma API REST +
WebSocket e o frontend consome essa API de forma assíncrona.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     USUÁRIO (Browser / Mobile)                           │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼───────────────────────────────────────────────┐
│         FRONTEND — Next.js 14 + TypeScript + Tailwind (Vercel)          │
│                                                                          │
│  ┌────────────┐  ┌──────────────────┐  ┌────────────┐  ┌─────────────┐ │
│  │  Control   │  │  Dashboard/      │  │  Biel/     │  │  Analytics/ │ │
│  │  Center    │  │  Paper Trading   │  │  Influencer│  │  Alpha      │ │
│  └────────────┘  └──────────────────┘  └────────────┘  └─────────────┘ │
│  ┌────────────┐  ┌──────────────────┐  ┌────────────┐  ┌─────────────┐ │
│  │  Scalper   │  │  Smart Money     │  │  Market    │  │  Trade      │ │
│  │            │  │  / Structure     │  │  Context   │  │  Management │ │
│  └────────────┘  └──────────────────┘  └────────────┘  └─────────────┘ │
│                                                                          │
│  lib/api.ts → fetch wrapper centralizado                                │
│  types/index.ts → tipos TypeScript espelhando schemas Pydantic          │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │ HTTP via rewrite (next.config.js) / WS
┌──────────────────────────▼───────────────────────────────────────────────┐
│             BACKEND — FastAPI + Python 3.11+ (Railway)                  │
│                                                                          │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────────┐  │
│  │  main.py     │  │  api/            │  │  models/ (14 tabelas ORM) │  │
│  │  (lifespan)  │  │  ├── router.py  │  │  schemas/ (Pydantic DTOs) │  │
│  │              │  │  └── endpoints/ │  │  config.py (pydantic-sets) │  │
│  └──────────────┘  └──────────────────┘  └───────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  services/                                                        │   │
│  │  ├── market_data/    (Binance REST + WS)                         │   │
│  │  ├── indicators/     (RSI, EMA, MACD, ATR)                       │   │
│  │  ├── analysis/       (análise técnica + sinais V6)               │   │
│  │  ├── paper_trading/  (simulador LONG/SHORT)                      │   │
│  │  ├── backtesting/    (backtest histórico)                        │   │
│  │  ├── market_context/ (Fear & Greed, Funding, OI, News)           │   │
│  │  ├── signal_analytics/ (regime classifier, signal tracker)       │   │
│  │  ├── market_structure/ (BOS, swing, SR zones)                    │   │
│  │  ├── smart_money/    (FVG, liquidity, sweep, volume profile)     │   │
│  │  ├── optimizer/      (adaptive weights, combination analyzer)    │   │
│  │  ├── alpha/          (pattern discovery, quality scorer)         │   │
│  │  ├── robustness/     (walk forward, Monte Carlo, stability)      │   │
│  │  ├── strategy/       (evolution engine, generator, evaluator)    │   │
│  │  ├── trade_management/ (break even, trailing, partial TP)        │   │
│  │  ├── scalper/        (MTF 1m/5m/15m scalping engine)            │   │
│  │  ├── biel/           (Instagram agent — brain, scheduler, post)  │   │
│  │  ├── websocket/      (manager + broadcast)                       │   │
│  │  ├── news/           (RSS fetcher + sentiment analysis)          │   │
│  │  └── sentiment/      (VADER-based sentiment)                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │ SQLAlchemy Async (aiosqlite)
┌──────────────────────────▼───────────────────────────────────────────────┐
│          BANCO DE DADOS — SQLite (data/tradeai.db)                      │
│                                                                          │
│  Tabelas principais:                                                     │
│  ├── system_logs            (auditoria)                                  │
│  ├── paper_accounts         (conta virtual)                              │
│  ├── paper_trades           (trades simulados)                           │
│  ├── signal_history         (histórico de sinais)                        │
│  ├── market_regimes         (classificação de regime)                    │
│  ├── market_indicators      (indicadores calculados)                     │
│  ├── market_candles         (candles OHLCV)                              │
│  ├── market_stats           (estatísticas 24h)                           │
│  ├── news_articles          (notícias + sentimento)                      │
│  ├── fear_greed             (índice medo/ganância)                       │
│  ├── funding_rates          (taxas de funding)                           │
│  ├── open_interest          (open interest)                              │
│  ├── biel_posts             (posts Instagram)                            │
│  ├── biel_tokens            (tokens de acesso)                           │
│  ├── biel_config            (configurações do Biel)                      │
│  └── (demais tabelas de cada fase)                                       │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Backend (FastAPI + Python 3.11+)

### Princípios

- **Async first**: todo o I/O utiliza `async/await` para não bloquear o event loop.
- **Dependency Injection**: FastAPI injeta sessões de BD, configurações e serviços.
- **Separation of Concerns**: endpoints não conhecem SQL; services não conhecem HTTP.
- **Pydantic everywhere**: validação automática de request/response via schemas.
- **Graceful degradation**: cada fase adiciona contexto sem quebrar fases anteriores.

### Camadas

| Camada | Responsabilidade |
|--------|-----------------|
| `main.py` | Ponto de entrada; lifespan, middlewares, rotas, background tasks |
| `config.py` | Configurações via variáveis de ambiente (pydantic-settings) |
| `logger.py` | Logger estruturado com rotação diária de arquivos |
| `database.py` | Engine SQLAlchemy Async, sessões, migrações |
| `database_migrations.py` | Migrações incrementais (ALTER TABLE) |
| `models/` | Definição ORM das tabelas |
| `schemas/` | DTOs Pydantic (request/response) |
| `api/endpoints/` | Handlers HTTP — finos, sem lógica de negócio |
| `services/` | Lógica de negócio — independente do HTTP |

### Módulos do Sistema (Fases 1–14)

| Fase | Módulo | Descrição |
|------|--------|-----------|
| 1 | **Sistema** | FastAPI base, health check, logs, config |
| 2 | **Mercado** | Dados OHLCV da Binance (REST + WebSocket) |
| 3 | **Indicadores** | RSI, EMA, MACD, ATR |
| 4 | **Paper Trading** | Simulador LONG/SHORT com gestão de risco |
| 5 | **Market Context** | Notícias, Fear & Greed, Funding Rate, Open Interest |
| 6 | **Signal Analytics** | Regime classifier, signal tracker, métricas |
| 6.5 | **Market Structure** | BOS, swing detection, suporte/resistência |
| 7 | **Smart Money** | FVG, Liquidez, Sweep, Volume Profile |
| 8 | **Optimizer** | Pesos adaptativos, combinação de critérios |
| 9 | **Alpha Discovery** | Pattern engine, qualidade de setup, meta-analytics |
| 10 | **Robustness** | Walk Forward, Monte Carlo, estabilidade |
| 11 | **Strategy Lab** | Evolution engine, gerador, avaliador |
| 12 | **Trade Management** | Break Even, Trailing Stop, Partial TP, Exit Score |
| 13 | **Scalper** | MTF scalping (1m/5m/15m), Sinais rápidos |
| 14 | **Biel Agent** | IA Generativa (Groq/Gemini) + Instagram Publisher |

### Endpoints da API

| Método | Rota | Fase | Descrição |
|--------|------|------|-----------|
| GET | `/` | 1 | Raiz — informações do servidor |
| GET | `/docs` | 1 | Swagger UI (development apenas) |
| GET | `/api/v1/system/health` | 1 | Health check + status do banco |
| GET | `/api/v1/system/status` | 1 | Status detalhado dos componentes |
| GET | `/api/v1/market/symbols` | 2 | Lista de ativos suportados |
| GET | `/api/v1/market/price` | 2 | Preço atual de um ativo |
| GET | `/api/v1/market/stats` | 2 | Estatísticas 24h + Market Score |
| GET | `/api/v1/market/candles` | 2 | Candles OHLCV históricos |
| WS | `/api/v1/ws/market` | 2 | WebSocket de preços em tempo real |
| GET | `/api/v1/indicators/latest` | 3 | Últimos valores dos indicadores |
| GET | `/api/v1/analysis/summary` | 3 | Análise técnica completa |
| GET | `/api/v1/paper/account` | 4 | Estado da conta virtual |
| GET | `/api/v1/paper/trades` | 4 | Lista de trades simulados |
| GET | `/api/v1/paper/stats` | 4 | Métricas de performance |
| POST | `/api/v1/backtest/run` | 4 | Executa backtest |
| GET | `/api/v1/backtest/results` | 4 | Resultados em cache |
| GET | `/api/v1/context/news` | 5 | Notícias + sentimento |
| GET | `/api/v1/context/fear-greed` | 5 | Índice de medo/ganância |
| GET | `/api/v1/context/funding` | 5 | Taxas de funding |
| GET | `/api/v1/context/open-interest` | 5 | Open interest |
| GET | `/api/v1/context/score` | 5 | Market Context Score |
| GET | `/api/v1/analytics/*` | 6 | Analytics, regime, sinais |
| GET | `/api/v1/structure/*` | 6.5 | Market Structure |
| GET | `/api/v1/smc/*` | 7 | Smart Money (FVG, liquidez, sweep) |
| GET | `/api/v1/optimizer/*` | 8 | Adaptive Optimizer |
| GET | `/api/v1/alpha/*` | 9 | Alpha Discovery |
| GET | `/api/v1/robustness/*` | 10 | Robustness Engine |
| GET | `/api/v1/strategies/*` | 11 | Strategy Lab |
| GET | `/api/v1/trade-management/*` | 12 | Trade Management |
| GET | `/api/v1/scalper/*` | 13 | Scalper Engine |
| GET/POST | `/api/v1/biel/*` | 14 | Biel Agent (setup, post, status, tokens) |
| GET | `/biel/images/*` | 14 | Imagens geradas para Instagram |

---

## Frontend (Next.js 14 + TypeScript + Tailwind)

### Princípios

- **App Router**: estrutura baseada no roteador do Next.js 14.
- **Server Components + Client Components**: uso criterioso de `"use client"`.
- **Tipagem forte**: todos os dados da API tipados via `src/types/index.ts`.
- **API centralizada**: toda comunicação HTTP passa por `src/lib/api.ts`.
- **UI escura**: tema dark com paleta TradeAI (azuis escuros, acentos por módulo).

### Páginas

| Rota | Módulo | Componentes |
|------|--------|-------------|
| `/` | Control Center | Métricas rápidas, health, módulos |
| `/dashboard` | Dashboard | Gráficos, indicadores, market score |
| `/paper-trading` | Paper Trading | Conta virtual, trades, backtest |
| `/trade-management` | Trade Management | Break Even, Trailing, Partial TP |
| `/analytics` | Analytics | Win rate, Sharpe, Profit Factor |
| `/alpha` | Alpha Discovery | Padrões, qualidade de setup |
| `/robustness` | Robustness | Walk Forward, Monte Carlo |
| `/strategies` | Strategy Lab | Evolution engine, ranking |
| `/market-context` | Market Context | Notícias, Fear & Greed, Funding |
| `/market-structure` | Market Structure | BOS, swings, SR zones |
| `/smart-money` | Smart Money | FVG, Liquidez, Sweep |
| `/scalper` | Scalper | Sinais 1m, trades rápidos |
| `/biel` | Biel Agent | Status, setup, posts |
| `/influencer` | Influencer Dashboard | Overview, agenda, feed |
| `/system-health` | System Health | Status detalhado |

### Comunicação Frontend → Backend

O arquivo `next.config.js` configura um rewrite transparente:

```
Frontend: GET /api/v1/system/health
  → rewrite → Backend: GET http://127.0.0.1:8000/api/v1/system/health
```

Em produção (Vercel), a variável `BACKEND_URL` aponta para o Railway.

---

## Banco de Dados (SQLite)

### Por que SQLite?

- Zero configuração: arquivo único `data/tradeai.db`.
- Suficiente para operação single-user.
- SQLAlchemy abstrai a troca para PostgreSQL quando necessário.

### Limitação conhecida

No Railway, o SQLite é efêmero (perdido a cada deploy). Para produção persistente,
considere:
1. **Volumes persistentes** no Railway (em beta)
2. **Migração para PostgreSQL** (Railway suporta nativamente)

---

## Deploy

### Infraestrutura

```
GitHub (bandittbr/TraderAi)
    │
    ├──► Vercel  →  Frontend (trader-ai-livid.vercel.app)
    │                • Next.js 14, build automático
    │                • Variável: BACKEND_URL → Railway URL
    │
    └──► Railway →  Backend  (traderai-production-cfe4.up.railway.app)
                     • Nixpacks builder
                     • Variáveis de ambiente (API keys, etc.)
```

### Variáveis de ambiente obrigatórias (Railway)

| Variável | Descrição |
|----------|-----------|
| `APP_ENV` | `production` |
| `APP_HOST` | `0.0.0.0` |
| `CORS_ORIGINS` | URL do frontend na Vercel |
| `BACKEND_URL` | URL pública do Railway (para imagens do Biel) |

### Variáveis de ambiente obrigatórias (Vercel)

| Variável | Descrição |
|----------|-----------|
| `BACKEND_URL` | URL do backend no Railway |

---

## Sistema de Logs

Dois destinos simultâneos:
1. **Console** — saída no terminal durante desenvolvimento.
2. **Arquivo** — `logs/tradeai.log` com rotação diária, retenção de 30 dias.

Hierarquia de loggers: `tradeai` → `tradeai.app.services.*` etc.

```python
from app.logger import get_logger
logger = get_logger(__name__)
logger.info("Mensagem de log")
```

---

## Sistema de Configuração

Arquivo `.env` → classe `Settings` (pydantic-settings) → instância `settings`.

```python
from app.config import settings
print(settings.app_port)        # 8000
print(settings.is_development)  # True
print(settings.cors_origins_list)  # ["http://localhost:3000", ...]
```

Nunca usar `os.environ` diretamente nos módulos — tudo passa por `settings`.

---

## Biel Agent (Fase 14)

Agente autônomo de Instagram que gera e publica posts com IA.

### Pipeline de post

```
Context Builder → Brain (Groq/Gemini) → Visual Generator → Instagram API
```

- **Context Builder**: coleta BTC price, regime, P&L, notícias, Fear & Greed
- **Brain**: gera texto via Groq LLaMA 3.3-70B ou Gemini 2.0 Flash (auto-detecção pelo prefixo da chave)
- **Visual Generator**: gera imagem com matplotlib
- **Scheduler**: 4 posts/dia (8h, 12h, 18h, 22h UTC)
- **Token Manager**: renovação automática 7 dias antes de expirar

### Endpoints do Biel

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/biel/setup` | Configuração inicial |
| GET | `/api/v1/biel/status` | Status atual |
| GET | `/api/v1/biel/metrics` | Métricas completas (Influencer Dashboard) |
| POST | `/api/v1/biel/post` | Forçar post manual |
| GET | `/api/v1/biel/posts` | Histórico de posts |
| GET | `/api/v1/biel/stats` | Estatísticas de publicação |
| POST | `/api/v1/biel/token/renew` | Renovar token manualmente |
| GET | `/api/v1/biel/token/verify` | Verificar validade do token |
| POST | `/api/v1/biel/token/update` | Atualizar token (sem refazer setup) |
