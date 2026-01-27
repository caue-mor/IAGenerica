# Arquitetura Frontend - IA-Generica

## Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                         Root Layout                              │
│                    (app/layout.tsx)                              │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              AuthProvider (contexts/auth-context.tsx)       │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │                   App Router                          │  │ │
│  │  │                                                        │  │ │
│  │  │  ┌────────────────┐     ┌──────────────────────────┐ │  │ │
│  │  │  │  Auth Routes   │     │   Dashboard Routes       │ │  │ │
│  │  │  │  (public)      │     │   (protected)            │ │  │ │
│  │  │  │                │     │                          │ │  │ │
│  │  │  │  - Sign In     │     │  ┌────────────────────┐ │ │  │ │
│  │  │  │  - Sign Up     │     │  │  Dashboard Layout  │ │ │  │ │
│  │  │  │  - Forgot Pass │     │  │                    │ │ │  │ │
│  │  │  └────────────────┘     │  │  ┌──────────────┐  │ │ │  │ │
│  │  │                         │  │  │   Sidebar    │  │ │ │  │ │
│  │  │                         │  │  └──────────────┘  │ │ │  │ │
│  │  │                         │  │  ┌──────────────┐  │ │ │  │ │
│  │  │                         │  │  │   Header     │  │ │ │  │ │
│  │  │                         │  │  └──────────────┘  │ │ │  │ │
│  │  │                         │  │  ┌──────────────┐  │ │ │  │ │
│  │  │                         │  │  │   Content    │  │ │ │  │ │
│  │  │                         │  │  │              │  │ │ │  │ │
│  │  │                         │  │  │  - Dashboard │  │ │ │  │ │
│  │  │                         │  │  │  - Leads     │  │ │ │  │ │
│  │  │                         │  │  │  - Kanban    │  │ │ │  │ │
│  │  │                         │  │  │  - Chat      │  │ │ │  │ │
│  │  │                         │  │  │  - Settings  │  │ │ │  │ │
│  │  │                         │  │  └──────────────┘  │ │ │  │ │
│  │  │                         │  └────────────────────┘ │ │  │ │
│  │  │                         └──────────────────────────┘ │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

## Fluxo de Dados

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       │ 1. Interage com UI
       ▼
┌─────────────────────────────┐
│   React Components          │
│  (pages, components)        │
└──────────┬──────────────────┘
           │
           │ 2. Usa hooks/contexts
           ▼
┌─────────────────────────────┐
│   AuthContext               │
│   - user                    │
│   - loading                 │
│   - signIn/signOut          │
└──────────┬──────────────────┘
           │
           │ 3. Chama API helpers
           ▼
┌─────────────────────────────┐
│   API Helpers               │
│   (lib/supabase.ts)         │
│   - apiGet()                │
│   - apiPost()               │
│   - apiPatch()              │
│   - apiDelete()             │
└──────────┬──────────────────┘
           │
           │ 4. HTTP Requests
           ▼
┌─────────────────────────────┐
│   Backend API               │
│   (FastAPI)                 │
│   + Supabase Auth           │
└─────────────────────────────┘
```

## Estrutura de Pastas Detalhada

```
frontend/
├── public/                      # Assets estáticos
│   └── next.svg, vercel.svg
│
├── src/
│   ├── app/                     # Next.js 14 App Router
│   │   ├── globals.css          # Estilos globais
│   │   ├── layout.tsx           # Layout raiz com AuthProvider
│   │   ├── page.tsx             # Home (redirect)
│   │   │
│   │   ├── (auth)/              # Grupo de rotas públicas
│   │   │   ├── layout.tsx       # Layout minimalista
│   │   │   └── auth/
│   │   │       ├── sign-in/
│   │   │       │   └── page.tsx
│   │   │       ├── sign-up/
│   │   │       │   └── page.tsx
│   │   │       └── forgot-password/
│   │   │           └── page.tsx
│   │   │
│   │   └── dashboard/           # Grupo de rotas protegidas
│   │       ├── layout.tsx       # Layout com Sidebar
│   │       ├── page.tsx         # Dashboard principal
│   │       │
│   │       ├── leads/
│   │       │   ├── page.tsx     # Lista
│   │       │   ├── novo/
│   │       │   │   └── page.tsx # Criar
│   │       │   └── [id]/
│   │       │       └── page.tsx # Editar/Detalhe
│   │       │
│   │       ├── kanban/
│   │       │   └── page.tsx
│   │       │
│   │       ├── conversations/
│   │       │   ├── page.tsx     # Lista
│   │       │   └── [id]/
│   │       │       └── page.tsx # Chat
│   │       │
│   │       ├── flow-builder/
│   │       │   └── page.tsx
│   │       │
│   │       ├── notifications/
│   │       │   └── page.tsx
│   │       │
│   │       └── settings/
│   │           ├── page.tsx     # Geral
│   │           ├── ia/
│   │           │   └── page.tsx
│   │           └── whatsapp/
│   │               └── page.tsx
│   │
│   ├── components/
│   │   └── layout/
│   │       ├── sidebar.tsx      # Menu lateral
│   │       └── header.tsx       # Header com busca
│   │
│   ├── contexts/
│   │   └── auth-context.tsx     # Context de autenticação
│   │
│   ├── lib/
│   │   ├── supabase.ts          # Cliente Supabase + API helpers
│   │   └── utils.ts             # Utilitários gerais
│   │
│   └── types/
│       ├── index.ts             # Tipos principais
│       └── flow.types.ts        # Tipos do flow builder
│
├── .env.local                   # Variáveis de ambiente (criar)
├── .gitignore
├── next.config.js
├── package.json
├── postcss.config.js
├── tailwind.config.ts
├── tsconfig.json
│
└── Documentação/
    ├── ARCHITECTURE.md          # Este arquivo
    ├── FRONTEND_IMPLEMENTATION.md
    ├── QUICK_START.md
    ├── VERIFICATION_CHECKLIST.md
    ├── RESUMO_EXECUTIVO.md
    └── INSTALL.sh
```

## Padrões de Componentes

### 1. Páginas Protegidas

```typescript
'use client';
import { useState, useEffect } from 'react';
import { Header } from '@/components/layout/header';
import { apiGet } from '@/lib/supabase';
import { useAuth } from '@/contexts/auth-context';
import { Loader2 } from 'lucide-react';

export default function MyPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) {
      loadData();
    }
  }, [user]);

  async function loadData() {
    try {
      const result = await apiGet('/api/endpoint');
      setData(result);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div>
        <Header title="Loading" />
        <div className="flex items-center justify-center h-96">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="Título" subtitle="Subtítulo" />
      <div className="p-6">
        {/* Conteúdo */}
      </div>
    </div>
  );
}
```

### 2. Formulários

```typescript
const [formData, setFormData] = useState({
  field1: '',
  field2: '',
});
const [saving, setSaving] = useState(false);

async function handleSubmit(e: React.FormEvent) {
  e.preventDefault();
  setSaving(true);

  try {
    await apiPost('/api/endpoint', formData);
    // Success
  } catch (error) {
    // Error
  } finally {
    setSaving(false);
  }
}

return (
  <form onSubmit={handleSubmit}>
    <input
      value={formData.field1}
      onChange={(e) => setFormData({ ...formData, field1: e.target.value })}
    />
    <button disabled={saving}>
      {saving ? 'Salvando...' : 'Salvar'}
    </button>
  </form>
);
```

### 3. Listas com Filtros

```typescript
const [items, setItems] = useState([]);
const [searchTerm, setSearchTerm] = useState('');
const [filter, setFilter] = useState('all');

const filteredItems = items.filter(item => {
  const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase());
  const matchesFilter = filter === 'all' || item.status === filter;
  return matchesSearch && matchesFilter;
});
```

## Estado e Gerenciamento

### AuthContext

```typescript
interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, companyName: string) => Promise<void>;
  signOut: () => Promise<void>;
}
```

**Uso:**
```typescript
const { user, loading, signIn, signOut } = useAuth();
```

### Estado Local

- `useState` para estados simples de componente
- `useEffect` para side effects (API calls, subscriptions)
- Optimistic updates onde apropriado

## Roteamento

### Rotas Públicas
```
/auth/sign-in          → Página de login
/auth/sign-up          → Página de cadastro
/auth/forgot-password  → Recuperação de senha
```

### Rotas Protegidas (requer autenticação)
```
/dashboard                       → Dashboard principal
/dashboard/leads                 → Lista de leads
/dashboard/leads/novo            → Criar lead
/dashboard/leads/[id]            → Editar lead
/dashboard/kanban                → Kanban board
/dashboard/conversations         → Lista conversas
/dashboard/conversations/[id]    → Chat individual
/dashboard/flow-builder          → Flow builder
/dashboard/notifications         → Notificações
/dashboard/settings              → Config geral
/dashboard/settings/ia           → Config IA
/dashboard/settings/whatsapp     → Config WhatsApp
```

## Estilização

### Tailwind Classes Comuns

```css
/* Cards */
.card {
  @apply bg-white rounded-xl shadow-sm border border-gray-200 p-6;
}

/* Botões Primários */
.btn-primary {
  @apply px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700
         disabled:bg-blue-400 transition-colors;
}

/* Inputs */
.input {
  @apply w-full px-4 py-2 border border-gray-300 rounded-lg
         focus:ring-2 focus:ring-blue-500 focus:border-transparent;
}

/* Loading State */
.loading {
  @apply flex items-center justify-center h-96;
}
```

## Convenções de Código

### Nomenclatura
- **Componentes**: PascalCase (e.g., `MyComponent.tsx`)
- **Funções**: camelCase (e.g., `handleSubmit`)
- **Constantes**: UPPER_SNAKE_CASE (e.g., `API_URL`)
- **Types/Interfaces**: PascalCase (e.g., `UserType`)

### Estrutura de Arquivo
```typescript
// 1. Imports
import { useState } from 'react';
import { Component } from 'library';

// 2. Types/Interfaces
interface Props {
  title: string;
}

// 3. Component
export default function MyComponent({ title }: Props) {
  // 4. State
  const [state, setState] = useState();

  // 5. Effects
  useEffect(() => {}, []);

  // 6. Handlers
  function handleClick() {}

  // 7. Render
  return <div>{title}</div>;
}
```

## Performance

### Otimizações Implementadas
- Loading states em todas as páginas
- Atualização otimista (Kanban)
- Lazy loading preparado
- Code splitting automático (Next.js)

### Melhorias Futuras
- React.memo para componentes pesados
- useMemo para cálculos complexos
- useCallback para funções em props
- Virtual scrolling para listas grandes

## Segurança

### Proteção de Rotas
- Layout do dashboard verifica autenticação
- Redirect automático se não autenticado
- Token gerenciado pelo Supabase

### Validações
- Validação client-side em formulários
- Sanitização de inputs
- HTTPS em produção

## Testes

### Preparação para Testes
```bash
# Unit tests (a implementar)
npm test

# E2E tests (a implementar)
npm run test:e2e

# Type check
npx tsc --noEmit
```

## Deploy

### Preparação
```bash
# Build
npm run build

# Test build
npm start

# Analyze bundle
npm run build && npx @next/bundle-analyzer
```

### Ambientes
- **Development**: `npm run dev`
- **Staging**: `npm run build && npm start`
- **Production**: Deploy em Vercel/Railway/etc

## Troubleshooting

### Problemas Comuns

1. **Erro de módulo não encontrado**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

2. **Erro de tipos TypeScript**
   ```bash
   npx tsc --noEmit
   ```

3. **Cache do Next.js**
   ```bash
   rm -rf .next
   npm run dev
   ```

4. **Variáveis de ambiente não carregam**
   - Reinicie o servidor dev após mudar .env.local
   - Variáveis devem começar com `NEXT_PUBLIC_` para client-side

## Links Úteis

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [TypeScript](https://www.typescriptlang.org)
- [Supabase Docs](https://supabase.com/docs)
