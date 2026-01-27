'use client';

import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { BaseNode } from './BaseNode';
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
} from 'lucide-react';

// Node data interface
export interface FlowNodeData {
  label: string;
  type: string;
  config: {
    mensagem?: string;
    pergunta?: string;
    campo_destino?: string;
    tipo_campo?: string;
    opcoes?: string[];
    campo?: string;
    operador?: string;
    valor?: any;
    motivo?: string;
    mensagem_cliente?: string;
    notificar_equipe?: boolean;
    intervalos?: number[];
    mensagens?: string[];
    tipo_acao?: string;
    url?: string;
    method?: string;
    // Audio/TTS settings (ElevenLabs)
    response_type?: 'text' | 'audio' | 'both';
    voice_id?: string;
    voice_stability?: number;
    voice_similarity?: number;
    custom_voice?: boolean;
  };
}

// ==================== GREETING NODE ====================
export const GreetingNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Saudação'}
      icon={Hand}
      color="#10B981"
      selected={selected}
      hasInput={false}
    >
      {data.config?.mensagem && (
        <p className="line-clamp-3">{data.config.mensagem}</p>
      )}
    </BaseNode>
  );
});
GreetingNode.displayName = 'GreetingNode';

// ==================== QUESTION NODE ====================
export const QuestionNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Pergunta'}
      icon={HelpCircle}
      color="#3B82F6"
      selected={selected}
    >
      {data.config?.pergunta && (
        <p className="line-clamp-2">{data.config.pergunta}</p>
      )}
      {data.config?.campo_destino && (
        <p className="mt-1 text-[10px] text-gray-400">
          → {data.config.campo_destino}
        </p>
      )}
    </BaseNode>
  );
});
QuestionNode.displayName = 'QuestionNode';

// ==================== CONDITION NODE ====================
export const ConditionNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Condição'}
      icon={GitBranch}
      color="#F59E0B"
      selected={selected}
      hasConditionalOutputs={true}
    >
      {data.config?.campo && data.config?.operador && (
        <p className="text-center font-mono text-[11px]">
          {data.config.campo} {data.config.operador} {String(data.config.valor || '')}
        </p>
      )}
    </BaseNode>
  );
});
ConditionNode.displayName = 'ConditionNode';

// ==================== MESSAGE NODE ====================
export const MessageNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Mensagem'}
      icon={MessageSquare}
      color="#8B5CF6"
      selected={selected}
    >
      {data.config?.mensagem && (
        <p className="line-clamp-3">{data.config.mensagem}</p>
      )}
    </BaseNode>
  );
});
MessageNode.displayName = 'MessageNode';

// ==================== ACTION NODE ====================
export const ActionNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Ação'}
      icon={Zap}
      color="#EC4899"
      selected={selected}
    >
      {data.config?.tipo_acao && (
        <p className="font-medium">{data.config.tipo_acao}</p>
      )}
      {data.config?.url && (
        <p className="truncate text-[10px] text-gray-400">{data.config.url}</p>
      )}
    </BaseNode>
  );
});
ActionNode.displayName = 'ActionNode';

// ==================== HANDOFF NODE ====================
export const HandoffNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Transferir'}
      icon={UserPlus}
      color="#EF4444"
      selected={selected}
      hasOutput={false}
    >
      {data.config?.mensagem_cliente && (
        <p className="line-clamp-2">{data.config.mensagem_cliente}</p>
      )}
      {data.config?.motivo && (
        <p className="mt-1 text-[10px] text-gray-400">
          Motivo: {data.config.motivo}
        </p>
      )}
    </BaseNode>
  );
});
HandoffNode.displayName = 'HandoffNode';

// ==================== FOLLOWUP NODE ====================
export const FollowupNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Follow-up'}
      icon={Clock}
      color="#6B7280"
      selected={selected}
    >
      {data.config?.intervalos && (
        <p className="text-[10px]">
          {data.config.intervalos.length} follow-up(s) configurado(s)
        </p>
      )}
    </BaseNode>
  );
});
FollowupNode.displayName = 'FollowupNode';

// ==================== NOME NODE (reuses Question style) ====================
export const NomeNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Coletar Nome'}
      icon={User}
      color="#06B6D4"
      selected={selected}
    >
      {data.config?.pergunta && (
        <p className="line-clamp-2">{data.config.pergunta}</p>
      )}
    </BaseNode>
  );
});
NomeNode.displayName = 'NomeNode';

// ==================== EMAIL NODE ====================
export const EmailNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Coletar Email'}
      icon={Mail}
      color="#0EA5E9"
      selected={selected}
    >
      {data.config?.pergunta && (
        <p className="line-clamp-2">{data.config.pergunta}</p>
      )}
    </BaseNode>
  );
});
EmailNode.displayName = 'EmailNode';

// ==================== TELEFONE NODE ====================
export const TelefoneNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Coletar Telefone'}
      icon={Phone}
      color="#14B8A6"
      selected={selected}
    >
      {data.config?.pergunta && (
        <p className="line-clamp-2">{data.config.pergunta}</p>
      )}
    </BaseNode>
  );
});
TelefoneNode.displayName = 'TelefoneNode';

// ==================== CIDADE NODE ====================
export const CidadeNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Coletar Cidade'}
      icon={MapPin}
      color="#F97316"
      selected={selected}
    >
      {data.config?.pergunta && (
        <p className="line-clamp-2">{data.config.pergunta}</p>
      )}
    </BaseNode>
  );
});
CidadeNode.displayName = 'CidadeNode';

// ==================== INTERESSE NODE ====================
export const InteresseNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Interesse'}
      icon={FileText}
      color="#A855F7"
      selected={selected}
    >
      {data.config?.pergunta && (
        <p className="line-clamp-2">{data.config.pergunta}</p>
      )}
    </BaseNode>
  );
});
InteresseNode.displayName = 'InteresseNode';

// ==================== ORCAMENTO NODE ====================
export const OrcamentoNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Orçamento'}
      icon={DollarSign}
      color="#22C55E"
      selected={selected}
    >
      {data.config?.pergunta && (
        <p className="line-clamp-2">{data.config.pergunta}</p>
      )}
    </BaseNode>
  );
});
OrcamentoNode.displayName = 'OrcamentoNode';

// ==================== URGENCIA NODE ====================
export const UrgenciaNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Urgência'}
      icon={AlertCircle}
      color="#EAB308"
      selected={selected}
    >
      {data.config?.pergunta && (
        <p className="line-clamp-2">{data.config.pergunta}</p>
      )}
    </BaseNode>
  );
});
UrgenciaNode.displayName = 'UrgenciaNode';

// ==================== AGENDAMENTO NODE ====================
export const AgendamentoNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Agendamento'}
      icon={Calendar}
      color="#7C3AED"
      selected={selected}
    >
      {data.config?.mensagem && (
        <p className="line-clamp-2">{data.config.mensagem}</p>
      )}
    </BaseNode>
  );
});
AgendamentoNode.displayName = 'AgendamentoNode';

// ==================== END NODE ====================
export const EndNode = memo(({ data, selected }: NodeProps<FlowNodeData>) => {
  return (
    <BaseNode
      label={data.label || 'Fim'}
      icon={CheckCircle}
      color="#64748B"
      selected={selected}
      hasOutput={false}
    >
      {data.config?.mensagem && (
        <p className="line-clamp-2">{data.config.mensagem}</p>
      )}
    </BaseNode>
  );
});
EndNode.displayName = 'EndNode';

// ==================== NODE TYPES MAPPING ====================
export const nodeTypes = {
  GREETING: GreetingNode,
  QUESTION: QuestionNode,
  CONDITION: ConditionNode,
  MESSAGE: MessageNode,
  ACTION: ActionNode,
  HANDOFF: HandoffNode,
  FOLLOWUP: FollowupNode,
  NOME: NomeNode,
  EMAIL: EmailNode,
  TELEFONE: TelefoneNode,
  CIDADE: CidadeNode,
  INTERESSE: InteresseNode,
  ORCAMENTO: OrcamentoNode,
  URGENCIA: UrgenciaNode,
  AGENDAMENTO: AgendamentoNode,
  END: EndNode,
  // Aliases for flexibility
  greeting: GreetingNode,
  question: QuestionNode,
  condition: ConditionNode,
  message: MessageNode,
  action: ActionNode,
  handoff: HandoffNode,
  followup: FollowupNode,
};
