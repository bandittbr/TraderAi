# TradeAI — Documentação de Arquitetura

## Visão Geral

O TradeAI é uma plataforma de trading algorítmico com inteligência artificial, construída
sobre uma arquitetura cliente-servidor desacoplada. O backend expõe uma API REST e o
frontend consome essa API de forma assíncrona.

```
┌─────────────────────────────────────────────────────────────────┐
│                        USUÁRIO (Browser)                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP / WebSocket (Fase 2)
┌─────────────────────────▼───────────────────────────────────────┐
│              FRONTEND — Next.js 14 (porta 3000)                 │
│  ┌──────────┐  ┌────────────────┐  ┌──────────────────────────┐ │
│  │  app/    │  │  components/   │  │  lib/api.ts              │ │
│  │ page.tsx │  │  dashboard/    │  │  (cliente HTTP central)  │ │
│  └──────────┘  └────────────────┘  └──────────────────────────┘ │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP via rewrite (next.config.js)
┌─────────────────────────▼───────────────────────────────────────┐
│              BACKEND — FastAPI (porta 8000)                     │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐  │
│  │ main.py  │  │  api/router  │  │  schemas/  │  │  logger  │  │
│  │(lifespan)│  │  endpoints/  │  │  (Pydantic)│  │  config  │  │
│  └──────────┘  └──────────────┘  └────────────┘  └──────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │ SQLAlchemy Async
┌─────────────────────────▼───────────────────────────────────────┐
│              BANCO DE DADOS — SQLite (data/tradeai.db)          │
│  ┌──────────────┐                                               │
│  │ system_logs  │  (tabela de auditoria)                        │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Backend (FastAPI + Python)

### Princípios

- **Async first**: todo o I/O utiliza `async/await` para não bloquear o event loop.
- **Dependency Injection**: FastAPI injeta sessões de BD, configurações e serviços.
- **Separation of Concerns**: endpoints não conhecem SQL; services não conhecem HTTP.
- **Pydantic everywhere**: validação automática de request/response via schemas.

### Camadas

| Camada | Responsabilidade |
|--------|-----------------|
| `main.py` | Ponto de entrada; lifespan, middlewares, rotas |
| `config.py` | Configurações via variáveis de ambiente (pydantic-settings) |
| `logger.py` | Logger estruturado com rotação de arquivos |
| `database.py` | Engine SQLAlchemy, sessões, inicialização do banco |
| `models/` | Definição das tabelas (ORM) |
| `schemas/` | DTOs Pydantic (request/response) |
| `api/endpoints/` | Handlers HTTP — finos, sem lógica de negócio |
| `services/` | Lógica de negócio — independente do HTTP (Fase 2+) |

### Endpoints disponíveis (Fase 1)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Raiz — confirma que o servidor está no ar |
| GET | `/docs` | Swagger UI (apenas em development) |
| GET | `/api/v1/system/health` | Health check com status do banco |
| GET | `/api/v1/system/status` | Status detalhado de todos os componentes |

---

## Frontend (Next.js 14 + TypeScript)

### Princípios

- **App Router**: estrutura baseada no novo roteador do Next.js 14.
- **Server Components + Client Components**: uso criterioso de `"use client"`.
- **Tipagem forte**: todos os dados da API tipados via `src/types/index.ts`.
- **API centralizada**: toda comunicação HTTP passa por `src/lib/api.ts`.

### Estrutura de componentes

```
src/
├── app/
│   ├── layout.tsx          # Layout raiz (metadados, fontes)
│   ├── page.tsx            # Dashboard principal
│   └── globals.css         # Estilos globais + Tailwind
├── components/
│   ├── dashboard/
│   │   ├── SystemStatus.tsx      # Status dos componentes (polling 30s)
│   │   ├── StatusCard.tsx        # Card reutilizável de métricas
│   │   ├── ChartPlaceholder.tsx  # Área reservada para gráfico
│   │   ├── SignalsPlaceholder.tsx # Área reservada para sinais
│   │   ├── NewsPlaceholder.tsx   # Área reservada para notícias
│   │   └── StatsPlaceholder.tsx  # Área reservada para KPIs
│   └── ui/
│       └── Badge.tsx             # Indicador de status visual
├── lib/
│   └── api.ts              # Cliente HTTP (fetch wrapper)
└── types/
    └── index.ts            # Tipos TypeScript globais
```

### Comunicação Frontend → Backend

O arquivo `next.config.js` configura um rewrite transparente:

```
Frontend: GET /api/v1/system/health
  → rewrite → Backend: GET http://127.0.0.1:8000/api/v1/system/health
```

Vantagem: o frontend nunca expõe a porta do backend ao usuário. Na Fase 2,
basta alterar o `destination` no `next.config.js` sem tocar nos componentes.

---

## Banco de Dados (SQLite)

### Por que SQLite na Fase 1?

- Zero configuração: arquivo único `data/tradeai.db`.
- Suficiente para persistir logs, configurações e dados históricos locais.
- SQLAlchemy abstrai a troca para PostgreSQL/TimescaleDB na Fase 3 com mínima alteração.

### Modelo atual

```sql
CREATE TABLE system_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    level      VARCHAR(20) NOT NULL,
    source     VARCHAR(100) NOT NULL,
    message    TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
);
```

---

## Sistema de Logs

Dois destinos simultâneos:
1. **Console** — saída colorida no terminal durante desenvolvimento.
2. **Arquivo** — `logs/tradeai.log` com rotação diária, retenção de 30 arquivos.

Hierarquia de loggers: `tradeai` → `tradeai.app.api.endpoints.health` etc.

Uso em qualquer módulo:
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
print(settings.app_port)      # 8000
print(settings.is_development) # True
```

Nunca usar `os.environ` diretamente nos módulos — tudo passa por `settings`.
