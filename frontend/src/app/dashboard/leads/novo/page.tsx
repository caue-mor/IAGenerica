'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Header } from '@/components/layout/header';
import { Save, Loader2, ArrowLeft } from 'lucide-react';
import { apiPost, apiGet } from '@/lib/supabase';
import { useAuth } from '@/contexts/auth-context';
import { LeadStatus } from '@/types';
import Link from 'next/link';

export default function NovoLeadPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [statuses, setStatuses] = useState<LeadStatus[]>([]);
  const [formData, setFormData] = useState({
    nome: '',
    celular: '',
    email: '',
    origem: '',
    status_id: undefined as number | undefined,
    ai_enabled: true,
  });

  useEffect(() => {
    loadStatuses();
  }, []);

  async function loadStatuses() {
    try {
      const statusesRes = await apiGet<LeadStatus[]>(
        `/api/lead-statuses/${user?.company_id}`
      );
      setStatuses(statusesRes);
      // Set default status
      const defaultStatus = statusesRes.find(s => s.is_default);
      if (defaultStatus) {
        setFormData(prev => ({ ...prev, status_id: defaultStatus.id }));
      }
    } catch (error) {
      console.error('Error loading statuses:', error);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    try {
      await apiPost('/api/leads', {
        ...formData,
        company_id: user?.company_id,
      });
      router.push('/dashboard/leads');
    } catch (error) {
      console.error('Error creating lead:', error);
      alert('Erro ao criar lead');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <Header title="Novo Lead" subtitle="Cadastre um novo contato" />

      <div className="p-6">
        <div className="max-w-2xl mx-auto">
          <Link
            href="/dashboard/leads"
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-6"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para lista
          </Link>

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
                    placeholder="João Silva"
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
                    placeholder="5511999999999"
                    required
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Formato: 5511999999999 (com DDI e DDD)
                  </p>
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
                    placeholder="joao@exemplo.com"
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
                    placeholder="Instagram, Google Ads, etc."
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
              <div className="flex items-center justify-end gap-4 pt-6 border-t border-gray-200">
                <Link
                  href="/dashboard/leads"
                  className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancelar
                </Link>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors"
                >
                  {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                  <Save className="w-4 h-4" />
                  {loading ? 'Salvando...' : 'Salvar Lead'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
