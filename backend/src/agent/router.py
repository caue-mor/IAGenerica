"""
Agent Router - Intelligent routing between different agent types.

Routes conversations to the appropriate agent based on lead state:
- ProposalAgent: When lead has active proposal (closing mode)
- QualificationAgent: Default agent for data collection

The router ensures the right specialist handles each conversation.
"""
import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models import Lead, Proposal, ProposalStatus
from ..services.proposal_service import proposal_service

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Types of agents available"""
    QUALIFICATION = "qualification"  # Default - collects data
    PROPOSAL = "proposal"            # Closing mode - handles objections
    SUPPORT = "support"              # Support requests
    HUMAN = "human"                  # Needs human handoff


@dataclass
class RoutingContext:
    """Context for routing decision"""
    lead_id: int
    lead_name: Optional[str]
    has_active_proposal: bool
    active_proposal: Optional[Proposal]
    proposal_status: Optional[str]
    proposal_was_viewed: bool
    collected_data: dict
    user_intent: Optional[str]
    sentiment: Optional[str]


@dataclass
class RoutingDecision:
    """Result of routing decision"""
    agent_type: AgentType
    reason: str
    context: RoutingContext
    proposal_info: Optional[dict] = None


class AgentRouter:
    """
    Routes conversations to the appropriate agent.

    Routing Logic:
    1. Check if lead has active proposal -> ProposalAgent
    2. Check if user explicitly requested support -> SupportAgent (future)
    3. Default -> QualificationAgent

    The router also enriches the context with proposal information
    when routing to the ProposalAgent.
    """

    async def route(
        self,
        lead: Lead,
        user_message: str,
        user_intent: Optional[str] = None,
        sentiment: Optional[str] = None
    ) -> RoutingDecision:
        """
        Determine which agent should handle this conversation.

        Args:
            lead: Lead model
            user_message: Current user message
            user_intent: Detected intent from message
            sentiment: Detected sentiment

        Returns:
            RoutingDecision with agent type and context
        """
        # Build routing context
        active_proposal = None
        proposal_status = None
        proposal_was_viewed = False

        # Check for active proposal
        if lead.proposta_ativa_id:
            active_proposal = await proposal_service.get_proposal(lead.proposta_ativa_id)
            if active_proposal:
                proposal_status = (
                    active_proposal.status.value
                    if isinstance(active_proposal.status, ProposalStatus)
                    else active_proposal.status
                )
                proposal_was_viewed = active_proposal.was_viewed

        context = RoutingContext(
            lead_id=lead.id,
            lead_name=lead.nome,
            has_active_proposal=active_proposal is not None,
            active_proposal=active_proposal,
            proposal_status=proposal_status,
            proposal_was_viewed=proposal_was_viewed,
            collected_data=lead.dados_coletados or {},
            user_intent=user_intent,
            sentiment=sentiment
        )

        # Route based on context
        decision = self._make_routing_decision(context, user_message)

        logger.info(
            f"[ROUTER] Lead {lead.id} routed to {decision.agent_type.value}: {decision.reason}"
        )

        return decision

    def _make_routing_decision(
        self,
        context: RoutingContext,
        user_message: str
    ) -> RoutingDecision:
        """Make the routing decision based on context"""

        # Check for explicit human request
        if self._wants_human(user_message, context.user_intent):
            return RoutingDecision(
                agent_type=AgentType.HUMAN,
                reason="Lead solicitou atendente humano",
                context=context
            )

        # Route to ProposalAgent if there's an active proposal
        if context.has_active_proposal and context.active_proposal:
            proposal_info = self._build_proposal_info(context.active_proposal)

            return RoutingDecision(
                agent_type=AgentType.PROPOSAL,
                reason=f"Lead tem proposta ativa (status: {context.proposal_status})",
                context=context,
                proposal_info=proposal_info
            )

        # Default to QualificationAgent
        return RoutingDecision(
            agent_type=AgentType.QUALIFICATION,
            reason="Modo padrão - coleta de dados",
            context=context
        )

    def _wants_human(self, message: str, intent: Optional[str]) -> bool:
        """Check if user wants human attention"""
        if intent == "humano":
            return True

        message_lower = message.lower()
        human_keywords = [
            "atendente", "humano", "pessoa real",
            "falar com alguém", "falar com alguem",
            "quero atendimento", "preciso de ajuda humana"
        ]

        return any(kw in message_lower for kw in human_keywords)

    def _build_proposal_info(self, proposal: Proposal) -> dict:
        """Build proposal info dict for agent context"""
        return {
            "id": proposal.id,
            "titulo": proposal.titulo,
            "valores": proposal.valores,
            "condicoes": proposal.condicoes,
            "status": (
                proposal.status.value
                if isinstance(proposal.status, ProposalStatus)
                else proposal.status
            ),
            "dias_restantes": proposal.days_until_expiry,
            "foi_visualizada": proposal.was_viewed,
            "enviada_em": proposal.enviada_em.isoformat() if proposal.enviada_em else None,
            "mensagem_rejeitacao": proposal.metadata.get("rejection_reason") if proposal.metadata else None
        }


# Utility functions for external use

async def route_conversation(
    lead: Lead,
    user_message: str,
    user_intent: Optional[str] = None,
    sentiment: Optional[str] = None
) -> RoutingDecision:
    """
    Convenience function to route a conversation.

    Args:
        lead: Lead model
        user_message: Current user message
        user_intent: Detected intent
        sentiment: Detected sentiment

    Returns:
        RoutingDecision
    """
    router = AgentRouter()
    return await router.route(lead, user_message, user_intent, sentiment)


def should_use_proposal_agent(lead: Lead) -> bool:
    """
    Quick check if ProposalAgent should be used.

    Args:
        lead: Lead model

    Returns:
        True if lead has active proposal
    """
    return lead.proposta_ativa_id is not None


# Singleton instance
agent_router = AgentRouter()
