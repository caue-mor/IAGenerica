'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Header } from '@/components/layout/header';
import {
  Phone,
  QrCode,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  User
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
interface WhatsAppStatus {
  connected: boolean;
  status: 'connected' | 'disconnected' | 'connecting';
  phone?: string;
  profile_name?: string;
  last_connected?: string;
}

interface ConnectResponse {
  qr_code?: string;
  status: string;
  message?: string;
}

export default function WhatsAppSettingsPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [whatsappStatus, setWhatsappStatus] = useState<WhatsAppStatus>({
    connected: false,
    status: 'disconnected'
  });

  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [phone, setPhone] = useState('');
  const [qrCode, setQrCode] = useState('');
  const [isGeneratingQr, setIsGeneratingQr] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState('');

  // Refs for polling
  const statusPollInterval = useRef<NodeJS.Timeout | null>(null);
  const qrRefreshInterval = useRef<NodeJS.Timeout | null>(null);

  // Load initial status
  useEffect(() => {
    if (user?.company_id) {
      loadWhatsAppStatus();
    }
  }, [user]);

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      stopStatusPolling();
      stopQrRefresh();
    };
  }, []);

  /**
   * Load WhatsApp connection status from API
   */
  const loadWhatsAppStatus = async () => {
    if (!user?.company_id) return;

    try {
      const data = await apiGet<WhatsAppStatus>(
        `/api/whatsapp/status/${user.company_id}`
      );
      setWhatsappStatus(data);
    } catch (error) {
      console.error('Error loading WhatsApp status:', error);
      setWhatsappStatus({
        connected: false,
        status: 'disconnected'
      });
    } finally {
      setLoading(false);
    }
  };

  /**
   * Start polling status every 3 seconds while connecting
   */
  const startStatusPolling = useCallback(() => {
    if (statusPollInterval.current) return;

    statusPollInterval.current = setInterval(async () => {
      if (!user?.company_id) return;

      try {
        const data = await apiGet<WhatsAppStatus>(
          `/api/whatsapp/status/${user.company_id}`
        );
        setWhatsappStatus(data);

        // Stop polling and close modal when connected
        if (data.connected && data.status === 'connected') {
          setIsConnecting(false);
          stopStatusPolling();
          stopQrRefresh();
          setTimeout(() => {
            setIsModalOpen(false);
            setQrCode('');
            setPhone('');
          }, 1000);
        }
      } catch (error) {
        console.error('Error polling status:', error);
      }
    }, 3000);
  }, [user]);

  /**
   * Stop status polling
   */
  const stopStatusPolling = () => {
    if (statusPollInterval.current) {
      clearInterval(statusPollInterval.current);
      statusPollInterval.current = null;
    }
  };

  /**
   * Start QR code refresh every 90 seconds
   */
  const startQrRefresh = useCallback(() => {
    if (qrRefreshInterval.current) return;

    qrRefreshInterval.current = setInterval(async () => {
      if (!user?.company_id || !phone) return;

      try {
        await generateQrCode();
      } catch (error) {
        console.error('Error refreshing QR code:', error);
      }
    }, 90000); // 90 seconds
  }, [user, phone]);

  /**
   * Stop QR code refresh
   */
  const stopQrRefresh = () => {
    if (qrRefreshInterval.current) {
      clearInterval(qrRefreshInterval.current);
      qrRefreshInterval.current = null;
    }
  };

  /**
   * Generate QR code for WhatsApp connection
   */
  const generateQrCode = async () => {
    if (!user?.company_id || !phone) {
      setConnectionError('Por favor, insira um número de telefone');
      return;
    }

    setIsGeneratingQr(true);
    setConnectionError('');

    try {
      const data = await apiPost<ConnectResponse>('/api/whatsapp/connect', {
        company_id: user.company_id,
        phone: phone,
        type: 'qrcode'
      });

      if (data.qr_code) {
        setQrCode(data.qr_code);
        setIsConnecting(true);

        // Start polling for connection status
        startStatusPolling();

        // Start QR refresh timer
        startQrRefresh();
      } else {
        setConnectionError(data.message || 'Erro ao gerar QR Code');
      }
    } catch (error: any) {
      console.error('Error generating QR code:', error);
      setConnectionError(
        error.message || 'Erro ao gerar QR Code. Tente novamente.'
      );
    } finally {
      setIsGeneratingQr(false);
    }
  };

  /**
   * Disconnect WhatsApp
   */
  const handleDisconnect = async () => {
    if (!user?.company_id) return;

    if (!confirm('Tem certeza que deseja desconectar o WhatsApp?')) {
      return;
    }

    try {
      await apiPost('/api/whatsapp/disconnect', {
        company_id: user.company_id
      });

      // Reload status
      await loadWhatsAppStatus();
    } catch (error) {
      console.error('Error disconnecting WhatsApp:', error);
      alert('Erro ao desconectar WhatsApp');
    }
  };

  /**
   * Open connection modal
   */
  const openConnectionModal = () => {
    setIsModalOpen(true);
    setQrCode('');
    setPhone('');
    setConnectionError('');
    setIsConnecting(false);
  };

  /**
   * Close connection modal and cleanup
   */
  const closeConnectionModal = () => {
    setIsModalOpen(false);
    stopStatusPolling();
    stopQrRefresh();
    setQrCode('');
    setPhone('');
    setConnectionError('');
    setIsConnecting(false);
  };

  /**
   * Format phone number for display
   */
  const formatPhoneNumber = (phoneNumber?: string) => {
    if (!phoneNumber) return '';

    // Remove +55 prefix if exists
    const cleaned = phoneNumber.replace(/^\+?55/, '');

    // Format as (XX) XXXXX-XXXX
    if (cleaned.length === 11) {
      return `(${cleaned.slice(0, 2)}) ${cleaned.slice(2, 7)}-${cleaned.slice(7)}`;
    }

    return phoneNumber;
  };

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

          {/* Connection Status Card */}
          <Card className="mb-6">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-lg ${
                    whatsappStatus.connected
                      ? 'bg-green-100'
                      : whatsappStatus.status === 'connecting'
                      ? 'bg-yellow-100'
                      : 'bg-gray-100'
                  }`}>
                    {whatsappStatus.connected ? (
                      <CheckCircle className="w-6 h-6 text-green-600" />
                    ) : whatsappStatus.status === 'connecting' ? (
                      <Loader2 className="w-6 h-6 text-yellow-600 animate-spin" />
                    ) : (
                      <XCircle className="w-6 h-6 text-gray-400" />
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <CardTitle className="text-xl">Status da Conexão</CardTitle>
                      <Badge
                        variant={
                          whatsappStatus.connected
                            ? 'success'
                            : whatsappStatus.status === 'connecting'
                            ? 'warning'
                            : 'secondary'
                        }
                      >
                        {whatsappStatus.connected
                          ? 'Conectado'
                          : whatsappStatus.status === 'connecting'
                          ? 'Conectando'
                          : 'Desconectado'}
                      </Badge>
                    </div>
                    <CardDescription>
                      {whatsappStatus.connected
                        ? 'WhatsApp conectado e funcionando'
                        : whatsappStatus.status === 'connecting'
                        ? 'Aguardando conexão com WhatsApp'
                        : 'Conecte seu WhatsApp para começar'}
                    </CardDescription>
                  </div>
                </div>
              </div>
            </CardHeader>

            <CardContent>
              {whatsappStatus.connected && (
                <div className="space-y-3 mb-4">
                  {whatsappStatus.profile_name && (
                    <div className="flex items-center gap-2 text-sm">
                      <User className="w-4 h-4 text-gray-500" />
                      <span className="text-gray-600">Nome:</span>
                      <span className="font-medium">{whatsappStatus.profile_name}</span>
                    </div>
                  )}

                  {whatsappStatus.phone && (
                    <div className="flex items-center gap-2 text-sm">
                      <Phone className="w-4 h-4 text-gray-500" />
                      <span className="text-gray-600">Número:</span>
                      <span className="font-medium">
                        {formatPhoneNumber(whatsappStatus.phone)}
                      </span>
                    </div>
                  )}
                </div>
              )}

              <div className="flex gap-3">
                {whatsappStatus.connected ? (
                  <Button
                    onClick={handleDisconnect}
                    variant="destructive"
                  >
                    <XCircle className="w-4 h-4 mr-2" />
                    Desconectar
                  </Button>
                ) : (
                  <Button
                    onClick={openConnectionModal}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    <QrCode className="w-4 h-4 mr-2" />
                    Conectar WhatsApp
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Info Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <AlertCircle className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <CardTitle className="text-lg">Como conectar</CardTitle>
                  <CardDescription>
                    Siga os passos para conectar seu WhatsApp
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700">
                <li>Clique em "Conectar WhatsApp"</li>
                <li>Digite seu número de telefone com DDD</li>
                <li>Clique em "Gerar QR Code"</li>
                <li>Abra o WhatsApp no seu celular</li>
                <li>Toque em Menu (três pontos) e depois em "Aparelhos conectados"</li>
                <li>Toque em "Conectar um aparelho"</li>
                <li>Aponte seu celular para o QR Code na tela</li>
                <li>Aguarde a confirmação da conexão</li>
              </ol>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Connection Modal */}
      <Dialog open={isModalOpen} onOpenChange={closeConnectionModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Conectar WhatsApp</DialogTitle>
            <DialogDescription>
              {!qrCode
                ? 'Digite seu número de telefone para gerar o QR Code'
                : isConnecting
                ? 'Escaneie o QR Code com seu WhatsApp'
                : 'QR Code gerado com sucesso'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {!qrCode ? (
              <>
                {/* Phone Input */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Número do WhatsApp
                  </label>
                  <div className="flex gap-2">
                    <div className="flex items-center px-3 bg-gray-100 rounded-md border border-gray-200">
                      <span className="text-sm text-gray-600">+55</span>
                    </div>
                    <Input
                      type="tel"
                      placeholder="11999999999"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
                      maxLength={11}
                      className="flex-1"
                    />
                  </div>
                  <p className="text-xs text-gray-500">
                    Digite apenas números: DDD + número
                  </p>
                </div>

                {connectionError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-800">{connectionError}</p>
                  </div>
                )}

                <Button
                  onClick={generateQrCode}
                  disabled={!phone || phone.length < 10 || isGeneratingQr}
                  className="w-full bg-green-600 hover:bg-green-700"
                >
                  {isGeneratingQr ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Gerando...
                    </>
                  ) : (
                    <>
                      <QrCode className="w-4 h-4 mr-2" />
                      Gerar QR Code
                    </>
                  )}
                </Button>
              </>
            ) : (
              <>
                {/* QR Code Display */}
                <div className="flex flex-col items-center justify-center space-y-4">
                  <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                    <img
                      src={qrCode}
                      alt="QR Code WhatsApp"
                      className="w-64 h-64"
                    />
                  </div>

                  {isConnecting && (
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Aguardando conexão...</span>
                    </div>
                  )}

                  <p className="text-xs text-center text-gray-500">
                    O QR Code será atualizado automaticamente a cada 90 segundos
                  </p>

                  <Button
                    onClick={generateQrCode}
                    variant="outline"
                    disabled={isGeneratingQr}
                    className="w-full"
                  >
                    {isGeneratingQr ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Atualizando...
                      </>
                    ) : (
                      'Atualizar QR Code'
                    )}
                  </Button>
                </div>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
