# Frontend IA-Generica - Implementação Completa

## Estrutura Criada

### Autenticação

**Arquivos:**
- `/src/contexts/auth-context.tsx` - Context de autenticação com Supabase
- `/src/app/(auth)/layout.tsx` - Layout das páginas de auth
- `/src/app/(auth)/auth/sign-in/page.tsx` - Página de login
- `/src/app/(auth)/auth/sign-up/page.tsx` - Página de cadastro
- `/src/app/(auth)/auth/forgot-password/page.tsx` - Recuperação de senha

**Features:**
- Login com email/senha
- Registro de novo usuário
- Recuperação de senha
- Persistência de sessão
- Redirecionamento automático

### Layout e Navegação

**Arquivos:**
- `/src/components/layout/sidebar.tsx` - Sidebar responsiva com menu
- `/src/components/layout/header.tsx` - Header com busca e notificações
- `/src/app/dashboard/layout.tsx` - Layout protegido do dashboard

**Features:**
- Menu lateral responsivo
- Mobile-first design
- Navegação por ícones
- Indicadores visuais de página ativa
- Logout integrado

### Dashboard Principal

**Arquivo:**
- `/src/app/dashboard/page.tsx`

**Features:**
- Cards de estatísticas (Leads, Conversas, Mensagens)
- Atividade recente
- Quick actions
- Design responsivo

### Leads

**Arquivos:**
- `/src/app/dashboard/leads/page.tsx` - Lista de leads
- `/src/app/dashboard/leads/novo/page.tsx` - Criar lead
- `/src/app/dashboard/leads/[id]/page.tsx` - Editar lead

**Features:**
- Tabela completa de leads
- Busca e filtros por status
- CRUD completo
- Campos: nome, celular, email, origem, status
- Toggle de IA ativo/inativo
- Histórico de conversas do lead

### Kanban Board

**Arquivo:**
- `/src/app/dashboard/kanban/page.tsx`

**Features:**
- Drag-and-drop nativo (sem biblioteca externa)
- Colunas por status
- Cards de leads
- Contadores por coluna
- Atualização otimista
- Cores personalizadas por status

### Conversas

**Arquivos:**
- `/src/app/dashboard/conversations/page.tsx` - Lista de conversas
- `/src/app/dashboard/conversations/[id]/page.tsx` - Chat individual

**Features:**
- Grid de conversas com cards
- Filtros: Todas, Ativas, IA, Humano
- Status de IA/Humano
- Chat completo com mensagens
- Envio de mensagens manuais
- Toggle IA on/off
- Sidebar com informações do lead
- Auto-scroll para última mensagem

### Notificações

**Arquivo:**
- `/src/app/dashboard/notifications/page.tsx`

**Features:**
- Lista de notificações
- Filtro: Todas / Não lidas
- Tipos: mensagem, lead, alert, system
- Marcar como lida (individual ou todas)
- Excluir notificações
- Contador de não lidas
- Links para recursos relacionados

### Configurações

**Arquivos:**
- `/src/app/dashboard/settings/page.tsx` - Configurações gerais
- `/src/app/dashboard/settings/ia/page.tsx` - Configuração da IA
- `/src/app/dashboard/settings/whatsapp/page.tsx` - Configuração WhatsApp

**Features:**

#### Geral:
- Informações da empresa
- Email, cidade, site
- Horário de funcionamento
- Informações complementares para IA

#### IA:
- Nome do assistente
- Tom de voz (amigável, formal, casual, técnico)
- Toggle de emojis
- Preview em tempo real

#### WhatsApp:
- Credenciais UazAPI (instância e token)
- Número do WhatsApp
- Status de conexão
- Teste de conexão

### Flow Builder

**Arquivo:**
- `/src/app/dashboard/flow-builder/page.tsx` (já existia, mantido)

## Tecnologias Utilizadas

- **Next.js 14** (App Router)
- **React 18** (Server e Client Components)
- **TypeScript** (Type safety completo)
- **Tailwind CSS** (Estilização)
- **Supabase** (Auth e Database)
- **Lucide React** (Ícones)
- **React Flow** (Flow builder - já existente)

## Padrões de Design

### Cores
- Primary: Blue-600 (#2563EB)
- Success: Green-600 (#16A34A)
- Danger: Red-600 (#DC2626)
- Warning: Orange-600 (#EA580C)
- Gray scale para texto e backgrounds

### Componentes
- Cards com `rounded-xl shadow-sm border`
- Botões com hover states e disabled states
- Inputs com `focus:ring-2 focus:ring-blue-500`
- Loading states com Loader2 animado
- Empty states com ícones e mensagens

### Responsividade
- Mobile-first approach
- Breakpoints: sm, md, lg, xl
- Sidebar responsiva com overlay em mobile
- Grids adaptáveis por tamanho de tela

## API Integration

Todas as chamadas de API usam os helpers em `/src/lib/supabase.ts`:

```typescript
apiGet<T>(endpoint: string): Promise<T>
apiPost<T>(endpoint: string, data: any): Promise<T>
apiPatch<T>(endpoint: string, data: any): Promise<T>
apiPut<T>(endpoint: string, data: any): Promise<T>
apiDelete(endpoint: string): Promise<void>
```

## Dependências Necessárias

Execute para instalar as dependências necessárias:

```bash
cd /Users/steveherison/IAGenerica/frontend
npm install @hello-pangea/dnd date-fns
```

## Variáveis de Ambiente

Crie um arquivo `.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://seu-projeto.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sua-chave-anonima
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Como Rodar

```bash
# Instalar dependências
npm install

# Rodar em desenvolvimento
npm run dev

# Build para produção
npm run build

# Rodar produção
npm start
```

## Próximos Passos

### Funcionalidades Adicionais
1. **Real-time** - Implementar subscriptions do Supabase para updates em tempo real
2. **Upload de arquivos** - Permitir envio de imagens/documentos
3. **Exportação** - Exportar leads para CSV/Excel
4. **Analytics** - Dashboard com gráficos de métricas
5. **Multi-idioma** - Suporte para PT/EN/ES
6. **Dark mode** - Tema escuro

### Melhorias de UX
1. **Toast notifications** - Feedback visual para ações
2. **Confirmações** - Modals para ações destrutivas
3. **Skeleton loaders** - Loading states mais elaborados
4. **Infinite scroll** - Para listas grandes
5. **Search debounce** - Otimizar buscas
6. **Keyboard shortcuts** - Atalhos para ações comuns

### Performance
1. **React Query** - Cache e invalidação inteligente
2. **Code splitting** - Lazy loading de rotas
3. **Image optimization** - Next.js Image component
4. **Bundle analysis** - Reduzir tamanho do bundle

### Testes
1. **Unit tests** - Jest + React Testing Library
2. **E2E tests** - Playwright ou Cypress
3. **Accessibility tests** - axe-core

## Estrutura de Pastas Final

```
src/
├── app/
│   ├── layout.tsx (AuthProvider wrapper)
│   ├── page.tsx (redirect para dashboard ou login)
│   ├── (auth)/
│   │   ├── layout.tsx
│   │   └── auth/
│   │       ├── sign-in/page.tsx
│   │       ├── sign-up/page.tsx
│   │       └── forgot-password/page.tsx
│   └── dashboard/
│       ├── layout.tsx (Sidebar + protected)
│       ├── page.tsx (dashboard principal)
│       ├── leads/
│       │   ├── page.tsx
│       │   ├── novo/page.tsx
│       │   └── [id]/page.tsx
│       ├── kanban/page.tsx
│       ├── conversations/
│       │   ├── page.tsx
│       │   └── [id]/page.tsx
│       ├── flow-builder/page.tsx
│       ├── notifications/page.tsx
│       └── settings/
│           ├── page.tsx (geral)
│           ├── ia/page.tsx
│           └── whatsapp/page.tsx
├── components/
│   └── layout/
│       ├── sidebar.tsx
│       └── header.tsx
├── contexts/
│   └── auth-context.tsx
├── lib/
│   ├── supabase.ts
│   └── utils.ts
└── types/
    ├── index.ts
    └── flow.types.ts
```

## Checklist de Implementação

- [x] Auth Context e páginas de autenticação
- [x] Layout com Sidebar e Header
- [x] Dashboard principal com estatísticas
- [x] CRUD completo de Leads
- [x] Kanban Board com drag-and-drop
- [x] Lista e detalhe de conversas
- [x] Chat funcional com envio de mensagens
- [x] Página de notificações
- [x] Configurações gerais da empresa
- [x] Configuração de IA personalizada
- [x] Configuração de WhatsApp/UazAPI
- [x] Página home com redirect
- [x] Design responsivo mobile-first
- [x] Loading states em todas as páginas
- [x] Error handling básico
- [x] TypeScript types completos

## Notas Importantes

1. **Autenticação**: O sistema usa Supabase Auth. Certifique-se de configurar as variáveis de ambiente corretamente.

2. **API**: Todas as páginas fazem chamadas para a API FastAPI no backend. Certifique-se que o backend está rodando.

3. **Company ID**: O sistema usa `user?.company_id` do contexto de autenticação. Em produção, isso deve vir do banco de dados.

4. **Mobile**: Todo o frontend é responsivo e funciona em dispositivos móveis.

5. **Acessibilidade**: Labels, ARIA attributes e navegação por teclado foram implementados onde necessário.

## Arquivos de Referência

- **SAAS-SOLAR**: Usado como referência de design e arquitetura
- **Types**: Todos os tipos estão em `/src/types/index.ts` e `/src/types/flow.types.ts`
- **API Helpers**: `/src/lib/supabase.ts` contém todos os métodos de API

## Contato e Suporte

Para dúvidas ou problemas, consulte a documentação do projeto ou entre em contato com o time de desenvolvimento.
