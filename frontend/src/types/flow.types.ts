import { Node, Edge } from 'reactflow';
import { NodeType, NodeConfig, FlowNode, FlowEdge, FlowConfig } from './index';

// React Flow node data
export interface FlowNodeData {
  label: string;
  type: NodeType;
  config: NodeConfig;
}

// Extended React Flow types
export type CustomNode = Node<FlowNodeData>;
export type CustomEdge = Edge;

// Node type configurations for the builder
export interface NodeTypeConfig {
  type: NodeType;
  label: string;
  icon: string;
  color: string;
  description: string;
  defaultConfig: Partial<NodeConfig>;
}

export const NODE_TYPES: NodeTypeConfig[] = [
  {
    type: 'GREETING',
    label: 'Saudacao',
    icon: 'Hand',
    color: '#10B981',
    description: 'Mensagem de boas-vindas',
    defaultConfig: {
      mensagem: 'Ola! Seja bem-vindo. Como posso ajudar?'
    }
  },
  {
    type: 'QUESTION',
    label: 'Pergunta',
    icon: 'HelpCircle',
    color: '#3B82F6',
    description: 'Coleta informacao do cliente',
    defaultConfig: {
      pergunta: 'Qual e o seu nome?',
      campo_destino: 'nome',
      tipo_campo: 'text'
    }
  },
  {
    type: 'CONDITION',
    label: 'Condicao',
    icon: 'GitBranch',
    color: '#F59E0B',
    description: 'Decisao baseada em dados',
    defaultConfig: {
      operador: 'equals'
    }
  },
  {
    type: 'MESSAGE',
    label: 'Mensagem',
    icon: 'MessageSquare',
    color: '#8B5CF6',
    description: 'Envia mensagem informativa',
    defaultConfig: {
      mensagem: ''
    }
  },
  {
    type: 'ACTION',
    label: 'Acao',
    icon: 'Zap',
    color: '#EC4899',
    description: 'Executa webhook ou API',
    defaultConfig: {
      tipo_acao: 'webhook',
      method: 'POST'
    }
  },
  {
    type: 'HANDOFF',
    label: 'Transferir',
    icon: 'UserPlus',
    color: '#EF4444',
    description: 'Transfere para humano',
    defaultConfig: {
      mensagem_cliente: 'Vou transferir voce para um de nossos atendentes.',
      notificar_equipe: true
    }
  },
  {
    type: 'FOLLOWUP',
    label: 'Follow-up',
    icon: 'Clock',
    color: '#6B7280',
    description: 'Agenda mensagens futuras',
    defaultConfig: {
      intervalos: [1440], // 24 hours in minutes
      mensagens: ['Ola! Tudo bem? Conseguiu resolver sua duvida?']
    }
  }
];

// Helper functions
export function flowNodeToReactFlow(node: FlowNode): CustomNode {
  return {
    id: node.id,
    type: 'customNode',
    position: node.position || { x: 0, y: 0 },
    data: {
      label: node.name,
      type: node.type,
      config: node.config
    }
  };
}

export function flowEdgeToReactFlow(edge: FlowEdge): CustomEdge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label,
    type: 'smoothstep',
    animated: true
  };
}

export function reactFlowToFlowConfig(
  nodes: CustomNode[],
  edges: CustomEdge[],
  startNodeId: string
): FlowConfig {
  const flowNodes: FlowNode[] = nodes.map(node => {
    const outgoingEdges = edges.filter(e => e.source === node.id);
    const nextEdge = outgoingEdges.find(e => !e.label || e.label === 'default');
    const trueEdge = outgoingEdges.find(e => e.label === 'true' || e.label === 'sim');
    const falseEdge = outgoingEdges.find(e => e.label === 'false' || e.label === 'nao');

    return {
      id: node.id,
      type: node.data.type,
      name: node.data.label,
      config: node.data.config,
      next_node_id: nextEdge?.target,
      true_node_id: trueEdge?.target,
      false_node_id: falseEdge?.target,
      position: node.position
    };
  });

  const flowEdges: FlowEdge[] = edges.map(edge => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label as string | undefined
  }));

  return {
    nodes: flowNodes,
    edges: flowEdges,
    start_node_id: startNodeId,
    version: '1.0'
  };
}

export function getNodeTypeConfig(type: NodeType): NodeTypeConfig | undefined {
  return NODE_TYPES.find(n => n.type === type);
}
