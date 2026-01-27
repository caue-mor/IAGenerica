'use client';
import { useState } from 'react';
import { Header } from '@/components/layout/header';
import {
  Bell,
  BellOff,
  CheckCheck,
  Clock,
  MessageSquare,
  UserPlus,
  AlertCircle,
  Trash2
} from 'lucide-react';

interface Notification {
  id: number;
  type: 'message' | 'lead' | 'alert' | 'system';
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  link?: string;
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([
    {
      id: 1,
      type: 'message',
      title: 'Nova mensagem recebida',
      message: 'João Silva enviou uma nova mensagem',
      read: false,
      created_at: new Date().toISOString(),
      link: '/dashboard/conversations/1'
    },
    {
      id: 2,
      type: 'lead',
      title: 'Novo lead cadastrado',
      message: 'Maria Santos foi adicionada como lead',
      read: false,
      created_at: new Date(Date.now() - 3600000).toISOString(),
      link: '/dashboard/leads/2'
    },
    {
      id: 3,
      type: 'alert',
      title: 'Erro no envio de mensagem',
      message: 'Falha ao enviar mensagem para +5511999999999',
      read: true,
      created_at: new Date(Date.now() - 7200000).toISOString(),
    },
    {
      id: 4,
      type: 'system',
      title: 'Sistema atualizado',
      message: 'Nova versão do sistema foi instalada',
      read: true,
      created_at: new Date(Date.now() - 86400000).toISOString(),
    },
  ]);

  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  function markAsRead(id: number) {
    setNotifications(notifications.map(n =>
      n.id === id ? { ...n, read: true } : n
    ));
  }

  function markAllAsRead() {
    setNotifications(notifications.map(n => ({ ...n, read: true })));
  }

  function deleteNotification(id: number) {
    setNotifications(notifications.filter(n => n.id !== id));
  }

  function getIcon(type: string) {
    switch (type) {
      case 'message':
        return <MessageSquare className="w-5 h-5" />;
      case 'lead':
        return <UserPlus className="w-5 h-5" />;
      case 'alert':
        return <AlertCircle className="w-5 h-5" />;
      case 'system':
        return <Bell className="w-5 h-5" />;
      default:
        return <Bell className="w-5 h-5" />;
    }
  }

  function getIconColor(type: string) {
    switch (type) {
      case 'message':
        return 'bg-blue-100 text-blue-600';
      case 'lead':
        return 'bg-green-100 text-green-600';
      case 'alert':
        return 'bg-red-100 text-red-600';
      case 'system':
        return 'bg-gray-100 text-gray-600';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  }

  const filteredNotifications = notifications.filter(n =>
    filter === 'all' || !n.read
  );

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <div>
      <Header
        title="Notificações"
        subtitle={`${unreadCount} não ${unreadCount === 1 ? 'lida' : 'lidas'}`}
      />

      <div className="p-6">
        <div className="max-w-4xl mx-auto">
          {/* Actions Bar */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex gap-2">
                <button
                  onClick={() => setFilter('all')}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    filter === 'all'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  Todas
                </button>
                <button
                  onClick={() => setFilter('unread')}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    filter === 'unread'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  Não lidas ({unreadCount})
                </button>
              </div>

              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  <CheckCheck className="w-4 h-4" />
                  Marcar todas como lidas
                </button>
              )}
            </div>
          </div>

          {/* Notifications List */}
          {filteredNotifications.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <BellOff className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Nenhuma notificação
              </h3>
              <p className="text-gray-500">
                {filter === 'unread'
                  ? 'Você leu todas as notificações'
                  : 'Você não tem notificações ainda'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredNotifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`bg-white rounded-xl shadow-sm border p-4 transition-all duration-200 hover:shadow-md ${
                    notification.read ? 'border-gray-200' : 'border-blue-200 bg-blue-50/30'
                  }`}
                >
                  <div className="flex gap-4">
                    {/* Icon */}
                    <div className={`p-3 rounded-lg ${getIconColor(notification.type)} flex-shrink-0`}>
                      {getIcon(notification.type)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 mb-1">
                            {notification.title}
                          </h3>
                          <p className="text-sm text-gray-600">{notification.message}</p>
                          <div className="flex items-center gap-1 text-xs text-gray-400 mt-2">
                            <Clock className="w-3 h-3" />
                            {new Date(notification.created_at).toLocaleString('pt-BR', {
                              day: '2-digit',
                              month: 'short',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2">
                          {!notification.read && (
                            <button
                              onClick={() => markAsRead(notification.id)}
                              className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                              title="Marcar como lida"
                            >
                              <CheckCheck className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => deleteNotification(notification.id)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Excluir"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {/* Link */}
                      {notification.link && (
                        <a
                          href={notification.link}
                          className="inline-block mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium"
                        >
                          Ver detalhes →
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
