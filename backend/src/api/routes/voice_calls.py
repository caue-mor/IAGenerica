"""
Voice Calls API Routes
Rotas para configurar e gerenciar o módulo de chamadas de voz
"""
import logging
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ...core.supabase_client import get_supabase
from ...services.voice_calls import (
    VoiceCallsService,
    voice_calls_manager,
    call_lead_if_enabled,
    CallChannel,
    CallStatus
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice-calls", tags=["voice-calls"])


# ============================================================
# SCHEMAS
# ============================================================

class VoiceCallsConfigSchema(BaseModel):
    """Configuração do módulo de chamadas"""
    api_key: str = Field(..., description="ElevenLabs API Key")
    agent_id: str = Field(..., description="ID do agente ElevenLabs")
    whatsapp_number_id: Optional[str] = Field(None, description="ID do número WhatsApp Business")
    twilio_from_number: Optional[str] = Field(None, description="Número Twilio de origem")


class VoiceCallsToggleSchema(BaseModel):
    """Schema para ativar/desativar o módulo"""
    enabled: bool


class InitiateCallSchema(BaseModel):
    """Schema para iniciar uma chamada"""
    phone: str = Field(..., description="Número de telefone do destino")
    lead_name: Optional[str] = Field(None, description="Nome do lead")
    lead_id: Optional[int] = Field(None, description="ID do lead no sistema")
    context: Optional[dict[str, Any]] = Field(None, description="Variáveis dinâmicas")
    channel: CallChannel = Field(CallChannel.WHATSAPP, description="Canal da chamada")
    first_message: Optional[str] = Field(None, description="Mensagem inicial customizada")


class VoiceCallsStatusResponse(BaseModel):
    """Resposta de status do módulo"""
    enabled: bool
    configured: bool
    agent_id: Optional[str] = None
    connection_status: Optional[dict] = None


# ============================================================
# ROUTES
# ============================================================

@router.get("/status/{company_id}", response_model=VoiceCallsStatusResponse)
async def get_voice_calls_status(company_id: int):
    """
    Retorna o status do módulo de chamadas para a empresa.

    - **enabled**: Se o toggle está ligado
    - **configured**: Se as credenciais estão configuradas
    - **connection_status**: Status da conexão com ElevenLabs
    """
    supabase = get_supabase()

    try:
        result = supabase.table("companies").select(
            "voice_calls_enabled, voice_calls_config"
        ).eq("id", company_id).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        enabled = result.data.get("voice_calls_enabled", False)
        config = result.data.get("voice_calls_config") or {}

        response = VoiceCallsStatusResponse(
            enabled=enabled,
            configured=bool(config.get("api_key") and config.get("agent_id")),
            agent_id=config.get("agent_id")
        )

        # Se configurado, testar conexão
        if response.configured:
            service = VoiceCallsService(
                api_key=config.get("api_key"),
                agent_id=config.get("agent_id")
            )
            response.connection_status = await service.check_connection()

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/toggle/{company_id}")
async def toggle_voice_calls(company_id: int, data: VoiceCallsToggleSchema):
    """
    Ativa ou desativa o módulo de chamadas de voz.

    - Se **enabled=true**: IA pode fazer ligações
    - Se **enabled=false**: Sistema continua normal, sem chamadas
    """
    supabase = get_supabase()

    try:
        # Verificar se empresa existe
        check = supabase.table("companies").select("id").eq("id", company_id).single().execute()
        if not check.data:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        # Atualizar toggle
        result = supabase.table("companies").update({
            "voice_calls_enabled": data.enabled
        }).eq("id", company_id).execute()

        # Limpar cache
        voice_calls_manager.clear_cache(company_id)

        logger.info(f"Voice calls {'ativado' if data.enabled else 'desativado'} para empresa {company_id}")

        return {
            "success": True,
            "voice_calls_enabled": data.enabled,
            "message": f"Chamadas de voz {'ativadas' if data.enabled else 'desativadas'}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao alterar toggle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configure/{company_id}")
async def configure_voice_calls(company_id: int, config: VoiceCallsConfigSchema):
    """
    Configura as credenciais do módulo de chamadas.

    Necessário antes de ativar o módulo:
    - **api_key**: Chave da API ElevenLabs
    - **agent_id**: ID do agente conversacional no ElevenLabs
    """
    supabase = get_supabase()

    try:
        # Verificar se empresa existe
        check = supabase.table("companies").select("id").eq("id", company_id).single().execute()
        if not check.data:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        # Validar credenciais antes de salvar
        test_service = VoiceCallsService(
            api_key=config.api_key,
            agent_id=config.agent_id
        )
        connection_test = await test_service.check_connection()

        if not connection_test.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Credenciais inválidas: {connection_test.get('error')}"
            )

        # Salvar configuração
        config_data = {
            "api_key": config.api_key,
            "agent_id": config.agent_id,
            "whatsapp_number_id": config.whatsapp_number_id,
            "twilio_from_number": config.twilio_from_number
        }

        result = supabase.table("companies").update({
            "voice_calls_config": config_data
        }).eq("id", company_id).execute()

        # Limpar cache
        voice_calls_manager.clear_cache(company_id)

        logger.info(f"Voice calls configurado para empresa {company_id}")

        return {
            "success": True,
            "message": "Configuração salva com sucesso",
            "connection_test": connection_test
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao configurar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/call/{company_id}")
async def initiate_call(company_id: int, data: InitiateCallSchema):
    """
    Inicia uma chamada de voz para um número.

    Só funciona se o módulo estiver **ativado** para a empresa.
    """
    supabase = get_supabase()

    # Verificar se módulo está ativo
    if not await voice_calls_manager.is_enabled_for_company(company_id, supabase):
        raise HTTPException(
            status_code=400,
            detail="Módulo de chamadas não está ativado para esta empresa"
        )

    # Obter serviço
    service = await voice_calls_manager.get_service_for_company(company_id, supabase)
    if not service:
        raise HTTPException(
            status_code=400,
            detail="Módulo não configurado corretamente"
        )

    # Preparar contexto
    context = data.context or {}
    if data.lead_name:
        context["lead_name"] = data.lead_name
    if data.lead_id:
        context["lead_id"] = str(data.lead_id)

    # Iniciar chamada baseado no canal
    if data.channel == CallChannel.WHATSAPP:
        result = await service.initiate_whatsapp_call(
            phone_number=data.phone,
            context=context,
            first_message=data.first_message
        )
    else:
        # Twilio - precisa do número de origem
        result_config = supabase.table("companies").select(
            "voice_calls_config"
        ).eq("id", company_id).single().execute()

        from_number = result_config.data.get("voice_calls_config", {}).get("twilio_from_number")
        if not from_number:
            raise HTTPException(
                status_code=400,
                detail="Número Twilio de origem não configurado"
            )

        result = await service.initiate_twilio_call(
            phone_number=data.phone,
            from_number=from_number,
            context=context
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Erro ao iniciar chamada")
        )

    # Log da chamada (opcional - para histórico)
    try:
        supabase.table("voice_call_logs").insert({
            "company_id": company_id,
            "lead_id": data.lead_id,
            "phone": data.phone,
            "channel": data.channel,
            "call_id": result.get("call_id"),
            "status": result.get("status"),
            "context": context
        }).execute()
    except Exception as e:
        # Não falha se log não funcionar
        logger.warning(f"Erro ao salvar log de chamada: {e}")

    return result


@router.get("/agents/{company_id}")
async def list_agents(company_id: int):
    """
    Lista os agentes disponíveis na conta ElevenLabs da empresa.
    Útil para selecionar qual agente usar nas chamadas.
    """
    supabase = get_supabase()

    try:
        result = supabase.table("companies").select(
            "voice_calls_config"
        ).eq("id", company_id).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        config = result.data.get("voice_calls_config") or {}
        if not config.get("api_key"):
            raise HTTPException(
                status_code=400,
                detail="API key não configurada"
            )

        service = VoiceCallsService(api_key=config.get("api_key"))
        agents_result = await service.get_agents()

        if not agents_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=agents_result.get("error")
            )

        return agents_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar agentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{company_id}")
async def get_call_history(
    company_id: int,
    limit: int = 50,
    lead_id: Optional[int] = None
):
    """
    Retorna histórico de chamadas da empresa.
    """
    supabase = get_supabase()

    try:
        query = supabase.table("voice_call_logs").select(
            "*"
        ).eq("company_id", company_id).order(
            "created_at", desc=True
        ).limit(limit)

        if lead_id:
            query = query.eq("lead_id", lead_id)

        result = query.execute()

        return {
            "success": True,
            "calls": result.data or [],
            "count": len(result.data or [])
        }

    except Exception as e:
        logger.error(f"Erro ao obter histórico: {e}")
        raise HTTPException(status_code=500, detail=str(e))
