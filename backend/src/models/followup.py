"""
Followup models for managing scheduled follow-up messages.

Supports:
- Multi-stage follow-ups (1h, 4h, 12h, 24h)
- Context preservation (last question, pending field)
- Automatic scheduling and cancellation
- Contextual templates
"""
from datetime import datetime
from typing import Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class FollowupStatus(str, Enum):
    """Followup status enum"""
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"
    EXPIRED = "expired"


class FollowupStage(str, Enum):
    """Followup stage enum - defines the timing"""
    FIRST = "first"      # 1 hour
    SECOND = "second"    # 4 hours
    THIRD = "third"      # 12 hours
    FOURTH = "fourth"    # 24 hours
    CUSTOM = "custom"    # Custom timing


# Stage timing in hours
STAGE_HOURS = {
    FollowupStage.FIRST: 1,
    FollowupStage.SECOND: 4,
    FollowupStage.THIRD: 12,
    FollowupStage.FOURTH: 24,
}


class FollowupReason(str, Enum):
    """Reason for the followup"""
    INACTIVITY = "inactivity"           # Lead stopped responding
    PROPOSAL_SENT = "proposal_sent"     # Follow up on sent proposal
    DOCUMENT_PENDING = "document_pending"  # Waiting for document
    FIELD_PENDING = "field_pending"     # Waiting for specific field
    SCHEDULED = "scheduled"             # Manually scheduled
    CUSTOM = "custom"


class Followup(BaseModel):
    """Followup model"""
    id: Optional[int] = None
    company_id: int
    lead_id: int

    # Scheduling
    scheduled_for: datetime
    stage: FollowupStage = FollowupStage.FIRST
    reason: FollowupReason = FollowupReason.INACTIVITY

    # Message content
    message: Optional[str] = None
    template_id: Optional[str] = None

    # Context preservation
    context: dict[str, Any] = Field(default_factory=dict)
    # Context includes:
    # - last_question: str - The last question asked
    # - pending_field: str - Field we're waiting for
    # - conversation_summary: str - Brief summary of conversation
    # - last_topic: str - What they were discussing
    # - lead_name: str - Lead's name for personalization
    # - proposal_id: int - If following up on proposal

    # Status tracking
    status: FollowupStatus = FollowupStatus.PENDING
    sent_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        use_enum_values = True

    @property
    def is_pending(self) -> bool:
        """Check if followup is still pending"""
        return self.status == FollowupStatus.PENDING

    @property
    def is_due(self) -> bool:
        """Check if followup is due to be sent"""
        return self.is_pending and datetime.utcnow() >= self.scheduled_for


class FollowupCreate(BaseModel):
    """Followup creation schema"""
    company_id: int
    lead_id: int
    scheduled_for: datetime
    stage: FollowupStage = FollowupStage.FIRST
    reason: FollowupReason = FollowupReason.INACTIVITY
    message: Optional[str] = None
    template_id: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FollowupUpdate(BaseModel):
    """Followup update schema"""
    scheduled_for: Optional[datetime] = None
    stage: Optional[FollowupStage] = None
    reason: Optional[FollowupReason] = None
    message: Optional[str] = None
    template_id: Optional[str] = None
    context: Optional[dict[str, Any]] = None
    status: Optional[FollowupStatus] = None
    metadata: Optional[dict[str, Any]] = None


class FollowupScheduleRequest(BaseModel):
    """Request schema for scheduling a followup"""
    lead_id: int
    delay_hours: Optional[float] = None  # If not provided, uses stage default
    stage: Optional[FollowupStage] = None
    reason: FollowupReason = FollowupReason.INACTIVITY
    message: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)


class FollowupTemplate(BaseModel):
    """Followup message template"""
    id: str
    name: str
    stage: FollowupStage
    reason: FollowupReason
    template: str  # Message template with {placeholders}
    description: Optional[str] = None

    def render(self, context: dict[str, Any]) -> str:
        """Render template with context"""
        try:
            return self.template.format(**context)
        except KeyError:
            # Return template with available substitutions
            result = self.template
            for key, value in context.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result


# Default templates for different scenarios
DEFAULT_TEMPLATES = [
    FollowupTemplate(
        id="inactivity_first",
        name="Primeiro lembrete",
        stage=FollowupStage.FIRST,
        reason=FollowupReason.INACTIVITY,
        template="Oi {lead_name}! Notei que ficamos sem resposta. Posso te ajudar com algo mais?",
        description="First gentle reminder after inactivity"
    ),
    FollowupTemplate(
        id="inactivity_second",
        name="Segundo lembrete",
        stage=FollowupStage.SECOND,
        reason=FollowupReason.INACTIVITY,
        template="Oi {lead_name}! Ainda estou por aqui caso precise de ajuda. Tem alguma duvida sobre o que conversamos?",
        description="Second reminder with context"
    ),
    FollowupTemplate(
        id="inactivity_third",
        name="Terceiro lembrete",
        stage=FollowupStage.THIRD,
        reason=FollowupReason.INACTIVITY,
        template="Oi {lead_name}! Quero garantir que conseguiu todas as informacoes que precisava. Posso ajudar em mais alguma coisa?",
        description="Third reminder showing care"
    ),
    FollowupTemplate(
        id="proposal_followup",
        name="Followup de proposta",
        stage=FollowupStage.FIRST,
        reason=FollowupReason.PROPOSAL_SENT,
        template="Oi {lead_name}! Vi que enviamos uma proposta para voce. Teve a chance de analisar? Fico a disposicao para esclarecer qualquer duvida!",
        description="Follow up after sending proposal"
    ),
    FollowupTemplate(
        id="proposal_reminder",
        name="Lembrete de proposta",
        stage=FollowupStage.SECOND,
        reason=FollowupReason.PROPOSAL_SENT,
        template="Oi {lead_name}! Lembrando que sua proposta ainda esta disponivel. A validade e de {dias_restantes} dias. Posso ajudar com alguma duvida?",
        description="Proposal reminder with urgency"
    ),
    FollowupTemplate(
        id="field_pending",
        name="Campo pendente",
        stage=FollowupStage.FIRST,
        reason=FollowupReason.FIELD_PENDING,
        template="Oi {lead_name}! Para continuar, preciso apenas do seu {pending_field}. Pode me informar?",
        description="Reminder for pending field"
    ),
    FollowupTemplate(
        id="document_pending",
        name="Documento pendente",
        stage=FollowupStage.FIRST,
        reason=FollowupReason.DOCUMENT_PENDING,
        template="Oi {lead_name}! Estou aguardando o documento que mencionamos. Consegue me enviar?",
        description="Reminder for pending document"
    ),
]


def get_template(stage: FollowupStage, reason: FollowupReason) -> Optional[FollowupTemplate]:
    """Get the best matching template for stage and reason"""
    for template in DEFAULT_TEMPLATES:
        if template.stage == stage and template.reason == reason:
            return template
    # Fallback to any template matching the reason
    for template in DEFAULT_TEMPLATES:
        if template.reason == reason:
            return template
    return None
