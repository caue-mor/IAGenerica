"""
Lead models
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class LeadStatus(BaseModel):
    """Lead status model (Kanban column)"""
    id: Optional[int] = None
    company_id: int
    nome: str
    cor: str = "#6B7280"
    ordem: int = 0
    is_default: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Lead(BaseModel):
    """Lead model"""
    id: Optional[int] = None
    company_id: int
    status_id: Optional[int] = None
    nome: Optional[str] = None
    celular: str
    email: Optional[str] = None
    dados_coletados: dict[str, Any] = {}
    memory: dict[str, Any] = {}  # Long-term AI memory for the lead
    ai_enabled: bool = True
    origem: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeadCreate(BaseModel):
    """Lead creation schema"""
    company_id: int
    status_id: Optional[int] = None
    nome: Optional[str] = None
    celular: str
    email: Optional[str] = None
    dados_coletados: dict[str, Any] = {}
    ai_enabled: bool = True
    origem: Optional[str] = None


class LeadUpdate(BaseModel):
    """Lead update schema"""
    status_id: Optional[int] = None
    nome: Optional[str] = None
    email: Optional[str] = None
    dados_coletados: Optional[dict[str, Any]] = None
    memory: Optional[dict[str, Any]] = None  # Long-term AI memory
    ai_enabled: Optional[bool] = None
    origem: Optional[str] = None


class LeadInfo(BaseModel):
    """Lead info used in agent context"""
    id: int
    nome: Optional[str] = None
    celular: str
    dados_coletados: dict[str, Any] = {}
    memory: dict[str, Any] = {}  # Long-term AI memory
    ai_enabled: bool = True

    @classmethod
    def from_lead(cls, lead: Lead) -> "LeadInfo":
        return cls(
            id=lead.id,
            nome=lead.nome,
            celular=lead.celular,
            dados_coletados=lead.dados_coletados,
            memory=lead.memory or {},
            ai_enabled=lead.ai_enabled
        )


class Conversation(BaseModel):
    """Conversation model"""
    id: Optional[int] = None
    company_id: int
    lead_id: int
    thread_id: str
    status: str = "active"
    ai_enabled: bool = True
    current_node_id: Optional[str] = None
    context: dict[str, Any] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Message(BaseModel):
    """Message model"""
    id: Optional[int] = None
    conversation_id: int
    lead_id: int
    direction: str  # inbound | outbound
    message_type: str = "text"
    content: Optional[str] = None
    media_url: Optional[str] = None
    status: str = "sent"
    uazapi_message_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Message creation schema"""
    conversation_id: int
    lead_id: int
    direction: str
    message_type: str = "text"
    content: Optional[str] = None
    media_url: Optional[str] = None
    status: str = "sent"
    uazapi_message_id: Optional[str] = None
