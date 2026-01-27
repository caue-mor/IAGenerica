"""
Conversational Question Handler - Humanizes flow questions using LLM

This module provides intelligent humanization of automated flow questions,
making conversations feel more natural and empathetic.

Features:
- Responds to what user said FIRST (empathy) before asking next question
- Retry handling with varied phrasing for 1st, 2nd, and 3rd attempts
- Field-specific hints for common fields (nome, email, telefone, etc.)
- WhatsApp formatting enforcement (double line breaks)
- Skip humanize flag for when exact text is needed
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import openai
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class FieldType(Enum):
    """Common field types for data collection"""
    NOME = "nome"
    EMAIL = "email"
    TELEFONE = "telefone"
    CIDADE = "cidade"
    ENDERECO = "endereco"
    CPF = "cpf"
    CNPJ = "cnpj"
    CEP = "cep"
    DATA_NASCIMENTO = "data_nascimento"
    INTERESSE = "interesse"
    ORCAMENTO = "orcamento"
    URGENCIA = "urgencia"
    EMPRESA = "empresa"
    CARGO = "cargo"
    CUSTOM = "custom"


@dataclass
class HumanizerContext:
    """Context for humanization with lead and agent information"""
    lead_name: Optional[str] = None
    agent_name: str = "Assistente"
    company_name: str = "nossa empresa"
    business_type: Optional[str] = None
    tone: str = "friendly"  # friendly, professional, casual
    extra_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationMessage:
    """Represents a message in the conversation history"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None


# Field-specific hints for better humanization
FIELD_HINTS: Dict[str, Dict[str, Any]] = {
    "nome": {
        "description": "nome completo do cliente",
        "examples": ["Maria Silva", "Joao Santos"],
        "validation_hint": "nome completo com pelo menos nome e sobrenome",
        "empathy_responses": [
            "Que bom ter voce aqui!",
            "Prazer em conhecer voce!",
            "Vamos la entao!",
        ],
        "retry_hints": [
            "Pode me dizer seu nome completo, por gentileza?",
            "Preciso do seu nome completo para prosseguir, por favor.",
            "Por favor, informe como gostaria de ser chamado(a).",
        ]
    },
    "email": {
        "description": "endereco de e-mail para contato",
        "examples": ["exemplo@email.com"],
        "validation_hint": "e-mail valido no formato nome@provedor.com",
        "empathy_responses": [
            "Perfeito!",
            "Otimo!",
            "Anotado!",
        ],
        "retry_hints": [
            "Qual seu melhor e-mail para contato?",
            "Poderia informar um e-mail valido?",
            "Preciso de um e-mail no formato correto, por exemplo: nome@email.com",
        ]
    },
    "telefone": {
        "description": "numero de telefone/WhatsApp",
        "examples": ["(11) 99999-9999", "11999999999"],
        "validation_hint": "telefone com DDD",
        "empathy_responses": [
            "Certo!",
            "Entendi!",
            "Anotado!",
        ],
        "retry_hints": [
            "Qual o melhor telefone para contato?",
            "Pode me passar seu numero com DDD?",
            "Preciso do telefone com o codigo de area (DDD), por favor.",
        ]
    },
    "cidade": {
        "description": "cidade onde mora ou deseja atendimento",
        "examples": ["Sao Paulo", "Rio de Janeiro"],
        "validation_hint": "nome da cidade",
        "empathy_responses": [
            "Que legal!",
            "Boa!",
            "Entendi!",
        ],
        "retry_hints": [
            "Em qual cidade voce esta?",
            "Poderia me dizer sua cidade?",
            "Preciso saber a cidade para dar continuidade.",
        ]
    },
    "endereco": {
        "description": "endereco completo",
        "examples": ["Rua das Flores, 123, Centro"],
        "validation_hint": "endereco com rua, numero e bairro",
        "empathy_responses": [
            "Perfeito!",
            "Anotado!",
            "Obrigado!",
        ],
        "retry_hints": [
            "Qual seu endereco completo?",
            "Pode informar rua, numero e bairro?",
            "Preciso do endereco completo para prosseguir.",
        ]
    },
    "cpf": {
        "description": "CPF para cadastro",
        "examples": ["123.456.789-00"],
        "validation_hint": "CPF com 11 digitos",
        "empathy_responses": [
            "Certo!",
            "Ok!",
            "Anotado!",
        ],
        "retry_hints": [
            "Qual seu CPF?",
            "Poderia informar os 11 digitos do seu CPF?",
            "Preciso do CPF no formato correto (11 digitos).",
        ]
    },
    "cnpj": {
        "description": "CNPJ da empresa",
        "examples": ["12.345.678/0001-99"],
        "validation_hint": "CNPJ com 14 digitos",
        "empathy_responses": [
            "Entendi!",
            "Certo!",
            "Ok!",
        ],
        "retry_hints": [
            "Qual o CNPJ da empresa?",
            "Poderia informar o CNPJ?",
            "Preciso do CNPJ completo (14 digitos).",
        ]
    },
    "cep": {
        "description": "CEP do endereco",
        "examples": ["01310-100"],
        "validation_hint": "CEP com 8 digitos",
        "empathy_responses": [
            "Perfeito!",
            "Anotado!",
            "Ok!",
        ],
        "retry_hints": [
            "Qual o CEP?",
            "Pode informar o CEP do endereco?",
            "Preciso do CEP (8 digitos) para continuar.",
        ]
    },
    "data_nascimento": {
        "description": "data de nascimento",
        "examples": ["15/03/1990", "15-03-1990"],
        "validation_hint": "data no formato DD/MM/AAAA",
        "empathy_responses": [
            "Certo!",
            "Ok!",
            "Anotado!",
        ],
        "retry_hints": [
            "Qual sua data de nascimento?",
            "Pode informar no formato dia/mes/ano?",
            "Preciso da data de nascimento (DD/MM/AAAA).",
        ]
    },
    "interesse": {
        "description": "interesse ou necessidade do cliente",
        "examples": ["produto X", "servico Y"],
        "validation_hint": "descricao do interesse",
        "empathy_responses": [
            "Que interessante!",
            "Entendi perfeitamente!",
            "Otima escolha!",
        ],
        "retry_hints": [
            "O que mais te interessa?",
            "Pode me contar mais sobre sua necessidade?",
            "Qual seu principal interesse ou objetivo?",
        ]
    },
    "orcamento": {
        "description": "orcamento ou valor disponivel",
        "examples": ["R$ 5.000", "5000", "entre 3 e 5 mil"],
        "validation_hint": "valor ou faixa de valores",
        "empathy_responses": [
            "Entendi!",
            "Certo!",
            "Perfeito!",
        ],
        "retry_hints": [
            "Qual valor voce tem em mente?",
            "Pode me dar uma ideia de orcamento?",
            "Qual sua faixa de investimento?",
        ]
    },
    "urgencia": {
        "description": "nivel de urgencia ou prazo",
        "examples": ["urgente", "pode esperar", "para ontem"],
        "validation_hint": "descricao da urgencia",
        "empathy_responses": [
            "Entendi a urgencia!",
            "Compreendo!",
            "Vou priorizar isso!",
        ],
        "retry_hints": [
            "Qual a urgencia?",
            "Para quando voce precisa?",
            "Qual o prazo ideal para voce?",
        ]
    },
    "empresa": {
        "description": "nome da empresa",
        "examples": ["Empresa ABC", "Comercio XYZ"],
        "validation_hint": "nome ou razao social",
        "empathy_responses": [
            "Interessante!",
            "Que bom!",
            "Legal!",
        ],
        "retry_hints": [
            "Qual o nome da empresa?",
            "Pode informar a empresa?",
            "Me diz o nome da empresa, por favor.",
        ]
    },
    "cargo": {
        "description": "cargo ou funcao na empresa",
        "examples": ["Gerente", "Diretor", "Analista"],
        "validation_hint": "cargo ou funcao",
        "empathy_responses": [
            "Entendi!",
            "Ok!",
            "Certo!",
        ],
        "retry_hints": [
            "Qual seu cargo?",
            "Qual sua funcao na empresa?",
            "Pode me dizer seu cargo atual?",
        ]
    },
}


class ConversationalQuestionHandler:
    """
    Humanizes flow questions using LLM to make conversations more natural.

    This class takes a flow question and transforms it into a natural,
    empathetic response that:
    1. First acknowledges/responds to what the user said (empathy)
    2. Then asks the next question in a natural way

    Attributes:
        client: AsyncOpenAI client for LLM calls
        model: Model to use (default: gpt-4o-mini)
        max_retries: Maximum retries for LLM calls
        default_context: Default context values
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_retries: int = 2,
        default_context: Optional[HumanizerContext] = None
    ):
        """
        Initialize the ConversationalQuestionHandler.

        Args:
            api_key: OpenAI API key (uses env var if not provided)
            model: OpenAI model to use
            max_retries: Maximum retries for LLM calls
            default_context: Default context for humanization
        """
        self.client = AsyncOpenAI(api_key=api_key) if api_key else AsyncOpenAI()
        self.model = model
        self.max_retries = max_retries
        self.default_context = default_context or HumanizerContext()

        logger.info(f"ConversationalQuestionHandler initialized with model: {model}")

    def _get_field_hints(self, field_to_collect: str) -> Dict[str, Any]:
        """Get hints for a specific field type"""
        # Normalize field name
        normalized = field_to_collect.lower().strip()

        # Direct match
        if normalized in FIELD_HINTS:
            return FIELD_HINTS[normalized]

        # Partial match
        for key, hints in FIELD_HINTS.items():
            if key in normalized or normalized in key:
                return hints

        # Default hints for unknown fields
        return {
            "description": f"informacao de {field_to_collect}",
            "examples": [],
            "validation_hint": "informacao valida",
            "empathy_responses": ["Entendi!", "Certo!", "Ok!"],
            "retry_hints": [
                f"Poderia informar {field_to_collect}?",
                f"Preciso da informacao de {field_to_collect}.",
                f"Por favor, informe {field_to_collect}.",
            ]
        }

    def _build_system_prompt(
        self,
        context: HumanizerContext,
        field_to_collect: str,
        retry_count: int
    ) -> str:
        """Build the system prompt for humanization"""
        field_hints = self._get_field_hints(field_to_collect)

        tone_instructions = {
            "friendly": "amigavel e acolhedor, como um amigo prestativo",
            "professional": "profissional mas caloroso, como um consultor experiente",
            "casual": "descontraido e informal, como um colega de trabalho",
        }

        tone_desc = tone_instructions.get(context.tone, tone_instructions["friendly"])

        retry_instruction = ""
        if retry_count == 1:
            retry_instruction = """
ATENCAO: Esta e a SEGUNDA tentativa de coletar esta informacao.
- Reformule a pergunta de forma DIFERENTE
- Seja mais especifico sobre o que precisa
- Mantenha tom compreensivo, sem parecer frustrado
"""
        elif retry_count >= 2:
            retry_instruction = """
ATENCAO: Esta e a TERCEIRA+ tentativa de coletar esta informacao.
- Use linguagem MUITO clara e direta
- De um exemplo concreto do formato esperado
- Explique POR QUE precisa dessa informacao
- Mantenha tom paciente e prestativo
"""

        system_prompt = f"""Voce e um assistente de atendimento da {context.company_name}.
Seu nome e {context.agent_name}. Seu tom deve ser {tone_desc}.

REGRAS FUNDAMENTAIS:
1. SEMPRE responda ao que o usuario disse PRIMEIRO (empatia/reconhecimento)
2. DEPOIS faca a pergunta de forma natural
3. Use linguagem brasileira natural (nao use "voce" formal demais)
4. NUNCA invente informacoes ou prometa coisas que nao pode cumprir
5. Mantenha respostas CURTAS e objetivas (maximo 3 frases)

FORMATACAO WHATSAPP (OBRIGATORIO):
- Use DUAS quebras de linha (\\n\\n) entre a parte de empatia e a pergunta
- NAO use markdown, asteriscos ou formatacao especial
- Mantenha texto simples e limpo

CAMPO A COLETAR: {field_to_collect}
DESCRICAO: {field_hints['description']}
DICA DE VALIDACAO: {field_hints['validation_hint']}
{f"EXEMPLOS: {', '.join(field_hints['examples'])}" if field_hints.get('examples') else ""}

{retry_instruction}

{"CONTEXTO DO CLIENTE: " + str(context.extra_context) if context.extra_context else ""}
{f"NOME DO CLIENTE: {context.lead_name}" if context.lead_name else ""}

Sua resposta deve:
1. Primeiro: Reagir empaticamente ao que o usuario disse (1 frase curta)
2. Segundo: Fazer a pergunta para coletar {field_to_collect} (1-2 frases)

Responda APENAS com o texto humanizado, sem explicacoes adicionais."""

        return system_prompt

    def _build_messages(
        self,
        user_message: str,
        conversation_history: List[ConversationMessage],
        original_question: str,
        system_prompt: str
    ) -> List[Dict[str, str]]:
        """Build the messages list for the LLM call"""
        messages = [{"role": "system", "content": system_prompt}]

        # Add relevant conversation history (last 4 messages for context)
        if conversation_history:
            for msg in conversation_history[-4:]:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Add the humanization request
        humanization_request = f"""
MENSAGEM DO USUARIO: "{user_message}"

PERGUNTA ORIGINAL DO FLUXO: "{original_question}"

Gere uma resposta humanizada que:
1. Primeiro reconheca/responda a mensagem do usuario
2. Depois faca a pergunta de forma natural

Lembre-se: Use DUAS quebras de linha (\\n\\n) entre a empatia e a pergunta."""

        messages.append({"role": "user", "content": humanization_request})

        return messages

    def _format_for_whatsapp(self, text: str) -> str:
        """
        Ensure text is properly formatted for WhatsApp.
        - Double line breaks between sections
        - No markdown or special formatting
        - Clean, readable text
        """
        if not text:
            return text

        # Remove markdown formatting
        text = text.replace("**", "").replace("__", "").replace("*", "").replace("_", "")

        # Ensure double line breaks are preserved
        # First normalize multiple newlines
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Ensure at least double line break between sentences that should be separated
        # Look for period followed by capital letter
        text = re.sub(r'\.(\s*)([A-Z])', r'.\n\n\2', text)

        # Clean up any trailing/leading whitespace per line
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)

        # Ensure proper double breaks
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _get_fallback_response(
        self,
        user_message: str,
        original_question: str,
        field_to_collect: str,
        retry_count: int,
        context: HumanizerContext
    ) -> str:
        """
        Generate a fallback response when LLM fails.
        Uses field hints to create a reasonable response.
        """
        field_hints = self._get_field_hints(field_to_collect)

        # Get appropriate empathy response
        empathy = field_hints.get("empathy_responses", ["Entendi!"])[0]

        # Get appropriate retry hint based on count
        retry_hints = field_hints.get("retry_hints", [original_question])
        retry_idx = min(retry_count, len(retry_hints) - 1)
        question = retry_hints[retry_idx] if retry_count > 0 else original_question

        # Personalize if we have the lead name
        if context.lead_name:
            empathy = f"{empathy} {context.lead_name},"

        return f"{empathy}\n\n{question}"

    async def humanize(
        self,
        user_message: str,
        conversation_history: Optional[List[ConversationMessage]] = None,
        field_to_collect: str = "resposta",
        original_question: str = "",
        context: Optional[HumanizerContext] = None,
        retry_count: int = 0,
        skip_humanize: bool = False
    ) -> str:
        """
        Humanize a flow question using LLM.

        This method takes the original question from the flow and transforms
        it into a natural, empathetic response that first acknowledges what
        the user said, then asks the next question.

        Args:
            user_message: The message the user just sent
            conversation_history: List of previous messages in the conversation
            field_to_collect: The field being collected (nome, email, etc.)
            original_question: The original question from the flow
            context: Context with lead_name, agent_name, company, etc.
            retry_count: Number of times this question has been asked (0, 1, 2+)
            skip_humanize: If True, return original_question without LLM processing

        Returns:
            Humanized response string formatted for WhatsApp

        Example:
            >>> handler = ConversationalQuestionHandler()
            >>> context = HumanizerContext(
            ...     lead_name="Maria",
            ...     agent_name="Julia",
            ...     company_name="TechCorp"
            ... )
            >>> response = await handler.humanize(
            ...     user_message="Oi, quero saber mais sobre o produto",
            ...     field_to_collect="nome",
            ...     original_question="Qual seu nome completo?",
            ...     context=context
            ... )
            >>> print(response)
            # "Ola! Fico feliz em ajudar com informacoes sobre nosso produto!
            #
            # Para comecar, pode me dizer seu nome completo?"
        """
        # Use default context if not provided
        ctx = context or self.default_context
        history = conversation_history or []

        # Skip humanization if flag is set
        if skip_humanize:
            logger.debug(f"Skipping humanization for field: {field_to_collect}")
            return self._format_for_whatsapp(original_question)

        # If no user message, just format the original question
        if not user_message or not user_message.strip():
            return self._format_for_whatsapp(original_question)

        # Build prompts
        system_prompt = self._build_system_prompt(ctx, field_to_collect, retry_count)
        messages = self._build_messages(
            user_message, history, original_question, system_prompt
        )

        # Attempt LLM call with retries
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    f"Humanizing question for field '{field_to_collect}' "
                    f"(retry_count={retry_count}, attempt={attempt})"
                )

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=200,
                    timeout=10.0
                )

                humanized_text = response.choices[0].message.content

                if humanized_text:
                    formatted = self._format_for_whatsapp(humanized_text)
                    logger.info(
                        f"Successfully humanized question for '{field_to_collect}': "
                        f"{len(formatted)} chars"
                    )
                    return formatted

            except openai.RateLimitError as e:
                logger.warning(f"Rate limit hit on attempt {attempt}: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                continue

            except openai.APIConnectionError as e:
                logger.warning(f"Connection error on attempt {attempt}: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5)
                continue

            except Exception as e:
                logger.error(f"Unexpected error during humanization: {e}")
                break

        # Fallback to template-based response
        logger.warning(
            f"LLM humanization failed for '{field_to_collect}', using fallback"
        )
        fallback = self._get_fallback_response(
            user_message, original_question, field_to_collect, retry_count, ctx
        )
        return self._format_for_whatsapp(fallback)

    async def humanize_validation_error(
        self,
        user_message: str,
        field_to_collect: str,
        error_message: str,
        original_question: str,
        context: Optional[HumanizerContext] = None,
        retry_count: int = 1
    ) -> str:
        """
        Humanize a validation error message.

        Creates a friendly message that explains the validation error
        and asks the user to try again.

        Args:
            user_message: What the user sent that failed validation
            field_to_collect: The field being collected
            error_message: The technical validation error
            original_question: The original question to re-ask
            context: Humanizer context
            retry_count: How many times we've asked

        Returns:
            Humanized error message with re-ask
        """
        ctx = context or self.default_context
        field_hints = self._get_field_hints(field_to_collect)

        # Build a specific prompt for validation errors
        system_prompt = f"""Voce e um assistente de atendimento da {ctx.company_name}.
Seu nome e {ctx.agent_name}. Seja amigavel e compreensivo.

O usuario forneceu uma informacao que nao passou na validacao.
Voce precisa explicar o problema de forma gentil e pedir novamente.

REGRAS:
1. NAO culpe o usuario, seja compreensivo
2. Explique o que precisa de forma clara
3. De um exemplo do formato correto
4. Use linguagem brasileira natural
5. Mantenha resposta CURTA (max 3 frases)

FORMATACAO WHATSAPP:
- Use DUAS quebras de linha (\\n\\n) entre explicacao e nova pergunta
- Texto simples, sem markdown

CAMPO: {field_to_collect}
ERRO: {error_message}
FORMATO ESPERADO: {field_hints['validation_hint']}
{f"EXEMPLO: {field_hints['examples'][0]}" if field_hints.get('examples') else ""}

Responda APENAS com o texto humanizado."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Usuario digitou: '{user_message}'\nPergunta original: '{original_question}'"}
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=150,
                timeout=10.0
            )

            humanized = response.choices[0].message.content
            if humanized:
                return self._format_for_whatsapp(humanized)

        except Exception as e:
            logger.error(f"Error humanizing validation error: {e}")

        # Fallback
        retry_hints = field_hints.get("retry_hints", [original_question])
        retry_idx = min(retry_count, len(retry_hints) - 1)

        fallback = f"Ops, parece que houve um probleminha com essa informacao.\n\n{retry_hints[retry_idx]}"
        return self._format_for_whatsapp(fallback)

    async def humanize_greeting(
        self,
        lead_name: Optional[str] = None,
        greeting_message: str = "",
        context: Optional[HumanizerContext] = None
    ) -> str:
        """
        Humanize a greeting message.

        Args:
            lead_name: Name of the lead (if known)
            greeting_message: Original greeting from flow
            context: Humanizer context

        Returns:
            Humanized greeting
        """
        ctx = context or self.default_context

        if ctx.lead_name or lead_name:
            name = ctx.lead_name or lead_name
            greeting_message = greeting_message.replace("{nome}", name)
            greeting_message = greeting_message.replace("{lead_name}", name)

        # Greetings usually don't need heavy humanization
        # Just format properly
        return self._format_for_whatsapp(greeting_message)

    def create_context(
        self,
        lead_name: Optional[str] = None,
        agent_name: str = "Assistente",
        company_name: str = "nossa empresa",
        business_type: Optional[str] = None,
        tone: str = "friendly",
        **extra
    ) -> HumanizerContext:
        """
        Factory method to create a HumanizerContext.

        Args:
            lead_name: Name of the lead
            agent_name: Name of the AI agent
            company_name: Name of the company
            business_type: Type of business (for context)
            tone: Conversation tone (friendly, professional, casual)
            **extra: Additional context data

        Returns:
            HumanizerContext instance
        """
        return HumanizerContext(
            lead_name=lead_name,
            agent_name=agent_name,
            company_name=company_name,
            business_type=business_type,
            tone=tone,
            extra_context=extra
        )


# Convenience function for quick humanization
async def humanize_question(
    user_message: str,
    field_to_collect: str,
    original_question: str,
    lead_name: Optional[str] = None,
    agent_name: str = "Assistente",
    company_name: str = "nossa empresa",
    retry_count: int = 0,
    skip_humanize: bool = False,
    api_key: Optional[str] = None
) -> str:
    """
    Convenience function for quick question humanization.

    Args:
        user_message: What the user said
        field_to_collect: Field being collected
        original_question: Original flow question
        lead_name: Lead's name (optional)
        agent_name: AI agent name
        company_name: Company name
        retry_count: Retry attempt number
        skip_humanize: Skip LLM processing
        api_key: OpenAI API key (optional)

    Returns:
        Humanized question string

    Example:
        >>> response = await humanize_question(
        ...     user_message="Oi, vim pelo Instagram",
        ...     field_to_collect="nome",
        ...     original_question="Qual seu nome?",
        ...     lead_name=None,
        ...     company_name="MinhaTech"
        ... )
    """
    handler = ConversationalQuestionHandler(api_key=api_key)
    context = handler.create_context(
        lead_name=lead_name,
        agent_name=agent_name,
        company_name=company_name
    )

    return await handler.humanize(
        user_message=user_message,
        field_to_collect=field_to_collect,
        original_question=original_question,
        context=context,
        retry_count=retry_count,
        skip_humanize=skip_humanize
    )


# Export main classes and functions
__all__ = [
    "ConversationalQuestionHandler",
    "HumanizerContext",
    "ConversationMessage",
    "FieldType",
    "FIELD_HINTS",
    "humanize_question",
]
