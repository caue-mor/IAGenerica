"""
Intelligent Flow Processor - Uses LLM to interpret and respond within flow context.

This module provides intelligent conversation handling where:
- The FLOW defines WHAT to collect (structure)
- The LLM interprets user responses (understanding)
- The LLM generates natural responses (conversation)

Unlike the deterministic flow_executor, this uses AI for:
1. Understanding user intent and extracting information
2. Deciding if the answer is valid
3. Generating natural, contextual responses
4. Handling off-topic questions while staying on track
"""

import logging
import json
from typing import Optional, Dict, Any, List, Tuple
from openai import AsyncOpenAI
from dataclasses import dataclass

from ..core.config import settings
from ..services.database import db

logger = logging.getLogger(__name__)


@dataclass
class FlowContext:
    """Current flow context for the LLM"""
    current_node_id: str
    node_type: str
    node_config: Dict[str, Any]
    field_to_collect: Optional[str]
    question_to_ask: Optional[str]
    collected_fields: Dict[str, Any]
    lead_name: Optional[str]
    company_info: Dict[str, Any]
    conversation_history: List[Dict[str, str]]


class IntelligentFlowProcessor:
    """
    Processes flow nodes using LLM intelligence.

    Instead of mechanical extraction, the LLM:
    1. Understands what the user said
    2. Extracts relevant information
    3. Decides if we can proceed or need clarification
    4. Generates a natural response
    """

    def __init__(self, model: str = None):
        self.model = model or settings.OPENAI_MODEL
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def process_user_message(
        self,
        user_message: str,
        flow_context: FlowContext,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process user message intelligently within flow context.

        Args:
            user_message: What the user said
            flow_context: Current flow state
            state: Full agent state

        Returns:
            Dict with response, extracted_value, should_proceed, etc.
        """

        # Build the system prompt that explains the current flow state
        system_prompt = self._build_system_prompt(flow_context, state)

        # Build messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add conversation history
        for msg in flow_context.conversation_history[-6:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            logger.info(f"[INTELLIGENT_FLOW] LLM result: {result}")

            return {
                "response": result.get("response", ""),
                "extracted_value": result.get("extracted_value"),
                "field_name": result.get("field_name"),
                "is_valid": result.get("is_valid", False),
                "should_proceed": result.get("should_proceed", False),
                "user_intent": result.get("user_intent"),
                "needs_clarification": result.get("needs_clarification", False),
                "off_topic_answer": result.get("off_topic_answer"),
                "sentiment": result.get("sentiment", "neutral")
            }

        except Exception as e:
            logger.error(f"[INTELLIGENT_FLOW] Error: {e}")
            return {
                "response": flow_context.question_to_ask or "Como posso ajudar?",
                "is_valid": False,
                "should_proceed": False,
                "error": str(e)
            }

    def _build_system_prompt(self, ctx: FlowContext, state: Dict[str, Any]) -> str:
        """Build a detailed system prompt for the LLM."""

        # Company info
        company = ctx.company_info
        agent_name = company.get("agent_name", "Assistente")
        company_name = company.get("nome_empresa") or company.get("empresa", "nossa empresa")
        tone = company.get("agent_tone", "amigavel")
        use_emojis = company.get("use_emojis", False)
        extra_info = company.get("informacoes_complementares", "")

        # Current flow state
        node_type = ctx.node_type
        field = ctx.field_to_collect
        question = ctx.question_to_ask
        collected = ctx.collected_fields or {}
        lead_name = ctx.lead_name

        # Build collected data summary
        collected_summary = ""
        if collected:
            items = [f"- {k}: {v}" for k, v in collected.items() if v]
            if items:
                collected_summary = "Dados ja coletados:\n" + "\n".join(items)

        prompt = f"""Voce e {agent_name}, assistente virtual da {company_name}.

PERSONALIDADE:
- Tom: {"amigavel e descontraido" if tone == "amigavel" else "profissional e educado"}
- {"Use emojis ocasionalmente para deixar a conversa mais leve" if use_emojis else "Nao use emojis"}
- Seja natural, como se estivesse conversando no WhatsApp
- Responda de forma concisa (maximo 2-3 frases)

{f"INFORMACOES SOBRE A EMPRESA:{chr(10)}{extra_info}" if extra_info else ""}

{f"Nome do cliente: {lead_name}" if lead_name else "Ainda nao sabemos o nome do cliente"}

{collected_summary}

SITUACAO ATUAL:
- Tipo de no: {node_type}
- Campo a coletar: {field or "nenhum"}
- Pergunta planejada: {question or "nenhuma"}

SUA TAREFA:
1. ENTENDA o que o usuario disse
2. Se estamos coletando "{field}":
   - Tente extrair o valor do que o usuario disse
   - Valide se a resposta faz sentido para o campo
   - Se valido, confirme naturalmente e prepare para o proximo
   - Se invalido ou incompleto, peca de forma natural
3. Se o usuario fez uma pergunta ou falou algo fora do contexto:
   - Responda brevemente a pergunta/comentario
   - Depois, volte ao fluxo de forma natural
4. Gere uma resposta NATURAL (nao robotic

IMPORTANTE:
- NAO repita perguntas de forma identica
- NAO seja robotico tipo "Desculpe, nao entendi. Pode repetir?"
- SE o usuario responder algo relacionado, tente extrair a informacao
- SE precisar perguntar de novo, reformule de forma diferente

Responda em JSON com esta estrutura:
{{
    "response": "sua resposta natural ao usuario",
    "extracted_value": "valor extraido ou null",
    "field_name": "{field or 'null'}",
    "is_valid": true/false,
    "should_proceed": true/false (se podemos ir para o proximo no),
    "user_intent": "o que o usuario queria dizer",
    "needs_clarification": true/false,
    "off_topic_answer": "resposta para pergunta fora do contexto ou null",
    "sentiment": "positive/negative/neutral"
}}"""

        return prompt

    async def generate_greeting_response(
        self,
        user_message: str,
        flow_context: FlowContext,
        greeting_text: str
    ) -> str:
        """Generate an intelligent greeting that responds to the user first."""

        company = flow_context.company_info
        agent_name = company.get("agent_name", "Assistente")
        company_name = company.get("nome_empresa") or company.get("empresa", "nossa empresa")

        prompt = f"""Voce e {agent_name} da {company_name}.
O usuario acabou de mandar: "{user_message}"

A saudacao padrao seria: "{greeting_text}"

Gere uma saudacao natural que:
1. Cumprimente o usuario de forma apropriada ao que ele disse
2. Se apresente brevemente
3. Mostre que esta pronto para ajudar

Responda de forma curta e natural (maximo 2 frases).
NAO use a saudacao padrao literalmente - adapte ao contexto."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[INTELLIGENT_FLOW] Greeting error: {e}")
            return greeting_text


class IntelligentExtractor:
    """
    Uses LLM to extract field values from natural language.

    Instead of regex patterns, the LLM understands context and extracts
    even when the format is unusual.
    """

    def __init__(self, model: str = None):
        self.model = model or settings.OPENAI_MODEL
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def extract_field(
        self,
        user_message: str,
        field_name: str,
        field_type: str = "text",
        options: List[str] = None,
        context: str = ""
    ) -> Tuple[Optional[str], bool, str]:
        """
        Extract a field value from user message using LLM.

        Args:
            user_message: What the user said
            field_name: Name of the field to extract
            field_type: Type (text, email, phone, number, choice)
            options: Valid options for choice fields
            context: Additional context

        Returns:
            Tuple of (extracted_value, is_valid, explanation)
        """

        options_text = ""
        if options:
            options_text = f"Opcoes validas: {', '.join(options)}"

        type_hints = {
            "text": "texto livre",
            "email": "endereco de email valido (ex: nome@email.com)",
            "phone": "numero de telefone (ex: 11999999999)",
            "telefone": "numero de telefone (ex: 11999999999)",
            "number": "numero",
            "choice": f"uma das opcoes: {options_text}",
            "nome": "nome de pessoa",
            "cidade": "nome de cidade",
            "cpf": "CPF (11 digitos)",
            "cnpj": "CNPJ (14 digitos)",
            "date": "data",
            "boolean": "sim ou nao"
        }

        type_hint = type_hints.get(field_type, type_hints.get(field_name.lower(), "texto"))

        prompt = f"""Extraia o valor do campo "{field_name}" da mensagem do usuario.

Mensagem do usuario: "{user_message}"

Campo a extrair: {field_name}
Tipo esperado: {type_hint}
{options_text}
{f"Contexto: {context}" if context else ""}

Analise a mensagem e:
1. Identifique se o usuario forneceu a informacao solicitada
2. Extraia o valor no formato correto
3. Valide se faz sentido

Responda em JSON:
{{
    "extracted_value": "valor extraido ou null",
    "is_valid": true/false,
    "confidence": "high/medium/low",
    "explanation": "breve explicacao"
}}

IMPORTANTE:
- Se o usuario respondeu algo relacionado, tente extrair
- Normalize o valor (ex: telefone sem formatacao, email em minusculas)
- Se for escolha e usuario respondeu algo similar, interprete"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            return (
                result.get("extracted_value"),
                result.get("is_valid", False),
                result.get("explanation", "")
            )

        except Exception as e:
            logger.error(f"[INTELLIGENT_EXTRACTOR] Error: {e}")
            return None, False, str(e)


# Singleton instances
intelligent_flow = IntelligentFlowProcessor()
intelligent_extractor = IntelligentExtractor()
