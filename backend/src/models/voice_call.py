"""
Voice Call models
Modelos para o módulo de chamadas de voz
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


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


class VoiceCallConfig(BaseModel):
    """Configuração do módulo de chamadas para uma empresa"""
    api_key: str = Field(..., description="ElevenLabs API Key")
    agent_id: str = Field(..., description="ID do agente no ElevenLabs")
    whatsapp_number_id: Optional[str] = Field(None, description="ID do número WhatsApp Business")
    twilio_from_number: Optional[str] = Field(None, description="Número Twilio de origem")
    webhook_secret: Optional[str] = Field(None, description="Secret para validar webhooks")
    settings: Optional[dict[str, Any]] = Field(None, description="Configurações adicionais")


class VoiceCallLog(BaseModel):
    """Log de uma chamada de voz"""
    id: Optional[int] = None
    company_id: int
    lead_id: Optional[int] = None

    # Identificação
    call_id: Optional[str] = None
    conversation_id: Optional[str] = None

    # Dados da chamada
    phone: str
    channel: CallChannel = CallChannel.WHATSAPP
    status: CallStatus = CallStatus.PENDING

    # Resultado
    duration_seconds: Optional[int] = None
    transcript: Optional[list[dict[str, Any]]] = None
    analysis: Optional[dict[str, Any]] = None

    # Contexto
    context: Optional[dict[str, Any]] = None
    first_message: Optional[str] = None

    # Metadados
    error_message: Optional[str] = None
    webhook_received_at: Optional[datetime] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VoiceCallLogCreate(BaseModel):
    """Schema para criar log de chamada"""
    company_id: int
    lead_id: Optional[int] = None
    phone: str
    channel: CallChannel = CallChannel.WHATSAPP
    context: Optional[dict[str, Any]] = None
    first_message: Optional[str] = None


class VoiceCallLogUpdate(BaseModel):
    """Schema para atualizar log de chamada"""
    call_id: Optional[str] = None
    conversation_id: Optional[str] = None
    status: Optional[CallStatus] = None
    duration_seconds: Optional[int] = None
    transcript: Optional[list[dict[str, Any]]] = None
    analysis: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None


class VoiceCallInitRequest(BaseModel):
    """Request para iniciar uma chamada"""
    phone: str = Field(..., description="Número de telefone")
    lead_id: Optional[int] = Field(None, description="ID do lead")
    lead_name: Optional[str] = Field(None, description="Nome do lead")
    context: Optional[dict[str, Any]] = Field(None, description="Variáveis dinâmicas")
    channel: CallChannel = Field(CallChannel.WHATSAPP, description="Canal")
    first_message: Optional[str] = Field(None, description="Mensagem inicial customizada")


class VoiceCallInitResponse(BaseModel):
    """Response ao iniciar uma chamada"""
    success: bool
    call_id: Optional[str] = None
    status: CallStatus
    channel: CallChannel
    phone: str
    error: Optional[str] = None


class VoiceCallsStatusResponse(BaseModel):
    """Status do módulo de chamadas"""
    enabled: bool
    configured: bool
    agent_id: Optional[str] = None
    connection_status: Optional[dict[str, Any]] = None
