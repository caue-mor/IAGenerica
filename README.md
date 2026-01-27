# IA Generica Nexma

Sistema de atendimento automatizado com IA para qualquer segmento de negocio.

## Stack

- **Backend**: FastAPI + LangGraph + Python + OpenAI (gpt-4o-mini)
- **Frontend**: Next.js 14 + React + TypeScript + Tailwind + shadcn/ui
- **Banco**: Supabase (PostgreSQL)
- **WhatsApp**: UAZAPI

## Estrutura

```
/IAGenerica/
├── backend/           # FastAPI + LangGraph
├── frontend/          # Next.js 14
└── database/          # Migrations SQL
```

## Tabelas no Supabase

Todas as tabelas usam o prefixo `iagenericanexma_*` para identificacao:

| Tabela | Descricao |
|--------|-----------|
| `iagenericanexma_companies` | Empresas cadastradas |
| `iagenericanexma_lead_statuses` | Status do Kanban |
| `iagenericanexma_leads` | Leads/Contatos |
| `iagenericanexma_conversations` | Conversas WhatsApp |
| `iagenericanexma_messages` | Mensagens |

## Setup

### 1. Banco de Dados (Supabase)

As tabelas ja foram criadas automaticamente via MCP.

Ou execute manualmente:
```bash
# Execute o SQL em database/migrations/001_initial_schema.sql no Supabase
```

### 2. Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variaveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais

# Rodar
python main.py
```

API disponivel em: http://localhost:8000

### 3. Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Configurar variaveis de ambiente
cp .env.example .env.local
# Edite o .env.local com suas credenciais

# Rodar
npm run dev
```

Dashboard disponivel em: http://localhost:3000

## Configuracao do Webhook (UAZAPI)

Configure o webhook no UAZAPI para apontar para:

```
POST https://seu-dominio.com/webhook/{company_id}
```

## Endpoints Principais

### API

- `GET /health` - Health check
- `POST /webhook/{company_id}` - Webhook UAZAPI
- `GET /api/companies` - Listar empresas
- `GET /api/leads?company_id=1` - Listar leads
- `GET /api/leads/{lead_id}/messages` - Mensagens do lead

### Dashboard

- `/` - Home
- `/dashboard/leads` - Gerenciar leads
- `/dashboard/conversations` - Ver conversas
- `/dashboard/flow-builder` - Configurar fluxos
- `/dashboard/settings` - Configuracoes

## Tipos de Nos do FlowBuilder

| Tipo | Descricao |
|------|-----------|
| `GREETING` | Saudacao inicial |
| `QUESTION` | Pergunta para coletar dados |
| `CONDITION` | Decisao if/else |
| `MESSAGE` | Mensagem informativa |
| `ACTION` | Webhook/API call |
| `HANDOFF` | Transferir para humano |
| `FOLLOWUP` | Agendar follow-up |

## Arquivos Principais

| Arquivo | Responsabilidade |
|---------|------------------|
| `backend/src/agent/graph.py` | Agente LangGraph |
| `backend/src/agent/prompts.py` | Prompts dinamicos |
| `backend/src/flow/executor.py` | Executor de fluxos |
| `backend/src/services/database.py` | CRUD (prefixo iagenericanexma_) |
| `frontend/src/types/flow.types.ts` | Tipos dos nos |

## Licenca

Privado - Nexma
