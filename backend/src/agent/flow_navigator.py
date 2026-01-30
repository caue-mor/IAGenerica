"""
Flow Graph Navigator - Navigates flows as graphs for intelligent AI processing.

Instead of treating the flow as a flat list of goals, this module
provides graph-based navigation that properly handles:
- SWITCH nodes (multiple branches)
- CONDITION nodes (true/false branches)
- PARALLEL nodes (concurrent execution)
- Complex flow topologies

The AI receives complete graph context to make intelligent decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List, Set
from enum import Enum

from ..models.flow import FlowConfig, FlowNode, NodeConfig, NodeType


class FlowPathType(str, Enum):
    """Type of path in the flow graph."""
    SEQUENTIAL = "sequential"      # Normal next_node_id path
    CONDITION_TRUE = "condition_true"
    CONDITION_FALSE = "condition_false"
    SWITCH_CASE = "switch_case"
    SWITCH_DEFAULT = "switch_default"
    PARALLEL = "parallel"


@dataclass
class FlowPath:
    """A possible path in the flow graph."""
    target_node_id: str
    path_type: FlowPathType
    condition: Optional[str] = None     # Ex: "interesse == 'comprar'"
    label: Optional[str] = None         # Ex: "Sim", "Não", "Opção A"
    case_value: Optional[str] = None    # For SWITCH: the case value

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_node_id": self.target_node_id,
            "path_type": self.path_type.value,
            "condition": self.condition,
            "label": self.label,
            "case_value": self.case_value
        }


@dataclass
class FlowCondition:
    """A condition to evaluate in the flow."""
    field: str
    operator: str
    value: Any
    expression: Optional[str] = None   # For complex expressions

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
            "expression": self.expression
        }


@dataclass
class FlowPosition:
    """Current position in the flow graph."""
    current_node_id: str
    current_node_type: str
    current_node_name: str
    available_paths: List[FlowPath] = field(default_factory=list)
    condition_to_evaluate: Optional[FlowCondition] = None
    switch_field: Optional[str] = None  # Field to evaluate for SWITCH
    switch_cases: Optional[Dict[str, str]] = None  # value -> node_id
    is_terminal: bool = False           # True if END node or no next node
    requires_data_collection: bool = False
    data_field: Optional[str] = None    # Field to collect if data node
    node_config: Optional[NodeConfig] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_node_id": self.current_node_id,
            "current_node_type": self.current_node_type,
            "current_node_name": self.current_node_name,
            "available_paths": [p.to_dict() for p in self.available_paths],
            "condition_to_evaluate": self.condition_to_evaluate.to_dict() if self.condition_to_evaluate else None,
            "switch_field": self.switch_field,
            "switch_cases": self.switch_cases,
            "is_terminal": self.is_terminal,
            "requires_data_collection": self.requires_data_collection,
            "data_field": self.data_field
        }


@dataclass
class FlowContext:
    """Complete context for the AI Brain at current position."""
    current_position: FlowPosition
    visited_nodes: Set[str] = field(default_factory=set)
    pending_parallel_paths: List[str] = field(default_factory=list)
    collected_data: Dict[str, Any] = field(default_factory=dict)

    # What the AI should focus on
    what_to_collect: Optional[str] = None
    what_to_ask: Optional[str] = None
    possible_branches: List[FlowPath] = field(default_factory=list)
    pending_condition: Optional[FlowCondition] = None

    # Navigation hints
    can_advance: bool = True
    reason_cannot_advance: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_position": self.current_position.to_dict(),
            "visited_nodes": list(self.visited_nodes),
            "pending_parallel_paths": self.pending_parallel_paths,
            "collected_data": self.collected_data,
            "what_to_collect": self.what_to_collect,
            "what_to_ask": self.what_to_ask,
            "possible_branches": [p.to_dict() for p in self.possible_branches],
            "pending_condition": self.pending_condition.to_dict() if self.pending_condition else None,
            "can_advance": self.can_advance,
            "reason_cannot_advance": self.reason_cannot_advance
        }


class ConditionEvaluator:
    """Evaluates flow conditions against collected data."""

    OPERATORS = {
        "equals": lambda a, b: str(a).lower() == str(b).lower(),
        "not_equals": lambda a, b: str(a).lower() != str(b).lower(),
        "contains": lambda a, b: str(b).lower() in str(a).lower(),
        "not_contains": lambda a, b: str(b).lower() not in str(a).lower(),
        "starts_with": lambda a, b: str(a).lower().startswith(str(b).lower()),
        "ends_with": lambda a, b: str(a).lower().endswith(str(b).lower()),
        "greater_than": lambda a, b: float(a) > float(b) if a and b else False,
        "less_than": lambda a, b: float(a) < float(b) if a and b else False,
        "greater_or_equal": lambda a, b: float(a) >= float(b) if a and b else False,
        "less_or_equal": lambda a, b: float(a) <= float(b) if a and b else False,
        "is_empty": lambda a, b: not a or str(a).strip() == "",
        "is_not_empty": lambda a, b: a and str(a).strip() != "",
        "exists": lambda a, b: a is not None,
        "in_list": lambda a, b: str(a).lower() in [str(x).lower() for x in (b if isinstance(b, list) else [b])],
        "not_in_list": lambda a, b: str(a).lower() not in [str(x).lower() for x in (b if isinstance(b, list) else [b])],
    }

    def evaluate(self, condition: FlowCondition, data: Dict[str, Any]) -> bool:
        """Evaluate a condition against collected data."""
        field_value = data.get(condition.field)
        operator_func = self.OPERATORS.get(condition.operator, lambda a, b: False)

        try:
            return operator_func(field_value, condition.value)
        except (ValueError, TypeError):
            return False

    def evaluate_expression(self, expression: str, data: Dict[str, Any]) -> bool:
        """Evaluate a complex expression (e.g., 'orcamento > 500000 and urgencia == "imediata"')."""
        if not expression:
            return False

        # Create safe evaluation context
        safe_data = {k: v for k, v in data.items() if isinstance(k, str)}

        try:
            # Simple expression evaluation - could be extended with a proper parser
            # For now, support basic comparisons
            result = eval(expression, {"__builtins__": {}}, safe_data)
            return bool(result)
        except Exception:
            return False


class FlowGraphNavigator:
    """
    Navigates through the flow as a graph, not as a flat list.

    This navigator:
    - Builds a graph representation of the flow
    - Tracks current position
    - Evaluates conditions to determine next node
    - Handles SWITCH nodes with multiple branches
    - Supports PARALLEL execution tracking
    """

    # Node types that collect data
    DATA_COLLECTION_TYPES = {
        "QUESTION", "NOME", "EMAIL", "TELEFONE", "CIDADE",
        "ENDERECO", "CPF", "DATA_NASCIMENTO", "INTERESSE",
        "ORCAMENTO", "URGENCIA", "CEP"
    }

    # Node type to field mapping
    NODE_TYPE_TO_FIELD = {
        "NOME": "nome",
        "EMAIL": "email",
        "TELEFONE": "telefone",
        "CIDADE": "cidade",
        "ENDERECO": "endereco",
        "CPF": "cpf",
        "DATA_NASCIMENTO": "data_nascimento",
        "INTERESSE": "interesse",
        "ORCAMENTO": "orcamento",
        "URGENCIA": "urgencia",
        "CEP": "cep",
    }

    def __init__(self, flow_config: FlowConfig, collected_data: Dict[str, Any] = None):
        """
        Initialize the navigator with a flow configuration.

        Args:
            flow_config: The flow configuration to navigate
            collected_data: Already collected data
        """
        self.flow_config = flow_config
        self.nodes_by_id: Dict[str, FlowNode] = {
            node.id: node for node in flow_config.nodes
        }
        self.edges = {(e.source, e.target): e for e in flow_config.edges}
        self.condition_evaluator = ConditionEvaluator()

        # State
        self.current_node_id: Optional[str] = flow_config.start_node_id
        self.visited_nodes: Set[str] = set()
        self.collected_data: Dict[str, Any] = collected_data or {}
        self.pending_parallel_paths: List[str] = []

    def get_current_position(self) -> Optional[FlowPosition]:
        """Get the current position in the flow."""
        if not self.current_node_id:
            return None

        node = self.nodes_by_id.get(self.current_node_id)
        if not node:
            return None

        node_type = node.type.upper() if isinstance(node.type, str) else node.type.value
        config = node.config or NodeConfig()

        position = FlowPosition(
            current_node_id=node.id,
            current_node_type=node_type,
            current_node_name=node.name,
            node_config=config
        )

        # Determine available paths based on node type
        if node_type == "CONDITION":
            position.condition_to_evaluate = FlowCondition(
                field=config.campo or "",
                operator=config.operador or "equals",
                value=config.valor,
                expression=config.expressao
            )
            if node.true_node_id:
                position.available_paths.append(FlowPath(
                    target_node_id=node.true_node_id,
                    path_type=FlowPathType.CONDITION_TRUE,
                    label="Verdadeiro",
                    condition=f"{config.campo} {config.operador} {config.valor}"
                ))
            if node.false_node_id:
                position.available_paths.append(FlowPath(
                    target_node_id=node.false_node_id,
                    path_type=FlowPathType.CONDITION_FALSE,
                    label="Falso"
                ))

        elif node_type == "SWITCH":
            position.switch_field = config.campo
            position.switch_cases = config.cases or {}
            # Add paths for each case
            if config.cases:
                for case_value, target_id in config.cases.items():
                    position.available_paths.append(FlowPath(
                        target_node_id=target_id,
                        path_type=FlowPathType.SWITCH_CASE,
                        label=case_value,
                        case_value=case_value
                    ))
            # Also from node's case_node_ids
            if node.case_node_ids:
                for case_value, target_id in node.case_node_ids.items():
                    position.available_paths.append(FlowPath(
                        target_node_id=target_id,
                        path_type=FlowPathType.SWITCH_CASE,
                        label=case_value,
                        case_value=case_value
                    ))
            if config.default_node_id:
                position.available_paths.append(FlowPath(
                    target_node_id=config.default_node_id,
                    path_type=FlowPathType.SWITCH_DEFAULT,
                    label="Padrão"
                ))

        elif node_type == "PARALLEL":
            if node.parallel_node_ids:
                for target_id in node.parallel_node_ids:
                    position.available_paths.append(FlowPath(
                        target_node_id=target_id,
                        path_type=FlowPathType.PARALLEL
                    ))
            if config.parallel_paths:
                for target_id in config.parallel_paths:
                    position.available_paths.append(FlowPath(
                        target_node_id=target_id,
                        path_type=FlowPathType.PARALLEL
                    ))

        elif node_type == "END":
            position.is_terminal = True

        else:
            # Sequential flow
            if node.next_node_id:
                position.available_paths.append(FlowPath(
                    target_node_id=node.next_node_id,
                    path_type=FlowPathType.SEQUENTIAL
                ))
            # Also check for CONDITION-style nodes (QUALIFICATION, etc.)
            if node.true_node_id:
                position.available_paths.append(FlowPath(
                    target_node_id=node.true_node_id,
                    path_type=FlowPathType.CONDITION_TRUE,
                    label="Qualificado"
                ))
            if node.false_node_id:
                position.available_paths.append(FlowPath(
                    target_node_id=node.false_node_id,
                    path_type=FlowPathType.CONDITION_FALSE,
                    label="Não Qualificado"
                ))

        # Check if this is a data collection node
        if node_type in self.DATA_COLLECTION_TYPES:
            position.requires_data_collection = True
            # Determine the field to collect
            position.data_field = config.campo_destino or self.NODE_TYPE_TO_FIELD.get(node_type, node_type.lower())

        # Mark as terminal if no paths available
        if not position.available_paths and not position.is_terminal:
            position.is_terminal = True

        return position

    def get_current_context(self) -> FlowContext:
        """Get complete context for the AI Brain."""
        position = self.get_current_position()
        if not position:
            return FlowContext(
                current_position=FlowPosition(
                    current_node_id="",
                    current_node_type="END",
                    current_node_name="Fim",
                    is_terminal=True
                ),
                can_advance=False,
                reason_cannot_advance="Flow não iniciado ou posição inválida"
            )

        context = FlowContext(
            current_position=position,
            visited_nodes=self.visited_nodes.copy(),
            pending_parallel_paths=self.pending_parallel_paths.copy(),
            collected_data=self.collected_data.copy(),
            possible_branches=position.available_paths.copy()
        )

        # Set what to collect/ask based on current node
        if position.requires_data_collection:
            context.what_to_collect = position.data_field
            if position.node_config and position.node_config.pergunta:
                context.what_to_ask = position.node_config.pergunta

        # Set pending condition
        if position.condition_to_evaluate:
            context.pending_condition = position.condition_to_evaluate

        # Check if can advance
        if position.is_terminal:
            context.can_advance = False
            context.reason_cannot_advance = "Fim do fluxo"
        elif position.requires_data_collection and position.data_field:
            # Check if we have the required data
            if position.data_field not in self.collected_data:
                context.can_advance = False
                context.reason_cannot_advance = f"Aguardando coleta de: {position.data_field}"

        return context

    def update_collected_data(self, data: Dict[str, Any]) -> None:
        """Update collected data."""
        self.collected_data.update(data)

    def evaluate_and_advance(self) -> Optional[FlowPosition]:
        """
        Evaluate current position and advance to next node.

        Returns:
            New position after advancing, or None if cannot advance
        """
        position = self.get_current_position()
        if not position or position.is_terminal:
            return None

        node_type = position.current_node_type.upper()
        next_node_id: Optional[str] = None

        # Handle CONDITION nodes
        if node_type == "CONDITION" and position.condition_to_evaluate:
            result = self.condition_evaluator.evaluate(
                position.condition_to_evaluate,
                self.collected_data
            )
            # Find the right path
            for path in position.available_paths:
                if result and path.path_type == FlowPathType.CONDITION_TRUE:
                    next_node_id = path.target_node_id
                    break
                elif not result and path.path_type == FlowPathType.CONDITION_FALSE:
                    next_node_id = path.target_node_id
                    break

        # Handle SWITCH nodes
        elif node_type == "SWITCH" and position.switch_field:
            field_value = self.collected_data.get(position.switch_field, "")
            field_value_str = str(field_value).lower() if field_value else ""

            # Try to match a case
            for path in position.available_paths:
                if path.path_type == FlowPathType.SWITCH_CASE:
                    if path.case_value and str(path.case_value).lower() == field_value_str:
                        next_node_id = path.target_node_id
                        break
                    # Also try contains match for flexibility
                    if path.case_value and str(path.case_value).lower() in field_value_str:
                        next_node_id = path.target_node_id
                        break

            # Fallback to default
            if not next_node_id:
                for path in position.available_paths:
                    if path.path_type == FlowPathType.SWITCH_DEFAULT:
                        next_node_id = path.target_node_id
                        break

        # Handle QUALIFICATION nodes (special condition)
        elif node_type == "QUALIFICATION":
            # Calculate qualification score
            qualified = self._check_qualification(position)
            for path in position.available_paths:
                if qualified and path.path_type == FlowPathType.CONDITION_TRUE:
                    next_node_id = path.target_node_id
                    break
                elif not qualified and path.path_type == FlowPathType.CONDITION_FALSE:
                    next_node_id = path.target_node_id
                    break

        # Handle PARALLEL nodes
        elif node_type == "PARALLEL":
            # Add all parallel paths to pending
            for path in position.available_paths:
                if path.path_type == FlowPathType.PARALLEL and path.target_node_id not in self.pending_parallel_paths:
                    self.pending_parallel_paths.append(path.target_node_id)
            # Get first parallel path
            if self.pending_parallel_paths:
                next_node_id = self.pending_parallel_paths.pop(0)

        # Sequential flow
        else:
            for path in position.available_paths:
                if path.path_type == FlowPathType.SEQUENTIAL:
                    next_node_id = path.target_node_id
                    break
            # Also check for implicit sequential (first available path)
            if not next_node_id and position.available_paths:
                next_node_id = position.available_paths[0].target_node_id

        # Advance to next node
        if next_node_id:
            self.visited_nodes.add(self.current_node_id)
            self.current_node_id = next_node_id
            return self.get_current_position()

        return None

    def _check_qualification(self, position: FlowPosition) -> bool:
        """Check if lead is qualified based on qualification node config."""
        config = position.node_config
        if not config:
            return True

        # Get global config for score weights
        global_config = self.flow_config.global_config
        if not global_config:
            return True

        # Calculate score
        score_map = global_config.score_qualificacao or {}
        total_score = 0
        for field, weight in score_map.items():
            if field in self.collected_data and self.collected_data[field]:
                total_score += weight

        # Check threshold
        threshold = config.score_minimo or global_config.score_minimo_qualificado or 70
        return total_score >= threshold

    def set_position(self, node_id: str) -> bool:
        """
        Set current position to a specific node.

        Args:
            node_id: ID of node to move to

        Returns:
            True if position was set successfully
        """
        if node_id in self.nodes_by_id:
            self.visited_nodes.add(self.current_node_id)
            self.current_node_id = node_id
            return True
        return False

    def get_next_data_collection_node(self) -> Optional[FlowPosition]:
        """Find the next node that requires data collection."""
        visited = set()
        to_visit = [self.current_node_id]

        while to_visit:
            node_id = to_visit.pop(0)
            if node_id in visited or node_id not in self.nodes_by_id:
                continue

            visited.add(node_id)
            node = self.nodes_by_id[node_id]
            node_type = node.type.upper() if isinstance(node.type, str) else node.type.value

            if node_type in self.DATA_COLLECTION_TYPES:
                # Temporarily move to this node to get position
                old_node_id = self.current_node_id
                self.current_node_id = node_id
                position = self.get_current_position()
                self.current_node_id = old_node_id
                return position

            # Add next nodes to visit
            if node.next_node_id:
                to_visit.append(node.next_node_id)
            if node.true_node_id:
                to_visit.append(node.true_node_id)
            if node.false_node_id:
                to_visit.append(node.false_node_id)
            if node.case_node_ids:
                to_visit.extend(node.case_node_ids.values())

        return None

    def get_all_data_fields(self) -> List[str]:
        """Get list of all data fields that can be collected in this flow."""
        fields = []
        for node in self.flow_config.nodes:
            node_type = node.type.upper() if isinstance(node.type, str) else node.type.value
            if node_type in self.DATA_COLLECTION_TYPES:
                config = node.config or NodeConfig()
                field = config.campo_destino or self.NODE_TYPE_TO_FIELD.get(node_type, node_type.lower())
                if field and field not in fields:
                    fields.append(field)
        return fields

    def is_complete(self) -> bool:
        """Check if the flow has reached a terminal state."""
        position = self.get_current_position()
        return position is None or position.is_terminal

    def get_completion_percentage(self) -> float:
        """Calculate flow completion percentage based on visited nodes."""
        total_nodes = len(self.nodes_by_id)
        if total_nodes == 0:
            return 100.0
        return (len(self.visited_nodes) / total_nodes) * 100

    def format_context_for_prompt(self) -> str:
        """Format current context for AI prompt."""
        context = self.get_current_context()
        position = context.current_position

        lines = []
        lines.append(f"**Posição Atual:** {position.current_node_name} ({position.current_node_type})")

        if context.what_to_collect:
            lines.append(f"**Objetivo:** Coletar {context.what_to_collect}")

        if context.what_to_ask:
            lines.append(f"**Pergunta Sugerida:** {context.what_to_ask}")

        if context.possible_branches:
            lines.append("**Caminhos Possíveis:**")
            for path in context.possible_branches:
                label = path.label or path.target_node_id
                lines.append(f"  - {label} ({path.path_type.value})")

        if context.pending_condition:
            cond = context.pending_condition
            lines.append(f"**Condição a Avaliar:** {cond.field} {cond.operator} {cond.value}")

        if not context.can_advance:
            lines.append(f"**Bloqueio:** {context.reason_cannot_advance}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize navigator state to dict."""
        return {
            "current_node_id": self.current_node_id,
            "visited_nodes": list(self.visited_nodes),
            "collected_data": self.collected_data,
            "pending_parallel_paths": self.pending_parallel_paths
        }

    @classmethod
    def from_dict(cls, flow_config: FlowConfig, state: dict[str, Any]) -> "FlowGraphNavigator":
        """Restore navigator from serialized state."""
        navigator = cls(flow_config)
        navigator.current_node_id = state.get("current_node_id", flow_config.start_node_id)
        navigator.visited_nodes = set(state.get("visited_nodes", []))
        navigator.collected_data = state.get("collected_data", {})
        navigator.pending_parallel_paths = state.get("pending_parallel_paths", [])
        return navigator


def create_navigator(flow_config: FlowConfig, collected_data: Dict[str, Any] = None) -> FlowGraphNavigator:
    """
    Factory function to create a FlowGraphNavigator.

    Args:
        flow_config: The flow configuration
        collected_data: Already collected data

    Returns:
        FlowGraphNavigator instance
    """
    return FlowGraphNavigator(flow_config, collected_data)
