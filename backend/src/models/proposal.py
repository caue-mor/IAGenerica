"""
Proposal models for managing business proposals.

Supports:
- Full proposal lifecycle (draft -> sent -> viewed -> accepted/rejected/expired)
- Tracking of views, responses, and expiration
- Document attachment (PDF/link)
- Custom conditions and values
"""
from datetime import datetime, timedelta
from typing import Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class ProposalStatus(str, Enum):
    """Proposal status enum"""
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    NEGOTIATING = "negotiating"


class Proposal(BaseModel):
    """Proposal model"""
    id: Optional[int] = None
    company_id: int
    lead_id: int
    titulo: str
    descricao: Optional[str] = None

    # Values and conditions
    valores: dict[str, Any] = Field(default_factory=dict)
    condicoes: list[str] = Field(default_factory=list)

    # Status tracking
    status: ProposalStatus = ProposalStatus.DRAFT

    # Document
    documento_url: Optional[str] = None
    documento_tipo: Optional[str] = None  # pdf, link, image

    # Timestamps
    enviada_em: Optional[datetime] = None
    visualizada_em: Optional[datetime] = None
    respondida_em: Optional[datetime] = None

    # Expiration
    validade_dias: int = 7
    expira_em: Optional[datetime] = None

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        use_enum_values = True

    @property
    def is_active(self) -> bool:
        """Check if proposal is still active (not expired, rejected, or accepted)"""
        if self.status in [ProposalStatus.ACCEPTED, ProposalStatus.REJECTED, ProposalStatus.EXPIRED]:
            return False
        if self.expira_em and datetime.utcnow() > self.expira_em:
            return False
        return True

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Days until proposal expires"""
        if not self.expira_em:
            return None
        delta = self.expira_em - datetime.utcnow()
        return max(0, delta.days)

    @property
    def was_viewed(self) -> bool:
        """Check if proposal was viewed"""
        return self.visualizada_em is not None


class ProposalCreate(BaseModel):
    """Proposal creation schema"""
    company_id: int
    lead_id: int
    titulo: str
    descricao: Optional[str] = None
    valores: dict[str, Any] = Field(default_factory=dict)
    condicoes: list[str] = Field(default_factory=list)
    documento_url: Optional[str] = None
    documento_tipo: Optional[str] = None
    validade_dias: int = 7
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProposalUpdate(BaseModel):
    """Proposal update schema"""
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    valores: Optional[dict[str, Any]] = None
    condicoes: Optional[list[str]] = None
    status: Optional[ProposalStatus] = None
    documento_url: Optional[str] = None
    documento_tipo: Optional[str] = None
    validade_dias: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None


class ProposalSend(BaseModel):
    """Schema for sending a proposal"""
    message: Optional[str] = None  # Custom message to send with proposal
    channels: list[str] = Field(default_factory=lambda: ["whatsapp"])


class ProposalResponse(BaseModel):
    """Schema for proposal response (accept/reject)"""
    accepted: bool
    reason: Optional[str] = None
    counter_offer: Optional[dict[str, Any]] = None


class ProposalView(BaseModel):
    """Schema for tracking proposal view"""
    viewed_at: datetime = Field(default_factory=datetime.utcnow)
    viewer_info: Optional[dict[str, Any]] = None


class ProposalInfo(BaseModel):
    """Proposal info for agent context"""
    id: int
    titulo: str
    valores: dict[str, Any]
    status: str
    dias_restantes: Optional[int]
    foi_visualizada: bool
    mensagem_rejeitacao: Optional[str] = None

    @classmethod
    def from_proposal(cls, proposal: Proposal) -> "ProposalInfo":
        """Create ProposalInfo from Proposal"""
        return cls(
            id=proposal.id,
            titulo=proposal.titulo,
            valores=proposal.valores,
            status=proposal.status.value if isinstance(proposal.status, ProposalStatus) else proposal.status,
            dias_restantes=proposal.days_until_expiry,
            foi_visualizada=proposal.was_viewed,
            mensagem_rejeitacao=proposal.metadata.get("rejection_reason")
        )
