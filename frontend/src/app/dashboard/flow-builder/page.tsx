'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
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
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { ArrowLeft, Save, Settings, Undo, Redo } from 'lucide-react';
import { apiGet, apiPut } from '@/lib/supabase';
import { FlowConfig, FlowNode as FlowNodeType, FlowEdge as FlowEdgeType } from '@/types';
import { nodeTypes, FlowNodeData } from '@/components/flow-builder/nodes';
import { FlowSidebar, getNodeDefinition, NODE_DEFINITIONS } from '@/components/flow-builder/FlowSidebar';
import { NodeEditorPanel } from '@/components/flow-builder/NodeEditorPanel';

// Company ID (temporary - should come from auth)
const COMPANY_ID = 1;

// Custom flow node type
type CustomFlowNode = Node<FlowNodeData>;
type CustomFlowEdge = Edge;

// Generate unique ID
let nodeIdCounter = 0;
function generateNodeId(): string {
  return `node-${Date.now()}-${nodeIdCounter++}`;
}

// Main FlowBuilder component
function FlowBuilderContent() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();

  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [startNodeId, setStartNodeId] = useState<string>('');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Get selected node
  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

  // Load flow config on mount
  useEffect(() => {
    loadFlowConfig();
  }, []);

  async function loadFlowConfig() {
    try {
      setLoading(true);
      const response = await apiGet<{ flow_config: FlowConfig | null }>(
        `/api/companies/${COMPANY_ID}/flow`
      );

      if (response.flow_config && response.flow_config.nodes?.length > 0) {
        // Convert FlowConfig to ReactFlow format
        const flowNodes: CustomFlowNode[] = response.flow_config.nodes.map((node) => ({
          id: node.id,
          type: node.type.toUpperCase(),
          position: node.position || { x: 0, y: 0 },
          data: {
            label: node.name,
            type: node.type.toUpperCase(),
            config: node.config || {},
          },
        }));

        const flowEdges: CustomFlowEdge[] = response.flow_config.edges.map((edge) => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.label === 'true' || edge.label === 'sim' ? 'true' :
                       edge.label === 'false' || edge.label === 'nao' ? 'false' : undefined,
          label: edge.label,
          type: 'smoothstep',
          animated: true,
          style: { strokeWidth: 2 },
        }));

        setNodes(flowNodes);
        setEdges(flowEdges);
        setStartNodeId(response.flow_config.start_node_id);
      } else {
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
    const greetingId = generateNodeId();
    const questionId = generateNodeId();

    const defaultNodes: CustomFlowNode[] = [
      {
        id: greetingId,
        type: 'GREETING',
        position: { x: 250, y: 50 },
        data: {
          label: 'Boas-vindas',
          type: 'GREETING',
          config: {
            mensagem: 'Olá! Seja bem-vindo. Como posso ajudar?',
          },
        },
      },
      {
        id: questionId,
        type: 'NOME',
        position: { x: 250, y: 200 },
        data: {
          label: 'Perguntar Nome',
          type: 'NOME',
          config: {
            pergunta: 'Qual é o seu nome?',
            campo_destino: 'nome',
            tipo_campo: 'text',
          },
        },
      },
    ];

    const defaultEdges: CustomFlowEdge[] = [
      {
        id: `edge-${greetingId}-${questionId}`,
        source: greetingId,
        target: questionId,
        type: 'smoothstep',
        animated: true,
        style: { strokeWidth: 2 },
      },
    ];

    setNodes(defaultNodes);
    setEdges(defaultEdges);
    setStartNodeId(greetingId);
    setHasChanges(true);
  }

  // Handle edge connection
  const onConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return;

      const newEdge: CustomFlowEdge = {
        id: `edge-${connection.source}-${connection.sourceHandle || ''}-${connection.target}`,
        source: connection.source,
        target: connection.target,
        sourceHandle: connection.sourceHandle,
        targetHandle: connection.targetHandle,
        type: 'smoothstep',
        animated: true,
        style: { strokeWidth: 2 },
        // Set label based on handle
        label: connection.sourceHandle === 'true' ? 'Sim' :
               connection.sourceHandle === 'false' ? 'Não' : undefined,
      };
      setEdges((eds) => addEdge(newEdge, eds));
      setHasChanges(true);
    },
    [setEdges]
  );

  // Handle node click - open editor
  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

  // Handle pane click - close editor
  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  // Update node data
  const updateNodeData = useCallback(
    (nodeId: string, data: Partial<FlowNodeData>) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === nodeId
            ? { ...node, data: { ...node.data, ...data } }
            : node
        )
      );
      setHasChanges(true);
    },
    [setNodes]
  );

  // Delete node
  const deleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((node) => node.id !== nodeId));
      setEdges((eds) =>
        eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId)
      );
      setSelectedNodeId(null);
      setHasChanges(true);
    },
    [setNodes, setEdges]
  );

  // Handle nodes delete (keyboard delete)
  const onNodesDelete = useCallback(
    (deleted: Node[]) => {
      setEdges((eds) =>
        eds.filter(
          (edge) =>
            !deleted.some(
              (node) => node.id === edge.source || node.id === edge.target
            )
        )
      );
      setHasChanges(true);
    },
    [setEdges]
  );

  // Add node from sidebar
  const addNode = useCallback(
    (type: string, defaultConfig: Record<string, any>) => {
      const nodeDef = getNodeDefinition(type);
      if (!nodeDef) return;

      const newNode: CustomFlowNode = {
        id: generateNodeId(),
        type: type.toUpperCase(),
        position: { x: Math.random() * 300 + 100, y: Math.random() * 300 + 100 },
        data: {
          label: nodeDef.label,
          type: type.toUpperCase(),
          config: { ...defaultConfig },
        },
      };

      setNodes((nds) => [...nds, newNode]);
      setHasChanges(true);

      // Set as start node if it's the first greeting
      if (type.toUpperCase() === 'GREETING' && !startNodeId) {
        setStartNodeId(newNode.id);
      }
    },
    [setNodes, startNodeId]
  );

  // Handle drop from sidebar
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow-type');
      const configStr = event.dataTransfer.getData('application/reactflow-config');

      if (!type) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const nodeDef = getNodeDefinition(type);
      if (!nodeDef) return;

      const defaultConfig = configStr ? JSON.parse(configStr) : nodeDef.defaultConfig;

      const newNode: CustomFlowNode = {
        id: generateNodeId(),
        type: type.toUpperCase(),
        position,
        data: {
          label: nodeDef.label,
          type: type.toUpperCase(),
          config: { ...defaultConfig },
        },
      };

      setNodes((nds) => [...nds, newNode]);
      setHasChanges(true);

      // Set as start node if it's the first greeting
      if (type.toUpperCase() === 'GREETING' && !startNodeId) {
        setStartNodeId(newNode.id);
      }
    },
    [screenToFlowPosition, setNodes, startNodeId]
  );

  // Save flow
  async function saveFlow() {
    // Determine start node
    let finalStartNodeId = startNodeId;
    if (!finalStartNodeId) {
      // Find first GREETING node or first node
      const greetingNode = nodes.find((n) => n.data.type === 'GREETING');
      finalStartNodeId = greetingNode?.id || nodes[0]?.id;
    }

    if (!finalStartNodeId) {
      alert('Por favor, adicione pelo menos um nó ao fluxo.');
      return;
    }

    try {
      setSaving(true);

      // Convert ReactFlow to FlowConfig
      const flowConfig: FlowConfig = {
        nodes: nodes.map((node) => {
          // Find outgoing edges
          const outgoingEdges = edges.filter((e) => e.source === node.id);
          const nextEdge = outgoingEdges.find((e) => !e.sourceHandle);
          const trueEdge = outgoingEdges.find((e) => e.sourceHandle === 'true');
          const falseEdge = outgoingEdges.find((e) => e.sourceHandle === 'false');

          return {
            id: node.id,
            type: node.data.type,
            name: node.data.label,
            config: node.data.config,
            next_node_id: nextEdge?.target,
            true_node_id: trueEdge?.target,
            false_node_id: falseEdge?.target,
            position: node.position,
          };
        }),
        edges: edges.map((edge) => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.label as string | undefined,
        })),
        start_node_id: finalStartNodeId,
        version: '1.0',
      };

      await apiPut(`/api/companies/${COMPANY_ID}/flow`, flowConfig);
      setHasChanges(false);
      alert('Fluxo salvo com sucesso!');
    } catch (error) {
      console.error('Error saving flow:', error);
      alert('Erro ao salvar fluxo. Verifique o console.');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-500">Carregando fluxo...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="z-10 flex-shrink-0 border-b bg-white shadow-sm">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-lg font-bold text-gray-900">Flow Builder</h1>
              <p className="text-sm text-gray-500">Configure o fluxo de atendimento</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {hasChanges && (
              <span className="rounded-full bg-amber-100 px-2 py-1 text-xs text-amber-700">
                Alterações não salvas
              </span>
            )}
            <button
              onClick={saveFlow}
              disabled={saving}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-blue-400"
            >
              <Save className="h-4 w-4" />
              {saving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <FlowSidebar onAddNode={addNode} />

        {/* Canvas */}
        <div className="flex-1" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onNodesDelete={onNodesDelete}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            fitView
            snapToGrid
            snapGrid={[15, 15]}
            deleteKeyCode={['Backspace', 'Delete']}
            defaultEdgeOptions={{
              type: 'smoothstep',
              animated: true,
              style: { strokeWidth: 2 },
            }}
          >
            <Controls />
            <MiniMap
              nodeColor={(node) => {
                const def = NODE_DEFINITIONS.find(
                  (d) => d.type === node.data?.type
                );
                return def?.color || '#6B7280';
              }}
            />
            <Background gap={15} size={1} />
            <Panel
              position="top-right"
              className="rounded-lg border bg-white px-3 py-2 text-xs text-gray-500 shadow-sm"
            >
              Arraste para conectar nós | Delete para remover | Clique para editar
            </Panel>
          </ReactFlow>
        </div>

        {/* Editor Panel */}
        {selectedNode && (
          <NodeEditorPanel
            node={selectedNode}
            onUpdate={updateNodeData}
            onDelete={deleteNode}
            onClose={() => setSelectedNodeId(null)}
          />
        )}
      </div>
    </div>
  );
}

// Wrap with ReactFlowProvider
export default function FlowBuilderPage() {
  return (
    <ReactFlowProvider>
      <FlowBuilderContent />
    </ReactFlowProvider>
  );
}
