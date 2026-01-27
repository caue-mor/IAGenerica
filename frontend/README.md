# IA-Generica Frontend

Sistema de atendimento automatizado com IA baseado em WhatsApp - Interface Web Completa

![Status](https://img.shields.io/badge/status-100%25%20implementado-brightgreen)
![Next.js](https://img.shields.io/badge/Next.js-14.1-black)
![React](https://img.shields.io/badge/React-18.2-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue)
![Tailwind](https://img.shields.io/badge/Tailwind-3.4-38bdf8)

## Visão Geral

Frontend completo e moderno construído com Next.js 14, React 18 e TypeScript. Oferece uma interface intuitiva e responsiva para gerenciar leads, conversas, configurações de IA e muito mais.

## Características Principais

- **Autenticação Completa** - Login, cadastro e recuperação de senha com Supabase
- **Dashboard Interativo** - Estatísticas em tempo real e métricas importantes
- **Gestão de Leads** - CRUD completo com busca, filtros e kanban board
- **Chat em Tempo Real** - Interface de conversas com toggle IA/Humano
- **Kanban Board** - Drag-and-drop para gerenciar status dos leads
- **Configurações Avançadas** - Personalização de IA e integração WhatsApp
- **Design Responsivo** - Mobile-first, funciona em todos os dispositivos
- **TypeScript 100%** - Type-safe em toda a aplicação

## Tecnologias

| Tecnologia | Versão | Descrição |
|------------|--------|-----------|
| Next.js | 14.1.0 | Framework React com SSR |
| React | 18.2.0 | Biblioteca de UI |
| TypeScript | 5.3.3 | Tipagem estática |
| Tailwind CSS | 3.4.1 | Framework CSS utility-first |
| Supabase | 2.39.3 | Auth e Database |
| Lucide React | 0.312.0 | Ícones modernos |
| React Flow | 11.10.3 | Flow builder |

## Início Rápido

### Pré-requisitos

- Node.js 18+
- npm ou yarn
- Backend FastAPI rodando
- Conta Supabase

### Instalação

```bash
# 1. Clone o repositório (se ainda não tiver)
git clone <repo-url>
cd IAGenerica/frontend

# 2. Instale as dependências
npm install

# 3. Instale dependências adicionais
npm install @hello-pangea/dnd date-fns

# 4. Configure as variáveis de ambiente
cp .env.example .env.local
# Edite .env.local com suas credenciais

# 5. Rode o projeto
npm run dev
```

### Variáveis de Ambiente

Crie um arquivo `.env.local`:

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://seu-projeto.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sua-chave-anonima

# API Backend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Acesse a Aplicação

Abra http://localhost:3000 no navegador.

## Estrutura do Projeto

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/            # Rotas de autenticação
│   │   └── dashboard/         # Rotas protegidas
│   ├── components/            # Componentes reutilizáveis
│   ├── contexts/              # React Contexts
│   ├── lib/                   # Utilitários e helpers
│   └── types/                 # TypeScript types
├── public/                    # Assets estáticos
└── docs/                      # Documentação
```

## Páginas Implementadas

### Públicas
- `/auth/sign-in` - Login
- `/auth/sign-up` - Cadastro
- `/auth/forgot-password` - Recuperar senha

### Dashboard (Protegidas)
- `/dashboard` - Dashboard principal
- `/dashboard/leads` - Gestão de leads
- `/dashboard/kanban` - Kanban board
- `/dashboard/conversations` - Chat e conversas
- `/dashboard/flow-builder` - Construtor de fluxos
- `/dashboard/notifications` - Notificações
- `/dashboard/settings` - Configurações

## Comandos Disponíveis

```bash
# Desenvolvimento
npm run dev

# Build de produção
npm run build

# Iniciar produção
npm start

# Lint
npm run lint

# Type check
npx tsc --noEmit
```

## Documentação Completa

Consulte os arquivos de documentação:

- **[QUICK_START.md](QUICK_START.md)** - Guia de início rápido
- **[FRONTEND_IMPLEMENTATION.md](FRONTEND_IMPLEMENTATION.md)** - Documentação técnica completa
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Arquitetura e padrões
- **[VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md)** - Checklist de testes
- **[RESUMO_EXECUTIVO.md](RESUMO_EXECUTIVO.md)** - Resumo executivo

## Features Detalhadas

### Sistema de Autenticação
- Login com email/senha via Supabase
- Registro de novos usuários
- Recuperação de senha por email
- Proteção automática de rotas
- Persistência de sessão

### Dashboard
- Cards de estatísticas (Leads, Conversas, Mensagens)
- Atividade recente
- Quick actions
- Design responsivo

### Gestão de Leads
- Lista completa com tabela
- Busca em tempo real
- Filtros por status
- CRUD completo
- Toggle IA ativo/inativo
- Visualização de histórico

### Kanban Board
- Drag-and-drop nativo
- Colunas por status
- Cores personalizadas
- Contadores automáticos
- Atualização otimista

### Sistema de Conversas
- Lista de conversas
- Chat funcional
- Envio de mensagens
- Toggle IA/Humano
- Histórico completo
- Auto-scroll

### Configurações
- Informações da empresa
- Personalização da IA
- Integração WhatsApp/UazAPI
- Interface intuitiva

## Design System

### Cores

```css
Primary: #2563EB (Blue-600)
Success: #16A34A (Green-600)
Danger: #DC2626 (Red-600)
Warning: #EA580C (Orange-600)
```

### Componentes Base

- **Cards**: `bg-white rounded-xl shadow-sm border`
- **Botões**: Estados hover, focus e disabled
- **Inputs**: Focus ring e validação visual
- **Loading**: Spinner animado com Lucide
- **Empty States**: Ícones e mensagens amigáveis

## Responsividade

- **Mobile**: < 768px - Menu hamburger, layout vertical
- **Tablet**: 768px - 1024px - Layout adaptativo
- **Desktop**: > 1024px - Sidebar fixa, múltiplas colunas

## Performance

- Loading states em todas as páginas
- Otimistic updates no Kanban
- Code splitting automático
- Image optimization ready
- Bundle otimizado

## Segurança

- Proteção de rotas via AuthContext
- Validações client-side
- Sanitização de inputs
- Token JWT via Supabase
- HTTPS em produção

## Próximos Passos

### Prioridade Alta
- [ ] Implementar testes (Jest + React Testing Library)
- [ ] Real-time updates com Supabase subscriptions
- [ ] Toast notifications para feedback
- [ ] Error boundaries global

### Prioridade Média
- [ ] Dashboard com gráficos (Chart.js/Recharts)
- [ ] Exportação de leads (CSV/Excel)
- [ ] Dark mode
- [ ] Multi-idioma (i18n)

### Prioridade Baixa
- [ ] PWA (Progressive Web App)
- [ ] Animações avançadas
- [ ] Upload de arquivos
- [ ] Filtros avançados

## Troubleshooting

### Erro: Module not found

```bash
rm -rf node_modules package-lock.json
npm install
```

### Cache do Next.js

```bash
rm -rf .next
npm run dev
```

### Tipos TypeScript

```bash
npx tsc --noEmit
```

## Contribuindo

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

Este projeto é proprietário. Todos os direitos reservados.

## Suporte

Para dúvidas ou problemas:

1. Consulte a documentação em `/docs`
2. Verifique os logs do console do navegador
3. Certifique-se que o backend está rodando
4. Entre em contato com o time de desenvolvimento

## Status do Projeto

✅ **100% Implementado e Funcional**

- [x] Autenticação completa
- [x] Dashboard interativo
- [x] CRUD de Leads
- [x] Kanban Board
- [x] Sistema de Chat
- [x] Notificações
- [x] Configurações
- [x] Design responsivo
- [x] TypeScript completo
- [x] Documentação

## Links Úteis

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [Supabase Docs](https://supabase.com/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

---

**Desenvolvido com ❤️ usando Next.js, React e TypeScript**

**Localização:** `/Users/steveherison/IAGenerica/frontend/`

**Última atualização:** Janeiro 2026
