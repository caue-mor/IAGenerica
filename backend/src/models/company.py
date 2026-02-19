"""
Company models
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class CompanyConfig(BaseModel):
    """Company AI configuration"""
    agent_name: str = "Assistente"
    agent_tone: str = "amigavel"  # amigavel, formal, casual
    use_emojis: bool = False
    informacoes_complementares: Optional[str] = None


class Company(BaseModel):
    """Company model"""
    id: Optional[int] = None
    empresa: str
    nome_empresa: Optional[str] = None
    email: str
    cidade: Optional[str] = None
    site: Optional[str] = None
    horario_funcionamento: Optional[str] = None
    uazapi_instancia: Optional[str] = None
    uazapi_token: Optional[str] = None
    whatsapp_numero: Optional[str] = None
    notification_phone: Optional[str] = None  # Admin phone for notifications
    agent_name: str = "Assistente"
    agent_tone: str = "amigavel"
    use_emojis: bool = False
    informacoes_complementares: Optional[str] = None
    flow_config: Optional[dict[str, Any]] = None

    # Voice Calls Module (opcional)
    voice_calls_enabled: bool = False  # Toggle para ativar/desativar chamadas
    voice_calls_config: Optional[dict[str, Any]] = None  # Config do módulo

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompanyCreate(BaseModel):
    """Company creation schema"""
    empresa: str
    nome_empresa: Optional[str] = None
    email: str
    cidade: Optional[str] = None
    site: Optional[str] = None
    horario_funcionamento: Optional[str] = None
    uazapi_instancia: Optional[str] = None
    uazapi_token: Optional[str] = None
    whatsapp_numero: Optional[str] = None
    notification_phone: Optional[str] = None  # Admin phone for notifications
    agent_name: str = "Assistente"
    agent_tone: str = "amigavel"
    use_emojis: bool = False
    informacoes_complementares: Optional[str] = None
    flow_config: Optional[dict[str, Any]] = None

    # Voice Calls Module (opcional - desativado por padrão)
    voice_calls_enabled: bool = False
    voice_calls_config: Optional[dict[str, Any]] = None


class CompanyUpdate(BaseModel):
    """Company update schema"""
    empresa: Optional[str] = None
    nome_empresa: Optional[str] = None
    email: Optional[str] = None
    cidade: Optional[str] = None
    site: Optional[str] = None
    horario_funcionamento: Optional[str] = None
    uazapi_instancia: Optional[str] = None
    uazapi_token: Optional[str] = None
    whatsapp_numero: Optional[str] = None
    notification_phone: Optional[str] = None  # Admin phone for notifications
    agent_name: Optional[str] = None
    agent_tone: Optional[str] = None
    use_emojis: Optional[bool] = None
    informacoes_complementares: Optional[str] = None
    flow_config: Optional[dict[str, Any]] = None

    # Voice Calls Module
    voice_calls_enabled: Optional[bool] = None
    voice_calls_config: Optional[dict[str, Any]] = None
