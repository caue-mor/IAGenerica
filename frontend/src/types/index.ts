// Company types
export interface Company {
  id: number;
  empresa: string;
  nome_empresa?: string;
  email: string;
  cidade?: string;
  site?: string;
  horario_funcionamento?: string;
  uazapi_instancia?: string;
  uazapi_token?: string;
  whatsapp_numero?: string;
  agent_name: string;
  agent_tone: string;
  use_emojis: boolean;
  informacoes_complementares?: string;
  flow_config?: FlowConfig;
  created_at: string;
  updated_at: string;
}

export interface CompanyCreate {
  empresa: string;
  nome_empresa?: string;
  email: string;
  cidade?: string;
  site?: string;
  horario_funcionamento?: string;
  uazapi_instancia?: string;
  uazapi_token?: string;
  whatsapp_numero?: string;
  agent_name?: string;
  agent_tone?: string;
  use_emojis?: boolean;
  informacoes_complementares?: string;
}

// Lead types
export interface LeadStatus {
  id: number;
  company_id: number;
  nome: string;
  cor: string;
  ordem: number;
  is_default: boolean;
  created_at: string;
}

export interface Lead {
  id: number;
  company_id: number;
  status_id?: number;
  nome?: string;
  celular: string;
  email?: string;
  dados_coletados: Record<string, any>;
  ai_enabled: boolean;
  origem?: string;
  created_at: string;
  updated_at: string;
}

export interface LeadCreate {
  company_id: number;
  nome?: string;
  celular: string;
  email?: string;
  origem?: string;
}

// Conversation types
export interface Conversation {
  id: number;
  company_id: number;
  lead_id: number;
  thread_id: string;
  status: string;
  ai_enabled: boolean;
  current_node_id?: string;
  context: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  lead_id: number;
  direction: 'inbound' | 'outbound';
  message_type: string;
  content?: string;
  media_url?: string;
  status: string;
  uazapi_message_id?: string;
  created_at: string;
}

// Flow types
export type NodeType =
  | 'GREETING'
  | 'QUESTION'
  | 'CONDITION'
  | 'MESSAGE'
  | 'ACTION'
  | 'HANDOFF'
  | 'FOLLOWUP';

export type FieldType = 'text' | 'number' | 'email' | 'phone' | 'date' | 'select' | 'boolean';

export type Operator =
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'not_contains'
  | 'greater_than'
  | 'less_than'
  | 'is_empty'
  | 'is_not_empty'
  | 'exists';

export type ActionType = 'webhook' | 'api_call' | 'update_field' | 'tag_lead' | 'move_status';

export interface NodeConfig {
  // GREETING / MESSAGE
  mensagem?: string;

  // QUESTION
  pergunta?: string;
  campo_destino?: string;
  tipo_campo?: FieldType;
  opcoes?: string[];
  validacao?: string;

  // CONDITION
  campo?: string;
  operador?: Operator;
  valor?: any;

  // ACTION
  tipo_acao?: ActionType;
  url?: string;
  method?: string;
  headers?: Record<string, string>;
  body?: Record<string, any>;
  novo_status_id?: number;
  tags?: string[];

  // HANDOFF
  motivo?: string;
  mensagem_cliente?: string;
  notificar_equipe?: boolean;

  // FOLLOWUP
  intervalos?: number[];
  mensagens?: string[];
}

export interface FlowNode {
  id: string;
  type: NodeType;
  name: string;
  config: NodeConfig;
  next_node_id?: string;
  true_node_id?: string;
  false_node_id?: string;
  position?: { x: number; y: number };
}

export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface FlowConfig {
  nodes: FlowNode[];
  edges: FlowEdge[];
  start_node_id: string;
  version: string;
}

// API Response types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
}
