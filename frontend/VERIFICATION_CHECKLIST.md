# Checklist de Verificação - Frontend IA-Generica

## Pré-requisitos

- [ ] Node.js 18+ instalado
- [ ] npm ou yarn instalado
- [ ] Backend FastAPI rodando
- [ ] Supabase configurado
- [ ] Variáveis de ambiente configuradas

## Instalação

- [ ] `npm install` executado sem erros
- [ ] `npm install @hello-pangea/dnd date-fns` executado
- [ ] Arquivo `.env.local` criado e configurado
- [ ] Sem erros de TypeScript ao rodar `npx tsc --noEmit`

## Páginas de Autenticação

### Sign In (/auth/sign-in)
- [ ] Página carrega corretamente
- [ ] Formulário renderiza com campos de email e senha
- [ ] Botão "Entrar" funciona
- [ ] Link para "Esqueceu a senha" funciona
- [ ] Link para "Criar conta" funciona
- [ ] Mensagens de erro aparecem quando credenciais inválidas
- [ ] Redireciona para /dashboard após login bem-sucedido
- [ ] Design responsivo em mobile

### Sign Up (/auth/sign-up)
- [ ] Página carrega corretamente
- [ ] Formulário com nome empresa, email, senha
- [ ] Validação de senha (mínimo 6 caracteres)
- [ ] Botão "Criar conta" funciona
- [ ] Link para "Entrar" funciona
- [ ] Redireciona após cadastro

### Forgot Password (/auth/forgot-password)
- [ ] Página carrega corretamente
- [ ] Campo de email funciona
- [ ] Botão "Enviar link" funciona
- [ ] Mensagem de sucesso aparece
- [ ] Link para voltar ao login funciona

## Layout do Dashboard

### Sidebar
- [ ] Sidebar renderiza no desktop
- [ ] Menu responsivo em mobile (botão hamburger)
- [ ] Todos os itens do menu aparecem
- [ ] Item ativo fica destacado
- [ ] Navegação entre páginas funciona
- [ ] Botão de logout funciona
- [ ] Email do usuário aparece

### Header
- [ ] Header renderiza em todas as páginas do dashboard
- [ ] Título e subtítulo corretos
- [ ] Campo de busca renderiza
- [ ] Ícone de notificações aparece com badge
- [ ] Avatar do usuário aparece

## Dashboard Principal (/dashboard)

- [ ] Página carrega sem erros
- [ ] 4 cards de estatísticas renderizam
- [ ] Cards são clicáveis e redirecionam
- [ ] Seção "Leads Recentes" renderiza
- [ ] Seção "Conversas Recentes" renderiza
- [ ] Quick Actions renderizam
- [ ] Design responsivo funciona
- [ ] Números de estatísticas carregam (mesmo que 0)

## Leads

### Lista (/dashboard/leads)
- [ ] Tabela de leads renderiza
- [ ] Campo de busca funciona
- [ ] Filtro por status funciona
- [ ] Botão "Novo Lead" funciona
- [ ] Leads aparecem na tabela
- [ ] Colunas: Nome, Status, IA, Origem, Data
- [ ] Botões de editar e excluir funcionam
- [ ] Empty state aparece quando não há leads
- [ ] Contador de leads funciona

### Novo Lead (/dashboard/leads/novo)
- [ ] Formulário renderiza
- [ ] Todos os campos aparecem
- [ ] Campo celular é obrigatório
- [ ] Dropdown de status funciona
- [ ] Checkbox de IA funciona
- [ ] Botão "Salvar" funciona
- [ ] Redireciona para lista após salvar
- [ ] Botão "Cancelar" volta para lista
- [ ] Validações funcionam

### Editar Lead (/dashboard/leads/[id])
- [ ] Página carrega com dados do lead
- [ ] Formulário pré-populado
- [ ] Edições são salvas
- [ ] Botão "Excluir" funciona com confirmação
- [ ] Sidebar com informações aparece
- [ ] Botão "Ver Conversas" funciona
- [ ] Contador de mensagens aparece

## Kanban (/dashboard/kanban)

- [ ] Board renderiza com todas as colunas
- [ ] Colunas aparecem na ordem correta
- [ ] Leads aparecem nos cards
- [ ] Drag and drop funciona (arrastar cards)
- [ ] Cards mudam de coluna ao soltar
- [ ] Contador de leads por coluna funciona
- [ ] Cores das colunas aparecem
- [ ] Botão "Novo Lead" funciona
- [ ] Empty state aparece em colunas vazias
- [ ] Informações do lead aparecem no card

## Conversas

### Lista (/dashboard/conversations)
- [ ] Grid de conversas renderiza
- [ ] Filtros funcionam (Todas, Ativas, IA, Humano)
- [ ] Campo de busca funciona
- [ ] Cards de conversas são clicáveis
- [ ] Status IA/Humano aparece
- [ ] Badge de mensagens não lidas aparece
- [ ] Data da última mensagem aparece
- [ ] Empty state funciona

### Chat (/dashboard/conversations/[id])
- [ ] Chat carrega com mensagens
- [ ] Mensagens aparecem na ordem correta
- [ ] Diferenciação visual entre inbound/outbound
- [ ] Campo de input funciona
- [ ] Botão de enviar funciona
- [ ] Toggle IA/Humano funciona
- [ ] Auto-scroll para última mensagem
- [ ] Sidebar com info do lead aparece
- [ ] Horário das mensagens aparece
- [ ] Link para detalhes do lead funciona

## Notificações (/dashboard/notifications)

- [ ] Lista de notificações renderiza
- [ ] Filtros funcionam (Todas, Não lidas)
- [ ] Contador de não lidas funciona
- [ ] Botão "Marcar todas como lidas" funciona
- [ ] Ícones corretos por tipo de notificação
- [ ] Cores por tipo funcionam
- [ ] Botão individual de marcar como lida funciona
- [ ] Botão de excluir funciona
- [ ] Links para recursos funcionam
- [ ] Empty state aparece

## Configurações

### Geral (/dashboard/settings)
- [ ] Formulário carrega com dados da empresa
- [ ] Tabs de navegação funcionam
- [ ] Todos os campos editáveis
- [ ] Botão "Salvar" funciona
- [ ] Botão "Cancelar" reverte mudanças
- [ ] Mensagem de sucesso aparece
- [ ] Validações funcionam
- [ ] Campos obrigatórios marcados

### IA (/dashboard/settings/ia)
- [ ] Formulário carrega
- [ ] Tabs de navegação funcionam
- [ ] Campo nome do assistente funciona
- [ ] Dropdown de tom de voz funciona
- [ ] Checkbox de emojis funciona
- [ ] Preview atualiza em tempo real
- [ ] Botão "Salvar" funciona
- [ ] Preview mostra mensagem correta

### WhatsApp (/dashboard/settings/whatsapp)
- [ ] Formulário carrega
- [ ] Tabs de navegação funcionam
- [ ] Status de conexão aparece
- [ ] Campos de instância e token funcionam
- [ ] Campo de número funciona
- [ ] Botão "Salvar" funciona
- [ ] Botão "Testar Conexão" aparece quando conectado
- [ ] Info box com instruções aparece

## Flow Builder (/dashboard/flow-builder)

- [ ] Página carrega (se já estava implementada)
- [ ] React Flow renderiza
- [ ] Ferramentas de edição funcionam

## Responsividade

### Mobile (< 768px)
- [ ] Sidebar vira hamburger menu
- [ ] Overlay funciona
- [ ] Tabelas têm scroll horizontal
- [ ] Cards empilham verticalmente
- [ ] Formulários são usáveis
- [ ] Botões têm tamanho adequado

### Tablet (768px - 1024px)
- [ ] Layout adapta corretamente
- [ ] Grids ajustam colunas
- [ ] Sidebar visível ou escondível

### Desktop (> 1024px)
- [ ] Sidebar sempre visível
- [ ] Grids com múltiplas colunas
- [ ] Espaçamento adequado

## Performance

- [ ] Páginas carregam em < 3 segundos
- [ ] Sem erros no console
- [ ] Sem warnings de React
- [ ] Loading states aparecem durante carregamento
- [ ] Não há memory leaks visíveis
- [ ] Navegação é fluida

## Acessibilidade

- [ ] Todos os inputs têm labels
- [ ] Botões têm texto ou aria-label
- [ ] Navegação por teclado funciona
- [ ] Contraste de cores adequado
- [ ] Focus states visíveis
- [ ] Imagens têm alt text

## Integrações

### Supabase Auth
- [ ] Login funciona
- [ ] Logout funciona
- [ ] Sessão persiste ao recarregar
- [ ] Redirecionamento automático funciona
- [ ] Recuperação de senha funciona

### API Backend
- [ ] GET requests funcionam
- [ ] POST requests funcionam
- [ ] PATCH requests funcionam
- [ ] DELETE requests funcionam
- [ ] Tratamento de erros funciona
- [ ] Loading states aparecem

## Bugs Conhecidos a Verificar

- [ ] Não há loops infinitos de renderização
- [ ] Estados não conflitam entre páginas
- [ ] Formulários limpam ao navegar
- [ ] Confirmações aparecem antes de excluir
- [ ] Mensagens de erro são claras

## Testes Finais

### Fluxo Completo de Usuário
1. [ ] Usuário consegue fazer cadastro
2. [ ] Usuário consegue fazer login
3. [ ] Usuário vê dashboard com dados
4. [ ] Usuário cria um novo lead
5. [ ] Usuário edita o lead
6. [ ] Usuário move lead no kanban
7. [ ] Usuário vê e envia mensagens no chat
8. [ ] Usuário atualiza configurações
9. [ ] Usuário faz logout

### Edge Cases
- [ ] Sistema funciona sem leads
- [ ] Sistema funciona sem conversas
- [ ] Sistema funciona sem notificações
- [ ] Campos vazios são tratados
- [ ] Formulários validam dados inválidos
- [ ] API offline mostra erro apropriado

## Documentação

- [ ] FRONTEND_IMPLEMENTATION.md está atualizado
- [ ] QUICK_START.md está completo
- [ ] Tipos TypeScript estão documentados
- [ ] Comentários úteis no código

## Deploy (Opcional)

- [ ] Build de produção funciona (`npm run build`)
- [ ] Não há erros de build
- [ ] Variáveis de ambiente de produção configuradas
- [ ] App funciona em produção

---

## Notas

- Marque cada item conforme for testando
- Anote bugs encontrados abaixo
- Priorize correções antes do deploy

## Bugs Encontrados

```
1. [DATA] [PÁGINA] - Descrição do bug
   - Passos para reproduzir
   - Comportamento esperado
   - Comportamento atual

2. [DATA] [PÁGINA] - Descrição do bug
   ...
```

## Melhorias Sugeridas

```
1. [PÁGINA/COMPONENTE] - Descrição da melhoria
   - Benefício
   - Prioridade (Alta/Média/Baixa)

2. [PÁGINA/COMPONENTE] - Descrição da melhoria
   ...
```
