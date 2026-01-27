'use client';
import { useState, useEffect } from 'react';
import { Header } from '@/components/layout/header';
import { Search, MessageSquare, Clock, Bot, User, Loader2 } from 'lucide-react';
import { apiGet } from '@/lib/supabase';
import { useAuth } from '@/contexts/auth-context';
import { Conversation, Lead } from '@/types';
import Link from 'next/link';

interface ConversationWithLead extends Conversation {
  lead: Lead;
  last_message_at?: string;
  unread_count?: number;
}

export default function ConversationsPage() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<ConversationWithLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  useEffect(() => {
    if (user) {
      loadConversations();
    }
  }, [user]);

  async function loadConversations() {
    try {
      const data = await apiGet<ConversationWithLead[]>(
        `/api/conversations?company_id=${user?.company_id}`
      );
      setConversations(data);
    } catch (error) {
      console.error('Error loading conversations:', error);
      setConversations([]);
    } finally {
      setLoading(false);
    }
  }

  const filteredConversations = conversations.filter((conv) => {
    const matchesSearch =
      conv.lead?.nome?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      conv.lead?.celular.includes(searchTerm);

    const matchesStatus =
      filterStatus === 'all' ||
      (filterStatus === 'active' && conv.status === 'active') ||
      (filterStatus === 'ai' && conv.ai_enabled) ||
      (filterStatus === 'human' && !conv.ai_enabled);

    return matchesSearch && matchesStatus;
  });

  if (loading) {
    return (
      <div>
        <Header title="Conversas" subtitle="Gerencie suas conversas" />
        <div className="flex items-center justify-center h-96">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="Conversas" subtitle="Gerencie suas conversas" />

      <div className="p-6">
        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar por nome ou telefone..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-11 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Status Filter */}
            <div className="flex gap-2">
              <button
                onClick={() => setFilterStatus('all')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  filterStatus === 'all'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                Todas
              </button>
              <button
                onClick={() => setFilterStatus('active')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  filterStatus === 'active'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                Ativas
              </button>
              <button
                onClick={() => setFilterStatus('ai')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  filterStatus === 'ai'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                IA
              </button>
              <button
                onClick={() => setFilterStatus('human')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  filterStatus === 'human'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                Humano
              </button>
            </div>
          </div>
        </div>

        {/* Conversations List */}
        {filteredConversations.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
            <div className="max-w-md mx-auto">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Nenhuma conversa encontrada
              </h3>
              <p className="text-gray-500">
                {searchTerm || filterStatus !== 'all'
                  ? 'Tente ajustar os filtros de busca'
                  : 'As conversas aparecerão aqui quando os leads iniciarem contato'}
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {filteredConversations.map((conversation) => (
              <Link
                key={conversation.id}
                href={`/dashboard/conversations/${conversation.id}`}
                className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:shadow-md transition-all duration-200 group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center text-white font-semibold">
                      {conversation.lead?.nome?.[0]?.toUpperCase() || 'L'}
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                        {conversation.lead?.nome || 'Sem nome'}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {conversation.lead?.celular}
                      </p>
                    </div>
                  </div>

                  {conversation.unread_count && conversation.unread_count > 0 && (
                    <span className="bg-blue-600 text-white text-xs font-semibold px-2 py-1 rounded-full">
                      {conversation.unread_count}
                    </span>
                  )}
                </div>

                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    {conversation.ai_enabled ? (
                      <span className="flex items-center gap-1.5 px-2.5 py-1 bg-green-100 text-green-700 rounded-full font-medium">
                        <Bot className="w-3 h-3" />
                        IA Ativa
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 px-2.5 py-1 bg-orange-100 text-orange-700 rounded-full font-medium">
                        <User className="w-3 h-3" />
                        Humano
                      </span>
                    )}

                    <span
                      className={`px-2.5 py-1 rounded-full font-medium ${
                        conversation.status === 'active'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {conversation.status === 'active' ? 'Ativa' : 'Inativa'}
                    </span>
                  </div>
                </div>

                {conversation.last_message_at && (
                  <div className="flex items-center gap-1 text-xs text-gray-400 mt-3 pt-3 border-t border-gray-100">
                    <Clock className="w-3 h-3" />
                    {new Date(conversation.last_message_at).toLocaleString('pt-BR', {
                      day: '2-digit',
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
