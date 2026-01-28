"""
AI Brain - The intelligent core of the conversation agent.

This module provides the central intelligence that:
- Understands context and user messages
- Decides what to do next
- Generates natural, contextual responses
- Extracts data intelligently from conversation

The AI Brain receives CONTEXT, not SCRIPTS. It decides HOW to achieve goals naturally.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from .memory import UnifiedMemory, Sentiment
from .flow_interpreter import FlowIntent, ConversationGoal
from .goal_tracker import GoalTracker, ExtractionResult
from ..core.config import settings


class ResponseAction(str, Enum):
    """Actions the brain can take."""
    RESPOND = "respond"          # Normal response
    COLLECT_DATA = "collect_data"  # Try to collect a field
    HANDOFF = "handoff"          # Transfer to human
    NOTIFY = "notify"            # Send notification
    END = "end"                  # End conversation


@dataclass
class CompanyContext:
    """Context about the company for the AI."""
    company_name: str
    agent_name: str
    agent_tone: str = "amigavel"
    use_emojis: bool = False
    company_info: str = ""
    industry: str = ""
    business_hours: str = ""
    timezone: str = "America/Sao_Paulo"


@dataclass
class BrainDecision:
    """Decision made by the AI brain."""
    action: ResponseAction
    response: str
    extractions: list[ExtractionResult] = field(default_factory=list)
    sentiment: Sentiment = Sentiment.NEUTRAL
    user_intent: str = ""
    should_handoff: bool = False
    handoff_reason: str = ""
    should_notify: bool = False
    notification_type: str = ""
    next_goal: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""


class AIBrain:
    """
    The intelligent core of the conversation agent.

    The brain receives:
    - User message
    - Complete memory (conversation + lead history)
    - Goals from flow (what to collect)
    - Company context

    And decides:
    - What the user said/wanted
    - What data can be extracted
    - How to respond naturally
    - Whether to handoff/notify
    """

    def __init__(self, model_name: str = None):
        """
        Initialize AIBrain.

        Args:
            model_name: OpenAI model to use (default from settings)
        """
        self.model = ChatOpenAI(
            model=model_name or settings.OPENAI_MODEL,
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )
        self.extraction_model = ChatOpenAI(
            model=model_name or settings.OPENAI_MODEL,
            temperature=0.1,  # Lower temperature for extraction
            api_key=settings.OPENAI_API_KEY
        )

    async def process(
        self,
        user_message: str,
        memory: UnifiedMemory,
        flow_intent: FlowIntent,
        company_context: CompanyContext,
        goal_tracker: GoalTracker
    ) -> BrainDecision:
        """
        Process user message with full context and decide response.

        Args:
            user_message: The user's message
            memory: UnifiedMemory with full context
            flow_intent: Interpreted flow with goals
            company_context: Company information
            goal_tracker: Goal progress tracker

        Returns:
            BrainDecision with response and actions
        """
        # Step 1: Understand user intent and extract data
        extractions = await self._extract_data(user_message, flow_intent, memory)

        # Step 2: Update goal tracker with extractions
        if extractions:
            goal_tracker.update_from_extractions(extractions)

        # Step 3: Detect sentiment and intent
        sentiment = await self._detect_sentiment(user_message)
        user_intent = await self._detect_intent(user_message)

        # Step 4: Check if handoff is needed
        should_handoff, handoff_reason = self._check_handoff(
            user_intent, sentiment, goal_tracker, memory
        )

        # Step 5: Generate natural response
        response = await self._generate_response(
            user_message=user_message,
            memory=memory,
            flow_intent=flow_intent,
            company_context=company_context,
            goal_tracker=goal_tracker,
            extractions=extractions,
            user_intent=user_intent
        )

        # Step 6: Determine next goal
        next_goal = goal_tracker.get_next_goal_to_collect()

        # Step 7: Check for notifications
        should_notify = False
        notification_type = ""
        notifications = goal_tracker.get_notifications_to_send()
        if notifications:
            should_notify = True
            notification_type = notifications[0].trigger

        return BrainDecision(
            action=ResponseAction.HANDOFF if should_handoff else ResponseAction.RESPOND,
            response=response,
            extractions=extractions,
            sentiment=sentiment,
            user_intent=user_intent,
            should_handoff=should_handoff,
            handoff_reason=handoff_reason,
            should_notify=should_notify,
            notification_type=notification_type,
            next_goal=next_goal.field_name if next_goal else None,
            confidence=0.9,
            reasoning=f"Intent: {user_intent}, Extracted: {len(extractions)} fields"
        )

    async def _extract_data(
        self,
        user_message: str,
        flow_intent: FlowIntent,
        memory: UnifiedMemory
    ) -> list[ExtractionResult]:
        """
        Extract data from user message based on pending goals.

        Uses LLM to intelligently extract data from natural conversation.
        """
        pending_goals = flow_intent.get_pending_goals()
        if not pending_goals:
            return []

        # Build extraction prompt
        goals_text = "\n".join([
            f"- {g.field_name} ({g.field_type}): {g.description}"
            for g in pending_goals[:5]  # Top 5 pending goals
        ])

        extraction_prompt = f"""Analise a mensagem do usuário e extraia TODAS as informações relevantes.

MENSAGEM DO USUÁRIO: "{user_message}"

INFORMAÇÕES A EXTRAIR (se presentes na mensagem):
{goals_text}

DADOS JÁ COLETADOS:
{json.dumps(memory.collected_data, ensure_ascii=False)}

INSTRUÇÕES:
1. Extraia APENAS informações que estão claramente presentes na mensagem
2. NÃO invente dados que não foram mencionados
3. Para cada informação extraída, retorne no formato JSON
4. Se a mensagem for uma saudação ou não contiver dados, retorne lista vazia
5. Considere variações naturais (ex: "meu nome é João", "sou o João", "João aqui")

REGRAS DE EXTRAÇÃO:
- nome: Nome da pessoa (capitalizar corretamente)
- email: Formato válido de email
- telefone: Números com DDD (pode ter formatação variada)
- cidade: Nome de cidade no Brasil
- interesse: O que a pessoa está buscando/precisa
- orcamento: Valores monetários ou faixas de preço
- urgencia: Indicações de prazo (imediato, esta semana, não tenho pressa, etc.)

Retorne APENAS um JSON válido no formato:
[{{"field": "nome_do_campo", "value": "valor_extraido", "confidence": 0.9}}]

Se não houver dados para extrair, retorne: []"""

        try:
            response = await self.extraction_model.ainvoke([
                SystemMessage(content="Você é um extrator de dados preciso. Retorne APENAS JSON válido, sem explicações."),
                HumanMessage(content=extraction_prompt)
            ])

            content = response.content.strip()

            # Try to parse JSON
            # Handle markdown code blocks
            if "```" in content:
                match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
                if match:
                    content = match.group(1)

            extractions_data = json.loads(content)

            extractions = []
            for item in extractions_data:
                if isinstance(item, dict) and "field" in item and "value" in item:
                    extractions.append(ExtractionResult(
                        field=item["field"],
                        value=item["value"],
                        confidence=float(item.get("confidence", 0.8)),
                        source_text=user_message
                    ))

            return extractions

        except (json.JSONDecodeError, Exception) as e:
            # Fallback: try simple pattern matching for common fields
            return self._simple_extraction(user_message, pending_goals)

    def _simple_extraction(
        self,
        message: str,
        goals: list[ConversationGoal]
    ) -> list[ExtractionResult]:
        """Simple pattern-based extraction as fallback."""
        extractions = []
        message_lower = message.lower()

        for goal in goals:
            field = goal.field_name
            value = None

            if field == "nome":
                # Pattern: "meu nome é X", "sou X", "chamo X"
                patterns = [
                    r"(?:meu nome [eé]|me chamo|sou o?|chamo[- ]me)\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)?)",
                    r"^([A-Za-zÀ-ÿ]{2,}(?:\s+[A-Za-zÀ-ÿ]+)?)$"  # Just a name
                ]
                for pattern in patterns:
                    match = re.search(pattern, message, re.IGNORECASE)
                    if match:
                        value = match.group(1).title()
                        break

            elif field == "email":
                match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', message)
                if match:
                    value = match.group(0).lower()

            elif field in ["telefone", "celular"]:
                # Remove non-digits, keep at least 10 digits
                digits = re.sub(r'\D', '', message)
                if len(digits) >= 10:
                    value = digits[:11]  # Max 11 digits for Brazilian phones

            elif field == "cidade":
                # Common patterns
                patterns = [
                    r"(?:moro em|estou em|sou de|de)\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)?)",
                ]
                for pattern in patterns:
                    match = re.search(pattern, message, re.IGNORECASE)
                    if match:
                        value = match.group(1).title()
                        break

            if value:
                extractions.append(ExtractionResult(
                    field=field,
                    value=value,
                    confidence=0.7,
                    source_text=message
                ))

        return extractions

    async def _detect_sentiment(self, message: str) -> Sentiment:
        """Detect sentiment of user message."""
        # Quick heuristic check first
        positive_words = ["obrigado", "perfeito", "otimo", "legal", "bom", "sim", "claro", "adorei"]
        negative_words = ["problema", "reclamar", "ruim", "pessimo", "nao", "nunca", "irritado", "cancelar"]

        message_lower = message.lower()

        pos_count = sum(1 for w in positive_words if w in message_lower)
        neg_count = sum(1 for w in negative_words if w in message_lower)

        if pos_count > neg_count:
            return Sentiment.POSITIVE
        elif neg_count > pos_count:
            return Sentiment.NEGATIVE
        return Sentiment.NEUTRAL

    async def _detect_intent(self, message: str) -> str:
        """Detect user intent from message."""
        message_lower = message.lower()

        # Quick pattern matching
        if any(w in message_lower for w in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]):
            return "saudacao"
        if any(w in message_lower for w in ["atendente", "humano", "pessoa", "falar com alguem"]):
            return "humano"
        if any(w in message_lower for w in ["preço", "preco", "valor", "quanto custa", "custo"]):
            return "preco"
        if any(w in message_lower for w in ["comprar", "quero", "preciso", "adquirir"]):
            return "compra"
        if any(w in message_lower for w in ["problema", "ajuda", "suporte", "erro", "nao funciona"]):
            return "suporte"
        if any(w in message_lower for w in ["agendar", "marcar", "horario"]):
            return "agendamento"
        if any(w in message_lower for w in ["tchau", "ate mais", "obrigado", "valeu", "finalizar"]):
            return "despedida"

        return "informacao"

    def _check_handoff(
        self,
        user_intent: str,
        sentiment: Sentiment,
        goal_tracker: GoalTracker,
        memory: UnifiedMemory
    ) -> tuple[bool, str]:
        """Check if conversation should be handed off to human."""
        # Explicit request for human
        if user_intent == "humano":
            return True, "Cliente solicitou atendente humano"

        # Very negative sentiment
        if sentiment == Sentiment.NEGATIVE and memory.conversation_state.retry_count > 2:
            return True, "Cliente insatisfeito após múltiplas tentativas"

        # Check goal tracker for handoff conditions
        should_handoff, reason = goal_tracker.should_handoff()
        if should_handoff:
            return True, reason

        return False, ""

    async def _generate_response(
        self,
        user_message: str,
        memory: UnifiedMemory,
        flow_intent: FlowIntent,
        company_context: CompanyContext,
        goal_tracker: GoalTracker,
        extractions: list[ExtractionResult],
        user_intent: str
    ) -> str:
        """Generate a natural, contextual response."""
        # Build system prompt
        system_prompt = self._build_system_prompt(
            memory=memory,
            flow_intent=flow_intent,
            company_context=company_context,
            goal_tracker=goal_tracker
        )

        # Build user context
        user_context = self._build_user_context(
            user_message=user_message,
            extractions=extractions,
            user_intent=user_intent,
            goal_tracker=goal_tracker
        )

        # Get response from LLM
        try:
            response = await self.model.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_context)
            ])
            return response.content.strip()
        except Exception as e:
            # Fallback response
            return self._get_fallback_response(company_context, user_intent)

    def _build_system_prompt(
        self,
        memory: UnifiedMemory,
        flow_intent: FlowIntent,
        company_context: CompanyContext,
        goal_tracker: GoalTracker
    ) -> str:
        """Build the system prompt with full context."""
        # Tone descriptions
        tone_desc = {
            "amigavel": "amigável, caloroso e acolhedor",
            "formal": "profissional, respeitoso e formal",
            "casual": "descontraído, informal e próximo",
            "tecnico": "técnico, preciso e informativo",
            "vendedor": "persuasivo, entusiasmado e focado em vendas",
            "consultivo": "consultivo, analítico e focado em soluções"
        }.get(company_context.agent_tone, "amigável")

        emoji_instruction = (
            "Use emojis de forma moderada para tornar a conversa mais amigável."
            if company_context.use_emojis else
            "NÃO use emojis nas respostas."
        )

        # Get context summary
        context_summary = memory.get_context_summary()
        recent_conversation = memory.get_recent_conversation(3)

        # Get goal status
        progress = goal_tracker.get_progress()
        goals_status = goal_tracker.format_status_for_prompt()
        pending_goals = flow_intent.format_pending_goals_for_prompt()

        # Lead name
        lead_name = memory.collected_data.get("nome", "")
        lead_greeting = f"O nome do lead é: {lead_name}. Use o nome dele quando apropriado." if lead_name else ""

        return f"""Você é {company_context.agent_name}, assistente virtual da empresa {company_context.company_name}.

PERSONALIDADE E TOM:
- Seu tom deve ser {tone_desc}
- {emoji_instruction}
- Seja conciso e direto (máximo 2-3 frases por resposta)
- Responda sempre em português brasileiro
{lead_greeting}

CONTEXTO DA CONVERSA:
{context_summary}

HISTÓRICO RECENTE:
{recent_conversation}

OBJETIVOS DO FLUXO:
{goals_status}

{pending_goals}

REGRAS IMPORTANTES:
1. SEMPRE reconheça o que o usuário disse PRIMEIRO antes de fazer perguntas
2. NÃO leia perguntas de script - formule-as naturalmente com base no contexto
3. Se o usuário responder algo fora do contexto, responda e depois volte ao assunto
4. Se já coletou uma informação, NÃO peça novamente
5. Seja natural - você está conversando, não preenchendo formulário
6. Se o usuário mostrar urgência ou preocupação, demonstre empatia
7. IMPORTANTE: Você está COLETANDO dados para nosso consultor de vendas entrar em contato
8. NÃO calcule frete, preço final ou faça cotações - apenas colete as informações
9. Quando pedir CEP, explique que é para nosso consultor calcular as melhores opções de entrega
10. Após coletar todas as informações, avise que um consultor entrará em contato em breve

INFORMAÇÕES DA EMPRESA:
{company_context.company_info if company_context.company_info else "Use seu conhecimento geral para responder perguntas sobre a empresa."}

Responda de forma natural e humana, avançando a conversa para coletar as informações pendentes."""

    def _build_user_context(
        self,
        user_message: str,
        extractions: list[ExtractionResult],
        user_intent: str,
        goal_tracker: GoalTracker
    ) -> str:
        """Build the context for processing user message."""
        extraction_text = ""
        if extractions:
            extraction_text = "\n\nINFORMAÇÕES EXTRAÍDAS DA MENSAGEM:\n" + "\n".join([
                f"- {e.field}: {e.value} (confiança: {e.confidence:.0%})"
                for e in extractions
            ])

        next_goal = goal_tracker.get_next_goal_to_collect()
        next_goal_text = ""
        if next_goal:
            next_goal_text = f"\n\nPRÓXIMO OBJETIVO: Coletar {next_goal.field_name} ({next_goal.description})"
            if next_goal.suggested_question:
                next_goal_text += f"\nSugestão de pergunta (adapte naturalmente): {next_goal.suggested_question}"

        return f"""MENSAGEM DO USUÁRIO: "{user_message}"

INTENÇÃO DETECTADA: {user_intent}
{extraction_text}
{next_goal_text}

Responda de forma natural, reconhecendo o que o usuário disse e avançando a conversa."""

    def _get_fallback_response(self, company_context: CompanyContext, intent: str) -> str:
        """Get a fallback response when LLM fails."""
        fallbacks = {
            "saudacao": f"Olá! Bem-vindo à {company_context.company_name}. Como posso ajudar você hoje?",
            "humano": "Entendi, vou transferir você para um de nossos atendentes. Um momento, por favor.",
            "despedida": "Obrigado pelo contato! Qualquer dúvida, estamos à disposição.",
            "default": "Desculpe, não consegui processar sua mensagem. Pode repetir de outra forma?"
        }
        return fallbacks.get(intent, fallbacks["default"])

    async def summarize_conversation(
        self,
        memory: UnifiedMemory,
        goal_tracker: GoalTracker
    ) -> str:
        """Generate a summary of the conversation."""
        prompt = f"""Resuma a conversa de forma concisa:

DADOS COLETADOS:
{json.dumps(memory.collected_data, ensure_ascii=False, indent=2)}

PROGRESSO DOS OBJETIVOS:
{goal_tracker.format_status_for_prompt()}

HISTÓRICO RECENTE:
{memory.get_recent_conversation(10)}

Gere um resumo de 2-3 frases sobre:
1. O que o lead queria
2. O que foi coletado
3. Status atual"""

        try:
            response = await self.model.ainvoke([
                SystemMessage(content="Você é um resumidor de conversas. Seja conciso e objetivo."),
                HumanMessage(content=prompt)
            ])
            return response.content.strip()
        except Exception:
            return "Conversa em andamento. Dados coletados parcialmente."


def create_brain(model_name: str = None) -> AIBrain:
    """
    Factory function to create an AIBrain instance.

    Args:
        model_name: Optional model name override

    Returns:
        AIBrain instance
    """
    return AIBrain(model_name=model_name)
