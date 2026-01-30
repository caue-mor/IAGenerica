"""
Proposal Agent - Specialized agent for closing deals after proposal is sent.

This agent activates when a lead has an active proposal (proposta_ativa_id).
It specializes in:
- Handling objections gracefully (without giving discounts)
- Detecting hot signals (urgency, buying intent)
- Notifying the company at critical moments
- Transferring to human when requested

Key Rules:
- NEVER offer discounts (company policy)
- Focus on VALUE, not price
- Detect urgency and escalate
- Be empathetic with objections
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..core.config import settings
from ..models import Proposal, ProposalStatus
from ..services.proposal_service import proposal_service
from ..services.notification import (
    notification_service,
    NotificationType,
    NotificationPriority
)
from .memory import UnifiedMemory, Sentiment

logger = logging.getLogger(__name__)


class ProposalSignal(str, Enum):
    """Signals detected during proposal conversation"""
    HOT = "hot"                    # Ready to close
    WARM = "warm"                  # Interested but hesitant
    COLD = "cold"                  # Low interest
    OBJECTION_PRICE = "objection_price"      # Price objection
    OBJECTION_TIME = "objection_time"        # Timing objection
    OBJECTION_TRUST = "objection_trust"      # Trust/quality objection
    OBJECTION_COMPETITION = "objection_competition"  # Comparing with competitors
    WANTS_HUMAN = "wants_human"              # Wants to talk to human
    WANTS_TO_CLOSE = "wants_to_close"        # Ready to accept
    WANTS_TO_REJECT = "wants_to_reject"      # Going to reject


class ObjectionType(str, Enum):
    """Types of objections"""
    PRICE = "price"           # "É muito caro"
    TIMING = "timing"         # "Agora não é o momento"
    TRUST = "trust"           # "Não tenho certeza se funciona"
    COMPETITION = "competition"  # "Vi preço melhor"
    AUTHORITY = "authority"   # "Preciso falar com alguém"
    FEATURE = "feature"       # "Não tem X que preciso"
    UNKNOWN = "unknown"


@dataclass
class ObjectionResponse:
    """Response strategy for an objection"""
    objection_type: ObjectionType
    detected_text: str
    suggested_response: str
    technique: str  # Name of the technique used


@dataclass
class ProposalDecision:
    """Decision made by the Proposal Agent"""
    response: str
    signals: List[ProposalSignal] = field(default_factory=list)
    objection_detected: Optional[ObjectionType] = None
    should_notify: bool = False
    notification_message: str = ""
    notification_priority: NotificationPriority = NotificationPriority.NORMAL
    should_handoff: bool = False
    handoff_reason: str = ""
    proposal_action: Optional[str] = None  # accept, reject, negotiate
    confidence: float = 0.8


class ProposalAgent:
    """
    Specialized agent for handling proposal conversations.

    This agent focuses on closing deals by:
    1. Detecting and handling objections
    2. Identifying buying signals
    3. Escalating hot leads
    4. Never offering discounts
    """

    # Objection detection patterns (in Portuguese)
    OBJECTION_PATTERNS = {
        ObjectionType.PRICE: [
            "caro", "muito caro", "preço alto", "não tenho grana",
            "fora do orçamento", "não posso pagar", "desconto",
            "abaixar o preço", "valor alto", "achei caro", "puxado"
        ],
        ObjectionType.TIMING: [
            "agora não", "depois", "mais tarde", "próximo mês",
            "não é o momento", "preciso pensar", "vou analisar",
            "deixa eu ver", "me dá um tempo"
        ],
        ObjectionType.TRUST: [
            "não sei se funciona", "será que", "tenho dúvida",
            "como sei que", "garantia", "e se não der certo",
            "não conheço", "nunca ouvi falar"
        ],
        ObjectionType.COMPETITION: [
            "vi mais barato", "concorrente", "outra empresa",
            "proposta melhor", "comparar", "cotação", "orçamento de outro"
        ],
        ObjectionType.AUTHORITY: [
            "falar com meu marido", "consultar", "não decido sozinho",
            "preciso autorização", "meu sócio", "minha esposa"
        ],
        ObjectionType.FEATURE: [
            "não tem", "falta", "precisava de", "seria bom ter",
            "vocês oferecem"
        ]
    }

    # Response techniques for objections (NO DISCOUNTS!)
    OBJECTION_TECHNIQUES = {
        ObjectionType.PRICE: {
            "technique": "Valor vs Preço",
            "approach": "Foque no valor e ROI, nunca ofereça desconto",
            "examples": [
                "Entendo sua preocupação com o investimento. Mas pense assim: {benefit}. O retorno costuma ser {roi}.",
                "É um investimento, não um gasto. Muitos clientes recuperam esse valor em {timeframe}.",
                "Posso explicar melhor o que está incluído? Às vezes o valor parece alto até entendermos tudo que vem junto."
            ]
        },
        ObjectionType.TIMING: {
            "technique": "Urgência Suave",
            "approach": "Criar senso de urgência sem pressionar demais",
            "examples": [
                "Entendo perfeitamente. Só lembro que essa condição é válida até {expiry}. Depois posso não conseguir manter.",
                "Sem problemas! Quando seria um bom momento para conversarmos? Quero garantir que você não perca essa oportunidade.",
                "Faz sentido. Posso te ligar em {days} dias para ver se algo mudou?"
            ]
        },
        ObjectionType.TRUST: {
            "technique": "Prova Social",
            "approach": "Usar casos de sucesso e garantias",
            "examples": [
                "Entendo sua cautela. Temos vários clientes na sua região que adoram o serviço. Posso compartilhar alguns casos?",
                "Sua preocupação é comum. Por isso oferecemos {guarantee}. Você não tem nada a perder.",
                "Posso te passar o contato de um cliente nosso para você conversar? Nada melhor que ouvir de quem já usa."
            ]
        },
        ObjectionType.COMPETITION: {
            "technique": "Diferenciação",
            "approach": "Destacar diferenciais únicos sem criticar concorrentes",
            "examples": [
                "Interessante! O que mais te chamou atenção nessa outra proposta? Quero entender para comparar pra você.",
                "Cada empresa tem seus pontos fortes. O nosso diferencial é {differential}. Isso faz diferença pra você?",
                "Compare não só o preço, mas o que está incluído. Às vezes o mais barato sai mais caro."
            ]
        },
        ObjectionType.AUTHORITY: {
            "technique": "Facilitação",
            "approach": "Oferecer ajuda para convencer o decisor",
            "examples": [
                "Claro! Gostaria que eu preparasse um resumo para você mostrar para {person}?",
                "Sem problemas. Quando vocês puderem conversar? Posso ligar junto para tirar dúvidas.",
                "Perfeito. Que informação seria mais importante para {person} tomar a decisão?"
            ]
        },
        ObjectionType.FEATURE: {
            "technique": "Alternativa",
            "approach": "Entender necessidade e oferecer alternativa",
            "examples": [
                "Entendi sua necessidade. Esse recurso específico não temos, mas temos {alternative} que resolve isso de outra forma.",
                "Interessante! Me conta mais sobre como você usaria isso? Talvez eu consiga te ajudar de outra maneira.",
                "Essa funcionalidade está em nosso roadmap. Enquanto isso, {workaround}."
            ]
        }
    }

    # Hot signals - indicate readiness to close
    HOT_SIGNALS = [
        "quero fechar", "vamos fechar", "aceito", "fechado",
        "pode mandar", "manda o contrato", "como faço para pagar",
        "pode ser agora", "vou aceitar", "topo", "combinado",
        "manda os dados", "vamos começar"
    ]

    # Warm signals - interested but need push
    WARM_SIGNALS = [
        "interessante", "gostei", "parece bom", "faz sentido",
        "entendi", "me convenceu", "quase lá"
    ]

    def __init__(self, model_name: str = None):
        """Initialize the Proposal Agent"""
        self.model = ChatOpenAI(
            model=model_name or settings.OPENAI_MODEL,
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )

    async def process(
        self,
        user_message: str,
        proposal: Proposal,
        memory: UnifiedMemory,
        company_name: str,
        agent_name: str = "Consultor"
    ) -> ProposalDecision:
        """
        Process user message in proposal context.

        Args:
            user_message: The user's message
            proposal: Active proposal
            memory: Conversation memory
            company_name: Company name
            agent_name: Agent name

        Returns:
            ProposalDecision with response and actions
        """
        # Step 1: Detect signals and objections
        signals = self._detect_signals(user_message)
        objection = self._detect_objection(user_message)

        logger.info(
            f"[PROPOSAL_AGENT] Signals: {[s.value for s in signals]}, "
            f"Objection: {objection.value if objection else 'None'}"
        )

        # Step 2: Check for immediate actions
        decision = ProposalDecision(response="", signals=signals, objection_detected=objection)

        # Handle human request
        if ProposalSignal.WANTS_HUMAN in signals:
            decision.should_handoff = True
            decision.handoff_reason = "Lead solicitou atendente humano durante negociação"
            decision.response = "Entendi! Vou transferir você para um de nossos consultores. Um momento, por favor."
            decision.should_notify = True
            decision.notification_message = f"Lead quer falar com humano sobre proposta '{proposal.titulo}'"
            decision.notification_priority = NotificationPriority.HIGH
            return decision

        # Handle acceptance intent
        if ProposalSignal.WANTS_TO_CLOSE in signals:
            decision.proposal_action = "accept"
            decision.should_notify = True
            decision.notification_message = f"Lead quer ACEITAR proposta '{proposal.titulo}'! Ação urgente necessária."
            decision.notification_priority = NotificationPriority.URGENT
            decision.response = await self._generate_acceptance_response(proposal, memory, company_name, agent_name)
            return decision

        # Handle rejection intent
        if ProposalSignal.WANTS_TO_REJECT in signals:
            decision.proposal_action = "reject"
            decision.should_notify = True
            decision.notification_message = f"Lead indicou que vai REJEITAR proposta '{proposal.titulo}'"
            decision.notification_priority = NotificationPriority.HIGH
            # Try to save the deal
            decision.response = await self._generate_save_attempt(
                user_message, proposal, objection, memory, company_name, agent_name
            )
            return decision

        # Handle hot signals
        if ProposalSignal.HOT in signals:
            decision.should_notify = True
            decision.notification_message = f"Lead QUENTE detectado! Interessado na proposta '{proposal.titulo}'"
            decision.notification_priority = NotificationPriority.URGENT

        # Step 3: Generate appropriate response
        if objection:
            decision.response = await self._handle_objection(
                user_message, objection, proposal, memory, company_name, agent_name
            )
        else:
            decision.response = await self._generate_response(
                user_message, proposal, memory, company_name, agent_name, signals
            )

        return decision

    def _detect_signals(self, message: str) -> List[ProposalSignal]:
        """Detect buying signals in the message"""
        signals = []
        message_lower = message.lower()

        # Check for hot signals
        if any(s in message_lower for s in self.HOT_SIGNALS):
            signals.append(ProposalSignal.HOT)
            signals.append(ProposalSignal.WANTS_TO_CLOSE)

        # Check for warm signals
        elif any(s in message_lower for s in self.WARM_SIGNALS):
            signals.append(ProposalSignal.WARM)

        # Check for human request
        human_keywords = ["atendente", "humano", "pessoa", "falar com alguém"]
        if any(kw in message_lower for kw in human_keywords):
            signals.append(ProposalSignal.WANTS_HUMAN)

        # Check for rejection intent
        rejection_keywords = ["não quero", "não vou", "desisto", "não aceito", "recuso"]
        if any(kw in message_lower for kw in rejection_keywords):
            signals.append(ProposalSignal.WANTS_TO_REJECT)
            signals.append(ProposalSignal.COLD)

        # Detect objection signals
        for objection_type, patterns in self.OBJECTION_PATTERNS.items():
            if any(p in message_lower for p in patterns):
                signal_name = f"objection_{objection_type.value}"
                try:
                    signals.append(ProposalSignal(signal_name))
                except ValueError:
                    pass  # Signal not in enum

        return signals

    def _detect_objection(self, message: str) -> Optional[ObjectionType]:
        """Detect the primary objection type"""
        message_lower = message.lower()

        for objection_type, patterns in self.OBJECTION_PATTERNS.items():
            if any(p in message_lower for p in patterns):
                return objection_type

        return None

    async def _handle_objection(
        self,
        user_message: str,
        objection: ObjectionType,
        proposal: Proposal,
        memory: UnifiedMemory,
        company_name: str,
        agent_name: str
    ) -> str:
        """Generate response for an objection"""

        technique_info = self.OBJECTION_TECHNIQUES.get(objection, {})
        technique_name = technique_info.get("technique", "Empatia")
        approach = technique_info.get("approach", "Seja empático e entenda a preocupação")

        prompt = f"""Você é {agent_name}, consultor de vendas da {company_name}.

O lead tem uma proposta ativa: "{proposal.titulo}"
Valores: {proposal.valores}
Status: {proposal.status}
Dias até expirar: {proposal.days_until_expiry}

O lead fez uma OBJEÇÃO do tipo: {objection.value}
Mensagem do lead: "{user_message}"

TÉCNICA A USAR: {technique_name}
ABORDAGEM: {approach}

REGRAS ABSOLUTAS:
1. NUNCA ofereça desconto - é política da empresa
2. Foque no VALOR, não no preço
3. Seja empático, não defensivo
4. Mantenha o relacionamento acima da venda
5. Resposta CURTA (máximo 2-3 frases)

DADOS DO LEAD:
Nome: {memory.collected_data.get('nome', 'Cliente')}
Histórico resumido: {memory.get_context_summary()[:200]}

Responda de forma empática, aplicando a técnica {technique_name}. Quebre a objeção sem pressionar demais."""

        try:
            response = await self.model.ainvoke([
                SystemMessage(content="Você é um consultor de vendas experiente. Responda de forma curta e empática."),
                HumanMessage(content=prompt)
            ])
            return response.content.strip()
        except Exception as e:
            logger.error(f"Error generating objection response: {e}")
            return self._get_fallback_objection_response(objection)

    def _get_fallback_objection_response(self, objection: ObjectionType) -> str:
        """Get fallback response for objection"""
        fallbacks = {
            ObjectionType.PRICE: "Entendo sua preocupação com o investimento. Posso explicar melhor o retorno que você terá?",
            ObjectionType.TIMING: "Sem problemas! Quando seria um bom momento para conversarmos novamente?",
            ObjectionType.TRUST: "Sua cautela é compreensível. Posso compartilhar casos de sucesso de outros clientes?",
            ObjectionType.COMPETITION: "Interessante! Me conta mais sobre o que viu? Quero entender para te ajudar a comparar.",
            ObjectionType.AUTHORITY: "Claro! Posso preparar um material para você mostrar? Ou gostaria que eu participasse da conversa?",
            ObjectionType.FEATURE: "Entendi sua necessidade. Me conta mais sobre como usaria isso?",
            ObjectionType.UNKNOWN: "Entendi. Me conta mais sobre sua preocupação para eu poder te ajudar melhor."
        }
        return fallbacks.get(objection, fallbacks[ObjectionType.UNKNOWN])

    async def _generate_acceptance_response(
        self,
        proposal: Proposal,
        memory: UnifiedMemory,
        company_name: str,
        agent_name: str
    ) -> str:
        """Generate response when lead wants to accept"""
        lead_name = memory.collected_data.get("nome", "")
        greeting = f"{lead_name}, que" if lead_name else "Que"

        return f"""{greeting} ótima notícia! Fico muito feliz que tenha decidido seguir em frente com a {company_name}.

Vou avisar nossa equipe agora mesmo para dar andamento. Um consultor vai entrar em contato em breve para finalizar os detalhes.

Muito obrigado pela confiança!"""

    async def _generate_save_attempt(
        self,
        user_message: str,
        proposal: Proposal,
        objection: Optional[ObjectionType],
        memory: UnifiedMemory,
        company_name: str,
        agent_name: str
    ) -> str:
        """Generate response to try to save a deal that's about to be rejected"""
        lead_name = memory.collected_data.get("nome", "")

        prompt = f"""Você é {agent_name}, consultor da {company_name}.

O lead está prestes a REJEITAR a proposta: "{proposal.titulo}"
Mensagem: "{user_message}"
{'Objeção detectada: ' + objection.value if objection else 'Sem objeção clara'}

OBJETIVO: Fazer uma última tentativa de salvar a negociação sem ser insistente.

REGRAS:
1. Seja respeitoso com a decisão do lead
2. Faça UMA última pergunta para entender o motivo
3. NUNCA ofereça desconto
4. Deixe a porta aberta para o futuro
5. Seja breve (2-3 frases)

Nome do lead: {lead_name or 'Cliente'}

Responda de forma empática e profissional."""

        try:
            response = await self.model.ainvoke([
                SystemMessage(content="Você é um consultor de vendas profissional."),
                HumanMessage(content=prompt)
            ])
            return response.content.strip()
        except Exception:
            return f"Entendo sua decisão{', ' + lead_name if lead_name else ''}. Posso perguntar o que faltou para fecharmos? Quero melhorar para o futuro."

    async def _generate_response(
        self,
        user_message: str,
        proposal: Proposal,
        memory: UnifiedMemory,
        company_name: str,
        agent_name: str,
        signals: List[ProposalSignal]
    ) -> str:
        """Generate general response in proposal context"""
        lead_name = memory.collected_data.get("nome", "")

        signal_context = ""
        if ProposalSignal.HOT in signals:
            signal_context = "O lead parece MUITO interessado. Encoraje o fechamento de forma natural."
        elif ProposalSignal.WARM in signals:
            signal_context = "O lead está interessado mas precisa de um empurrãozinho."

        prompt = f"""Você é {agent_name}, consultor de vendas da {company_name}.

O lead tem uma proposta ativa: "{proposal.titulo}"
Valores: {proposal.valores}
Dias até expirar: {proposal.days_until_expiry}
Já visualizou: {'Sim' if proposal.was_viewed else 'Não'}

Mensagem do lead: "{user_message}"

{signal_context}

REGRAS:
1. Responda à pergunta/comentário do lead
2. Mantenha o foco na proposta de forma natural
3. NUNCA ofereça desconto
4. Seja consultivo, não vendedor
5. Resposta curta (2-3 frases)

Nome do lead: {lead_name or 'Cliente'}
Contexto: {memory.get_context_summary()[:200]}

Responda de forma natural e profissional."""

        try:
            response = await self.model.ainvoke([
                SystemMessage(content="Você é um consultor de vendas experiente e empático."),
                HumanMessage(content=prompt)
            ])
            return response.content.strip()
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Como posso te ajudar com a proposta?"

    async def notify_critical_moment(
        self,
        company_id: int,
        lead_id: int,
        proposal: Proposal,
        notification_message: str,
        priority: NotificationPriority
    ):
        """Send notification for critical moments"""
        await notification_service.send_notification(
            company_id=company_id,
            notification_type=NotificationType.URGENT if priority == NotificationPriority.URGENT else NotificationType.INFO,
            title="Momento Crítico na Negociação",
            message=notification_message,
            lead_id=lead_id,
            data={
                "proposal_id": proposal.id,
                "proposal_titulo": proposal.titulo,
                "proposal_valores": proposal.valores
            },
            priority=priority
        )


# Factory function
def create_proposal_agent(model_name: str = None) -> ProposalAgent:
    """Create a ProposalAgent instance"""
    return ProposalAgent(model_name=model_name)


# Singleton instance
proposal_agent = ProposalAgent()
