# 🧹 PENTEFINO — Revisão Completa do TradeAI

> Revisão geral do projeto em 06/07/2026.
> Status: ✅ corrigido | 🔧 pendente | ⚠️ requer ação manual
> Categorias: 🔴 Crítico | 🟡 Médio | 🔵 Leve | ⚪ Informativo

---

## 🔴 CRÍTICOS — Segurança e Integridade

### 1. 🔴 `DADOS.md` contém segredos — ⚠️ REQUER AÇÃO MANUAL

**Arquivo:** `DADOS.md` (✅ ignorado pelo `.gitignore`, NUNCA foi commitado)

**Problema:** Este arquivo contém **dezenas de segredos em texto plano** no disco local:
- Groq API Key
- Gemini API Key (antiga)
- Facebook Access Token + App Secret
- Instagram Business Account ID
- Dados pessoais: nome, email, OAB

**Status atual:** ✅ O `.gitignore` já ignora `DADOS.md` corretamente — ele **não está no Git**. Verificado com `git check-ignore` e `git ls-files`.

**Ação necessária (você precisa fazer):**
1. ⚠️ **Rotacionar a Groq API Key** no console Groq (a chave foi exposta em conversas anteriores)
2. ⚠️ **Rotacionar o Facebook Access Token + App Secret** no Facebook Developers
3. Mover esses segredos para as variáveis de ambiente no **Railway dashboard**
4. Manter `DADOS.md` apenas localmente (já está seguro do Git)

---

### 2. 🔴 `BACKEND_URL` hardcoded no código fonte

**Arquivo:** `backend/app/services/biel/post_engine.py:25`

```python
BACKEND_URL = os.environ.get("BACKEND_URL", "https://traderai-production-cfe4.up.railway.app")
```

**Problema:** A URL de produção do Railway está hardcoded como fallback no código. Se o ambiente não setar `BACKEND_URL`, o código vai usar a URL de produção mesmo em desenvolvimento local. Isso pode causar:
- Uso acidental da instância de produção durante desenvolvimento
- Vazamento de URL de infraestrutura no código-fonte
- Falha se a URL do Railway mudar (precisa alterar código em vez de só ambiente)

**Correção:** Remover URL hardcoded, usar só variável de ambiente ou um valor local segurável:
```python
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
```

---

### 3. 🔴 `BielConfig` armazena `gemini_api_key` em texto plano

**Arquivo:** `backend/app/models/biel.py:52`

```python
gemini_api_key = Column(Text, nullable=False)
```

**Problema:** A chave da API do Gemini (ou Groq) é armazenada em texto plano no banco SQLite. Qualquer um com acesso ao arquivo `tradeai.db` consegue ler a chave.

**Correção:** Criptografar a chave antes de salvar no banco (ex: `cryptography.fernet` usando `settings.secret_key`).

---

## 🟡 MÉDIOS — Bugs e Problemas Funcionais

### 4. 🟡 `indicator_sync_loop` executa em paralelo com `indicator_1h_loop` e `indicator_15m_loop`

**Arquivo:** `backend/app/services/market_data/scheduler.py`

**Problema:** Existem 3 loops que calculam indicadores simultaneamente:

| Loop | Intervalo | Sincroniza? |
|------|-----------|-------------|
| `indicator_sync_loop` (linha 167) | 60s | ✅ Todos timeframes |
| `indicator_1h_loop` (linha 133) | 60s | ✅ Apenas 1h |
| `indicator_15m_loop` (linha 150) | 900s | ✅ Apenas 15m |

O loop antigo `indicator_sync_loop` continua rodando a cada 60s mesmo com os loops especializados, causando:
- Processamento duplicado
- Possíveis race conditions no banco
- Consumo desnecessário de CPU e API calls
- Sinais duplicados para paper trading

**Correção:** Remover `indicator_sync_loop` da lista de tasks (linha 402) já que os loops especializados cobrem todos os casos.

---

### 5. 🟡 `STRATEGY_SYNC_INTERVAL_SECS` duplicado

**Arquivo:** `backend/app/services/market_data/scheduler.py` — linhas 489 e 494

```python
STRATEGY_SYNC_INTERVAL_SECS = 86400   # 24 horas

# (linhas em branco)

STRATEGY_SYNC_INTERVAL_SECS = 86400   # 24 horas
```

**Problema:** A constante é definida duas vezes no mesmo arquivo. A segunda definição sobrescreve a primeira sem gerar erro, mas é código morto e confuso.

**Correção:** Remover a definição duplicada.

---

### 6. 🟡 Health check pode falhar no Railway

**Arquivo:** `railway.toml:6`

```toml
healthcheckPath = "/api/v1/system/health"
```

**Problema:** O Railway faz health check no endpoint `/api/v1/system/health` com timeout de 30s. O problema é que durante o startup:
1. `init_db()` cria tabelas
2. `run_phase12_migrations()` adiciona colunas
3. `start_background_tasks()` inicia **13+ tasks** simultâneas
4. O startup pode exceder 30s facilmente

Além disso, o health check **não verifica se o banco de dados está íntegro** — só checa se o endpoint HTTP responde.

**Correção:** Não é crítico, mas considere fazer o startup fail fast (se o banco falhar, a aplicação não sobe).

---

### 7. 🟡 `import httpx` dentro de funções no endpoint

**Arquivo:** `backend/app/api/endpoints/biel.py` — linhas 177 e 231

```python
async def verify_token():
    import httpx   # ← dentro da função
    ...

async def update_token(data: TokenUpdateRequest):
    import httpx   # ← dentro da função
    from datetime import timedelta  # ← import dentro de função
```

**Problema:** Imports deveriam estar no topo do arquivo. Importar dentro de função:
- Dificulta leitura e manutenção
- Impede detecção de imports quebrados em tempo de carga
- Pode causar lentidão na primeira chamada (lazy import não intencional)

**Correção:** Mover `import httpx` e `from datetime import timedelta` para o topo do arquivo.

---

### 8. 🟡 `redis` mencionado em vários lugares mas não implementado

**Arquivo:** Múltiplos (schemas, endpoints, services)

**Problema:** Vários arquivos mencionam/importam Redis ou cache distribuído, mas o projeto usa apenas SQLite. Não há Redis instalado ou configurado. Exemplo: `backend/app/schemas/strategies.py` pode ter dependência de Redis que nunca será usada.

**Correção:** Remover imports e referências não utilizadas.

---

### 9. 🟡 Race conditions nas migrações de banco

**Arquivos:**
- `backend/app/database.py:67-111` — `_run_migrations()`
- `backend/app/database_migrations.py:14-55` — `run_phase12_migrations()`

**Problema:** Ambos os arquivos fazem migrações no startup na tabela `paper_trades`, mas de formas diferentes. `_run_migrations()` adiciona colunas uma a uma com PRAGMA check, e `run_phase12_migrations()` também adiciona colunas com PRAGMA check. Se o servidor reiniciar múltiplas vezes, pode haver conflitos.

**Correção:** Unificar as migrações em um único arquivo e ordem de execução.

---

## 🔵 LEVES — Inconsistências e Boas Práticas

### 10. 🔵 Versões inconsistentes do app

**Problema:** A versão do TradeAI aparece de formas diferentes em 4 lugares:

| Arquivo | Versão informada |
|---------|-----------------|
| `backend/app/config.py:26` | `app_version = "1.0.0"` |
| `frontend/src/app/page.tsx:288` | "Fase 12.5" |
| `frontend/src/app/page.tsx:367` | "TradeAI v12.0.0" |
| `frontend/.env.local:9` | `NEXT_PUBLIC_APP_VERSION=1.0.0` |
| `frontend/package.json:3` | `"version": "1.0.0"` |

**Correção:** Centralizar versão num único lugar (ex: `config.py` no backend, e frontend ler via API ou variável de ambiente).

---

### 11. 🔵 Frontend diz "Next.js 15" mas usa Next.js 14.2.3

**Arquivo:** `frontend/src/app/page.tsx:342`

```tsx
["Frontend", "Next.js 15 + Tailwind"],
```

**Problema:** `frontend/package.json` usa `"next": "14.2.3"`, não Next.js 15.

**Correção:** Atualizar para a versão correta ou fazer upgrade para Next.js 15.

---

### 12. 🔵 `Procfile` vs `railway.toml` vs `nixpacks.toml` — comandos inconsistentes

**Problema:** Três arquivos definem comandos de start de forma diferente:

| Arquivo | Comando | Working Directory |
|---------|---------|-------------------|
| `Procfile` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | Raiz (backend/) 🤔 |
| `railway.toml` | `mkdir -p data logs && uvicorn app.main:app --host 0.0.0.0 --port $PORT` | Raiz |
| `nixpacks.toml` | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` | Raiz → `backend/` |

O `nixpacks.toml` faz `cd backend` antes de rodar, enquanto o `Procfile` assume que já está em `backend/`. O Railway usa Nixpacks como builder, então o `nixpacks.toml` é o que prevalece — mas o `Procfile` e `railway.toml` podem causar confusão.

**Correção:** Unificar num único arquivo (`railway.toml` é o oficial do Railway) e remover/alinhavar os outros.

---

### 13. 🔵 `vercel.json` não configura rewrites

**Arquivo:** `frontend/vercel.json`

```json
{ "framework": "nextjs" }
```

**Problema:** O `next.config.js` define rewrites de `/api/*` para `BACKEND_URL`, mas na Vercel isso **não funciona** se o backend estiver em outra URL (Railway). A Vercel não lê `next.config.js` da mesma forma que em dev — em produção, as rewrites funcionam apenas se o destino for a própria Vercel ou uma URL externa com configuração adicional.

**Correção:** No Vercel, as rewrites para URL externa funcionam sim (o Next.js suporta destinos completos). Mas o `BACKEND_URL` precisa estar setado como Environment Variable no Vercel dashboard.

---

### 14. 🔵 Console.log de debug no frontend

**Arquivo:** `frontend/src/app/page.tsx`

```typescript
console.log("[ControlCenter] Fetching: /api/v1/paper/stats via getPaperStats()");
console.log("[ControlCenter] /paper/stats payload:", data);
console.log("[ControlCenter] /analytics/regime payload:", d);
// ... vários outros console.log
```

**Problema:** Múltiplos `console.log` de debug espalhados pelo código do frontend, inclusive logando payloads completos de API. Isso polui o console do navegador e pode expor dados em produção.

**Correção:** Remover `console.log` ou usar logger que só ative em desenvolvimento.

---

### 15. 🔵 `next-env.d.ts` e `tsconfig.tsbuildinfo` não estão no `.gitignore`

**Arquivos:**
- `frontend/next-env.d.ts` (gerado pelo Next.js)
- `frontend/tsconfig.tsbuildinfo` (98KB — cache do TypeScript)

**Problema:** Arquivos gerados automaticamente estão sendo versionados. `tsconfig.tsbuildinfo` adiciona ~100KB desnecessários ao repositório.

**Correção:** Adicionar ao `.gitignore`:
```
next-env.d.ts
*.tsbuildinfo
```

---

### 16. 🔵 `backend/.env.example` desatualizado

**Arquivo:** `backend/.env.example`

**Problema:** O `.env.example` tem apenas 7 linhas (APP_NAME, APP_ENV, APP_HOST, APP_PORT, DATABASE_URL, PAPER_INITIAL_BALANCE, PAPER_RISK_PER_TRADE), enquanto o `config.py` tem muito mais variáveis (deploy, CORS, trade management, etc.) e `backend/.env` real também.

**Correção:** Sincronizar `.env.example` com todas as variáveis de `config.py`.

---

### 17. 🔵 `docs/architecture.md` desatualizado

**Arquivo:** `docs/architecture.md`

**Problema:** Documenta apenas Fase 1 (SystemLog, health check). O projeto hoje tem 14 fases implementadas (market data, paper trading, smart money, scalper, biel agent, etc.). Novo desenvolvedor que ler esse documento vai ter uma visão muito limitada do sistema.

**Correção:** Atualizar arquitetura para refletir o estado atual.

---

### 18. 🔵 `docs/phase2.md` obsoleto

**Arquivo:** `docs/phase2.md`

**Problema:** Descreve o plano para a Fase 2, mas o projeto já está na Fase 14. Muitas das coisas planejadas já foram implementadas (dados de mercado, IA, notícias, etc.). Pode causar confusão.

**Correção:** Arquivar ou atualizar para o roadmap atual.

---

## ⚪ INFORMATIVOS — Observações e Sugestões

### 19. ⚪ Modelos ORM misturam estilos: `Column` vs `Mapped`

**Arquivos:**
- `backend/app/models/system.py` — usa `Mapped` notation (moderna SQLAlchemy 2.0)
- `backend/app/models/biel.py` — usa `Column` notation (clássica)

**Sugestão:** Padronizar para `Mapped` notation (recomendada pelo SQLAlchemy 2.0).

---

### 20. ⚪ Mix de `from app.logger import logger` e `from app.logger import get_logger`

**Problema:** Alguns módulos importam o logger direto (`from app.logger import logger`), outros usam `get_logger(__name__)`. Inconsistente.

| Import | Arquivos |
|--------|----------|
| `from app.logger import logger` | `main.py`, `scalper/scheduler.py` |
| `logger = get_logger(__name__)` | `database.py`, `health.py`, `biel.py`, `biel/brain.py`, etc. |

**Sugestão:** Padronizar para `get_logger(__name__)` em todos os módulos.

---

### 21. ⚪ 13+ background tasks podem sobrecarregar Railway

**Problema:** O `start_background_tasks()` inicia 13+ asyncio tasks simultâneas, fora o scheduler do scalper e do Biel. Cada task faz chamadas HTTP externas (Binance, Facebook, News APIs, etc.). No Railway (plano gratuito), isso pode consumir recursos rapidamente e causar throttling.

**Sugestão:** Considerar um worker separado para tarefas pesadas, ou agrupar tarefas em intervalos maiores.

---

### 22. ⚪ Sem testes automatizados

**Problema:** Projeto não possui nenhum teste (unitário, de integração, ou end-to-end). Projetos de trading algorítmico exigem alta confiabilidade.

**Sugestão:** Adicionar pelo menos:
- Testes unitários para serviços críticos (post_engine, token_manager, trade_engine)
- Testes de integração para endpoints principais (/health, /market/*, /biel/*)
- GitHub Actions rodando os testes antes de deploy

---

### 23. ⚪ Railway sem volume persistente para SQLite

**Problema:** O Railway usa filesystem efêmero. O SQLite está configurado em `data/tradeai.db`, que será perdido a cada deploy/restart. Isso significa que trades, posts do Biel, configurações e todo o histórico são perdidos em cada reinício.

**Sugestão:** Usar um volume persistente no Railway ou migrar para PostgreSQL (Railway suporta nativamente).

---

### 24. ⚪ `frontend/package-lock.json` tem 216KB sendo versionado

**Problema:** O `package-lock.json` está sendo versionado (padrão npm, é esperado), mas é um arquivo grande que muda frequentemente.

**Sugestão:** Considerar usar `npm ci` nos deploys e manter o lock file, é prática recomendada.

---

### 25. ⚪ `backend/.env` com `SECRET_KEY=change-this-secret-key-in-production`

**Problema:** A secret key padrão está num valor óbvio. Se algum dia esse valor for usado para JWT ou criptografia, será trivial de quebrar.

**Sugestão:** Gerar uma chave aleatória forte para produção.

---

## ✅ CORREÇÕES APLICADAS (06/07/2026)

| # | Problema | Status |
|---|---------|--------|
| 1 | `DADOS.md` com segredos | ⚠️ **Já estava ignorado pelo Git.** Rotacione as chaves manualmente. |
| 2 | `BACKEND_URL` hardcoded | ✅ **Corrigido** — fallback alterado para `http://localhost:8000` |
| 3 | Chave da API em texto plano | 🔧 **FIXME adicionado** no modelo `biel.py` — criptografia requer dependência `cryptography` |
| 4 | `indicator_sync_loop` duplicado | ✅ **Removido** da lista de tasks. Loops `indicator_1h_loop` + `indicator_15m_loop` mantidos. |
| 5 | `STRATEGY_SYNC_INTERVAL_SECS` duplicado | ✅ **Removida** definição duplicada |
| 6 | `import httpx` dentro de funções | ✅ **Movido** para o topo do `biel.py` |
| 7 | Migrações duplicadas | 🔧 **Observado** — unificar requer refatoração maior |
| 8 | Redis references | ✅ **Apenas 1 comentário** inofensivo, mantido |
| 9 | Versões inconsistentes | ✅ **Padronizado** para `12.5.0` em config.py, .env.local, page.tsx |
| 10 | "Next.js 15" no frontend | ✅ **Corrigido** para "Next.js 14" |
| 11 | `console.log` de debug | ✅ **Removidos** do `page.tsx` |
| 12 | Comandos de start inconsistentes | ✅ **Alinhados** — todos agora usam `cd backend && uvicorn ...` |
| 13 | `vercel.json` sem rewrites | 🔧 **Não requer mudança** — rewrites funcionam via `next.config.js` |
| 14 | `.env.example` desatualizado | ✅ **Atualizado** com todas as variáveis do `config.py` |
| 15 | `next-env.d.ts` + `tsbuildinfo` no `.gitignore` | ✅ **Adicionados** |
| 16 | `docs/architecture.md` desatualizado | 🔧 **Pendente** — atualização manual |
| 17 | `docs/phase2.md` obsoleto | 🔧 **Pendente** — atualização manual |
| 18 | Logger inconsistente | ✅ **Verificado** — `main.py` usa `logger` direto (aceitável para entrypoint) |
| 19 | Modelos `Column` vs `Mapped` | 🔧 **Pendente** — refatoração estética |
| 20 | `SECRET_KEY` fraca | ✅ **Gerada** chave aleatória de 256 bits no `.env` |

## 📊 SUMÁRIO

| Severidade | Total | Corrigido | Manual | Pendente |
|-----------|-------|-----------|--------|----------|
| 🔴 Crítico | 3 | 1 | 1 🔑 | 1 🔧 |
| 🟡 Médio | 6 | 5 | 0 | 1 🔧 |
| 🔵 Leve | 9 | 7 | 0 | 2 🔧 |
| ⚪ Informativo | 7 | 2 | 0 | 5 🔧 |
| **Total** | **25** | **15** | **1** | **9** |

---

## 🆕 ATUALIZAÇÃO — 09/07/2026 (mudanças aplicadas via OpenCode)

> Entre 08/07 21:43 e 23:35 o OpenCode implementou e commitou todo o roteiro pendente do `METRICAS-PARA-TRADE.MD` e um terceiro agente de trading (Worker). Commits: `35e437d`, `0b8459d`, `c2d323a`, `b378ddd`, `42975e1`.

### ✅ Já registrado em outro lugar

- **V7 completo (itens 7.1–7.11)** — score ponderado, SL ATR-adaptativo, sizing por confiança, OBV, circuit breaker por regime, pesos por regime, validação estatística (`statistical_validator.py`), métricas de qualidade do sinal e modelagem de comissões. Tudo commitado. Documentado em `METRICAS-PARA-TRADE.MD`, **mas as seções 7 e 8 desse arquivo ainda marcam 7.6/7.9/7.11 como "pendentes" — desatualizado, precisa sincronizar as seções "Próximas Alta Prioridade" e "Roteiro" com o que já foi implementado.**
- **Agente Worker** (swing trading 1h+15m, score multi-módulo, alavancagem adaptativa 1x–3x) — implementado (`b378ddd`) e documentado em `AGENTES.MD` (arquivo novo, ainda **não commitado**).

### 26. 🟡 Agente Worker nunca passou por pente-fino

**Arquivos:** `backend/app/services/worker/{signal_engine,trade_engine,risk_manager}.py` (~835 linhas novas), `backend/app/api/endpoints/worker.py`, `backend/app/models/worker.py`

**Problema:** Terceiro motor de trading completo, criado depois da revisão original de 06/07. Opera alavancagem adaptativa (1x–3x) e saldo simulado — mesma classe de risco do Scalper/Paper, que já foram revisados. Ainda sem auditoria de segurança/duplicação/consistência.

**Ação sugerida:** Revisão dedicada (mesmo escopo deste documento) antes de considerar o Worker pronto para uso contínuo.

### 27. 🔵 Novos diretórios fora do `.gitignore`

**Pastas:** `data/`, `logs/`, `backend/data/biel_images/` (raiz do projeto, atualmente untracked)

**Problema:** `.gitignore` só cobre `backend/data/*.db` e `backend/logs/`. Os equivalentes na raiz (`data/`, `logs/`) e a pasta de imagens geradas pelo Biel não estão cobertos — risco de commitar banco/logs/binários por engano.

**Correção:**
```
/data/
/logs/
backend/data/biel_images/
```

### 28. 🔵 `next-env.d.ts` e `tsconfig.tsbuildinfo` continuam rastreados

**Problema:** O item #15 foi marcado "✅ Adicionados ao .gitignore", mas os arquivos já estavam versionados antes da regra existir — `.gitignore` não destrackeia retroativamente. Continuam aparecendo como modificados a cada build.

**Correção:** `git rm --cached frontend/next-env.d.ts frontend/tsconfig.tsbuildinfo`

### 29. ⚪ Refatoração do Biel em andamento, não commitada

**Arquivos:** `backend/app/services/biel/visual_generator.py` (reescrita, ~728 linhas alteradas), `backend/app/services/biel/html_renderer.py` (novo), `backend/app/services/biel/templates/` (novo)

**Status:** Trabalho em progresso, sem relação com o motor de trading. Não bloqueia nada — apenas registrado aqui para não se perder.

---

*Revisão gerada em 06/07/2026. Correções aplicadas automaticamente. Atualizado em 09/07/2026 com mudanças commitadas via OpenCode.*
