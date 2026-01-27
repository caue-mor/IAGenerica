'use client';

import { useState, useCallback, useEffect } from 'react';
import Link from 'next/link';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { ArrowLeft, Save, Plus, Hand, HelpCircle, GitBranch, MessageSquare, Zap, UserPlus, Clock } from 'lucide-react';
import { apiGet, apiPut } from '@/lib/supabase';
import { FlowConfig, FlowNode as FlowNodeType, NodeType } from '@/types';
import { NODE_TYPES, flowNodeToReactFlow, flowEdgeToReactFlow, reactFlowToFlowConfig } from '@/types/flow.types';
import { generateId } from '@/lib/utils';

// Temporary company ID
const COMPANY_ID = 1;

const nodeIcons: Record<NodeType, any> = {
  GREETING: Hand,
  QUESTION: HelpCircle,
  CONDITION: GitBranch,
  MESSAGE: MessageSquare,
  ACTION: Zap,
  HANDOFF: UserPlus,
  FOLLOWUP: Clock,
};

// Custom Node Component
function CustomNode({ data }: { data: any }) {
  const nodeConfig = NODE_TYPES.find(n => n.type === data.type);
  const Icon = nodeIcons[data.type as NodeType] || MessageSquare;

  return (
    <div
      className="px-4 py-3 rounded-lg shadow-md border-2 bg-white min-w-[180px]"
      style={{ borderColor: nodeConfig?.color || '#6B7280' }}
    >
      <div className="flex items-center gap-2">
        <div
          className="p-1.5 rounded"
          style={{ backgroundColor: `${nodeConfig?.color}20` }}
        >
          <Icon className="w-4 h-4" style={{ color: nodeConfig?.color }} />
        </div>
        <div>
          <div className="text-sm font-medium text-gray-900">{data.label}</div>
          <div className="text-xs text-gray-500">{nodeConfig?.label}</div>
        </div>
      </div>
      {data.config?.mensagem && (
        <div className="mt-2 text-xs text-gray-600 truncate max-w-[200px]">
          {data.config.mensagem}
        </div>
      )}
      {data.config?.pergunta && (
        <div className="mt-2 text-xs text-gray-600 truncate max-w-[200px]">
          {data.config.pergunta}
        </div>
      )}
    </div>
  );
}

const nodeTypes = {
  customNode: CustomNode,
};

export default function FlowBuilderPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [startNodeId, setStartNodeId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadFlowConfig();
  }, []);

  async function loadFlowConfig() {
    try {
      setLoading(true);
      const response = await apiGet<{ flow_config: FlowConfig | null }>(
        `/api/companies/${COMPANY_ID}/flow`
      );

      if (response.flow_config) {
        const flowNodes = response.flow_config.nodes.map(flowNodeToReactFlow);
        const flowEdges = response.flow_config.edges.map(flowEdgeToReactFlow);
        setNodes(flowNodes);
        setEdges(flowEdges);
        setStartNodeId(response.flow_config.start_node_id);
      } else {
        // Create default flow
        createDefaultFlow();
      }
    } catch (error) {
      console.error('Error loading flow:', error);
      createDefaultFlow();
    } finally {
      setLoading(false);
    }
  }

  function createDefaultFlow() {
    const greetingId = generateId();
    const questionId = generateId();

    setNodes([
      {
        id: greetingId,
        type: 'customNode',
        position: { x: 250, y: 50 },
        data: {
          label: 'Boas-vindas',
          type: 'GREETING',
          config: {
            mensagem: 'Ola! Seja bem-vindo. Como posso ajudar?'
          }
        }
      },
      {
        id: questionId,
        type: 'customNode',
        position: { x: 250, y: 200 },
        data: {
          label: 'Perguntar Nome',
          type: 'QUESTION',
          config: {
            pergunta: 'Qual e o seu nome?',
            campo_destino: 'nome',
            tipo_campo: 'text'
          }
        }
      }
    ]);

    setEdges([
      {
        id: `e-${greetingId}-${questionId}`,
        source: greetingId,
        target: questionId,
        type: 'smoothstep',
        animated: true
      }
    ]);

    setStartNodeId(greetingId);
  }

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({
        ...connection,
        type: 'smoothstep',
        animated: true
      }, eds));
    },
    [setEdges]
  );

  async function saveFlow() {
    if (!startNodeId) {
      alert('Por favor, defina o no inicial do fluxo.');
      return;
    }

    try {
      setSaving(true);
      const flowConfig = reactFlowToFlowConfig(nodes, edges, startNodeId);
      await apiPut(`/api/companies/${COMPANY_ID}/flow`, flowConfig);
      alert('Fluxo salvo com sucesso!');
    } catch (error) {
      console.error('Error saving flow:', error);
      alert('Erro ao salvar fluxo.');
    } finally {
      setSaving(false);
    }
  }

  function addNode(type: NodeType) {
    const nodeConfig = NODE_TYPES.find(n => n.type === type);
    if (!nodeConfig) return;

    const newNode: Node = {
      id: generateId(),
      type: 'customNode',
      position: { x: Math.random() * 300 + 100, y: Math.random() * 300 + 100 },
      data: {
        label: nodeConfig.label,
        type: type,
        config: { ...nodeConfig.defaultConfig }
      }
    };

    setNodes((nds) => [...nds, newNode]);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Carregando fluxo...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm border-b flex-shrink-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-gray-500 hover:text-gray-700">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Flow Builder</h1>
                <p className="text-gray-500 text-sm">Configure o fluxo de atendimento</p>
              </div>
            </div>
            <button
              onClick={saveFlow}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Sidebar - Node Types */}
        <div className="w-64 bg-white border-r p-4 overflow-y-auto">
          <h3 className="font-medium text-gray-900 mb-4">Adicionar No</h3>
          <div className="space-y-2">
            {NODE_TYPES.map(nodeType => {
              const Icon = nodeIcons[nodeType.type];
              return (
                <button
                  key={nodeType.type}
                  onClick={() => addNode(nodeType.type)}
                  className="w-full flex items-center gap-3 p-3 rounded-lg border hover:bg-gray-50 text-left"
                >
                  <div
                    className="p-2 rounded"
                    style={{ backgroundColor: `${nodeType.color}20` }}
                  >
                    <Icon className="w-4 h-4" style={{ color: nodeType.color }} />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {nodeType.label}
                    </div>
                    <div className="text-xs text-gray-500">
                      {nodeType.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            snapToGrid
            snapGrid={[15, 15]}
          >
            <Controls />
            <MiniMap />
            <Background gap={15} size={1} />
            <Panel position="top-right" className="bg-white p-2 rounded shadow-sm border text-xs text-gray-500">
              Arraste para conectar nos | Clique para selecionar
            </Panel>
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}
