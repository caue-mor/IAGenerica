'use client';
import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Header } from '@/components/layout/header';
import {
  ArrowLeft,
  Send,
  Bot,
  User,
  Loader2,
  ToggleLeft,
  ToggleRight,
  Phone,
  Mail
} from 'lucide-react';
import { apiGet, apiPost, apiPatch } from '@/lib/supabase';
import { useAuth } from '@/contexts/auth-context';
import { Conversation, Lead, Message } from '@/types';
import Link from 'next/link';

interface ConversationWithLead extends Conversation {
  lead: Lead;
}

export default function ConversationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const conversationId = params?.id as string;
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [loading, setLoading] = useState(true);
  const [conversation, setConversation] = useState<ConversationWithLead | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (conversationId) {
      loadData();
    }
  }, [conversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  function scrollToBottom() {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }

  async function loadData() {
    try {
      const [convRes, messagesRes] = await Promise.all([
        apiGet<ConversationWithLead>(`/api/conversations/${conversationId}`),
        apiGet<Message[]>(`/api/conversations/${conversationId}/messages`),
      ]);
      setConversation(convRes);
      setMessages(messagesRes);
    } catch (error) {
      console.error('Error loading conversation:', error);
      alert('Erro ao carregar conversa');
      router.push('/dashboard/conversations');
    } finally {
      setLoading(false);
    }
  }

  async function handleSendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!newMessage.trim() || !conversation) return;

    setSending(true);
    try {
      const message = await apiPost<Message>('/api/messages', {
        conversation_id: conversation.id,
        lead_id: conversation.lead_id,
        direction: 'outbound',
        message_type: 'text',
        content: newMessage,
      });

      setMessages([...messages, message]);
      setNewMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
      alert('Erro ao enviar mensagem');
    } finally {
      setSending(false);
    }
  }

  async function toggleAI() {
    if (!conversation) return;

    try {
      const updated = await apiPatch<ConversationWithLead>(
        `/api/conversations/${conversationId}`,
        { ai_enabled: !conversation.ai_enabled }
      );
      setConversation(updated);
    } catch (error) {
      console.error('Error toggling AI:', error);
      alert('Erro ao alterar modo IA');
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

  if (!conversation) {
    return null;
  }

  return (
    <div className="h-screen flex flex-col">
      <Header
        title={conversation.lead?.nome || 'Conversa'}
        subtitle={conversation.lead?.celular}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col bg-gray-50">
          {/* Chat Header */}
          <div className="bg-white border-b p-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/dashboard/conversations"
                className="text-gray-600 hover:text-gray-900"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center text-white font-semibold text-lg">
                {conversation.lead?.nome?.[0]?.toUpperCase() || 'L'}
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">
                  {conversation.lead?.nome || 'Sem nome'}
                </h3>
                <div className="flex items-center gap-3 text-sm text-gray-500">
                  <span className="flex items-center gap-1">
                    <Phone className="w-3 h-3" />
                    {conversation.lead?.celular}
                  </span>
                  {conversation.lead?.email && (
                    <span className="flex items-center gap-1">
                      <Mail className="w-3 h-3" />
                      {conversation.lead.email}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* AI Toggle */}
            <button
              onClick={toggleAI}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                conversation.ai_enabled
                  ? 'bg-green-100 text-green-700 hover:bg-green-200'
                  : 'bg-orange-100 text-orange-700 hover:bg-orange-200'
              }`}
            >
              {conversation.ai_enabled ? (
                <>
                  <Bot className="w-5 h-5" />
                  <span>IA Ativa</span>
                  <ToggleRight className="w-5 h-5" />
                </>
              ) : (
                <>
                  <User className="w-5 h-5" />
                  <span>Modo Humano</span>
                  <ToggleLeft className="w-5 h-5" />
                </>
              )}
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                Nenhuma mensagem ainda
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${
                    message.direction === 'outbound' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  <div
                    className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                      message.direction === 'outbound'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-gray-900 shadow-sm border border-gray-200'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap break-words">
                      {message.content}
                    </p>
                    <p
                      className={`text-xs mt-1 ${
                        message.direction === 'outbound'
                          ? 'text-blue-200'
                          : 'text-gray-400'
                      }`}
                    >
                      {new Date(message.created_at).toLocaleString('pt-BR', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="bg-white border-t p-4">
            {conversation.ai_enabled && (
              <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
                A IA está ativa. Suas mensagens manuais podem interferir no fluxo automático.
              </div>
            )}
            <form onSubmit={handleSendMessage} className="flex gap-3">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Digite uma mensagem..."
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={sending}
              />
              <button
                type="submit"
                disabled={sending || !newMessage.trim()}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {sending ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-80 bg-white border-l p-6 overflow-y-auto">
          <h3 className="font-semibold text-gray-900 mb-4">Informações do Lead</h3>

          <div className="space-y-4">
            <div>
              <label className="text-xs text-gray-500 uppercase font-medium">Nome</label>
              <p className="text-sm text-gray-900 mt-1">
                {conversation.lead?.nome || 'Não informado'}
              </p>
            </div>

            <div>
              <label className="text-xs text-gray-500 uppercase font-medium">Celular</label>
              <p className="text-sm text-gray-900 mt-1">{conversation.lead?.celular}</p>
            </div>

            {conversation.lead?.email && (
              <div>
                <label className="text-xs text-gray-500 uppercase font-medium">Email</label>
                <p className="text-sm text-gray-900 mt-1">{conversation.lead.email}</p>
              </div>
            )}

            {conversation.lead?.origem && (
              <div>
                <label className="text-xs text-gray-500 uppercase font-medium">Origem</label>
                <p className="text-sm text-gray-900 mt-1">{conversation.lead.origem}</p>
              </div>
            )}

            <div className="pt-4 border-t border-gray-200">
              <label className="text-xs text-gray-500 uppercase font-medium">
                Status da Conversa
              </label>
              <p className="text-sm text-gray-900 mt-1 capitalize">
                {conversation.status}
              </p>
            </div>

            <div>
              <label className="text-xs text-gray-500 uppercase font-medium">
                Thread ID
              </label>
              <p className="text-xs text-gray-600 mt-1 font-mono break-all">
                {conversation.thread_id}
              </p>
            </div>
          </div>

          <div className="mt-6">
            <Link
              href={`/dashboard/leads/${conversation.lead_id}`}
              className="block w-full text-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Ver Detalhes do Lead
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
