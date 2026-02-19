'use client';

import { useState, useEffect } from 'react';
import { Header } from '@/components/layout/header';
import {
  Phone,
  PhoneCall,
  PhoneOff,
  Settings,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  History,
  Play,
  Key,
  Bot
} from 'lucide-react';
import { apiGet, apiPost } from '@/lib/supabase';
import { useAuth } from '@/contexts/auth-context';
import Link from 'next/link';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

// Types
interface VoiceCallsStatus {
  enabled: boolean;
  configured: boolean;
  agent_id?: string;
  connection_status?: {
    success: boolean;
    tier?: string;
    character_count?: number;
    character_limit?: number;
    error?: string;
  };
}

interface VoiceCallLog {
  id: number;
  lead_id?: number;
  phone: string;
  channel: string;
  status: string;
  duration_seconds?: number;
  created_at: string;
}

interface Agent {
  agent_id: string;
  name: string;
}

export default function VoiceCallsSettingsPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<VoiceCallsStatus>({
    enabled: false,
    configured: false
  });
  const [callHistory, setCallHistory] = useState<VoiceCallLog[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);

  // Config modal
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [configForm, setConfigForm] = useState({
    api_key: '',
    agent_id: ''
  });
  const [configError, setConfigError] = useState('');

  // Test call modal
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [testPhone, setTestPhone] = useState('');
  const [testLoading, setTestLoading] = useState(false);

  useEffect(() => {
    if (user?.company_id) {
      loadStatus();
      loadCallHistory();
    }
  }, [user]);

  async function loadStatus() {
    if (!user?.company_id) return;

    try {
      const data = await apiGet<VoiceCallsStatus>(
        `/api/voice-calls/status/${user.company_id}`
      );
      setStatus(data);

      // If configured, load agents
      if (data.configured) {
        loadAgents();
      }
    } catch (error) {
      console.error('Error loading status:', error);
    } finally {
      setLoading(false);
    }
  }

  async function loadAgents() {
    if (!user?.company_id) return;

    try {
      const data = await apiGet<{ success: boolean; agents: Agent[] }>(
        `/api/voice-calls/agents/${user.company_id}`
      );
      if (data.success) {
        setAgents(data.agents);
      }
    } catch (error) {
      console.error('Error loading agents:', error);
    }
  }

  async function loadCallHistory() {
    if (!user?.company_id) return;

    try {
      const data = await apiGet<{ calls: VoiceCallLog[] }>(
        `/api/voice-calls/history/${user.company_id}?limit=10`
      );
      setCallHistory(data.calls || []);
    } catch (error) {
      console.error('Error loading call history:', error);
    }
  }

  async function handleToggle() {
    if (!user?.company_id) return;

    // If trying to enable but not configured, open config modal
    if (!status.enabled && !status.configured) {
      setIsConfigModalOpen(true);
      return;
    }

    setSaving(true);
    try {
      await apiPost(`/api/voice-calls/toggle/${user.company_id}`, {
        enabled: !status.enabled
      });
      await loadStatus();
    } catch (error) {
      console.error('Error toggling voice calls:', error);
      alert('Erro ao alterar configuração');
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveConfig() {
    if (!user?.company_id) return;
    if (!configForm.api_key || !configForm.agent_id) {
      setConfigError('Preencha todos os campos');
      return;
    }

    setSaving(true);
    setConfigError('');

    try {
      await apiPost(`/api/voice-calls/configure/${user.company_id}`, configForm);

      // Enable after configuring
      await apiPost(`/api/voice-calls/toggle/${user.company_id}`, {
        enabled: true
      });

      setIsConfigModalOpen(false);
      setConfigForm({ api_key: '', agent_id: '' });
      await loadStatus();
      alert('Configuração salva com sucesso!');
    } catch (error: any) {
      console.error('Error saving config:', error);
      setConfigError(error.message || 'Erro ao salvar configuração');
    } finally {
      setSaving(false);
    }
  }

  async function handleTestCall() {
    if (!user?.company_id || !testPhone) return;

    setTestLoading(true);
    try {
      const result = await apiPost(`/api/voice-calls/call/${user.company_id}`, {
        phone: testPhone,
        lead_name: 'Teste'
      });

      if (result.success) {
        alert('Chamada iniciada com sucesso!');
        setIsTestModalOpen(false);
        setTestPhone('');
        loadCallHistory();
      } else {
        alert(`Erro: ${result.error}`);
      }
    } catch (error: any) {
      console.error('Error making test call:', error);
      alert(error.message || 'Erro ao fazer chamada de teste');
    } finally {
      setTestLoading(false);
    }
  }

  function formatDuration(seconds?: number) {
    if (!seconds) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  function formatPhone(phone: string) {
    const cleaned = phone.replace(/\D/g, '').replace(/^55/, '');
    if (cleaned.length === 11) {
      return `(${cleaned.slice(0, 2)}) ${cleaned.slice(2, 7)}-${cleaned.slice(7)}`;
    }
    return phone;
  }

  function getStatusBadge(callStatus: string) {
    const colors: Record<string, string> = {
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      initiated: 'bg-blue-100 text-blue-800',
      pending: 'bg-yellow-100 text-yellow-800',
      no_answer: 'bg-gray-100 text-gray-800'
    };
    return colors[callStatus] || 'bg-gray-100 text-gray-800';
  }

  if (loading) {
    return (
      <div>
        <Header title="Chamadas de Voz" subtitle="Configure chamadas de voz IA" />
        <div className="flex items-center justify-center h-96">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header
        title="Chamadas de Voz IA"
        subtitle="Configure chamadas automatizadas via ElevenLabs"
      />

      <div className="p-6">
        <div className="max-w-5xl mx-auto">
          {/* Navigation Tabs */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-2 mb-6">
            <div className="flex gap-2 overflow-x-auto">
              <Link
                href="/dashboard/settings"
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg font-medium whitespace-nowrap"
              >
                Geral
              </Link>
              <Link
                href="/dashboard/settings/ia"
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg font-medium whitespace-nowrap"
              >
                Configurar IA
              </Link>
              <Link
                href="/dashboard/settings/whatsapp"
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg font-medium whitespace-nowrap"
              >
                WhatsApp
              </Link>
              <Link
                href="/dashboard/settings/voice-calls"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium whitespace-nowrap"
              >
                Chamadas de Voz
              </Link>
            </div>
          </div>

          {/* Main Toggle Card */}
          <Card className="mb-6">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-lg ${
                    status.enabled ? 'bg-green-100' : 'bg-gray-100'
                  }`}>
                    {status.enabled ? (
                      <PhoneCall className="w-6 h-6 text-green-600" />
                    ) : (
                      <PhoneOff className="w-6 h-6 text-gray-400" />
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <CardTitle className="text-xl">Chamadas de Voz IA</CardTitle>
                      <Badge variant={status.enabled ? 'success' : 'secondary'}>
                        {status.enabled ? 'Ativado' : 'Desativado'}
                      </Badge>
                    </div>
                    <CardDescription>
                      {status.enabled
                        ? 'A IA pode fazer ligações para seus leads'
                        : 'Ative para permitir chamadas automáticas'}
                    </CardDescription>
                  </div>
                </div>

                {/* Toggle Switch */}
                <button
                  onClick={handleToggle}
                  disabled={saving}
                  className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${
                    status.enabled ? 'bg-green-600' : 'bg-gray-300'
                  } ${saving ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                >
                  <span
                    className={`inline-block h-6 w-6 transform rounded-full bg-white shadow-md transition-transform ${
                      status.enabled ? 'translate-x-7' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </CardHeader>

            {status.enabled && status.connection_status && (
              <CardContent>
                <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                  {status.connection_status.success ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-600" />
                  )}
                  <div className="flex-1">
                    <p className="text-sm font-medium">
                      {status.connection_status.success
                        ? `Conectado - Plano: ${status.connection_status.tier}`
                        : 'Erro de conexão'}
                    </p>
                    {status.connection_status.character_limit && (
                      <p className="text-xs text-gray-500">
                        Caracteres: {status.connection_status.character_count?.toLocaleString()} /{' '}
                        {status.connection_status.character_limit?.toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            )}
          </Card>

          {/* Actions */}
          {status.enabled && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <Button
                onClick={() => setIsConfigModalOpen(true)}
                variant="outline"
                className="h-auto py-4"
              >
                <div className="flex flex-col items-center gap-2">
                  <Settings className="w-5 h-5" />
                  <span>Configurar</span>
                </div>
              </Button>

              <Button
                onClick={() => setIsTestModalOpen(true)}
                variant="outline"
                className="h-auto py-4"
              >
                <div className="flex flex-col items-center gap-2">
                  <Play className="w-5 h-5" />
                  <span>Chamada de Teste</span>
                </div>
              </Button>

              <Button
                onClick={loadCallHistory}
                variant="outline"
                className="h-auto py-4"
              >
                <div className="flex flex-col items-center gap-2">
                  <History className="w-5 h-5" />
                  <span>Atualizar Histórico</span>
                </div>
              </Button>
            </div>
          )}

          {/* Call History */}
          {status.enabled && callHistory.length > 0 && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <History className="w-5 h-5" />
                  Histórico de Chamadas
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {callHistory.map((call) => (
                    <div
                      key={call.id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <Phone className="w-4 h-4 text-gray-500" />
                        <div>
                          <p className="font-medium text-sm">
                            {formatPhone(call.phone)}
                          </p>
                          <p className="text-xs text-gray-500">
                            {new Date(call.created_at).toLocaleString('pt-BR')}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-gray-600">
                          {formatDuration(call.duration_seconds)}
                        </span>
                        <span className={`px-2 py-1 text-xs rounded-full ${getStatusBadge(call.status)}`}>
                          {call.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Info Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <AlertCircle className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <CardTitle className="text-lg">Como funciona</CardTitle>
                  <CardDescription>
                    Chamadas de voz automatizadas com IA
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 text-sm text-gray-700">
                <p>
                  Com este módulo ativado, sua IA pode fazer ligações de voz para leads
                  usando a tecnologia ElevenLabs Conversational AI.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="font-medium mb-1">Canais Suportados</p>
                    <ul className="text-xs space-y-1">
                      <li>- WhatsApp Voice Call</li>
                      <li>- Telefone (via Twilio)</li>
                    </ul>
                  </div>

                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="font-medium mb-1">Funcionalidades</p>
                    <ul className="text-xs space-y-1">
                      <li>- Voz natural em PT-BR</li>
                      <li>- Conversa em tempo real</li>
                      <li>- Transcrição automática</li>
                    </ul>
                  </div>
                </div>

                <p className="text-xs text-gray-500">
                  Você precisa de uma conta ElevenLabs com um agente conversacional
                  configurado. Obtenha sua API key em{' '}
                  <a
                    href="https://elevenlabs.io"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    elevenlabs.io
                  </a>
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Config Modal */}
      <Dialog open={isConfigModalOpen} onOpenChange={setIsConfigModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Configurar Chamadas de Voz</DialogTitle>
            <DialogDescription>
              Insira suas credenciais do ElevenLabs
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Key className="w-4 h-4" />
                API Key
              </label>
              <Input
                type="password"
                placeholder="xi_..."
                value={configForm.api_key}
                onChange={(e) => setConfigForm({ ...configForm, api_key: e.target.value })}
              />
              <p className="text-xs text-gray-500">
                Encontre em elevenlabs.io/app/settings/api-keys
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Bot className="w-4 h-4" />
                Agent ID
              </label>
              <Input
                type="text"
                placeholder="agent_..."
                value={configForm.agent_id}
                onChange={(e) => setConfigForm({ ...configForm, agent_id: e.target.value })}
              />
              <p className="text-xs text-gray-500">
                ID do seu agente conversacional no ElevenLabs
              </p>
            </div>

            {configError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">{configError}</p>
              </div>
            )}

            <div className="flex gap-2">
              <Button
                onClick={() => setIsConfigModalOpen(false)}
                variant="outline"
                className="flex-1"
              >
                Cancelar
              </Button>
              <Button
                onClick={handleSaveConfig}
                disabled={saving || !configForm.api_key || !configForm.agent_id}
                className="flex-1"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Salvando...
                  </>
                ) : (
                  'Salvar e Ativar'
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Test Call Modal */}
      <Dialog open={isTestModalOpen} onOpenChange={setIsTestModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Chamada de Teste</DialogTitle>
            <DialogDescription>
              Faça uma chamada de teste para verificar a configuração
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Número de Telefone
              </label>
              <div className="flex gap-2">
                <div className="flex items-center px-3 bg-gray-100 rounded-md border border-gray-200">
                  <span className="text-sm text-gray-600">+55</span>
                </div>
                <Input
                  type="tel"
                  placeholder="11999999999"
                  value={testPhone}
                  onChange={(e) => setTestPhone(e.target.value.replace(/\D/g, ''))}
                  maxLength={11}
                  className="flex-1"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={() => setIsTestModalOpen(false)}
                variant="outline"
                className="flex-1"
              >
                Cancelar
              </Button>
              <Button
                onClick={handleTestCall}
                disabled={testLoading || testPhone.length < 10}
                className="flex-1 bg-green-600 hover:bg-green-700"
              >
                {testLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Ligando...
                  </>
                ) : (
                  <>
                    <PhoneCall className="w-4 h-4 mr-2" />
                    Fazer Chamada
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
