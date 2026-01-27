"""
Dynamic prompt builder - 100% generic.

This module contains all prompt templates for the agent, including:
- System prompts for different scenarios
- Extraction prompts for data collection
- Qualification prompts
- Proposal prompts
- Follow-up prompts
"""
from typing import Optional, Any
from datetime import datetime


class PromptBuilder:
    """Builds dynamic prompts based on company configuration and context."""

    # Tone descriptions mapping
    TONE_DESCRIPTIONS = {
        "amigavel": "amigavel, caloroso e acolhedor",
        "formal": "profissional, respeitoso e formal",
        "casual": "descontraido, informal e proximo",
        "tecnico": "tecnico, preciso e informativo",
        "vendedor": "persuasivo, entusiasmado e focado em vendas",
        "consultivo": "consultivo, analitico e focado em solucoes"
    }

    @staticmethod
    def build_system_prompt(
        agent_name: str,
        agent_tone: str,
        use_emojis: bool,
        company_name: str,
        company_info: Optional[str] = None,
        lead_name: Optional[str] = None,
        lead_data: Optional[dict[str, Any]] = None,
        current_question: Optional[str] = None,
        expected_field: Optional[str] = None,
        qualification_stage: Optional[str] = None,
        available_tools: Optional[list[str]] = None
    ) -> str:
        """
        Build the main system prompt for the agent.

        Args:
            agent_name: Name of the AI agent
            agent_tone: Tone style (amigavel, formal, casual, tecnico, etc.)
            use_emojis: Whether to use emojis in responses
            company_name: Name of the company
            company_info: Additional company information
            lead_name: Customer's name if known
            lead_data: Dictionary of collected customer data
            current_question: Question being asked (for flow context)
            expected_field: Field expected in response
            qualification_stage: Current qualification stage
            available_tools: List of available tool names

        Returns:
            Formatted system prompt string
        """
        # Get tone description
        tone_desc = PromptBuilder.TONE_DESCRIPTIONS.get(
            agent_tone,
            PromptBuilder.TONE_DESCRIPTIONS["amigavel"]
        )

        # Emoji instruction
        emoji_instruction = (
            "Use emojis de forma moderada para tornar a conversa mais amigavel."
            if use_emojis else
            "NAO use emojis nas respostas."
        )

        # Lead context
        lead_context = ""
        if lead_name:
            lead_context = f"\nO nome do cliente e: {lead_name}. Use o nome dele quando apropriado."
        if lead_data:
            formatted_data = ", ".join([f"{k}: {v}" for k, v in lead_data.items() if v])
            if formatted_data:
                lead_context += f"\nInformacoes ja coletadas: {formatted_data}"

        # Question context
        question_context = ""
        if current_question and expected_field:
            question_context = f"""
IMPORTANTE: Voce fez a seguinte pergunta ao cliente: "{current_question}"
O cliente deve responder sobre: {expected_field}
Analise a resposta do cliente e extraia a informacao solicitada.
Se a resposta nao for clara, peca educadamente para ele esclarecer."""

        # Company info
        extra_info = ""
        if company_info:
            extra_info = f"\n\nINFORMACOES ADICIONAIS DA EMPRESA:\n{company_info}"

        # Qualification stage context
        stage_context = ""
        if qualification_stage:
            stage_contexts = {
                "initial": "Voce esta no primeiro contato. Foque em entender a necessidade do cliente.",
                "qualifying": "Voce esta qualificando o lead. Colete informacoes importantes.",
                "qualified": "O lead ja esta qualificado. Foque em apresentar solucoes.",
                "proposal": "Momento de apresentar proposta. Seja persuasivo mas honesto.",
                "negotiation": "Cliente em negociacao. Seja flexivel mas mantenha o valor.",
                "closed_won": "Parabens! Cliente fechou. Foque no onboarding.",
                "closed_lost": "Mantenha relacionamento. Talvez haja oportunidade futura."
            }
            stage_context = f"\n\nESTAGIO ATUAL: {stage_contexts.get(qualification_stage, '')}"

        # Tools context
        tools_context = ""
        if available_tools:
            tools_context = f"\n\nFERRAMENTAS DISPONIVEIS: {', '.join(available_tools)}"

        # Build the prompt
        system_prompt = f"""Voce e {agent_name}, assistente virtual da empresa {company_name}.

PERSONALIDADE:
- Seu tom deve ser {tone_desc}
- {emoji_instruction}
- Seja conciso e direto nas respostas
- Mantenha o foco na conversa e nos objetivos

REGRAS:
1. Nunca invente informacoes que nao possui
2. Se nao souber responder algo, diga que vai verificar ou encaminhe para um atendente
3. Responda sempre em portugues brasileiro
4. Mantenha as respostas curtas (maximo 3 frases quando possivel)
5. Seja educado e prestativo
6. Colete informacoes de forma natural durante a conversa
7. Use as ferramentas disponiveis quando apropriado
{lead_context}
{question_context}
{stage_context}
{extra_info}
{tools_context}

Responda a mensagem do cliente de forma natural e adequada ao contexto."""

        return system_prompt

    @staticmethod
    def build_extraction_prompt(
        user_message: str,
        field_name: str,
        field_type: str,
        options: Optional[list[str]] = None
    ) -> str:
        """
        Build prompt for extracting a specific field value from user message.

        Args:
            user_message: The user's message to extract from
            field_name: Name of the field being extracted
            field_type: Type of field (text, number, email, phone, date, boolean, select)
            options: For select type, list of valid options

        Returns:
            Formatted extraction prompt
        """
        type_instructions = {
            "text": "Extraia o texto da resposta de forma limpa.",
            "number": "Extraia apenas o numero da resposta. Retorne apenas digitos. Se houver unidade (R$, kg, m), ignore-a.",
            "email": "Extraia o endereco de email da resposta. Verifique se e um email valido.",
            "phone": "Extraia o numero de telefone da resposta. Mantenha apenas os digitos. Se necessario, adicione o DDD.",
            "date": "Extraia a data da resposta no formato DD/MM/AAAA. Interprete datas relativas (amanha, proxima semana).",
            "boolean": "Determine se a resposta e afirmativa (retorne 'sim') ou negativa (retorne 'nao').",
            "select": f"Identifique qual das opcoes o cliente escolheu: {', '.join(options or [])}. Retorne exatamente a opcao escolhida.",
            "name": "Extraia o nome da pessoa. Capitalize corretamente (primeira letra maiuscula).",
            "cpf": "Extraia o CPF. Retorne apenas os 11 digitos, sem pontos ou tracos.",
            "cnpj": "Extraia o CNPJ. Retorne apenas os 14 digitos, sem pontos ou tracos."
        }

        instruction = type_instructions.get(field_type, type_instructions["text"])

        return f"""Mensagem do cliente: "{user_message}"

Campo a extrair: {field_name}
Tipo do campo: {field_type}

{instruction}

REGRAS:
1. Retorne APENAS o valor extraido, sem explicacoes adicionais
2. Se nao for possivel extrair a informacao com certeza, retorne "INVALID"
3. Nao invente informacoes
4. Para nomes, use formato adequado (Ex: "joao silva" -> "Joao Silva")
5. Para numeros de telefone, mantenha formato brasileiro (Ex: 11999998888)

Valor extraido:"""

    @staticmethod
    def build_qualification_prompt(
        lead_data: dict[str, Any],
        company_info: Optional[str] = None,
        qualification_criteria: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Build prompt for qualifying a lead.

        Args:
            lead_data: Dictionary with collected lead data
            company_info: Company information for context
            qualification_criteria: Custom qualification criteria

        Returns:
            Formatted qualification prompt
        """
        formatted_data = "\n".join([f"- {k}: {v}" for k, v in lead_data.items() if v])

        criteria_text = ""
        if qualification_criteria:
            criteria_text = "\nCRITERIOS DE QUALIFICACAO:\n" + "\n".join(
                [f"- {k}: {v}" for k, v in qualification_criteria.items()]
            )

        company_context = ""
        if company_info:
            company_context = f"\nCONTEXTO DA EMPRESA:\n{company_info}"

        return f"""Analise os dados do lead e determine sua qualificacao:

DADOS DO LEAD:
{formatted_data}
{company_context}
{criteria_text}

TAREFA:
1. Avalie o potencial do lead com base nos dados
2. Atribua uma pontuacao de 0 a 100
3. Identifique o estagio de qualificacao: initial, qualifying, qualified, proposal, negotiation
4. Liste os pontos fortes e fracos
5. Sugira proximos passos

Responda no formato:
PONTUACAO: [0-100]
ESTAGIO: [estagio]
PONTOS_FORTES: [lista]
PONTOS_FRACOS: [lista]
PROXIMOS_PASSOS: [sugestoes]"""

    @staticmethod
    def build_proposal_prompt(
        lead_data: dict[str, Any],
        company_name: str,
        products_services: Optional[str] = None,
        pricing_info: Optional[str] = None,
        proposal_type: str = "standard"
    ) -> str:
        """
        Build prompt for generating a proposal.

        Args:
            lead_data: Dictionary with lead data
            company_name: Company name
            products_services: Available products/services
            pricing_info: Pricing information
            proposal_type: Type of proposal (standard, custom, budget)

        Returns:
            Formatted proposal prompt
        """
        formatted_data = "\n".join([f"- {k}: {v}" for k, v in lead_data.items() if v])

        products_context = ""
        if products_services:
            products_context = f"\nPRODUTOS/SERVICOS DISPONIVEIS:\n{products_services}"

        pricing_context = ""
        if pricing_info:
            pricing_context = f"\nINFORMACOES DE PRECO:\n{pricing_info}"

        proposal_styles = {
            "standard": "Crie uma proposta padrao com os beneficios principais.",
            "custom": "Crie uma proposta personalizada destacando como atende as necessidades especificas.",
            "budget": "Crie uma proposta focada no custo-beneficio e economia."
        }

        style_instruction = proposal_styles.get(proposal_type, proposal_styles["standard"])

        return f"""Crie uma proposta comercial para o cliente.

DADOS DO CLIENTE:
{formatted_data}

EMPRESA: {company_name}
{products_context}
{pricing_context}

TIPO DE PROPOSTA: {proposal_type}
{style_instruction}

A proposta deve:
1. Ser personalizada para o cliente
2. Destacar os beneficios relevantes
3. Apresentar opcoes quando possivel
4. Incluir um call-to-action claro
5. Ser concisa mas completa

Proposta:"""

    @staticmethod
    def build_followup_prompt(
        lead_data: dict[str, Any],
        last_interaction: Optional[str] = None,
        days_since_contact: int = 0,
        followup_type: str = "check_in"
    ) -> str:
        """
        Build prompt for generating follow-up messages.

        Args:
            lead_data: Dictionary with lead data
            last_interaction: Summary of last interaction
            days_since_contact: Days since last contact
            followup_type: Type of follow-up (check_in, proposal, reminder, re_engagement)

        Returns:
            Formatted follow-up prompt
        """
        lead_name = lead_data.get("nome", "Cliente")

        last_context = ""
        if last_interaction:
            last_context = f"\nULTIMA INTERACAO:\n{last_interaction}"

        followup_contexts = {
            "check_in": f"Faz {days_since_contact} dias desde o ultimo contato. Faca um check-in amigavel.",
            "proposal": "O cliente recebeu uma proposta. Pergunte se teve chance de analisar.",
            "reminder": "Lembre o cliente sobre algo pendente de forma educada.",
            "re_engagement": f"Cliente inativo ha {days_since_contact} dias. Tente reengajar com novidade ou oferta."
        }

        context = followup_contexts.get(followup_type, followup_contexts["check_in"])

        return f"""Crie uma mensagem de follow-up para {lead_name}.
{last_context}

CONTEXTO: {context}

DADOS DO CLIENTE:
{", ".join([f"{k}: {v}" for k, v in lead_data.items() if v and k != "nome"])}

A mensagem deve:
1. Ser breve e direta
2. Personalizada para o cliente
3. Ter um objetivo claro
4. Nao parecer spam ou automatizada
5. Incluir uma pergunta ou call-to-action

Mensagem de follow-up:"""

    @staticmethod
    def build_summary_prompt(
        messages: list[dict[str, str]],
        lead_data: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Build prompt for summarizing a conversation.

        Args:
            messages: List of conversation messages
            lead_data: Optional lead data for context

        Returns:
            Formatted summary prompt
        """
        conversation_text = "\n".join([
            f"{'Cliente' if m.get('role') == 'user' or m.get('direction') == 'inbound' else 'Assistente'}: {m.get('content', '')}"
            for m in messages
        ])

        lead_context = ""
        if lead_data:
            lead_context = f"\nDADOS DO CLIENTE: {lead_data}"

        return f"""Resuma a conversa abaixo de forma concisa:

CONVERSA:
{conversation_text}
{lead_context}

O resumo deve incluir:
1. Motivo do contato
2. Principais pontos discutidos
3. Informacoes coletadas
4. Status atual (resolvido, pendente, transferido)
5. Proximos passos recomendados

Resumo:"""

    @staticmethod
    def build_intent_detection_prompt(user_message: str) -> str:
        """
        Build prompt for detecting user intent.

        Args:
            user_message: The user's message

        Returns:
            Formatted intent detection prompt
        """
        return f"""Analise a mensagem do usuario e identifique a intencao principal.

Mensagem: "{user_message}"

Intencoes possiveis:
- saudacao: O usuario esta cumprimentando
- informacao: O usuario quer saber algo
- compra: O usuario quer comprar algo
- suporte: O usuario precisa de ajuda/suporte
- reclamacao: O usuario esta reclamando
- agendamento: O usuario quer agendar algo
- preco: O usuario pergunta sobre precos
- humano: O usuario quer falar com uma pessoa
- despedida: O usuario esta se despedindo
- outro: Nenhuma das anteriores

Responda APENAS com a intencao identificada (uma palavra)."""

    @staticmethod
    def build_sentiment_prompt(user_message: str) -> str:
        """
        Build prompt for sentiment analysis.

        Args:
            user_message: The user's message

        Returns:
            Formatted sentiment analysis prompt
        """
        return f"""Analise o sentimento da mensagem do usuario.

Mensagem: "{user_message}"

Responda APENAS com: positive, neutral, ou negative"""

    @staticmethod
    def build_flow_prompt(
        node_type: str,
        node_config: dict[str, Any],
        lead_data: dict[str, Any],
        user_message: str
    ) -> str:
        """
        Build prompt for flow node processing.

        Args:
            node_type: Type of flow node
            node_config: Node configuration
            lead_data: Current lead data
            user_message: User's message

        Returns:
            Formatted flow processing prompt
        """
        if node_type == "QUESTION":
            return f"""O cliente respondeu: "{user_message}"

A pergunta feita foi: "{node_config.get('pergunta', '')}"
O campo a ser preenchido e: {node_config.get('campo_destino', '')}
Tipo esperado: {node_config.get('tipo_campo', 'text')}

Extraia a informacao da resposta do cliente.
Se a resposta for valida, retorne apenas o valor extraido.
Se nao for possivel extrair a informacao, explique educadamente o que precisa."""

        elif node_type == "GREETING":
            return node_config.get('mensagem', 'Ola! Como posso ajudar?')

        elif node_type == "MESSAGE":
            # Replace placeholders in message
            message = node_config.get('mensagem', '')
            for key, value in lead_data.items():
                message = message.replace(f"{{{key}}}", str(value) if value else "")
            return message

        return ""

    @staticmethod
    def format_message_history(
        messages: list[dict[str, str]],
        max_messages: int = 10
    ) -> list[dict[str, str]]:
        """
        Format message history for context.

        Args:
            messages: List of message dictionaries
            max_messages: Maximum number of messages to include

        Returns:
            Formatted list of messages with role and content
        """
        # Get last N messages
        recent = messages[-max_messages:] if len(messages) > max_messages else messages

        formatted = []
        for msg in recent:
            role = "user" if msg.get("direction") == "inbound" else "assistant"
            if msg.get("role"):
                role = msg.get("role")
            formatted.append({
                "role": role,
                "content": msg.get("content", "")
            })

        return formatted

    @staticmethod
    def get_current_datetime_context() -> str:
        """
        Get current datetime context for prompts.

        Returns:
            String with current date, time, and day of week in Portuguese
        """
        now = datetime.now()
        days = ["Segunda-feira", "Terca-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sabado", "Domingo"]
        months = ["Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

        return f"""Data atual: {now.day} de {months[now.month - 1]} de {now.year}
Dia da semana: {days[now.weekday()]}
Horario: {now.strftime('%H:%M')}"""
