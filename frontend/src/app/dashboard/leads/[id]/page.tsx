'use client';
import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Header } from '@/components/layout/header';
import { Save, Loader2, ArrowLeft, MessageSquare, Trash2 } from 'lucide-react';
import { apiGet, apiPatch, apiDelete } from '@/lib/supabase';
import { useAuth } from '@/contexts/auth-context';
import { Lead, LeadStatus, Message } from '@/types';
import Link from 'next/link';

export default function EditLeadPage() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuth();
  const leadId = params?.id as string;

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [lead, setLead] = useState<Lead | null>(null);
  const [statuses, setStatuses] = useState<LeadStatus[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [formData, setFormData] = useState({
    nome: '',
    celular: '',
    email: '',
    origem: '',
    status_id: undefined as number | undefined,
    ai_enabled: true,
  });

  useEffect(() => {
    if (leadId) {
      loadData();
    }
  }, [leadId]);

  async function loadData() {
    try {
      const [leadRes, statusesRes, messagesRes] = await Promise.all([
        apiGet<Lead>(`/api/leads/${leadId}`),
        apiGet<LeadStatus[]>(`/api/lead-statuses/${user?.company_id}`),
        apiGet<Message[]>(`/api/messages?lead_id=${leadId}`).catch(() => []),
      ]);

      setLead(leadRes);
      setStatuses(statusesRes);
      setMessages(messagesRes);
      setFormData({
        nome: leadRes.nome || '',
        celular: leadRes.celular,
        email: leadRes.email || '',
        origem: leadRes.origem || '',
        status_id: leadRes.status_id,
        ai_enabled: leadRes.ai_enabled,
      });
    } catch (error) {
      console.error('Error loading lead:', error);
      alert('Erro ao carregar lead');
      router.push('/dashboard/leads');
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);

    try {
      await apiPatch(`/api/leads/${leadId}`, formData);
      router.push('/dashboard/leads');
    } catch (error) {
      console.error('Error updating lead:', error);
      alert('Erro ao atualizar lead');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm('Tem certeza que deseja excluir este lead?')) return;

    try {
      await apiDelete(`/api/leads/${leadId}`);
      router.push('/dashboard/leads');
    } catch (error) {
      console.error('Error deleting lead:', error);
      alert('Erro ao excluir lead');
    }
  }

  if (loading) {
    return (
      <div>
        <Header title="Carregando..." subtitle="Aguarde" />
        <div className="flex items-center justify-center h-96">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  if (!lead) {
    return null;
  }

  return (
    <div>
      <Header title="Editar Lead" subtitle={`ID: ${leadId}`} />

      <div className="p-6">
        <div className="max-w-6xl mx-auto">
          <Link
            href="/dashboard/leads"
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-6"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para lista
          </Link>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Form */}
            <div className="lg:col-span-2">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Nome */}
                    <div className="md:col-span-2">
                      <label htmlFor="nome" className="block text-sm font-medium text-gray-700 mb-2">
                        Nome Completo
                      </label>
                      <input
                        id="nome"
                        type="text"
                        value={formData.nome}
                        onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>

                    {/* Celular */}
                    <div>
                      <label htmlFor="celular" className="block text-sm font-medium text-gray-700 mb-2">
                        Celular *
                      </label>
                      <input
                        id="celular"
                        type="tel"
                        value={formData.celular}
                        onChange={(e) => setFormData({ ...formData, celular: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                      />
                    </div>

                    {/* Email */}
                    <div>
                      <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                        Email
                      </label>
                      <input
                        id="email"
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>

                    {/* Origem */}
                    <div>
                      <label htmlFor="origem" className="block text-sm font-medium text-gray-700 mb-2">
                        Origem
                      </label>
                      <input
                        id="origem"
                        type="text"
                        value={formData.origem}
                        onChange={(e) => setFormData({ ...formData, origem: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>

                    {/* Status */}
                    <div>
                      <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-2">
                        Status
                      </label>
                      <select
                        id="status"
                        value={formData.status_id || ''}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            status_id: e.target.value ? Number(e.target.value) : undefined,
                          })
                        }
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="">Selecione um status</option>
                        {statuses.map((status) => (
                          <option key={status.id} value={status.id}>
                            {status.nome}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* IA Enabled */}
                    <div className="md:col-span-2">
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.ai_enabled}
                          onChange={(e) =>
                            setFormData({ ...formData, ai_enabled: e.target.checked })
                          }
                          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <div>
                          <span className="text-sm font-medium text-gray-700">
                            Atendimento com IA ativo
                          </span>
                          <p className="text-xs text-gray-500">
                            A IA responderá automaticamente às mensagens deste lead
                          </p>
                        </div>
                      </label>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-between pt-6 border-t border-gray-200">
                    <button
                      type="button"
                      onClick={handleDelete}
                      className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                      Excluir Lead
                    </button>

                    <div className="flex items-center gap-4">
                      <Link
                        href="/dashboard/leads"
                        className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        Cancelar
                      </Link>
                      <button
                        type="submit"
                        disabled={saving}
                        className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors"
                      >
                        {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                        <Save className="w-4 h-4" />
                        {saving ? 'Salvando...' : 'Salvar'}
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Info */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h3 className="font-semibold text-gray-900 mb-4">Informações</h3>
                <div className="space-y-3 text-sm">
                  <div>
                    <span className="text-gray-500">Criado em:</span>
                    <p className="font-medium text-gray-900">
                      {new Date(lead.created_at).toLocaleString('pt-BR')}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Atualizado em:</span>
                    <p className="font-medium text-gray-900">
                      {new Date(lead.updated_at).toLocaleString('pt-BR')}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Total de mensagens:</span>
                    <p className="font-medium text-gray-900">{messages.length}</p>
                  </div>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h3 className="font-semibold text-gray-900 mb-4">Ações Rápidas</h3>
                <div className="space-y-2">
                  <Link
                    href={`/dashboard/conversations?lead_id=${leadId}`}
                    className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors w-full"
                  >
                    <MessageSquare className="w-4 h-4" />
                    Ver Conversas
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
