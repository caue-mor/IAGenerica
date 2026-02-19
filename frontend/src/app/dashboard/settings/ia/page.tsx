'use client';
import { useState, useEffect } from 'react';
import { Header } from '@/components/layout/header';
import { Save, Loader2, Bot, Sparkles } from 'lucide-react';
import { apiGet, apiPatch } from '@/lib/supabase';
import { useAuth } from '@/contexts/auth-context';
import { Company } from '@/types';
import Link from 'next/link';

export default function IASettingsPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    agent_name: 'Assistente',
    agent_tone: 'amigavel',
    use_emojis: false,
  });

  useEffect(() => {
    if (user) {
      loadCompany();
    }
  }, [user]);

  async function loadCompany() {
    try {
      const data = await apiGet<Company>(`/api/companies/${user?.company_id}`);
      setFormData({
        agent_name: data.agent_name,
        agent_tone: data.agent_tone,
        use_emojis: data.use_emojis,
      });
    } catch (error) {
      console.error('Error loading company:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);

    try {
      await apiPatch(`/api/companies/${user?.company_id}`, formData);
      alert('Configurações da IA salvas com sucesso!');
      loadCompany();
    } catch (error) {
      console.error('Error saving settings:', error);
      alert('Erro ao salvar configurações');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div>
        <Header title="Configurar IA" subtitle="Personalize o agente" />
        <div className="flex items-center justify-center h-96">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="Configurar IA" subtitle="Personalize o comportamento do agente" />

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
                className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium whitespace-nowrap"
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
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg font-medium whitespace-nowrap"
              >
                Chamadas de Voz
              </Link>
            </div>
          </div>

          {/* Form */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Personalização do Agente
                </h2>
                <p className="text-sm text-gray-500">
                  Configure como a IA se apresenta e se comporta
                </p>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Agent Name */}
              <div>
                <label htmlFor="agent_name" className="block text-sm font-medium text-gray-700 mb-2">
                  Nome do Assistente
                </label>
                <input
                  id="agent_name"
                  type="text"
                  value={formData.agent_name}
                  onChange={(e) => setFormData({ ...formData, agent_name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Assistente"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  Como a IA se apresentará aos clientes
                </p>
              </div>

              {/* Agent Tone */}
              <div>
                <label htmlFor="agent_tone" className="block text-sm font-medium text-gray-700 mb-2">
                  Tom de Voz
                </label>
                <select
                  id="agent_tone"
                  value={formData.agent_tone}
                  onChange={(e) => setFormData({ ...formData, agent_tone: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="amigavel">Amigável - Tom casual e acolhedor</option>
                  <option value="formal">Formal - Tom profissional e educado</option>
                  <option value="casual">Casual - Tom descontraído e leve</option>
                  <option value="tecnico">Técnico - Tom objetivo e direto</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Define o estilo de comunicação da IA
                </p>
              </div>

              {/* Use Emojis */}
              <div>
                <label className="flex items-start gap-3 cursor-pointer p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                  <input
                    type="checkbox"
                    checked={formData.use_emojis}
                    onChange={(e) => setFormData({ ...formData, use_emojis: e.target.checked })}
                    className="w-4 h-4 mt-0.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-yellow-500" />
                      <span className="text-sm font-medium text-gray-700">
                        Usar emojis nas respostas
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      A IA incluirá emojis para tornar a conversa mais amigável
                    </p>
                  </div>
                </label>
              </div>

              {/* Preview */}
              <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                    {formData.agent_name[0]?.toUpperCase() || 'A'}
                  </div>
                  <div className="flex-1">
                    <p className="text-xs text-gray-600 mb-1">{formData.agent_name}</p>
                    <div className="bg-white rounded-lg p-3 shadow-sm">
                      <p className="text-sm text-gray-900">
                        {formData.agent_tone === 'amigavel' &&
                          `Olá! ${formData.use_emojis ? '👋 ' : ''}Eu sou ${formData.agent_name}. Como posso te ajudar hoje?${formData.use_emojis ? ' 😊' : ''}`}
                        {formData.agent_tone === 'formal' &&
                          `Olá. Meu nome é ${formData.agent_name}. Como posso auxiliá-lo?`}
                        {formData.agent_tone === 'casual' &&
                          `E aí! ${formData.use_emojis ? '😎 ' : ''}Sou o ${formData.agent_name}. Em que posso ajudar?`}
                        {formData.agent_tone === 'tecnico' &&
                          `${formData.agent_name}. Como posso ajudar?`}
                      </p>
                    </div>
                  </div>
                </div>
                <p className="text-xs text-gray-600 mt-3">Preview do estilo de conversa</p>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-4 pt-6 border-t border-gray-200">
                <button
                  type="button"
                  onClick={loadCompany}
                  className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors"
                >
                  {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                  <Save className="w-4 h-4" />
                  {saving ? 'Salvando...' : 'Salvar Alterações'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
