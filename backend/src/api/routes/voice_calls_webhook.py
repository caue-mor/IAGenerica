"""
Voice Calls Webhook Routes
Endpoints para receber callbacks do ElevenLabs após chamadas
"""
import logging
import hmac
import hashlib
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, Request, Header

from ...core.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/elevenlabs", tags=["webhooks"])


def verify_elevenlabs_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """
    Verifica a assinatura HMAC do webhook ElevenLabs.

    Args:
        payload: Body da requisição em bytes
        signature: Header ElevenLabs-Signature
        secret: Secret compartilhado

    Returns:
        True se válido, False caso contrário
    """
    if not secret:
        # Se não tem secret configurado, aceita (dev mode)
        return True

    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@router.post("/post-call")
async def elevenlabs_post_call_webhook(
    request: Request,
    elevenlabs_signature: Optional[str] = Header(None, alias="ElevenLabs-Signature")
):
    """
    Recebe webhook de post-call do ElevenLabs.

    Chamado automaticamente quando uma chamada termina.
    Atualiza o status e salva a transcrição.
    """
    body = await request.body()

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Extrair informações básicas
    conversation_id = data.get("conversation_id")
    agent_id = data.get("agent_id")
    status = data.get("status", "completed")

    logger.info(f"Webhook ElevenLabs recebido: conversation_id={conversation_id}, status={status}")

    supabase = get_supabase()

    try:
        # Buscar o log da chamada pelo call_id ou conversation_id
        result = supabase.table("voice_call_logs").select(
            "id, company_id"
        ).or_(
            f"call_id.eq.{conversation_id},conversation_id.eq.{conversation_id}"
        ).single().execute()

        if result.data:
            log_id = result.data["id"]
            company_id = result.data["company_id"]

            # Verificar assinatura se empresa tem secret configurado
            company_result = supabase.table("companies").select(
                "voice_calls_config"
            ).eq("id", company_id).single().execute()

            if company_result.data:
                config = company_result.data.get("voice_calls_config") or {}
                webhook_secret = config.get("webhook_secret")

                if webhook_secret and elevenlabs_signature:
                    if not verify_elevenlabs_signature(body, elevenlabs_signature, webhook_secret):
                        logger.warning(f"Assinatura inválida para webhook {conversation_id}")
                        raise HTTPException(status_code=401, detail="Invalid signature")

            # Atualizar o log com dados do webhook
            update_data = {
                "status": status,
                "webhook_received_at": "now()"
            }

            # Adicionar transcrição se presente
            if data.get("transcript"):
                update_data["transcript"] = data["transcript"]

            # Adicionar duração se presente
            if data.get("duration_seconds"):
                update_data["duration_seconds"] = data["duration_seconds"]

            # Adicionar análise se presente
            if data.get("analysis"):
                update_data["analysis"] = data["analysis"]

            # Adicionar conversation_id se não tinha
            if conversation_id:
                update_data["conversation_id"] = conversation_id

            supabase.table("voice_call_logs").update(
                update_data
            ).eq("id", log_id).execute()

            logger.info(f"Log de chamada {log_id} atualizado com dados do webhook")

        else:
            # Chamada não encontrada - criar novo registro
            # Isso pode acontecer se a chamada foi iniciada fora do sistema
            logger.warning(f"Chamada {conversation_id} não encontrada, criando registro")

            # Tentar identificar empresa pelo agent_id
            if agent_id:
                company_search = supabase.table("companies").select(
                    "id"
                ).filter(
                    "voice_calls_config->agent_id", "eq", agent_id
                ).single().execute()

                if company_search.data:
                    supabase.table("voice_call_logs").insert({
                        "company_id": company_search.data["id"],
                        "conversation_id": conversation_id,
                        "call_id": conversation_id,
                        "phone": data.get("to_number", "unknown"),
                        "channel": "whatsapp",
                        "status": status,
                        "duration_seconds": data.get("duration_seconds"),
                        "transcript": data.get("transcript"),
                        "analysis": data.get("analysis"),
                        "webhook_received_at": "now()"
                    }).execute()

        return {"success": True, "message": "Webhook processed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        # Retorna 200 mesmo em erro para não causar retry infinito
        return {"success": False, "error": str(e)}


@router.post("/call-failed")
async def elevenlabs_call_failed_webhook(request: Request):
    """
    Recebe webhook quando uma chamada falha ao iniciar.

    Motivos comuns:
    - Usuário não atendeu
    - Usuário recusou
    - Erro de conexão
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    conversation_id = data.get("conversation_id")
    error_code = data.get("error_code")
    error_message = data.get("error_message")

    logger.info(f"Webhook call-failed: {conversation_id}, error={error_code}")

    supabase = get_supabase()

    try:
        # Atualizar status da chamada
        result = supabase.table("voice_call_logs").update({
            "status": "failed",
            "error_message": f"{error_code}: {error_message}",
            "webhook_received_at": "now()"
        }).or_(
            f"call_id.eq.{conversation_id},conversation_id.eq.{conversation_id}"
        ).execute()

        return {"success": True, "message": "Webhook processed"}

    except Exception as e:
        logger.error(f"Erro ao processar webhook call-failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/health")
async def webhook_health():
    """Health check para o endpoint de webhooks"""
    return {"status": "ok", "endpoint": "elevenlabs-webhooks"}
