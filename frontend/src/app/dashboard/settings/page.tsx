'use client';
import { useState, useEffect } from 'react';
import { Header } from '@/components/layout/header';
import { Save, Loader2, Building, Globe, Clock, Mail } from 'lucide-react';
import { apiGet, apiPatch } from '@/lib/supabase';
import { useAuth } from '@/contexts/auth-context';
import { Company } from '@/types';
import Link from 'next/link';

export default function SettingsPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [company, setCompany] = useState<Company | null>(null);
  const [formData, setFormData] = useState({
    empresa: '',
    nome_empresa: '',
    email: '',
    cidade: '',
    site: '',
    horario_funcionamento: '',
    informacoes_complementares: '',
  });

  useEffect(() => {
    if (user) {
      loadCompany();
    }
  }, [user]);

  async function loadCompany() {
    try {
      const data = await apiGet<Company>(`/api/companies/${user?.company_id}`);
      setCompany(data);
      setFormData({
        empresa: data.empresa,
        nome_empresa: data.nome_empresa || '',
        email: data.email,
        cidade: data.cidade || '',
        site: data.site || '',
        horario_funcionamento: data.horario_funcionamento || '',
        informacoes_complementares: data.informacoes_complementares || '',
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
      alert('Configurações salvas com sucesso!');
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
        <Header title="Configurações" subtitle="Gerencie sua conta" />
        <div className="flex items-center justify-center h-96">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="Configurações" subtitle="Gerencie sua conta e preferências" />

      <div className="p-6">
        <div className="max-w-5xl mx-auto">
          {/* Navigation Tabs */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-2 mb-6">
            <div className="flex gap-2 overflow-x-auto">
              <Link
                href="/dashboard/settings"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium whitespace-nowrap"
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
            </div>
          </div>

          {/* Form */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">
              Informações da Empresa
            </h2>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Empresa (slug) */}
                <div>
                  <label htmlFor="empresa" className="block text-sm font-medium text-gray-700 mb-2">
                    <Building className="w-4 h-4 inline mr-1" />
                    Identificador da Empresa
                  </label>
                  <input
                    id="empresa"
                    type="text"
                    value={formData.empresa}
                    onChange={(e) => setFormData({ ...formData, empresa: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Usado para identificação única (sem espaços)
                  </p>
                </div>

                {/* Nome da Empresa */}
                <div>
                  <label htmlFor="nome_empresa" className="block text-sm font-medium text-gray-700 mb-2">
                    Nome Completo da Empresa
                  </label>
                  <input
                    id="nome_empresa"
                    type="text"
                    value={formData.nome_empresa}
                    onChange={(e) => setFormData({ ...formData, nome_empresa: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {/* Email */}
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                    <Mail className="w-4 h-4 inline mr-1" />
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>

                {/* Cidade */}
                <div>
                  <label htmlFor="cidade" className="block text-sm font-medium text-gray-700 mb-2">
                    Cidade
                  </label>
                  <input
                    id="cidade"
                    type="text"
                    value={formData.cidade}
                    onChange={(e) => setFormData({ ...formData, cidade: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {/* Site */}
                <div>
                  <label htmlFor="site" className="block text-sm font-medium text-gray-700 mb-2">
                    <Globe className="w-4 h-4 inline mr-1" />
                    Site
                  </label>
                  <input
                    id="site"
                    type="url"
                    value={formData.site}
                    onChange={(e) => setFormData({ ...formData, site: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="https://exemplo.com.br"
                  />
                </div>

                {/* Horário de Funcionamento */}
                <div>
                  <label htmlFor="horario" className="block text-sm font-medium text-gray-700 mb-2">
                    <Clock className="w-4 h-4 inline mr-1" />
                    Horário de Funcionamento
                  </label>
                  <input
                    id="horario"
                    type="text"
                    value={formData.horario_funcionamento}
                    onChange={(e) =>
                      setFormData({ ...formData, horario_funcionamento: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Seg-Sex: 9h-18h"
                  />
                </div>

                {/* Informações Complementares */}
                <div className="md:col-span-2">
                  <label htmlFor="info" className="block text-sm font-medium text-gray-700 mb-2">
                    Informações Complementares
                  </label>
                  <textarea
                    id="info"
                    value={formData.informacoes_complementares}
                    onChange={(e) =>
                      setFormData({ ...formData, informacoes_complementares: e.target.value })
                    }
                    rows={4}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Informações adicionais sobre sua empresa que a IA pode usar..."
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Estas informações serão usadas pela IA para personalizar o atendimento
                  </p>
                </div>
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
