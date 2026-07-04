# TradeAI — Guia de Evolução para a Fase 2

## O que a Fase 2 deve implementar

### 1. Módulo de Dados de Mercado

**Objetivo**: ingestão e armazenamento de dados OHLCV em tempo real e histórico.

**Passos:**
1. Criar modelo SQLAlchemy `MarketData` (ativo, timeframe, OHLCV, volume).
2. Implementar `services/market_data_service.py` com cliente para API pública (ex.: yfinance, Alpha Vantage, Binance).
3. Criar endpoint `GET /api/v1/market/candles?asset=PETR4&tf=1h&limit=200`.
4. No frontend, instalar `lightweight-charts` (TradingView) e conectar ao endpoint.

**Arquivo a criar:** `backend/app/services/market_data_service.py`

### 2. Módulo de Inteligência Artificial

**Objetivo**: geração de sinais de compra/venda a partir de modelos de ML.

**Passos:**
1. Instalar `scikit-learn`, `pandas`, `numpy` no `requirements.txt`.
2. Criar `services/ai_service.py` com modelo base (ex.: média móvel como baseline).
3. Criar modelo `Signal` no banco (ativo, direção, confiança, timestamp).
4. Criar endpoint `GET /api/v1/signals/latest`.
5. No frontend, descomentar `SignalsPlaceholder` e substituir por componente real.

**Arquivo a criar:** `backend/app/services/ai_service.py`

### 3. Feed de Notícias com Análise de Sentimento

**Objetivo**: consumir notícias financeiras e classificar sentimento.

**Passos:**
1. Integrar API de notícias (ex.: NewsAPI, Finnhub).
2. Implementar NLP simples (VADER ou modelo HuggingFace).
3. Criar endpoint `GET /api/v1/news/latest`.
4. No frontend, substituir `NewsPlaceholder` por componente real.

### 4. Autenticação e Autorização

**Objetivo**: proteger a API com JWT.

**Passos:**
1. Instalar `python-jose[cryptography]`, `passlib[bcrypt]`.
2. Criar modelo `User` no banco.
3. Criar endpoints `POST /api/v1/auth/login` e `POST /api/v1/auth/refresh`.
4. Adicionar `Depends(get_current_user)` nos endpoints protegidos.
5. No frontend, implementar contexto de autenticação com `localStorage` do token.

### 5. WebSocket para Dados em Tempo Real

**Objetivo**: streaming de preços e sinais sem polling.

**Passos:**
1. Adicionar `GET /api/v1/ws/market` com `WebSocket` do FastAPI.
2. No frontend, criar hook `useWebSocket` em `src/lib/websocket.ts`.
3. Substituir polling de 30s no `SystemStatus` por WebSocket.

---

## Diagrama de evolução

```
Fase 1 (atual)           Fase 2                      Fase 3
──────────────           ──────                      ──────
FastAPI base        →    Dados de mercado       →    Integração corretora
SQLite básico       →    Modelos ML             →    Execução de ordens
Dashboard estático  →    Gráficos ao vivo       →    Gestão de carteira
Sem autenticação    →    JWT + usuários         →    Multi-usuário
```

---

## Checklist de pré-requisitos para a Fase 2

- [ ] Backend Fase 1 funcionando (`uvicorn` respondendo em 8000)
- [ ] Frontend Fase 1 funcionando (`next dev` respondendo em 3000)
- [ ] Banco SQLite criado (`data/tradeai.db` existe)
- [ ] Logs configurados (`logs/tradeai.log` sendo gerado)
- [ ] Testes unitários básicos adicionados (pytest)
- [ ] `.env` configurado (a partir de `.env.example`)
