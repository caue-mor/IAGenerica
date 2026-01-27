'use client';
import { useEffect, useState } from 'react';
import { Header } from '@/components/layout/header';
import { Users, MessageSquare, TrendingUp, Clock, ArrowUpRight } from 'lucide-react';
import { apiGet } from '@/lib/supabase';
import { useAuth } from '@/contexts/auth-context';
import Link from 'next/link';

interface DashboardStats {
  total_leads: number;
  leads_hoje: number;
  conversas_ativas: number;
  mensagens_hoje: number;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats>({
    total_leads: 0,
    leads_hoje: 0,
    conversas_ativas: 0,
    mensagens_hoje: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  async function loadStats() {
    try {
      // In production, fetch from API
      // const data = await apiGet<DashboardStats>(`/api/dashboard/stats?company_id=${user?.company_id}`);
      // For now, using mock data
      setStats({
        total_leads: 0,
        leads_hoje: 0,
        conversas_ativas: 0,
        mensagens_hoje: 0,
      });
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
    }
  }

  const statCards = [
    {
      title: 'Total de Leads',
      value: stats.total_leads,
      icon: Users,
      color: 'blue',
      change: '+12%',
      href: '/dashboard/leads'
    },
    {
      title: 'Leads Hoje',
      value: stats.leads_hoje,
      icon: TrendingUp,
      color: 'green',
      change: '+5',
      href: '/dashboard/leads'
    },
    {
      title: 'Conversas Ativas',
      value: stats.conversas_ativas,
      icon: MessageSquare,
      color: 'purple',
      change: '8 ativos',
      href: '/dashboard/conversations'
    },
    {
      title: 'Mensagens Hoje',
      value: stats.mensagens_hoje,
      icon: Clock,
      color: 'orange',
      change: '+23%',
      href: '/dashboard/conversations'
    },
  ];

  const getColorClasses = (color: string) => {
    const colors = {
      blue: 'bg-blue-50 text-blue-600',
      green: 'bg-green-50 text-green-600',
      purple: 'bg-purple-50 text-purple-600',
      orange: 'bg-orange-50 text-orange-600',
    };
    return colors[color as keyof typeof colors] || colors.blue;
  };

  return (
    <div>
      <Header title="Dashboard" subtitle="Visão geral do sistema" />

      <div className="p-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {statCards.map((card) => (
            <Link
              key={card.title}
              href={card.href}
              className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all duration-200 group"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="text-sm text-gray-600 mb-1">{card.title}</p>
                  <p className="text-3xl font-bold text-gray-900 mb-2">
                    {loading ? '...' : card.value}
                  </p>
                  <p className="text-xs text-gray-500">{card.change}</p>
                </div>
                <div className={`p-3 rounded-lg ${getColorClasses(card.color)}`}>
                  <card.icon className="w-6 h-6" />
                </div>
              </div>
              <ArrowUpRight className="w-4 h-4 text-gray-400 mt-4 opacity-0 group-hover:opacity-100 transition-opacity" />
            </Link>
          ))}
        </div>

        {/* Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Leads */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Leads Recentes</h2>
              <Link
                href="/dashboard/leads"
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Ver todos
              </Link>
            </div>
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                    <Users className="w-5 h-5 text-gray-600" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">Novo Lead</p>
                    <p className="text-xs text-gray-500">Há 2 minutos</p>
                  </div>
                </div>
              ))}
              {stats.total_leads === 0 && (
                <p className="text-sm text-gray-500 text-center py-8">
                  Nenhum lead cadastrado ainda
                </p>
              )}
            </div>
          </div>

          {/* Recent Conversations */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Conversas Recentes</h2>
              <Link
                href="/dashboard/conversations"
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Ver todas
              </Link>
            </div>
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                    <MessageSquare className="w-5 h-5 text-green-600" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">Nova conversa</p>
                    <p className="text-xs text-gray-500">Há 5 minutos</p>
                  </div>
                </div>
              ))}
              {stats.conversas_ativas === 0 && (
                <p className="text-sm text-gray-500 text-center py-8">
                  Nenhuma conversa ativa
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-8 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl shadow-lg p-6 text-white">
          <h2 className="text-xl font-semibold mb-4">Começar</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link
              href="/dashboard/leads/novo"
              className="bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-4 transition-all"
            >
              <Users className="w-8 h-8 mb-2" />
              <h3 className="font-medium mb-1">Adicionar Lead</h3>
              <p className="text-sm text-blue-100">Cadastre um novo contato</p>
            </Link>
            <Link
              href="/dashboard/flow-builder"
              className="bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-4 transition-all"
            >
              <MessageSquare className="w-8 h-8 mb-2" />
              <h3 className="font-medium mb-1">Configurar Fluxo</h3>
              <p className="text-sm text-blue-100">Crie seu atendimento</p>
            </Link>
            <Link
              href="/dashboard/settings/whatsapp"
              className="bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-4 transition-all"
            >
              <Clock className="w-8 h-8 mb-2" />
              <h3 className="font-medium mb-1">Configurar WhatsApp</h3>
              <p className="text-sm text-blue-100">Conecte sua conta</p>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
