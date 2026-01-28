"""
Flow Interpreter - Converts flow JSON to goals/intent for intelligent AI.

Instead of treating the flow as a script to follow mechanically,
this module interprets the flow as a set of OBJECTIVES that the AI
should accomplish through natural conversation.
"""
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

from ..models.flow import FlowConfig, FlowNode, NodeConfig


class GoalPriority(int, Enum):
    """Priority levels for conversation goals."""
    CRITICAL = 1    # Must collect (e.g., nome, telefone)
    HIGH = 2        # Very important
    MEDIUM = 3      # Important but can skip
    LOW = 4         # Nice to have
    OPTIONAL = 5    # Only if conversation allows


class FieldCategory(str, Enum):
    """Categories of fields to collect."""
    IDENTIFICATION = "identification"   # nome, cpf
    CONTACT = "contact"                 # email, telefone
    LOCATION = "location"               # cidade, endereco
    QUALIFICATION = "qualification"     # interesse, orcamento, urgencia
    COMMERCIAL = "commercial"           # proposta, negociacao
    CUSTOM = "custom"                   # campos personalizados


@dataclass
class ValidationRule:
    """Validation rule for a goal."""
    rule_type: str  # regex, min_length, max_length, format, etc.
    value: Any
    error_message: str = ""


@dataclass
class ConversationGoal:
    """
    A single objective for the conversation.

    This represents something the AI should try to collect
    through natural conversation, not a script question to read.
    """
    # Identification
    field_name: str                     # nome, email, telefone
    field_type: str                     # text, email, phone, etc.

    # Description for AI understanding
    description: str                    # What to collect (natural language)
    example_values: list[str] = field(default_factory=list)  # Examples

    # Requirements
    required: bool = True               # Must collect?
    priority: GoalPriority = GoalPriority.MEDIUM

    # Validation
    validation_rules: list[ValidationRule] = field(default_factory=list)

    # Suggested prompts (AI can use as inspiration, not script)
    suggested_question: str = ""        # From flow config
    error_hint: str = ""                # What to say if validation fails

    # Category for grouping
    category: FieldCategory = FieldCategory.CUSTOM

    # Status (updated during conversation)
    collected: bool = False
    value: Any = None
    attempts: int = 0

    # Options for select fields
    options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "field_type": self.field_type,
            "description": self.description,
            "required": self.required,
            "priority": self.priority.value,
            "collected": self.collected,
            "value": self.value,
            "attempts": self.attempts,
            "options": self.options,
            "suggested_question": self.suggested_question,
            "category": self.category.value
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationGoal":
        return cls(
            field_name=data.get("field_name", ""),
            field_type=data.get("field_type", "text"),
            description=data.get("description", ""),
            required=data.get("required", True),
            priority=GoalPriority(data.get("priority", 3)),
            collected=data.get("collected", False),
            value=data.get("value"),
            attempts=data.get("attempts", 0),
            options=data.get("options", []),
            suggested_question=data.get("suggested_question", ""),
            category=FieldCategory(data.get("category", "custom"))
        )


@dataclass
class FlowCondition:
    """A condition that triggers flow bifurcation."""
    field: str                          # Field to check
    operator: str                       # equals, greater_than, etc.
    value: Any                          # Value to compare
    true_action: str                    # What to do if true
    false_action: str                   # What to do if false
    description: str = ""               # Natural language description

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
            "true_action": self.true_action,
            "false_action": self.false_action,
            "description": self.description
        }


@dataclass
class FlowAction:
    """An action to execute during conversation."""
    action_type: str                    # notify, schedule, webhook, etc.
    trigger: str                        # When to execute
    config: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "trigger": self.trigger,
            "config": self.config,
            "description": self.description
        }


@dataclass
class NotificationConfig:
    """Configuration for notifications during conversation."""
    trigger: str                        # When to notify
    channel: str                        # email, whatsapp, slack
    recipients: list[str] = field(default_factory=list)
    template: str = ""
    urgency: str = "normal"

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger": self.trigger,
            "channel": self.channel,
            "recipients": self.recipients,
            "template": self.template,
            "urgency": self.urgency
        }


@dataclass
class HandoffTrigger:
    """Configuration for when to transfer to human."""
    condition: str                      # What triggers handoff
    reason: str                         # Why transferring
    message_to_lead: str = ""           # What to say to lead
    priority: str = "normal"
    department: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "reason": self.reason,
            "message_to_lead": self.message_to_lead,
            "priority": self.priority,
            "department": self.department
        }


@dataclass
class FlowIntent:
    """
    Complete interpreted intent of a flow.

    This is what the AI receives instead of a script.
    The AI uses this to understand WHAT to accomplish,
    not HOW to do it step-by-step.
    """
    # What to collect
    goals: list[ConversationGoal] = field(default_factory=list)

    # Conditions for branching
    conditions: list[FlowCondition] = field(default_factory=list)

    # Actions to execute
    actions: list[FlowAction] = field(default_factory=list)

    # Notifications
    notifications: list[NotificationConfig] = field(default_factory=list)

    # Handoff triggers
    handoff_triggers: list[HandoffTrigger] = field(default_factory=list)

    # Company/conversation settings
    company_name: str = ""
    agent_name: str = ""
    agent_tone: str = "amigavel"        # formal, amigavel, tecnico, vendedor
    use_emojis: bool = False
    greeting_message: str = ""
    farewell_message: str = ""

    # Qualification settings
    qualification_score_map: dict[str, int] = field(default_factory=dict)
    qualification_threshold: int = 70

    def to_dict(self) -> dict[str, Any]:
        return {
            "goals": [g.to_dict() for g in self.goals],
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "notifications": [n.to_dict() for n in self.notifications],
            "handoff_triggers": [h.to_dict() for h in self.handoff_triggers],
            "company_name": self.company_name,
            "agent_name": self.agent_name,
            "agent_tone": self.agent_tone,
            "use_emojis": self.use_emojis,
            "greeting_message": self.greeting_message,
            "farewell_message": self.farewell_message,
            "qualification_score_map": self.qualification_score_map,
            "qualification_threshold": self.qualification_threshold
        }

    def get_pending_goals(self) -> list[ConversationGoal]:
        """Get goals not yet collected."""
        return [g for g in self.goals if not g.collected]

    def get_required_pending(self) -> list[ConversationGoal]:
        """Get required goals not yet collected."""
        return [g for g in self.goals if g.required and not g.collected]

    def get_next_priority_goal(self) -> Optional[ConversationGoal]:
        """Get the highest priority pending goal."""
        pending = self.get_pending_goals()
        if not pending:
            return None
        return min(pending, key=lambda g: g.priority.value)

    def calculate_completion(self) -> float:
        """Calculate completion percentage."""
        if not self.goals:
            return 1.0
        collected = sum(1 for g in self.goals if g.collected)
        return collected / len(self.goals)

    def is_complete(self) -> bool:
        """Check if all required goals are collected."""
        return all(g.collected for g in self.goals if g.required)


# Field type to category mapping
FIELD_CATEGORY_MAP = {
    "nome": FieldCategory.IDENTIFICATION,
    "cpf": FieldCategory.IDENTIFICATION,
    "email": FieldCategory.CONTACT,
    "telefone": FieldCategory.CONTACT,
    "celular": FieldCategory.CONTACT,
    "cidade": FieldCategory.LOCATION,
    "endereco": FieldCategory.LOCATION,
    "cep": FieldCategory.LOCATION,
    "interesse": FieldCategory.QUALIFICATION,
    "orcamento": FieldCategory.QUALIFICATION,
    "urgencia": FieldCategory.QUALIFICATION,
    "proposta": FieldCategory.COMMERCIAL,
    "negociacao": FieldCategory.COMMERCIAL,
}

# Field type to description mapping
FIELD_DESCRIPTIONS = {
    "nome": "Nome completo da pessoa",
    "email": "Endereço de email para contato",
    "telefone": "Número de telefone/celular",
    "celular": "Número de celular com DDD",
    "cidade": "Cidade onde a pessoa está localizada",
    "endereco": "Endereço completo",
    "cpf": "CPF (número de identificação)",
    "cep": "CEP (código postal)",
    "interesse": "O que a pessoa está buscando/seu interesse principal",
    "orcamento": "Valor disponível para investimento",
    "urgencia": "Nível de urgência/prazo para decisão",
    "data_nascimento": "Data de nascimento",
}

# Field type to priority mapping
FIELD_PRIORITY_MAP = {
    "nome": GoalPriority.CRITICAL,
    "telefone": GoalPriority.CRITICAL,
    "celular": GoalPriority.CRITICAL,
    "email": GoalPriority.HIGH,
    "interesse": GoalPriority.HIGH,
    "cidade": GoalPriority.MEDIUM,
    "orcamento": GoalPriority.MEDIUM,
    "urgencia": GoalPriority.MEDIUM,
    "endereco": GoalPriority.LOW,
    "cpf": GoalPriority.LOW,
    "cep": GoalPriority.LOW,
    "data_nascimento": GoalPriority.OPTIONAL,
}


class FlowInterpreter:
    """
    Interprets flow configuration as goals/intent for the AI.

    Instead of executing nodes mechanically, this creates a
    semantic understanding of what the conversation should achieve.
    """

    def __init__(self, flow_config: FlowConfig):
        """
        Initialize with flow configuration.

        Args:
            flow_config: The flow configuration to interpret
        """
        self.flow_config = flow_config
        self.nodes_by_id = {node.id: node for node in flow_config.nodes}
        self.global_config = flow_config.global_config

    def interpret(self) -> FlowIntent:
        """
        Interpret the flow and return a FlowIntent.

        Returns:
            FlowIntent with goals, conditions, actions, etc.
        """
        intent = FlowIntent()

        # Extract global settings
        if self.global_config:
            intent.agent_tone = self.global_config.comportamento_ia
            intent.use_emojis = self.global_config.usar_emojis
            intent.greeting_message = self.global_config.saudacao_padrao
            intent.farewell_message = self.global_config.mensagem_despedida
            intent.qualification_score_map = self.global_config.score_qualificacao
            intent.qualification_threshold = self.global_config.score_minimo_qualificado

        # Process each node
        for node in self.flow_config.nodes:
            self._process_node(node, intent)

        # Sort goals by priority
        intent.goals.sort(key=lambda g: g.priority.value)

        return intent

    def _process_node(self, node: FlowNode, intent: FlowIntent):
        """Process a single node and extract goals/actions."""
        node_type = node.type.upper() if isinstance(node.type, str) else node.type.value

        # Data collection nodes become goals
        if node_type in self._get_collection_types():
            goal = self._create_goal_from_node(node)
            if goal:
                intent.goals.append(goal)

        # Condition nodes
        elif node_type == "CONDITION":
            condition = self._create_condition_from_node(node)
            if condition:
                intent.conditions.append(condition)

        # Qualification nodes
        elif node_type == "QUALIFICATION":
            # Qualification can create conditions based on score
            if node.config and node.config.score_minimo:
                intent.qualification_threshold = node.config.score_minimo

        # Handoff nodes
        elif node_type == "HANDOFF":
            trigger = self._create_handoff_trigger(node)
            if trigger:
                intent.handoff_triggers.append(trigger)

        # Notification nodes
        elif node_type in ["NOTIFICACAO", "ALERTA"]:
            notification = self._create_notification(node)
            if notification:
                intent.notifications.append(notification)

        # Action nodes
        elif node_type == "ACTION":
            action = self._create_action(node)
            if action:
                intent.actions.append(action)

        # Greeting nodes - extract greeting message
        elif node_type == "GREETING":
            if node.config and node.config.mensagem:
                intent.greeting_message = node.config.mensagem

    def _get_collection_types(self) -> set:
        """Get node types that collect data."""
        return {
            "QUESTION", "NOME", "EMAIL", "TELEFONE", "CIDADE",
            "ENDERECO", "CPF", "DATA_NASCIMENTO", "INTERESSE",
            "ORCAMENTO", "URGENCIA"
        }

    def _create_goal_from_node(self, node: FlowNode) -> Optional[ConversationGoal]:
        """Create a ConversationGoal from a data collection node."""
        config = node.config or NodeConfig()

        # Determine field name
        field_name = config.campo_destino
        if not field_name:
            # Infer from node type
            node_type = node.type.upper() if isinstance(node.type, str) else node.type.value
            field_name = node_type.lower()

        # Get field type
        field_type = config.tipo_campo or "text"
        if isinstance(field_type, Enum):
            field_type = field_type.value

        # Get description
        description = FIELD_DESCRIPTIONS.get(
            field_name,
            config.descricao or f"Coletar {field_name}"
        )

        # Get category
        category = FIELD_CATEGORY_MAP.get(field_name, FieldCategory.CUSTOM)

        # Get priority
        priority = FIELD_PRIORITY_MAP.get(field_name, GoalPriority.MEDIUM)

        # Check if required
        required = config.obrigatorio if config.obrigatorio is not None else True

        # If in required fields list, make it critical
        if self.global_config and field_name in (self.global_config.campos_obrigatorios or []):
            required = True
            priority = GoalPriority.CRITICAL

        # Get options for select fields
        options = config.opcoes or []

        # Get suggested question
        suggested_question = config.pergunta or ""

        # Get error hint
        error_hint = config.mensagem_erro or ""

        # Build validation rules
        validation_rules = []
        if config.validacao_rules:
            for rule in config.validacao_rules:
                validation_rules.append(ValidationRule(
                    rule_type=rule.type,
                    value=rule.value,
                    error_message=rule.error_message or ""
                ))

        return ConversationGoal(
            field_name=field_name,
            field_type=field_type,
            description=description,
            category=category,
            priority=priority,
            required=required,
            suggested_question=suggested_question,
            error_hint=error_hint,
            options=options,
            validation_rules=validation_rules
        )

    def _create_condition_from_node(self, node: FlowNode) -> Optional[FlowCondition]:
        """Create a FlowCondition from a condition node."""
        config = node.config or NodeConfig()

        if not config.campo:
            return None

        return FlowCondition(
            field=config.campo,
            operator=config.operador or "equals",
            value=config.valor,
            true_action=node.true_node_id or "",
            false_action=node.false_node_id or "",
            description=config.descricao or ""
        )

    def _create_handoff_trigger(self, node: FlowNode) -> Optional[HandoffTrigger]:
        """Create a HandoffTrigger from a handoff node."""
        config = node.config or NodeConfig()

        return HandoffTrigger(
            condition="goal_complete",  # Or custom from node
            reason=config.motivo or "Lead qualificado",
            message_to_lead=config.mensagem_cliente or "",
            priority=config.prioridade or "normal",
            department=config.departamento or ""
        )

    def _create_notification(self, node: FlowNode) -> Optional[NotificationConfig]:
        """Create NotificationConfig from notification node."""
        config = node.config or NodeConfig()

        return NotificationConfig(
            trigger="on_node_reach",  # Or custom
            channel=config.canal_notificacao or "whatsapp",
            recipients=config.destinatarios or [],
            template=config.template_notificacao or "",
            urgency=config.nivel_urgencia or "normal"
        )

    def _create_action(self, node: FlowNode) -> Optional[FlowAction]:
        """Create FlowAction from action node."""
        config = node.config or NodeConfig()

        if not config.tipo_acao:
            return None

        return FlowAction(
            action_type=config.tipo_acao,
            trigger="on_node_reach",
            config={
                "url": config.url,
                "method": config.method,
                "headers": config.headers,
                "body": config.body,
                "timeout": config.timeout_seconds
            },
            description=config.descricao or ""
        )

    def update_goal_status(self, intent: FlowIntent, field_name: str,
                           collected: bool, value: Any = None):
        """Update the status of a goal."""
        for goal in intent.goals:
            if goal.field_name == field_name:
                goal.collected = collected
                goal.value = value
                if not collected:
                    goal.attempts += 1
                break

    def format_goals_for_prompt(self, intent: FlowIntent) -> str:
        """
        Format goals for inclusion in AI system prompt.

        Returns a natural language description of what the AI
        should try to collect.
        """
        lines = []

        # Group by category
        by_category = {}
        for goal in intent.goals:
            cat = goal.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(goal)

        # Format each category
        category_names = {
            "identification": "Identificação",
            "contact": "Contato",
            "location": "Localização",
            "qualification": "Qualificação",
            "commercial": "Comercial",
            "custom": "Outros"
        }

        for cat, goals in by_category.items():
            lines.append(f"\n**{category_names.get(cat, cat)}:**")
            for goal in goals:
                status = "✓" if goal.collected else "○"
                required = "(obrigatório)" if goal.required else "(opcional)"
                value_str = f" = {goal.value}" if goal.collected and goal.value else ""
                lines.append(f"  {status} {goal.field_name}: {goal.description} {required}{value_str}")

        return "\n".join(lines)

    def format_pending_goals_for_prompt(self, intent: FlowIntent) -> str:
        """Format only pending goals for the prompt."""
        pending = intent.get_pending_goals()
        if not pending:
            return "Todos os objetivos foram coletados."

        lines = ["Objetivos pendentes (em ordem de prioridade):"]
        for i, goal in enumerate(pending[:5], 1):  # Top 5
            required = "⚠️ OBRIGATÓRIO" if goal.required else "opcional"
            options = f" (opções: {', '.join(goal.options)})" if goal.options else ""
            lines.append(f"{i}. {goal.field_name}: {goal.description} - {required}{options}")

        return "\n".join(lines)


def interpret_flow(flow_config: FlowConfig) -> FlowIntent:
    """
    Convenience function to interpret a flow.

    Args:
        flow_config: The flow configuration

    Returns:
        FlowIntent with interpreted goals and actions
    """
    interpreter = FlowInterpreter(flow_config)
    return interpreter.interpret()


def create_intent_from_dict(flow_dict: dict[str, Any]) -> FlowIntent:
    """
    Create FlowIntent from a flow config dictionary.

    Args:
        flow_dict: Flow configuration as dictionary

    Returns:
        FlowIntent with interpreted goals and actions
    """
    flow_config = FlowConfig(**flow_dict)
    return interpret_flow(flow_config)
