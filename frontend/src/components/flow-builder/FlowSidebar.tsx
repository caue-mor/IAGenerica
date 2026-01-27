'use client';

import {
  Hand,
  HelpCircle,
  GitBranch,
  MessageSquare,
  Zap,
  UserPlus,
  Clock,
  Mail,
  Phone,
  MapPin,
  User,
  FileText,
  DollarSign,
  AlertCircle,
  Calendar,
  CheckCircle,
  LucideIcon,
} from 'lucide-react';

// Node category definition
interface NodeCategory {
  name: string;
  nodes: NodeDefinition[];
}

// Node definition
interface NodeDefinition {
  type: string;
  label: string;
  description: string;
  icon: LucideIcon;
  color: string;
  defaultConfig: Record<string, any>;
}

// All available node types
export const NODE_DEFINITIONS: NodeDefinition[] = [
  // Início
  {
    type: 'GREETING',
    label: 'Saudação',
    description: 'Mensagem de boas-vindas',
    icon: Hand,
    color: '#10B981',
    defaultConfig: {
      mensagem: 'Olá! Seja bem-vindo. Como posso ajudar?',
    },
  },
  // Coleta de Dados
  {
    type: 'QUESTION',
    label: 'Pergunta',
    description: 'Pergunta genérica',
    icon: HelpCircle,
    color: '#3B82F6',
    defaultConfig: {
      pergunta: '',
      campo_destino: '',
      tipo_campo: 'text',
    },
  },
  {
    type: 'NOME',
    label: 'Nome',
    description: 'Coletar nome do cliente',
    icon: User,
    color: '#06B6D4',
    defaultConfig: {
      pergunta: 'Qual é o seu nome?',
      campo_destino: 'nome',
      tipo_campo: 'text',
    },
  },
  {
    type: 'EMAIL',
    label: 'Email',
    description: 'Coletar email',
    icon: Mail,
    color: '#0EA5E9',
    defaultConfig: {
      pergunta: 'Qual é o seu email?',
      campo_destino: 'email',
      tipo_campo: 'email',
    },
  },
  {
    type: 'TELEFONE',
    label: 'Telefone',
    description: 'Coletar telefone',
    icon: Phone,
    color: '#14B8A6',
    defaultConfig: {
      pergunta: 'Qual é o seu telefone?',
      campo_destino: 'telefone',
      tipo_campo: 'phone',
    },
  },
  {
    type: 'CIDADE',
    label: 'Cidade',
    description: 'Coletar cidade',
    icon: MapPin,
    color: '#F97316',
    defaultConfig: {
      pergunta: 'Em qual cidade você está?',
      campo_destino: 'cidade',
      tipo_campo: 'text',
    },
  },
  {
    type: 'INTERESSE',
    label: 'Interesse',
    description: 'O que o cliente procura',
    icon: FileText,
    color: '#A855F7',
    defaultConfig: {
      pergunta: 'O que você está procurando?',
      campo_destino: 'interesse',
      tipo_campo: 'text',
    },
  },
  {
    type: 'ORCAMENTO',
    label: 'Orçamento',
    description: 'Coletar orçamento',
    icon: DollarSign,
    color: '#22C55E',
    defaultConfig: {
      pergunta: 'Qual o seu orçamento disponível?',
      campo_destino: 'orcamento',
      tipo_campo: 'select',
      opcoes: ['Até R$ 1.000', 'R$ 1.000 - R$ 5.000', 'R$ 5.000 - R$ 10.000', 'Acima de R$ 10.000'],
    },
  },
  {
    type: 'URGENCIA',
    label: 'Urgência',
    description: 'Nível de urgência',
    icon: AlertCircle,
    color: '#EAB308',
    defaultConfig: {
      pergunta: 'Qual a urgência?',
      campo_destino: 'urgencia',
      tipo_campo: 'select',
      opcoes: ['Imediata', 'Esta semana', 'Este mês', 'Apenas pesquisando'],
    },
  },
  // Decisão
  {
    type: 'CONDITION',
    label: 'Condição',
    description: 'Decisão baseada em dados',
    icon: GitBranch,
    color: '#F59E0B',
    defaultConfig: {
      campo: '',
      operador: 'equals',
      valor: '',
    },
  },
  // Mensagens
  {
    type: 'MESSAGE',
    label: 'Mensagem',
    description: 'Envia mensagem',
    icon: MessageSquare,
    color: '#8B5CF6',
    defaultConfig: {
      mensagem: '',
    },
  },
  // Ações
  {
    type: 'ACTION',
    label: 'Ação',
    description: 'Webhook ou API',
    icon: Zap,
    color: '#EC4899',
    defaultConfig: {
      tipo_acao: 'webhook',
      method: 'POST',
    },
  },
  {
    type: 'AGENDAMENTO',
    label: 'Agendamento',
    description: 'Agendar reunião/visita',
    icon: Calendar,
    color: '#7C3AED',
    defaultConfig: {
      mensagem: 'Vou agendar uma reunião para você.',
    },
  },
  // Fim
  {
    type: 'HANDOFF',
    label: 'Transferir',
    description: 'Transferir para humano',
    icon: UserPlus,
    color: '#EF4444',
    defaultConfig: {
      mensagem_cliente: 'Vou transferir você para um de nossos atendentes.',
      notificar_equipe: true,
    },
  },
  {
    type: 'FOLLOWUP',
    label: 'Follow-up',
    description: 'Mensagens futuras',
    icon: Clock,
    color: '#6B7280',
    defaultConfig: {
      intervalos: [1440],
      mensagens: ['Olá! Tudo bem? Conseguiu resolver sua dúvida?'],
    },
  },
  {
    type: 'END',
    label: 'Fim',
    description: 'Encerrar conversa',
    icon: CheckCircle,
    color: '#64748B',
    defaultConfig: {
      mensagem: 'Obrigado pelo contato! Até logo.',
    },
  },
];

// Group nodes by category
export const NODE_CATEGORIES: NodeCategory[] = [
  {
    name: 'Início',
    nodes: NODE_DEFINITIONS.filter((n) => n.type === 'GREETING'),
  },
  {
    name: 'Coleta de Dados',
    nodes: NODE_DEFINITIONS.filter((n) =>
      ['QUESTION', 'NOME', 'EMAIL', 'TELEFONE', 'CIDADE', 'INTERESSE', 'ORCAMENTO', 'URGENCIA'].includes(n.type)
    ),
  },
  {
    name: 'Decisão',
    nodes: NODE_DEFINITIONS.filter((n) => n.type === 'CONDITION'),
  },
  {
    name: 'Mensagens',
    nodes: NODE_DEFINITIONS.filter((n) => n.type === 'MESSAGE'),
  },
  {
    name: 'Ações',
    nodes: NODE_DEFINITIONS.filter((n) => ['ACTION', 'AGENDAMENTO'].includes(n.type)),
  },
  {
    name: 'Finalização',
    nodes: NODE_DEFINITIONS.filter((n) => ['HANDOFF', 'FOLLOWUP', 'END'].includes(n.type)),
  },
];

interface FlowSidebarProps {
  onAddNode: (type: string, config: Record<string, any>) => void;
}

export function FlowSidebar({ onAddNode }: FlowSidebarProps) {
  const onDragStart = (event: React.DragEvent, nodeType: string, defaultConfig: Record<string, any>) => {
    event.dataTransfer.setData('application/reactflow-type', nodeType);
    event.dataTransfer.setData('application/reactflow-config', JSON.stringify(defaultConfig));
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="h-full w-64 overflow-y-auto border-r bg-white p-4">
      <h3 className="mb-4 text-sm font-semibold text-gray-900">Adicionar Nó</h3>
      <p className="mb-4 text-xs text-gray-500">
        Arraste um nó para o canvas ou clique para adicionar
      </p>

      {NODE_CATEGORIES.map((category) => (
        <div key={category.name} className="mb-4">
          <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-400">
            {category.name}
          </h4>
          <div className="space-y-1">
            {category.nodes.map((node) => {
              const Icon = node.icon;
              return (
                <div
                  key={node.type}
                  draggable
                  onDragStart={(e) => onDragStart(e, node.type, node.defaultConfig)}
                  onClick={() => onAddNode(node.type, node.defaultConfig)}
                  className="flex cursor-grab items-center gap-3 rounded-lg border border-gray-200 bg-white p-2.5 transition-all hover:border-gray-300 hover:shadow-sm active:cursor-grabbing"
                >
                  <div
                    className="flex h-8 w-8 items-center justify-center rounded-lg"
                    style={{ backgroundColor: `${node.color}15` }}
                  >
                    <Icon className="h-4 w-4" style={{ color: node.color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{node.label}</p>
                    <p className="truncate text-xs text-gray-500">{node.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// Export node definition finder
export function getNodeDefinition(type: string): NodeDefinition | undefined {
  return NODE_DEFINITIONS.find((n) => n.type === type || n.type === type.toUpperCase());
}
