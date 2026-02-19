"""
ElevenLabs Voice Calls Service
Módulo isolado para chamadas de voz IA via WhatsApp/Twilio
Pode ser ativado/desativado por empresa sem afetar o sistema principal
"""
import logging
import httpx
from datetime import datetime
from typing import Optional, Any
from enum import Enum

from ..core.config import settings

logger = logging.getLogger(__name__)


class CallChannel(str, Enum):
    """Canais disponíveis para chamadas"""
    WHATSAPP = "whatsapp"
    TWILIO = "twilio"


class CallStatus(str, Enum):
    """Status de uma chamada"""
    PENDING = "pending"
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    VOICEMAIL = "voicemail"


class VoiceCallsService:
    """
    Serviço para chamadas de voz usando ElevenLabs Conversational AI.

    Este módulo é 100% opcional e isolado:
    - Só executa se voice_calls_enabled = True na empresa
    - Falhas não afetam o sistema principal
    - Pode ser ativado/desativado a qualquer momento
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        agent_id: Optional[str] = None
    ):
        self.api_key = api_key
        self.agent_id = agent_id

    def _get_headers(self) -> dict[str, str]:
        """Headers para requisições à API"""
        return {
            "Content-Type": "application/json",
            "xi-api-key": self.api_key or ""
        }

    def is_configured(self) -> bool:
        """Verifica se o serviço está configurado"""
        return bool(self.api_key and self.agent_id)

    async def check_connection(self) -> dict[str, Any]:
        """
        Testa a conexão com ElevenLabs.
        Útil para validar API key antes de ativar o módulo.
        """
        if not self.api_key:
            return {"success": False, "error": "API key não configurada"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/user/subscription",
                    headers=self._get_headers(),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "tier": data.get("tier"),
                        "character_count": data.get("character_count"),
                        "character_limit": data.get("character_limit")
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
        except Exception as e:
            logger.error(f"Erro ao verificar conexão ElevenLabs: {e}")
            return {"success": False, "error": str(e)}

    async def initiate_whatsapp_call(
        self,
        phone_number: str,
        context: Optional[dict[str, Any]] = None,
        first_message: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Inicia uma chamada de voz via WhatsApp.

        Args:
            phone_number: Número do WhatsApp (formato internacional)
            context: Variáveis dinâmicas para o agente (nome, etc)
            first_message: Mensagem inicial customizada

        Returns:
            Dict com resultado da operação
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Serviço não configurado (API key ou Agent ID faltando)"
            }

        # Normalizar número (remover caracteres especiais)
        phone_clean = "".join(filter(str.isdigit, phone_number))
        if not phone_clean.startswith("55"):
            phone_clean = f"55{phone_clean}"

        url = f"{self.BASE_URL}/convai/whatsapp/outbound-call"

        payload = {
            "agent_id": self.agent_id,
            "whatsapp_number": phone_clean
        }

        # Adicionar variáveis dinâmicas se fornecidas
        if context:
            payload["dynamic_variables"] = context

        if first_message:
            payload["first_message"] = first_message

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=60
                )

                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(f"Chamada WhatsApp iniciada para {phone_clean}")
                    return {
                        "success": True,
                        "call_id": data.get("call_id") or data.get("conversation_id"),
                        "status": CallStatus.INITIATED,
                        "channel": CallChannel.WHATSAPP,
                        "phone": phone_clean,
                        "data": data
                    }
                else:
                    logger.error(f"Erro ao iniciar chamada: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "status": CallStatus.FAILED
                    }

        except Exception as e:
            logger.error(f"Exceção ao iniciar chamada WhatsApp: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": CallStatus.FAILED
            }

    async def initiate_twilio_call(
        self,
        phone_number: str,
        from_number: str,
        context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Inicia uma chamada de voz via Twilio (telefone tradicional).

        Args:
            phone_number: Número destino (formato internacional)
            from_number: Número Twilio de origem
            context: Variáveis dinâmicas para o agente

        Returns:
            Dict com resultado da operação
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Serviço não configurado"
            }

        phone_clean = "".join(filter(str.isdigit, phone_number))
        if not phone_clean.startswith("+"):
            phone_clean = f"+{phone_clean}"

        url = f"{self.BASE_URL}/convai/twilio/outbound-call"

        payload = {
            "agent_id": self.agent_id,
            "to": phone_clean,
            "from": from_number
        }

        if context:
            payload["dynamic_variables"] = context

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=60
                )

                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(f"Chamada Twilio iniciada para {phone_clean}")
                    return {
                        "success": True,
                        "call_id": data.get("call_sid") or data.get("call_id"),
                        "status": CallStatus.INITIATED,
                        "channel": CallChannel.TWILIO,
                        "phone": phone_clean,
                        "data": data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "status": CallStatus.FAILED
                    }

        except Exception as e:
            logger.error(f"Exceção ao iniciar chamada Twilio: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": CallStatus.FAILED
            }

    async def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """
        Obtém detalhes de uma conversa/chamada.

        Args:
            conversation_id: ID da conversa

        Returns:
            Dict com detalhes da conversa
        """
        if not self.api_key:
            return {"success": False, "error": "API key não configurada"}

        url = f"{self.BASE_URL}/convai/conversations/{conversation_id}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "data": response.json()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_agents(self) -> dict[str, Any]:
        """
        Lista agentes disponíveis na conta ElevenLabs.

        Returns:
            Dict com lista de agentes
        """
        if not self.api_key:
            return {"success": False, "error": "API key não configurada"}

        url = f"{self.BASE_URL}/convai/agents"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "agents": data.get("agents", [])
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}


class VoiceCallsManager:
    """
    Gerenciador de chamadas de voz para empresas.

    Centraliza a lógica de verificação se o módulo está ativo
    e gerencia instâncias do serviço por empresa.
    """

    def __init__(self):
        self._services: dict[int, VoiceCallsService] = {}

    async def is_enabled_for_company(self, company_id: int, supabase) -> bool:
        """
        Verifica se chamadas de voz estão ativadas para a empresa.

        Args:
            company_id: ID da empresa
            supabase: Cliente Supabase

        Returns:
            True se ativado, False caso contrário
        """
        try:
            result = supabase.table("companies").select(
                "voice_calls_enabled"
            ).eq("id", company_id).single().execute()

            if result.data:
                return result.data.get("voice_calls_enabled", False)
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar voice_calls_enabled: {e}")
            return False

    async def get_service_for_company(
        self,
        company_id: int,
        supabase
    ) -> Optional[VoiceCallsService]:
        """
        Obtém o serviço de chamadas configurado para a empresa.
        Retorna None se o módulo não estiver ativo.

        Args:
            company_id: ID da empresa
            supabase: Cliente Supabase

        Returns:
            VoiceCallsService ou None
        """
        # Verificar se está ativo
        if not await self.is_enabled_for_company(company_id, supabase):
            return None

        # Verificar cache
        if company_id in self._services:
            return self._services[company_id]

        # Buscar configuração
        try:
            result = supabase.table("companies").select(
                "voice_calls_config"
            ).eq("id", company_id).single().execute()

            if result.data and result.data.get("voice_calls_config"):
                config = result.data["voice_calls_config"]
                service = VoiceCallsService(
                    api_key=config.get("api_key"),
                    agent_id=config.get("agent_id")
                )
                self._services[company_id] = service
                return service

            return None
        except Exception as e:
            logger.error(f"Erro ao obter configuração de voice calls: {e}")
            return None

    def clear_cache(self, company_id: Optional[int] = None):
        """Limpa cache de serviços"""
        if company_id:
            self._services.pop(company_id, None)
        else:
            self._services.clear()


# Instância global do gerenciador
voice_calls_manager = VoiceCallsManager()


# Função helper para uso simplificado
async def call_lead_if_enabled(
    company_id: int,
    phone: str,
    lead_name: Optional[str] = None,
    context: Optional[dict] = None,
    supabase=None
) -> Optional[dict[str, Any]]:
    """
    Função helper para chamar um lead SE o módulo estiver ativo.
    Se não estiver ativo, simplesmente retorna None sem erros.

    Uso:
        result = await call_lead_if_enabled(
            company_id=1,
            phone="5511999999999",
            lead_name="João",
            supabase=supabase
        )
        # result é None se módulo desativado
        # result é dict com resultado se módulo ativo

    Args:
        company_id: ID da empresa
        phone: Telefone do lead
        lead_name: Nome do lead (opcional)
        context: Contexto adicional (opcional)
        supabase: Cliente Supabase

    Returns:
        Dict com resultado ou None se módulo desativado
    """
    if not supabase:
        from ..core.supabase_client import get_supabase
        supabase = get_supabase()

    service = await voice_calls_manager.get_service_for_company(company_id, supabase)

    if not service:
        # Módulo não ativo - retorna silenciosamente
        return None

    # Preparar contexto
    call_context = context or {}
    if lead_name:
        call_context["lead_name"] = lead_name

    # Fazer chamada
    return await service.initiate_whatsapp_call(
        phone_number=phone,
        context=call_context
    )
