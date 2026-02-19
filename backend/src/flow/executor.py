"""
Flow Executor - Extended with 25+ node types support
Converts JSON configuration to executable flow with full validation and context management
"""
import logging
import re
import asyncio
from typing import Optional, Any, Dict, List, Callable, Awaitable
from datetime import datetime
import httpx
import random

from ..models.flow import (
    FlowConfig, FlowNode, NodeType, NodeConfig, ActionType,
    FieldType, GlobalConfig, Operator, MediaType, UrgencyLevel
)
from .context import FlowContext, FlowStatus, create_context
from .result import (
    FlowResult, ResultType, MediaRequestType,
    message_result, question_result, collected_result,
    validation_error_result, handoff_result, error_result,
    end_result, media_request_result, continue_result
)
from .validator import FlowValidator
from .evaluator import ConditionEvaluator

logger = logging.getLogger(__name__)


class FlowExecutor:
    """
    Extended Flow Executor with support for 25+ node types.

    Features:
    - Full validation and auto-correction
    - Context management for conversation state
    - Data collection with validation
    - Qualification scoring
    - Media handling
    - Webhook/API integration
    - Notification system
    - Commercial actions (proposals, scheduling, etc.)
    """

    # Validation patterns for field types
    VALIDATION_PATTERNS = {
        FieldType.EMAIL: r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        FieldType.PHONE: r'^[\d\s\(\)\-\+]{8,20}$',
        FieldType.CPF: r'^\d{3}\.?\d{3}\.?\d{3}\-?\d{2}$',
        FieldType.CNPJ: r'^\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2}$',
        FieldType.CEP: r'^\d{5}\-?\d{3}$',
        FieldType.DATE: r'^\d{2}[\/\-]\d{2}[\/\-]\d{4}$',
        FieldType.URL: r'^https?:\/\/[^\s]+$',
    }

    def __init__(
        self,
        flow_config: FlowConfig | Dict[str, Any],
        context: Optional[FlowContext] = None
    ):
        """
        Initialize the FlowExecutor.

        Args:
            flow_config: Flow configuration (FlowConfig or dict)
            context: Optional FlowContext for state management
        """
        # Handle dict input
        if isinstance(flow_config, dict):
            # Validate and autocorrect
            corrected_config = FlowValidator.autocorrect(flow_config)
            self.config = FlowConfig(**corrected_config)
            self._raw_config = corrected_config
        else:
            self.config = flow_config
            self._raw_config = flow_config.model_dump() if hasattr(flow_config, 'model_dump') else {}

        # Index nodes by ID
        self.nodes: Dict[str, FlowNode] = {}
        for node_data in self.config.nodes:
            if isinstance(node_data, dict):
                node = FlowNode(**node_data)
            else:
                node = node_data
            self.nodes[node.id] = node

        # Global configuration
        if self.config.global_config:
            if isinstance(self.config.global_config, dict):
                self.global_config = GlobalConfig(**self.config.global_config)
            else:
                self.global_config = self.config.global_config
        else:
            self.global_config = GlobalConfig()

        # Context and evaluator
        self.context = context
        self.evaluator = ConditionEvaluator()

        # Handler registry
        self._handlers: Dict[str, Callable] = self._register_handlers()

        logger.info(
            f"FlowExecutor initialized with {len(self.nodes)} nodes, "
            f"start_node: {self.config.start_node_id}"
        )

    def _register_handlers(self) -> Dict[str, Callable]:
        """Register all node type handlers"""
        return {
            # Basic nodes
            NodeType.GREETING.value: self._handle_greeting,
            NodeType.MESSAGE.value: self._handle_message,
            NodeType.QUESTION.value: self._handle_question,
            NodeType.CONDITION.value: self._handle_condition,
            NodeType.ACTION.value: self._handle_action,
            NodeType.HANDOFF.value: self._handle_handoff,
            NodeType.FOLLOWUP.value: self._handle_followup,

            # Data collection nodes
            NodeType.NOME.value: self._handle_data_collection,
            NodeType.EMAIL.value: self._handle_data_collection,
            NodeType.TELEFONE.value: self._handle_data_collection,
            NodeType.CIDADE.value: self._handle_data_collection,
            NodeType.ENDERECO.value: self._handle_data_collection,
            NodeType.CPF.value: self._handle_data_collection,
            NodeType.DATA_NASCIMENTO.value: self._handle_data_collection,

            # Qualification nodes
            NodeType.QUALIFICATION.value: self._handle_qualification,
            NodeType.INTERESSE.value: self._handle_data_collection,
            NodeType.ORCAMENTO.value: self._handle_data_collection,
            NodeType.URGENCIA.value: self._handle_data_collection,

            # Commercial nodes
            NodeType.PROPOSTA.value: self._handle_proposta,
            NodeType.NEGOCIACAO.value: self._handle_negociacao,
            NodeType.AGENDAMENTO.value: self._handle_agendamento,
            NodeType.VISITA.value: self._handle_visita,

            # Notification nodes
            NodeType.NOTIFICACAO.value: self._handle_notificacao,
            NodeType.ALERTA.value: self._handle_alerta,

            # Media nodes
            NodeType.FOTO.value: self._handle_foto,
            NodeType.DOCUMENTO.value: self._handle_documento,
            NodeType.AUDIO.value: self._handle_audio,
            NodeType.VIDEO.value: self._handle_video,

            # Integration nodes
            NodeType.WEBHOOK_CALL.value: self._handle_webhook,
            NodeType.API_INTEGRATION.value: self._handle_api_integration,

            # Control flow nodes
            NodeType.DELAY.value: self._handle_delay,
            NodeType.LOOP.value: self._handle_loop,
            NodeType.SWITCH.value: self._handle_switch,
            NodeType.PARALLEL.value: self._handle_parallel,
            NodeType.END.value: self._handle_end,
        }

    # ==================== Core Methods ====================

    def get_node(self, node_id: str) -> Optional[FlowNode]:
        """Get a node by ID"""
        return self.nodes.get(node_id)

    def get_start_node(self) -> Optional[FlowNode]:
        """Get the starting node"""
        return self.get_node(self.config.start_node_id)

    def get_next_node(
        self,
        current_node: FlowNode,
        condition_result: bool = True
    ) -> Optional[FlowNode]:
        """Get the next node based on current node and conditions"""
        if current_node.type == NodeType.CONDITION:
            if condition_result and current_node.true_node_id:
                return self.get_node(current_node.true_node_id)
            elif not condition_result and current_node.false_node_id:
                return self.get_node(current_node.false_node_id)

        if current_node.type == NodeType.QUALIFICATION:
            if condition_result and current_node.true_node_id:
                return self.get_node(current_node.true_node_id)
            elif not condition_result and current_node.false_node_id:
                return self.get_node(current_node.false_node_id)

        if current_node.next_node_id:
            return self.get_node(current_node.next_node_id)

        return None

    async def process_message(
        self,
        message: str,
        context: Optional[FlowContext] = None,
        lead_data: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """
        Process an incoming message through the flow.

        Args:
            message: User's message
            context: Flow context (uses self.context if not provided)
            lead_data: Additional lead data

        Returns:
            FlowResult with response and next actions
        """
        ctx = context or self.context
        data = lead_data or {}

        if ctx:
            data.update(ctx.collected_data)

        start_time = datetime.now()

        try:
            # Get current node
            current_node_id = ctx.current_node_id if ctx else self.config.start_node_id
            node = self.get_node(current_node_id)

            if not node:
                logger.warning(f"Node not found: {current_node_id}")
                # Start from beginning if node not found
                node = self.get_start_node()
                if not node:
                    return error_result("Fluxo nao configurado corretamente")

            # Clear waiting flags if we received input
            if ctx and (ctx.awaiting_input or ctx.awaiting_media):
                ctx.clear_waiting()

            # Get handler for node type
            handler = self._handlers.get(node.type.value, self._handle_unknown)

            # Execute handler
            result = await handler(node, message, data)

            # Record execution time
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            result.execution_time_ms = execution_time
            result.node_id = node.id
            result.node_type = node.type.value

            # Update context
            if ctx:
                ctx.record_node_response(
                    user_input=message,
                    response=result.response,
                    data_collected={result.collected_field: result.collected_value}
                    if result.collected_field else None
                )

                if result.collected_field and result.collected_value:
                    ctx.collect_field(result.collected_field, result.collected_value)

                if result.next_node_id:
                    next_node = self.get_node(result.next_node_id)
                    if next_node:
                        ctx.move_to_node(result.next_node_id, next_node.type.value)

                if result.should_wait:
                    ctx.set_waiting_input(result.collected_field)

                if result.requires_media:
                    ctx.set_waiting_media(result.media_type.value if result.media_type else "any")

                if result.should_handoff:
                    ctx.set_handoff(result.handoff_reason)

            logger.info(
                f"Processed message in {execution_time}ms - "
                f"Node: {node.id}, Type: {node.type.value}, "
                f"Next: {result.next_node_id}"
            )

            return result

        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            return error_result(
                str(e),
                error_code="EXECUTION_ERROR",
                is_recoverable=True,
                message=self.global_config.mensagem_timeout
            )

    async def execute_node(
        self,
        node: FlowNode,
        lead_data: Dict[str, Any],
        user_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a single node (backward compatibility).

        Args:
            node: The node to execute
            lead_data: Current lead data
            user_message: User's message

        Returns:
            Dictionary with execution results
        """
        result = await self.process_message(
            message=user_message or "",
            lead_data=lead_data
        )

        # Convert to legacy format
        return {
            "node_id": result.node_id,
            "node_type": result.node_type,
            "message": result.response,
            "next_node_id": result.next_node_id,
            "should_wait": result.should_wait,
            "data_collected": {result.collected_field: result.collected_value}
            if result.collected_field else {},
            "should_handoff": result.should_handoff,
            "action_result": result.action_result
        }

    # ==================== Template Processing ====================

    def _process_template(self, template: str, data: Dict[str, Any]) -> str:
        """Replace placeholders in template with actual values"""
        if not template:
            return ""

        result = template

        # Replace {field} placeholders
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value) if value else "")

        # Remove any remaining placeholders
        result = re.sub(r'\{[^}]+\}', '', result)

        return result.strip()

    def _get_message_with_variation(self, config: NodeConfig) -> str:
        """Get message with possible variation"""
        if config.mensagens_alternativas and random.random() > 0.5:
            return random.choice(config.mensagens_alternativas)
        return config.mensagem or ""

    # ==================== Validation ====================

    def _validate_field(
        self,
        value: str,
        field_type: Optional[FieldType],
        config: NodeConfig
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a field value.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value or not value.strip():
            if config.obrigatorio:
                return False, "Este campo e obrigatorio"
            return True, None

        value = value.strip()

        # Check field type pattern
        if field_type and field_type in self.VALIDATION_PATTERNS:
            pattern = self.VALIDATION_PATTERNS[field_type]
            if not re.match(pattern, value, re.IGNORECASE):
                return False, config.mensagem_erro or f"Formato invalido para {field_type.value}"

        # Check custom validation rules
        if config.validacao_rules:
            for rule in config.validacao_rules:
                if rule.type == "min_length" and len(value) < rule.value:
                    return False, rule.error_message or f"Minimo {rule.value} caracteres"
                if rule.type == "max_length" and len(value) > rule.value:
                    return False, rule.error_message or f"Maximo {rule.value} caracteres"
                if rule.type == "regex" and not re.match(rule.value, value):
                    return False, rule.error_message or "Formato invalido"

        # Check options for SELECT type
        if field_type == FieldType.SELECT and config.opcoes:
            if value.lower() not in [o.lower() for o in config.opcoes]:
                return False, f"Opcao invalida. Escolha entre: {', '.join(config.opcoes)}"

        return True, None

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number"""
        # Remove non-digits
        digits = re.sub(r'\D', '', phone)

        # Add country code if missing
        if len(digits) == 11:  # Brazilian mobile
            return f"+55{digits}"
        elif len(digits) == 10:  # Brazilian landline
            return f"+55{digits}"
        elif len(digits) == 13 and digits.startswith('55'):  # Already has country code
            return f"+{digits}"

        return phone

    def _normalize_cpf(self, cpf: str) -> str:
        """Normalize CPF"""
        digits = re.sub(r'\D', '', cpf)
        if len(digits) == 11:
            return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        return cpf

    # ==================== Basic Node Handlers ====================

    async def _handle_greeting(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle GREETING node"""
        response = self._process_template(
            self._get_message_with_variation(node.config),
            data
        )

        # Add delay if configured
        if node.config.delay_ms:
            await asyncio.sleep(node.config.delay_ms / 1000)

        return message_result(response, node.next_node_id)

    async def _handle_message(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle MESSAGE node"""
        response = self._process_template(
            self._get_message_with_variation(node.config),
            data
        )

        if node.config.delay_ms:
            await asyncio.sleep(node.config.delay_ms / 1000)

        return message_result(response, node.next_node_id)

    async def _handle_question(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle QUESTION node"""
        config = node.config
        field = config.campo_destino or "resposta"

        # First interaction: ask the question
        if not message:
            question = self._process_template(config.pergunta or "", data)

            # Add options if SELECT type
            if config.tipo_campo == FieldType.SELECT and config.opcoes:
                options_text = "\n".join([f"- {opt}" for opt in config.opcoes])
                question = f"{question}\n\nOpcoes:\n{options_text}"

            return question_result(question, field, node.next_node_id)

        # Validate response
        is_valid, error = self._validate_field(message, config.tipo_campo, config)

        if not is_valid:
            retry_msg = config.mensagem_erro or self.global_config.mensagem_erro_validacao
            return validation_error_result(field, error or "Valor invalido", retry_msg)

        # Success - collect and move on
        return collected_result(field, message, node.next_node_id)

    async def _handle_condition(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle CONDITION node"""
        config = node.config

        # Evaluate condition
        if config.expressao:
            # Complex expression
            condition_met = self.evaluator.evaluate_expression(config.expressao, data)
        else:
            # Simple field comparison
            field_value = data.get(config.campo)
            condition_met = self.evaluator.evaluate(
                field_value,
                config.operador,
                config.valor
            )

        # Get next node based on condition
        if condition_met and node.true_node_id:
            next_node_id = node.true_node_id
        elif not condition_met and node.false_node_id:
            next_node_id = node.false_node_id
        else:
            next_node_id = node.next_node_id

        logger.debug(
            f"Condition evaluated: {config.campo} {config.operador} {config.valor} = {condition_met}"
        )

        return continue_result(next_node_id)

    async def _handle_action(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle ACTION node"""
        config = node.config
        action_type = config.tipo_acao

        result = FlowResult(next_node_id=node.next_node_id)

        try:
            if action_type == ActionType.WEBHOOK:
                action_result = await self._execute_webhook(config, data)
                result.action_result = action_result
                result.action_triggered = "webhook"

            elif action_type == ActionType.UPDATE_FIELD:
                # Field update is handled at agent level
                result.action_triggered = "update_field"
                result.action_result = {"success": True}

            elif action_type == ActionType.MOVE_STATUS:
                result.action_triggered = "move_status"
                result.action_result = {"new_status_id": config.novo_status_id}

            elif action_type == ActionType.TAG_LEAD:
                result.action_triggered = "tag_lead"
                result.action_result = {"tags": config.tags}

            elif action_type == ActionType.NOTIFY_TEAM:
                result.should_notify = True
                result.notification_data = {
                    "channel": config.canal_notificacao or "email",
                    "message": self._process_template(
                        config.template_notificacao or "Nova acao no fluxo",
                        data
                    ),
                    "recipients": config.destinatarios
                }
                result.action_triggered = "notify_team"

            elif action_type == ActionType.SEND_EMAIL:
                result.action_triggered = "send_email"
                result.action_result = {"success": True}

            elif action_type == ActionType.SEND_SMS:
                result.action_triggered = "send_sms"
                result.action_result = {"success": True}

            elif action_type == ActionType.SET_VARIABLE:
                result.action_triggered = "set_variable"
                result.action_result = {"success": True}

            else:
                logger.warning(f"Unknown action type: {action_type}")

        except Exception as e:
            logger.exception(f"Error executing action: {e}")
            result.error = str(e)
            result.error_code = "ACTION_ERROR"

        return result

    async def _handle_handoff(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle HANDOFF node"""
        config = node.config

        response = self._process_template(
            config.mensagem_cliente or "Transferindo para atendimento humano.",
            data
        )

        result = handoff_result(
            message=response,
            reason=config.motivo or "Solicitacao do cliente",
            department=config.departamento
        )

        # Set notification if configured
        if config.notificar_equipe:
            result.set_notification(
                channel=config.canal_notificacao or "email",
                message=f"Handoff: {config.motivo}",
                urgency=config.prioridade or "normal"
            )

        return result

    async def _handle_followup(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle FOLLOWUP node"""
        config = node.config

        response = self._process_template(config.mensagem or "", data)

        result = FlowResult(
            response=response,
            next_node_id=node.next_node_id,
            action_triggered="schedule_followup",
            action_result={
                "intervals": config.intervalos,
                "messages": config.mensagens,
                "max_followups": config.max_followups
            }
        )

        return result

    # ==================== Data Collection Handlers ====================

    async def _handle_data_collection(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """
        Generic handler for data collection nodes.
        Works for: NOME, EMAIL, TELEFONE, CIDADE, ENDERECO, CPF,
                   DATA_NASCIMENTO, INTERESSE, ORCAMENTO, URGENCIA
        """
        config = node.config
        node_type = node.type.value

        # Map node types to field names and types
        field_mapping = {
            NodeType.NOME.value: ("nome", FieldType.TEXT),
            NodeType.EMAIL.value: ("email", FieldType.EMAIL),
            NodeType.TELEFONE.value: ("telefone", FieldType.PHONE),
            NodeType.CIDADE.value: ("cidade", FieldType.TEXT),
            NodeType.ENDERECO.value: ("endereco", FieldType.TEXT),
            NodeType.CPF.value: ("cpf", FieldType.CPF),
            NodeType.DATA_NASCIMENTO.value: ("data_nascimento", FieldType.DATE),
            NodeType.INTERESSE.value: ("interesse", FieldType.TEXT),
            NodeType.ORCAMENTO.value: ("orcamento", FieldType.CURRENCY),
            NodeType.URGENCIA.value: ("urgencia", FieldType.SELECT),
        }

        default_field, default_type = field_mapping.get(node_type, ("resposta", FieldType.TEXT))
        field = config.campo_destino or default_field
        field_type = config.tipo_campo or default_type

        # First interaction: ask for the data
        if not message:
            question = self._process_template(config.pergunta or f"Informe seu {default_field}:", data)

            # Add options for SELECT types
            if field_type == FieldType.SELECT and config.opcoes:
                options_text = "\n".join([f"- {opt}" for opt in config.opcoes])
                question = f"{question}\n\nOpcoes:\n{options_text}"

            return question_result(question, field, node.next_node_id)

        # Validate response
        is_valid, error = self._validate_field(message, field_type, config)

        if not is_valid:
            retry_msg = config.mensagem_erro or f"Por favor, informe um {default_field} valido."
            return validation_error_result(field, error or "Valor invalido", retry_msg)

        # Normalize specific fields
        normalized_value = message
        if node_type == NodeType.TELEFONE.value:
            normalized_value = self._normalize_phone(message)
        elif node_type == NodeType.CPF.value:
            normalized_value = self._normalize_cpf(message)
        elif node_type == NodeType.EMAIL.value:
            normalized_value = message.lower().strip()

        logger.info(f"Collected {field} = {normalized_value}")

        return collected_result(field, normalized_value, node.next_node_id)

    # ==================== Qualification Handlers ====================

    async def _handle_qualification(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle QUALIFICATION node - scores and qualifies leads"""
        config = node.config

        # Get score configuration
        score_config = self.global_config.score_qualificacao
        min_score = config.score_minimo or self.global_config.score_minimo_qualificado

        # Calculate score
        total_score = 0
        fields_evaluated = []

        evaluated_fields = config.campos_avaliados or list(score_config.keys())

        for field in evaluated_fields:
            if field in data and data[field]:
                points = score_config.get(field, 0)
                total_score += points
                fields_evaluated.append(f"{field}: +{points}")

        is_qualified = total_score >= min_score

        logger.info(
            f"Qualification: score={total_score}/{min_score}, "
            f"qualified={is_qualified}, fields={fields_evaluated}"
        )

        # Determine next node
        if is_qualified and node.true_node_id:
            next_node_id = node.true_node_id
        elif not is_qualified and node.false_node_id:
            next_node_id = node.false_node_id
        else:
            next_node_id = node.next_node_id

        result = FlowResult(
            next_node_id=next_node_id,
            is_qualified=is_qualified,
            qualification_score=total_score,
            metadata={
                "score_breakdown": fields_evaluated,
                "min_score": min_score
            }
        )

        return result

    # ==================== Commercial Handlers ====================

    async def _handle_proposta(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle PROPOSTA node - generates and sends proposals"""
        config = node.config

        # Generate proposal from template
        template = config.template_proposta or "Proposta para {nome}"
        proposal_text = self._process_template(template, data)

        # Add values if configured
        if config.valores:
            values_text = "\n".join([f"- {k}: {v}" for k, v in config.valores.items()])
            proposal_text = f"{proposal_text}\n\nValores:\n{values_text}"

        # Add conditions if configured
        if config.condicoes:
            conditions_text = "\n".join([f"- {c}" for c in config.condicoes])
            proposal_text = f"{proposal_text}\n\nCondicoes:\n{conditions_text}"

        # Add validity
        if config.prazo_validade_dias:
            proposal_text = f"{proposal_text}\n\nValidade: {config.prazo_validade_dias} dias"

        result = FlowResult(
            response=proposal_text,
            next_node_id=node.next_node_id,
            action_triggered="proposta_enviada",
            action_result={
                "template": config.template_proposta,
                "valores": config.valores,
                "validade_dias": config.prazo_validade_dias
            }
        )

        return result

    async def _handle_negociacao(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle NEGOCIACAO node - negotiation flow"""
        config = node.config

        response = self._process_template(
            config.mensagem or "Vamos negociar as melhores condicoes para voce.",
            data
        )

        result = FlowResult(
            response=response,
            next_node_id=node.next_node_id,
            action_triggered="negociacao_iniciada"
        )

        return result

    async def _handle_agendamento(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle AGENDAMENTO node - schedule meetings/calls"""
        config = node.config

        response = self._process_template(
            config.mensagem or "Vou agendar seu atendimento.",
            data
        )

        # Add available times if configured
        if config.horarios_disponiveis:
            times_text = "\n".join([f"- {t}" for t in config.horarios_disponiveis])
            response = f"{response}\n\nHorarios disponiveis:\n{times_text}"

        result = FlowResult(
            response=response,
            next_node_id=node.next_node_id,
            action_triggered="agendamento",
            action_result={
                "tipo": config.tipo_agendamento,
                "duracao_minutos": config.duracao_minutos,
                "local": config.local,
                "responsavel": config.responsavel
            }
        )

        return result

    async def _handle_visita(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle VISITA node - schedule visits"""
        config = node.config

        response = self._process_template(
            config.mensagem or "Vou agendar uma visita.",
            data
        )

        result = FlowResult(
            response=response,
            next_node_id=node.next_node_id,
            action_triggered="visita_agendada",
            action_result={
                "local": config.local or data.get("endereco"),
                "responsavel": config.responsavel
            }
        )

        return result

    # ==================== Notification Handlers ====================

    async def _handle_notificacao(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle NOTIFICACAO node"""
        config = node.config

        notification_message = self._process_template(
            config.template_notificacao or "Nova notificacao",
            data
        )

        result = FlowResult(
            next_node_id=node.next_node_id,
            should_notify=True
        )

        result.set_notification(
            channel=config.canal_notificacao or "email",
            message=notification_message,
            recipients=config.destinatarios,
            urgency=config.nivel_urgencia.value if config.nivel_urgencia else "normal"
        )

        return result

    async def _handle_alerta(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle ALERTA node - high priority notifications"""
        config = node.config

        alert_message = self._process_template(
            config.template_notificacao or "ALERTA!",
            data
        )

        result = FlowResult(
            next_node_id=node.next_node_id,
            should_notify=True
        )

        result.set_notification(
            channel=config.canal_notificacao or "email",
            message=alert_message,
            recipients=config.destinatarios,
            urgency=config.nivel_urgencia.value if config.nivel_urgencia else "alta"
        )

        return result

    # ==================== Media Handlers ====================

    async def _handle_foto(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle FOTO node - request or send image"""
        config = node.config

        # If we have a URL, send the image
        if config.url_midia:
            url = self._process_template(config.url_midia, data)
            caption = self._process_template(config.caption or "", data)

            result = FlowResult(next_node_id=node.next_node_id)
            result.set_media_send(url, MediaRequestType.IMAGE, caption)
            return result

        # Otherwise, request an image
        request_msg = self._process_template(
            config.mensagem or "Por favor, envie uma foto.",
            data
        )

        return media_request_result(MediaRequestType.IMAGE, request_msg)

    async def _handle_documento(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle DOCUMENTO node"""
        config = node.config

        if config.url_midia:
            url = self._process_template(config.url_midia, data)
            caption = self._process_template(config.caption or "", data)

            result = FlowResult(next_node_id=node.next_node_id)
            result.set_media_send(url, MediaRequestType.DOCUMENT, caption)
            return result

        request_msg = self._process_template(
            config.mensagem or "Por favor, envie o documento.",
            data
        )

        return media_request_result(MediaRequestType.DOCUMENT, request_msg)

    async def _handle_audio(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle AUDIO node"""
        config = node.config

        if config.url_midia:
            url = self._process_template(config.url_midia, data)

            result = FlowResult(next_node_id=node.next_node_id)
            result.set_media_send(url, MediaRequestType.AUDIO, None)
            return result

        request_msg = self._process_template(
            config.mensagem or "Por favor, envie um audio.",
            data
        )

        return media_request_result(MediaRequestType.AUDIO, request_msg)

    async def _handle_video(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle VIDEO node"""
        config = node.config

        if config.url_midia:
            url = self._process_template(config.url_midia, data)
            caption = self._process_template(config.caption or "", data)

            result = FlowResult(next_node_id=node.next_node_id)
            result.set_media_send(url, MediaRequestType.VIDEO, caption)
            return result

        request_msg = self._process_template(
            config.mensagem or "Por favor, envie um video.",
            data
        )

        return media_request_result(MediaRequestType.VIDEO, request_msg)

    # ==================== Integration Handlers ====================

    async def _handle_webhook(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle WEBHOOK_CALL node"""
        config = node.config

        webhook_result = await self._execute_webhook(config, data)

        result = FlowResult(
            next_node_id=node.next_node_id,
            action_triggered="webhook_call",
            action_result=webhook_result
        )

        if not webhook_result.get("success"):
            result.error = webhook_result.get("error")
            result.error_code = "WEBHOOK_ERROR"

        return result

    async def _handle_api_integration(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle API_INTEGRATION node"""
        config = node.config

        api_result = await self._execute_webhook(config, data)

        result = FlowResult(
            next_node_id=node.next_node_id,
            action_triggered="api_integration",
            action_result=api_result
        )

        return result

    async def _execute_webhook(
        self,
        config: NodeConfig,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a webhook call"""
        result = {"success": False, "error": None, "data": None}

        try:
            url = self._process_template(config.url or "", data)
            method = config.method or "POST"
            headers = config.headers or {}
            body = config.body or {}

            # Process body template
            processed_body = {}
            for key, value in body.items():
                if isinstance(value, str):
                    processed_body[key] = self._process_template(value, data)
                else:
                    processed_body[key] = value

            timeout = config.timeout_seconds or 30

            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, timeout=timeout)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=headers, json=processed_body, timeout=timeout)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers, timeout=timeout)
                else:
                    response = await client.post(url, headers=headers, json=processed_body, timeout=timeout)

                result["success"] = response.status_code < 400
                result["data"] = {
                    "status_code": response.status_code,
                    "response": response.text[:1000]
                }

                logger.info(f"Webhook {method} {url} - Status: {response.status_code}")

        except Exception as e:
            logger.exception(f"Webhook error: {e}")
            result["error"] = str(e)

        return result

    # ==================== Control Flow Handlers ====================

    async def _handle_delay(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle DELAY node - pause execution"""
        config = node.config
        delay = config.delay_seconds or 5

        logger.debug(f"Delay node: waiting {delay} seconds")
        await asyncio.sleep(delay)

        return continue_result(node.next_node_id)

    async def _handle_loop(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle LOOP node - conditional loop"""
        config = node.config

        # Check loop condition
        if config.loop_condition:
            should_continue = self.evaluator.evaluate_expression(config.loop_condition, data)
        else:
            should_continue = False

        # Check max iterations
        loop_count = data.get(f"_loop_{node.id}_count", 0)
        max_iterations = config.max_iterations or 10

        if loop_count >= max_iterations:
            should_continue = False

        if should_continue:
            # Continue loop
            data[f"_loop_{node.id}_count"] = loop_count + 1
            next_node_id = node.true_node_id or node.next_node_id
        else:
            # Exit loop
            next_node_id = node.false_node_id or node.next_node_id

        return continue_result(next_node_id)

    async def _handle_switch(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle SWITCH node - multiple condition branches"""
        config = node.config

        field_value = str(data.get(config.campo, "")).lower()

        # Check cases
        if config.cases:
            for case_value, case_node_id in config.cases.items():
                if str(case_value).lower() == field_value:
                    return continue_result(case_node_id)

        # Use case_node_ids from node
        if node.case_node_ids:
            for case_value, case_node_id in node.case_node_ids.items():
                if str(case_value).lower() == field_value:
                    return continue_result(case_node_id)

        # Default case
        default_node = config.default_node_id or node.next_node_id
        return continue_result(default_node)

    async def _handle_parallel(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """
        Handle PARALLEL node - execute multiple paths simultaneously.

        PARALLEL nodes allow branching into multiple concurrent paths.
        All paths execute independently and can optionally merge back.

        Config:
            parallel_paths: List of node_ids to start each parallel path
            wait_for_all: If True, wait for all paths before continuing
            merge_node_id: Node to continue after all paths complete

        Node fields:
            parallel_node_ids: Alternative way to specify parallel paths
        """
        config = node.config

        # Get parallel paths from config or node
        parallel_paths = config.parallel_paths or node.parallel_node_ids or []

        if not parallel_paths:
            logger.warning(f"PARALLEL node {node.id} has no paths defined")
            return continue_result(node.next_node_id)

        # Store parallel execution state
        parallel_state = {
            "parallel_node_id": node.id,
            "paths": parallel_paths,
            "completed_paths": [],
            "wait_for_all": config.wait_for_all if config.wait_for_all is not None else True,
            "merge_node_id": config.merge_node_id or node.next_node_id
        }

        # Store state for tracking
        data[f"_parallel_{node.id}"] = parallel_state

        logger.info(
            f"PARALLEL node {node.id}: Starting {len(parallel_paths)} parallel paths: {parallel_paths}"
        )

        # For now, we start the FIRST path and store the others
        # The conversation system will need to handle tracking multiple paths
        # This is a simplified implementation that executes paths sequentially
        # but allows the flow to branch into multiple directions

        # Return result with all parallel paths
        return FlowResult(
            response="",
            result_type=ResultType.PARALLEL,
            next_node_id=parallel_paths[0] if parallel_paths else None,
            parallel_paths=parallel_paths[1:] if len(parallel_paths) > 1 else None,
            data={"_parallel_state": parallel_state},
            should_continue=True
        )

    async def _handle_end(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle END node - terminate flow"""
        config = node.config

        farewell = self._process_template(
            config.mensagem or self.global_config.mensagem_despedida,
            data
        )

        return end_result(farewell)

    async def _handle_unknown(
        self,
        node: FlowNode,
        message: str,
        data: Dict[str, Any]
    ) -> FlowResult:
        """Handle unknown node types"""
        logger.warning(f"Unknown node type: {node.type}")

        return FlowResult(
            response="",
            next_node_id=node.next_node_id,
            error=f"Unknown node type: {node.type}",
            error_code="UNKNOWN_NODE_TYPE"
        )

    # ==================== Flow Execution ====================

    async def run_flow(
        self,
        start_node_id: Optional[str] = None,
        lead_data: Optional[Dict[str, Any]] = None,
        max_steps: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Run the complete flow (for testing/debugging).

        Args:
            start_node_id: Starting node (defaults to flow's start_node_id)
            lead_data: Initial data
            max_steps: Maximum steps to prevent infinite loops

        Returns:
            List of execution results
        """
        results = []
        data = lead_data.copy() if lead_data else {}

        current_node_id = start_node_id or self.config.start_node_id
        steps = 0

        while current_node_id and steps < max_steps:
            node = self.get_node(current_node_id)
            if not node:
                logger.warning(f"Node not found: {current_node_id}")
                break

            result = await self.execute_node(node, data)
            results.append(result)

            # Update data with collected fields
            if result.get("data_collected"):
                data.update(result["data_collected"])

            # Check termination conditions
            if result.get("should_wait") or result.get("should_handoff"):
                break

            current_node_id = result.get("next_node_id")
            steps += 1

        return results


def create_flow_executor(
    flow_config: FlowConfig | Dict[str, Any],
    context: Optional[FlowContext] = None
) -> FlowExecutor:
    """Factory function to create a FlowExecutor"""
    return FlowExecutor(flow_config, context)
