# Quick Start Guide - Frontend IA-Generica

## Instalação Rápida

```bash
# 1. Navegue para a pasta do frontend
cd /Users/steveherison/IAGenerica/frontend

# 2. Instale as dependências
npm install

# 3. Instale dependências adicionais necessárias
npm install @hello-pangea/dnd date-fns

# 4. Configure as variáveis de ambiente
cp .env.example .env.local
# Edite .env.local com suas credenciais
```

## Configuração das Variáveis de Ambiente

Crie o arquivo `.env.local` na raiz do projeto frontend:

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://seu-projeto.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sua-chave-anonima-aqui

# API Backend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Rodar o Projeto

```bash
# Desenvolvimento
npm run dev
# Abre em http://localhost:3000

# Build de produção
npm run build

# Rodar build de produção
npm start

# Lint
npm run lint
```

## Estrutura de Rotas

### Páginas Públicas
- `/` - Redireciona para /dashboard ou /auth/sign-in
- `/auth/sign-in` - Login
- `/auth/sign-up` - Cadastro
- `/auth/forgot-password` - Recuperar senha

### Dashboard (Protegido)
- `/dashboard` - Dashboard principal com estatísticas
- `/dashboard/leads` - Lista de leads
- `/dashboard/leads/novo` - Criar novo lead
- `/dashboard/leads/[id]` - Editar lead específico
- `/dashboard/kanban` - Kanban board
- `/dashboard/conversations` - Lista de conversas
- `/dashboard/conversations/[id]` - Chat individual
- `/dashboard/flow-builder` - Construtor de fluxos
- `/dashboard/notifications` - Notificações
- `/dashboard/settings` - Configurações gerais
- `/dashboard/settings/ia` - Configurar IA
- `/dashboard/settings/whatsapp` - Configurar WhatsApp

## Credenciais de Teste

Para desenvolvimento, você pode criar um usuário através da página de cadastro ou usar:

```
Email: teste@exemplo.com
Senha: 123456
```

## Comandos Úteis

### Limpar cache do Next.js
```bash
rm -rf .next
npm run dev
```

### Verificar tipos TypeScript
```bash
npx tsc --noEmit
```

### Analisar bundle
```bash
npm run build
# Veja o tamanho dos arquivos em .next/analyze/
```

## Troubleshooting

### Erro: "Module not found"
```bash
# Reinstale as dependências
rm -rf node_modules package-lock.json
npm install
```

### Erro de autenticação
1. Verifique se as variáveis `NEXT_PUBLIC_SUPABASE_*` estão corretas
2. Verifique se o backend está rodando
3. Limpe o cache do navegador

### Página em branco
1. Abra o console do navegador (F12)
2. Verifique erros de JavaScript
3. Verifique se a API está respondendo

### Erro 404 em produção
```bash
# Certifique-se de fazer build antes de rodar
npm run build
npm start
```

## Features Principais

### Autenticação
- Login/Logout com Supabase
- Registro de novos usuários
- Recuperação de senha
- Proteção de rotas

### Gerenciamento de Leads
- Criar, editar, excluir leads
- Busca e filtros
- Status personalizáveis
- Toggle de IA ativo/inativo

### Kanban
- Drag-and-drop de leads
- Colunas por status
- Cores personalizadas
- Atualização em tempo real

### Conversas
- Lista de conversas ativas
- Chat funcional
- Envio de mensagens
- Toggle IA/Humano
- Histórico completo

### Configurações
- Dados da empresa
- Personalização da IA
- Integração WhatsApp/UazAPI

## Componentes Principais

### AuthContext
```typescript
import { useAuth } from '@/contexts/auth-context';

const { user, loading, signIn, signOut } = useAuth();
```

### API Helpers
```typescript
import { apiGet, apiPost, apiPatch, apiDelete } from '@/lib/supabase';

const leads = await apiGet('/api/leads');
await apiPost('/api/leads', { nome: 'João' });
```

### Header Component
```typescript
import { Header } from '@/components/layout/header';

<Header title="Título" subtitle="Subtítulo" />
```

## Próximos Passos

1. Configure as variáveis de ambiente
2. Rode `npm install`
3. Inicie o servidor de desenvolvimento: `npm run dev`
4. Acesse http://localhost:3000
5. Faça login ou crie uma conta
6. Explore o dashboard!

## Links Úteis

- **Next.js Docs**: https://nextjs.org/docs
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Supabase**: https://supabase.com/docs
- **Lucide Icons**: https://lucide.dev/
- **React Flow**: https://reactflow.dev/

## Suporte

Para problemas ou dúvidas:
1. Verifique o FRONTEND_IMPLEMENTATION.md
2. Consulte os logs do console
3. Verifique se o backend está funcionando
4. Entre em contato com a equipe de desenvolvimento
