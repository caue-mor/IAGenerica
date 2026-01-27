'use client';
import { useState, useEffect } from 'react';
import { Header } from '@/components/layout/header';
import { Save, Loader2, Phone, QrCode, CheckCircle, XCircle } from 'lucide-react';
import { apiGet, apiPatch, apiPost } from '@/lib/supabase';
import { useAuth } from '@/contexts/auth-context';
import { Company } from '@/types';
import Link from 'next/link';

export default function WhatsAppSettingsPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [company, setCompany] = useState<Company | null>(null);
  const [formData, setFormData] = useState({
    uazapi_instancia: '',
    uazapi_token: '',
    whatsapp_numero: '',
  });
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'unknown'>('unknown');

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
        uazapi_instancia: data.uazapi_instancia || '',
        uazapi_token: data.uazapi_token || '',
        whatsapp_numero: data.whatsapp_numero || '',
      });

      if (data.uazapi_instancia && data.uazapi_token) {
        setConnectionStatus('connected');
      } else {
        setConnectionStatus('disconnected');
      }
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
      alert('Configurações do WhatsApp salvas com sucesso!');
      loadCompany();
    } catch (error) {
      console.error('Error saving settings:', error);
      alert('Erro ao salvar configurações');
    } finally {
      setSaving(false);
    }
  }

  async function testConnection() {
    try {
      // Implementar teste de conexão com UazAPI
      alert('Teste de conexão será implementado');
    } catch (error) {
      console.error('Error testing connection:', error);
    }
  }

  if (loading) {
    return (
      <div>
        <Header title="WhatsApp" subtitle="Configure sua conexão" />
        <div className="flex items-center justify-center h-96">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="WhatsApp" subtitle="Configure sua conexão com WhatsApp" />

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
                className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium whitespace-nowrap"
              >
                WhatsApp
              </Link>
            </div>
          </div>

          {/* Connection Status */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-lg ${
                  connectionStatus === 'connected' ? 'bg-green-100' : 'bg-gray-100'
                }`}>
                  {connectionStatus === 'connected' ? (
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  ) : (
                    <XCircle className="w-6 h-6 text-gray-400" />
                  )}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Status da Conexão</h3>
                  <p className="text-sm text-gray-500">
                    {connectionStatus === 'connected' ? 'Conectado ao WhatsApp' : 'Não conectado'}
                  </p>
                </div>
              </div>

              {connectionStatus === 'connected' && (
                <button
                  onClick={testConnection}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                >
                  Testar Conexão
                </button>
              )}
            </div>
          </div>

          {/* Form */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-3 bg-gradient-to-br from-green-500 to-emerald-600 rounded-lg">
                <Phone className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Configurações UazAPI
                </h2>
                <p className="text-sm text-gray-500">
                  Configure sua instância do WhatsApp
                </p>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Instância */}
              <div>
                <label htmlFor="instancia" className="block text-sm font-medium text-gray-700 mb-2">
                  Nome da Instância
                </label>
                <input
                  id="instancia"
                  type="text"
                  value={formData.uazapi_instancia}
                  onChange={(e) => setFormData({ ...formData, uazapi_instancia: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="minha-instancia"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Nome da sua instância no UazAPI
                </p>
              </div>

              {/* Token */}
              <div>
                <label htmlFor="token" className="block text-sm font-medium text-gray-700 mb-2">
                  Token de Acesso
                </label>
                <input
                  id="token"
                  type="password"
                  value={formData.uazapi_token}
                  onChange={(e) => setFormData({ ...formData, uazapi_token: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="••••••••••••••••"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Token de autenticação da API
                </p>
              </div>

              {/* Número WhatsApp */}
              <div>
                <label htmlFor="numero" className="block text-sm font-medium text-gray-700 mb-2">
                  Número do WhatsApp
                </label>
                <input
                  id="numero"
                  type="tel"
                  value={formData.whatsapp_numero}
                  onChange={(e) => setFormData({ ...formData, whatsapp_numero: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="5511999999999"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Número com DDI e DDD (ex: 5511999999999)
                </p>
              </div>

              {/* Info Box */}
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <QrCode className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-blue-800">
                    <p className="font-medium mb-1">Como obter suas credenciais:</p>
                    <ol className="list-decimal list-inside space-y-1 text-blue-700">
                      <li>Acesse o painel do UazAPI</li>
                      <li>Crie uma nova instância ou use uma existente</li>
                      <li>Copie o nome da instância e o token</li>
                      <li>Cole os dados aqui e salve</li>
                    </ol>
                  </div>
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
