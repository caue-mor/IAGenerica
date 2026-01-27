'use client';

import { Node } from 'reactflow';
import { X, Trash2, Volume2, MessageSquare } from 'lucide-react';
import { FlowNodeData } from './nodes';

// Vozes disponíveis do ElevenLabs
const AVAILABLE_VOICES = [
  { id: '', label: 'Padrão do sistema' },
  { id: 'xPnmQf6Ow3GGYWWURFPi', label: '⭐ Paula (Português, conversacional)' },
  { id: '21m00Tcm4TlvDq8ikWAM', label: 'Rachel (Feminina, calma)' },
  { id: 'EXAVITQu4vr4xnSDxMaL', label: 'Bella (Feminina, suave)' },
  { id: 'MF3mGyEYCl7XYWbV9V6O', label: 'Elli (Feminina, jovem)' },
  { id: 'ErXwobaYiN019PkySvjV', label: 'Antoni (Masculino, amigável)' },
  { id: 'TxGEqnHWrfWFTfGW9XjX', label: 'Josh (Masculino, grave)' },
  { id: 'pNInz6obpgDQGcFmaJgB', label: 'Adam (Masculino, profundo)' },
  { id: '29vD33N1CtxCmqQRPOHJ', label: 'Drew (Masculino, confiante)' },
  { id: 'custom', label: '🔧 Usar ID personalizado...' },
];

interface NodeEditorPanelProps {
  node: Node<FlowNodeData>;
  onUpdate: (nodeId: string, data: Partial<FlowNodeData>) => void;
  onDelete: (nodeId: string) => void;
  onClose: () => void;
}

export function NodeEditorPanel({
  node,
  onUpdate,
  onDelete,
  onClose,
}: NodeEditorPanelProps) {
  const { data } = node;
  const nodeType = data.type?.toUpperCase() || 'UNKNOWN';

  const updateField = (field: string, value: any) => {
    onUpdate(node.id, {
      ...data,
      config: {
        ...data.config,
        [field]: value,
      },
    });
  };

  const updateLabel = (label: string) => {
    onUpdate(node.id, {
      ...data,
      label,
    });
  };

  // Get title based on node type
  const getTitle = () => {
    const titles: Record<string, string> = {
      GREETING: 'Editar Saudação',
      QUESTION: 'Editar Pergunta',
      CONDITION: 'Editar Condição',
      MESSAGE: 'Editar Mensagem',
      ACTION: 'Editar Ação',
      HANDOFF: 'Editar Transferência',
      FOLLOWUP: 'Editar Follow-up',
      NOME: 'Coletar Nome',
      EMAIL: 'Coletar Email',
      TELEFONE: 'Coletar Telefone',
      CIDADE: 'Coletar Cidade',
      INTERESSE: 'Coletar Interesse',
      ORCAMENTO: 'Coletar Orçamento',
      URGENCIA: 'Coletar Urgência',
      AGENDAMENTO: 'Editar Agendamento',
      END: 'Editar Fim',
    };
    return titles[nodeType] || 'Editar Nó';
  };

  // Render editor based on node type
  const renderEditor = () => {
    switch (nodeType) {
      case 'GREETING':
        return renderGreetingEditor();
      case 'QUESTION':
      case 'NOME':
      case 'EMAIL':
      case 'TELEFONE':
      case 'CIDADE':
      case 'INTERESSE':
      case 'ORCAMENTO':
      case 'URGENCIA':
        return renderQuestionEditor();
      case 'CONDITION':
        return renderConditionEditor();
      case 'MESSAGE':
      case 'END':
        return renderMessageEditor();
      case 'ACTION':
        return renderActionEditor();
      case 'HANDOFF':
        return renderHandoffEditor();
      case 'FOLLOWUP':
        return renderFollowupEditor();
      case 'AGENDAMENTO':
        return renderAgendamentoEditor();
      default:
        return <p className="text-gray-500">Editor não disponível para este tipo de nó.</p>;
    }
  };

  // ==================== EDITORS ====================

  const renderGreetingEditor = () => (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Nome do Nó
        </label>
        <input
          type="text"
          value={data.label || ''}
          onChange={(e) => updateLabel(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Mensagem de Boas-vindas
        </label>
        <textarea
          value={data.config?.mensagem || ''}
          onChange={(e) => updateField('mensagem', e.target.value)}
          rows={4}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="Olá! Seja bem-vindo..."
        />
        <p className="mt-1 text-xs text-gray-500">
          Use {'{nome}'} para personalizar com o nome do cliente
        </p>
      </div>

      {renderResponseTypeSelector()}
    </div>
  );

  const renderQuestionEditor = () => (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Nome do Nó
        </label>
        <input
          type="text"
          value={data.label || ''}
          onChange={(e) => updateLabel(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Pergunta
        </label>
        <textarea
          value={data.config?.pergunta || ''}
          onChange={(e) => updateField('pergunta', e.target.value)}
          rows={3}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="Qual é o seu nome?"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Salvar em (campo)
        </label>
        <input
          type="text"
          value={data.config?.campo_destino || ''}
          onChange={(e) => updateField('campo_destino', e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="nome"
        />
        <p className="mt-1 text-xs text-gray-500">
          Nome do campo onde a resposta será salva
        </p>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Tipo do Campo
        </label>
        <select
          value={data.config?.tipo_campo || 'text'}
          onChange={(e) => updateField('tipo_campo', e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="text">Texto</option>
          <option value="number">Número</option>
          <option value="email">Email</option>
          <option value="phone">Telefone</option>
          <option value="date">Data</option>
          <option value="select">Seleção</option>
          <option value="boolean">Sim/Não</option>
        </select>
      </div>

      {data.config?.tipo_campo === 'select' && (
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Opções (uma por linha)
          </label>
          <textarea
            value={data.config?.opcoes?.join('\n') || ''}
            onChange={(e) => updateField('opcoes', e.target.value.split('\n').filter(Boolean))}
            rows={4}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Opção 1&#10;Opção 2&#10;Opção 3"
          />
        </div>
      )}

      {renderResponseTypeSelector()}
    </div>
  );

  const renderConditionEditor = () => (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Nome do Nó
        </label>
        <input
          type="text"
          value={data.label || ''}
          onChange={(e) => updateLabel(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Campo a Verificar
        </label>
        <input
          type="text"
          value={data.config?.campo || ''}
          onChange={(e) => updateField('campo', e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="nome"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Operador
        </label>
        <select
          value={data.config?.operador || 'equals'}
          onChange={(e) => updateField('operador', e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="equals">É igual a</option>
          <option value="not_equals">É diferente de</option>
          <option value="contains">Contém</option>
          <option value="not_contains">Não contém</option>
          <option value="greater_than">Maior que</option>
          <option value="less_than">Menor que</option>
          <option value="is_empty">Está vazio</option>
          <option value="is_not_empty">Não está vazio</option>
          <option value="exists">Existe</option>
        </select>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Valor
        </label>
        <input
          type="text"
          value={data.config?.valor || ''}
          onChange={(e) => updateField('valor', e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="valor para comparar"
        />
      </div>

      <div className="rounded-lg bg-amber-50 p-3">
        <p className="text-xs text-amber-800">
          <strong>Saída Sim (verde):</strong> Condição verdadeira<br />
          <strong>Saída Não (vermelho):</strong> Condição falsa
        </p>
      </div>
    </div>
  );

  const renderMessageEditor = () => (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Nome do Nó
        </label>
        <input
          type="text"
          value={data.label || ''}
          onChange={(e) => updateLabel(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Mensagem
        </label>
        <textarea
          value={data.config?.mensagem || ''}
          onChange={(e) => updateField('mensagem', e.target.value)}
          rows={5}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="Digite a mensagem..."
        />
        <p className="mt-1 text-xs text-gray-500">
          Use {'{nome}'}, {'{email}'}, etc. para personalizar
        </p>
      </div>

      {renderResponseTypeSelector()}
    </div>
  );

  const renderActionEditor = () => (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Nome do Nó
        </label>
        <input
          type="text"
          value={data.label || ''}
          onChange={(e) => updateLabel(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Tipo de Ação
        </label>
        <select
          value={data.config?.tipo_acao || 'webhook'}
          onChange={(e) => updateField('tipo_acao', e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="webhook">Webhook</option>
          <option value="api_call">Chamada API</option>
          <option value="update_field">Atualizar Campo</option>
          <option value="tag_lead">Adicionar Tag</option>
          <option value="move_status">Mover Status</option>
          <option value="notify_team">Notificar Equipe</option>
        </select>
      </div>

      {(data.config?.tipo_acao === 'webhook' || data.config?.tipo_acao === 'api_call') && (
        <>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              URL
            </label>
            <input
              type="text"
              value={data.config?.url || ''}
              onChange={(e) => updateField('url', e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="https://..."
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Método
            </label>
            <select
              value={data.config?.method || 'POST'}
              onChange={(e) => updateField('method', e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="POST">POST</option>
              <option value="GET">GET</option>
              <option value="PUT">PUT</option>
              <option value="PATCH">PATCH</option>
            </select>
          </div>
        </>
      )}
    </div>
  );

  const renderHandoffEditor = () => (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Nome do Nó
        </label>
        <input
          type="text"
          value={data.label || ''}
          onChange={(e) => updateLabel(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Mensagem para o Cliente
        </label>
        <textarea
          value={data.config?.mensagem_cliente || ''}
          onChange={(e) => updateField('mensagem_cliente', e.target.value)}
          rows={3}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="Vou transferir você para um atendente..."
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Motivo da Transferência
        </label>
        <input
          type="text"
          value={data.config?.motivo || ''}
          onChange={(e) => updateField('motivo', e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="Lead qualificado"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="notificar_equipe"
          checked={data.config?.notificar_equipe !== false}
          onChange={(e) => updateField('notificar_equipe', e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        <label htmlFor="notificar_equipe" className="text-sm text-gray-700">
          Notificar equipe
        </label>
      </div>

      {renderResponseTypeSelector()}
    </div>
  );

  const renderFollowupEditor = () => (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Nome do Nó
        </label>
        <input
          type="text"
          value={data.label || ''}
          onChange={(e) => updateLabel(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Intervalos (em minutos, um por linha)
        </label>
        <textarea
          value={data.config?.intervalos?.join('\n') || ''}
          onChange={(e) => updateField('intervalos', e.target.value.split('\n').map(Number).filter(Boolean))}
          rows={3}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="1440&#10;4320&#10;10080"
        />
        <p className="mt-1 text-xs text-gray-500">
          1440 = 1 dia, 4320 = 3 dias, 10080 = 7 dias
        </p>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Mensagens (uma por linha, na mesma ordem dos intervalos)
        </label>
        <textarea
          value={data.config?.mensagens?.join('\n') || ''}
          onChange={(e) => updateField('mensagens', e.target.value.split('\n').filter(Boolean))}
          rows={4}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="Olá {nome}, tudo bem?&#10;Conseguiu avaliar nossa proposta?&#10;Ainda posso ajudar?"
        />
      </div>
    </div>
  );

  const renderAgendamentoEditor = () => (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Nome do Nó
        </label>
        <input
          type="text"
          value={data.label || ''}
          onChange={(e) => updateLabel(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Mensagem
        </label>
        <textarea
          value={data.config?.mensagem || ''}
          onChange={(e) => updateField('mensagem', e.target.value)}
          rows={3}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="Vou agendar uma reunião para você..."
        />
      </div>
    </div>
  );

  // ==================== RESPONSE TYPE SELECTOR ====================
  const renderResponseTypeSelector = () => (
    <div className="space-y-3 rounded-lg border border-purple-200 bg-purple-50 p-3">
      <div className="flex items-center gap-2">
        <Volume2 className="h-4 w-4 text-purple-600" />
        <span className="text-sm font-medium text-purple-800">Tipo de Resposta</span>
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => updateField('response_type', 'text')}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
            (data.config?.response_type || 'text') === 'text'
              ? 'bg-purple-600 text-white'
              : 'bg-white text-purple-700 hover:bg-purple-100'
          }`}
        >
          <MessageSquare className="h-3.5 w-3.5" />
          Texto
        </button>
        <button
          type="button"
          onClick={() => updateField('response_type', 'audio')}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
            data.config?.response_type === 'audio'
              ? 'bg-purple-600 text-white'
              : 'bg-white text-purple-700 hover:bg-purple-100'
          }`}
        >
          <Volume2 className="h-3.5 w-3.5" />
          Áudio
        </button>
        <button
          type="button"
          onClick={() => updateField('response_type', 'both')}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
            data.config?.response_type === 'both'
              ? 'bg-purple-600 text-white'
              : 'bg-white text-purple-700 hover:bg-purple-100'
          }`}
        >
          Ambos
        </button>
      </div>

      {(data.config?.response_type === 'audio' || data.config?.response_type === 'both') && (
        <div className="space-y-2">
          <label className="block text-xs font-medium text-purple-700">
            Voz (ElevenLabs)
          </label>
          <select
            value={
              AVAILABLE_VOICES.some(v => v.id === data.config?.voice_id)
                ? data.config?.voice_id || ''
                : 'custom'
            }
            onChange={(e) => {
              if (e.target.value === 'custom') {
                updateField('voice_id', '');
                updateField('custom_voice', true);
              } else {
                updateField('voice_id', e.target.value);
                updateField('custom_voice', false);
              }
            }}
            className="w-full rounded-lg border border-purple-200 bg-white px-3 py-2 text-xs focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
          >
            {AVAILABLE_VOICES.map((voice) => (
              <option key={voice.id || 'custom'} value={voice.id}>
                {voice.label}
              </option>
            ))}
          </select>

          {(data.config?.custom_voice || (data.config?.voice_id && !AVAILABLE_VOICES.some(v => v.id === data.config?.voice_id))) && (
            <div className="mt-2">
              <label className="block text-xs font-medium text-purple-700 mb-1">
                ID da Voz Personalizada
              </label>
              <input
                type="text"
                value={data.config?.voice_id || ''}
                onChange={(e) => updateField('voice_id', e.target.value)}
                placeholder="Ex: xPnmQf6Ow3GGYWWURFPi"
                className="w-full rounded-lg border border-purple-200 bg-white px-3 py-2 text-xs focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 font-mono"
              />
            </div>
          )}

          <p className="text-xs text-purple-600">
            O áudio será enviado como mensagem de voz no WhatsApp
          </p>
        </div>
      )}
    </div>
  );

  return (
    <div className="flex h-full w-80 flex-col border-l bg-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h3 className="font-semibold text-gray-900">{getTitle()}</h3>
        <button
          onClick={onClose}
          className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">{renderEditor()}</div>

      {/* Footer */}
      <div className="border-t p-4">
        <button
          onClick={() => onDelete(node.id)}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-100"
        >
          <Trash2 className="h-4 w-4" />
          Excluir Nó
        </button>
      </div>
    </div>
  );
}
