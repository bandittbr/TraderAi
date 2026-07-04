# TradeAI 🤖📈

Plataforma de trading algorítmico com inteligência artificial.
Construída sobre FastAPI (backend) + Next.js (frontend) + SQLite (banco de dados).

> **Fase 1 — Fundação**: estrutura base do sistema. Nenhuma operação de trading é executada nesta fase.

---

## Pré-requisitos

| Ferramenta | Versão mínima | Instalação |
|-----------|---------------|------------|
| Python    | 3.11+         | https://python.org |
| Node.js   | 18+           | https://nodejs.org |
| npm       | 9+            | Incluso com Node.js |
| Git       | qualquer      | https://git-scm.com |

---

## Execução local (Windows)

### 1. Clonar / posicionar o projeto

```cmd
cd C:\caminho\para\tradeai
```

### 2. Backend (FastAPI)

```cmd
cd backend

:: Criar ambiente virtual
python -m venv .venv
.venv\Scripts\activate

:: Instalar dependências
pip install -r requirements.txt

:: Configurar variáveis de ambiente
copy .env.example .env

:: Iniciar servidor (porta 8000)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

O banco SQLite (`data/tradeai.db`) é criado automaticamente na primeira execução.

Acesse: http://127.0.0.1:8000/docs (Swagger UI)

### 3. Frontend (Next.js)

Abra um **novo terminal**:

```cmd
cd frontend

:: Instalar dependências
npm install

:: Configurar variáveis de ambiente
copy .env.local.example .env.local

:: Iniciar servidor de desenvolvimento (porta 3000)
npm run dev
```

Acesse: http://localhost:3000

> **Importante**: o backend deve estar em execução antes de iniciar o frontend.

---

## Estrutura do Projeto

```
tradeai/
│
├── backend/                    # Servidor FastAPI (Python)
│   ├── app/
│   │   ├── main.py             # Ponto de entrada — lifespan, middlewares
│   │   ├── config.py           # Configuração centralizada (pydantic-settings)
│   │   ├── database.py         # Engine SQLAlchemy + sessões assíncronas
│   │   ├── logger.py           # Sistema de logs com rotação de arquivos
│   │   ├── api/
│   │   │   ├── router.py       # Roteador principal (/api/v1)
│   │   │   └── endpoints/
│   │   │       └── health.py   # GET /system/health, GET /system/status
│   │   ├── models/
│   │   │   └── system.py       # Modelo ORM: SystemLog
│   │   ├── schemas/
│   │   │   └── system.py       # DTOs Pydantic: HealthResponse, SystemStatusResponse
│   │   └── services/           # Lógica de negócio (vazio — Fase 2+)
│   ├── data/
│   │   └── tradeai.db          # Banco SQLite (gerado automaticamente)
│   ├── logs/
│   │   └── tradeai.log         # Logs com rotação diária
│   ├── requirements.txt        # Dependências Python
│   └── .env.example            # Template de variáveis de ambiente
│
├── frontend/                   # Aplicação Next.js (TypeScript)
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx      # Layout raiz (metadados, fontes)
│   │   │   ├── page.tsx        # Dashboard principal
│   │   │   └── globals.css     # Estilos globais + Tailwind
│   │   ├── components/
│   │   │   ├── dashboard/
│   │   │   │   ├── SystemStatus.tsx      # Status dos componentes (polling 30s)
│   │   │   │   ├── StatusCard.tsx        # Card reutilizável
│   │   │   │   ├── ChartPlaceholder.tsx  # Área para gráfico (Fase 2)
│   │   │   │   ├── SignalsPlaceholder.tsx # Área para sinais (Fase 2)
│   │   │   │   ├── NewsPlaceholder.tsx   # Área para notícias (Fase 2)
│   │   │   │   └── StatsPlaceholder.tsx  # Área para KPIs (Fase 2)
│   │   │   └── ui/
│   │   │       └── Badge.tsx             # Indicador de status
│   │   ├── lib/
│   │   │   └── api.ts          # Cliente HTTP centralizado
│   │   └── types/
│   │       └── index.ts        # Tipos TypeScript globais
│   ├── next.config.js          # Rewrite /api/* → backend:8000
│   ├── tailwind.config.ts      # Paleta de cores TradeAI
│   ├── tsconfig.json           # Configuração TypeScript
│   └── .env.local.example      # Template de variáveis de ambiente
│
├── docs/
│   ├── architecture.md         # Documentação técnica da arquitetura
│   └── phase2.md               # Guia de evolução para a Fase 2
│
└── README.md                   # Este arquivo
```

---

## Endpoints da API (Fase 1)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `http://localhost:8000/` | Raiz — informações básicas |
| GET | `http://localhost:8000/docs` | Swagger UI interativo |
| GET | `http://localhost:8000/api/v1/system/health` | Health check + status do banco |
| GET | `http://localhost:8000/api/v1/system/status` | Status detalhado de componentes |

---

## Stack Tecnológica

**Backend**
- Python 3.11+
- FastAPI 0.111 — framework web assíncrono
- SQLAlchemy 2.0 (async) — ORM com suporte a aiosqlite
- Pydantic v2 — validação e serialização de dados
- Uvicorn — servidor ASGI de alta performance

**Frontend**
- Next.js 14 (App Router)
- React 18
- TypeScript 5
- Tailwind CSS 3

**Banco de Dados**
- SQLite com aiosqlite (driver assíncrono)

---

## Roteiro de Fases

| Fase | Status | Descrição |
|------|--------|-----------|
| **Fase 1** | ✅ Concluída | Fundação: FastAPI + Next.js + SQLite + Dashboard |
| Fase 2 | 🔜 Próxima | Dados de mercado, IA, autenticação, WebSocket |
| Fase 3 | 📋 Planejada | Integração com corretoras, execução de ordens |
| Fase 4 | 📋 Planejada | Deploy, escalabilidade, multi-usuário |

Consulte `docs/phase2.md` para o plano detalhado da Fase 2.

---

## Licença

Uso privado — TradeAI. Todos os direitos reservados.
