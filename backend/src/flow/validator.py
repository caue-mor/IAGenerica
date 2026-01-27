"""
Flow Validator - Validates and auto-corrects flow configurations
"""
import logging
from typing import Tuple, List, Dict, Any, Set, Optional
from datetime import datetime

from ..models.flow import (
    FlowConfig, FlowNode, FlowEdge, NodeConfig, NodeType,
    GlobalConfig, FieldType, Operator
)

logger = logging.getLogger(__name__)


class FlowValidationError:
    """Represents a validation error"""

    def __init__(
        self,
        code: str,
        message: str,
        node_id: Optional[str] = None,
        severity: str = "error"  # error, warning, info
    ):
        self.code = code
        self.message = message
        self.node_id = node_id
        self.severity = severity
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "node_id": self.node_id,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat()
        }

    def __str__(self) -> str:
        node_info = f" [Node: {self.node_id}]" if self.node_id else ""
        return f"[{self.severity.upper()}] {self.code}: {self.message}{node_info}"


class FlowValidator:
    """
    Validates and auto-corrects flow configurations.

    Features:
    - Validates flow structure (nodes, edges, connections)
    - Checks for orphan nodes
    - Validates node configurations
    - Auto-corrects common issues
    - Provides detailed error reporting
    """

    # Required fields per node type
    REQUIRED_FIELDS: Dict[str, List[str]] = {
        NodeType.GREETING.value: ["mensagem"],
        NodeType.MESSAGE.value: ["mensagem"],
        NodeType.QUESTION.value: ["pergunta", "campo_destino"],
        NodeType.CONDITION.value: ["campo", "operador"],
        NodeType.NOME.value: ["pergunta"],
        NodeType.EMAIL.value: ["pergunta"],
        NodeType.TELEFONE.value: ["pergunta"],
        NodeType.CIDADE.value: ["pergunta"],
        NodeType.ENDERECO.value: ["pergunta"],
        NodeType.CPF.value: ["pergunta"],
        NodeType.DATA_NASCIMENTO.value: ["pergunta"],
        NodeType.INTERESSE.value: ["pergunta"],
        NodeType.ORCAMENTO.value: ["pergunta"],
        NodeType.URGENCIA.value: ["pergunta"],
        NodeType.HANDOFF.value: ["mensagem_cliente"],
        NodeType.QUALIFICATION.value: [],
        NodeType.AGENDAMENTO.value: [],
        NodeType.VISITA.value: [],
        NodeType.PROPOSTA.value: [],
        NodeType.NEGOCIACAO.value: [],
        NodeType.NOTIFICACAO.value: ["canal_notificacao"],
        NodeType.ALERTA.value: ["canal_notificacao"],
        NodeType.FOTO.value: [],
        NodeType.DOCUMENTO.value: [],
        NodeType.AUDIO.value: [],
        NodeType.VIDEO.value: [],
        NodeType.WEBHOOK_CALL.value: ["url"],
        NodeType.API_INTEGRATION.value: ["url"],
        NodeType.FOLLOWUP.value: [],
        NodeType.ACTION.value: ["tipo_acao"],
        NodeType.DELAY.value: ["delay_seconds"],
        NodeType.LOOP.value: ["loop_condition"],
        NodeType.SWITCH.value: ["campo"],
        NodeType.END.value: [],
    }

    # Default values for node configurations
    DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
        NodeType.GREETING.value: {"mensagem": "Ola! Como posso ajudar?"},
        NodeType.MESSAGE.value: {"mensagem": ""},
        NodeType.QUESTION.value: {
            "pergunta": "Por favor, responda:",
            "campo_destino": "resposta",
            "tipo_campo": FieldType.TEXT.value
        },
        NodeType.NOME.value: {
            "pergunta": "Qual e o seu nome?",
            "campo_destino": "nome",
            "tipo_campo": FieldType.TEXT.value
        },
        NodeType.EMAIL.value: {
            "pergunta": "Qual seu email?",
            "campo_destino": "email",
            "tipo_campo": FieldType.EMAIL.value
        },
        NodeType.TELEFONE.value: {
            "pergunta": "Qual seu telefone?",
            "campo_destino": "telefone",
            "tipo_campo": FieldType.PHONE.value
        },
        NodeType.CIDADE.value: {
            "pergunta": "Em qual cidade voce esta?",
            "campo_destino": "cidade",
            "tipo_campo": FieldType.TEXT.value
        },
        NodeType.ENDERECO.value: {
            "pergunta": "Qual seu endereco?",
            "campo_destino": "endereco",
            "tipo_campo": FieldType.TEXT.value
        },
        NodeType.CPF.value: {
            "pergunta": "Qual seu CPF?",
            "campo_destino": "cpf",
            "tipo_campo": FieldType.CPF.value
        },
        NodeType.DATA_NASCIMENTO.value: {
            "pergunta": "Qual sua data de nascimento?",
            "campo_destino": "data_nascimento",
            "tipo_campo": FieldType.DATE.value
        },
        NodeType.INTERESSE.value: {
            "pergunta": "No que posso ajuda-lo?",
            "campo_destino": "interesse",
            "tipo_campo": FieldType.TEXT.value
        },
        NodeType.ORCAMENTO.value: {
            "pergunta": "Qual seu orcamento?",
            "campo_destino": "orcamento",
            "tipo_campo": FieldType.CURRENCY.value
        },
        NodeType.URGENCIA.value: {
            "pergunta": "Qual a urgencia?",
            "campo_destino": "urgencia",
            "tipo_campo": FieldType.SELECT.value,
            "opcoes": ["Baixa", "Media", "Alta", "Urgente"]
        },
        NodeType.HANDOFF.value: {
            "mensagem_cliente": "Transferindo para atendimento humano.",
            "motivo": "Solicitacao do cliente"
        },
        NodeType.NOTIFICACAO.value: {"canal_notificacao": "email"},
        NodeType.ALERTA.value: {"canal_notificacao": "email"},
        NodeType.DELAY.value: {"delay_seconds": 5},
    }

    @classmethod
    def validate(cls, flow_config: Dict[str, Any]) -> Tuple[bool, List[FlowValidationError]]:
        """
        Validate a flow configuration.

        Args:
            flow_config: Flow configuration dictionary

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors: List[FlowValidationError] = []

        # 1. Basic structure validation
        errors.extend(cls._validate_structure(flow_config))

        if errors:
            # If basic structure is invalid, return early
            return False, errors

        # 2. Node validation
        nodes = flow_config.get("nodes", [])
        node_ids = {n.get("id") for n in nodes if n.get("id")}

        for node_data in nodes:
            errors.extend(cls._validate_node(node_data, node_ids))

        # 3. Edge validation
        edges = flow_config.get("edges", [])
        errors.extend(cls._validate_edges(edges, node_ids))

        # 4. Connection validation
        errors.extend(cls._validate_connections(flow_config, node_ids))

        # 5. Orphan node detection
        errors.extend(cls._detect_orphan_nodes(flow_config))

        # 6. Cycle detection (potential infinite loops)
        errors.extend(cls._detect_cycles(flow_config))

        # 7. Global config validation
        if flow_config.get("global_config"):
            errors.extend(cls._validate_global_config(flow_config["global_config"]))

        is_valid = not any(e.severity == "error" for e in errors)

        if errors:
            logger.warning(f"Flow validation found {len(errors)} issues")
            for error in errors:
                if error.severity == "error":
                    logger.error(str(error))
                else:
                    logger.warning(str(error))

        return is_valid, errors

    @classmethod
    def _validate_structure(cls, flow_config: Dict[str, Any]) -> List[FlowValidationError]:
        """Validate basic flow structure"""
        errors = []

        if not isinstance(flow_config, dict):
            errors.append(FlowValidationError(
                "INVALID_TYPE",
                "Flow configuration must be a dictionary"
            ))
            return errors

        # Check required fields
        if "nodes" not in flow_config:
            errors.append(FlowValidationError(
                "MISSING_NODES",
                "Flow must have a 'nodes' array"
            ))

        if "start_node_id" not in flow_config:
            errors.append(FlowValidationError(
                "MISSING_START_NODE",
                "Flow must have a 'start_node_id'"
            ))

        # Check nodes is a list
        if "nodes" in flow_config and not isinstance(flow_config["nodes"], list):
            errors.append(FlowValidationError(
                "INVALID_NODES_TYPE",
                "'nodes' must be an array"
            ))

        # Check edges is a list if present
        if "edges" in flow_config and not isinstance(flow_config["edges"], list):
            errors.append(FlowValidationError(
                "INVALID_EDGES_TYPE",
                "'edges' must be an array"
            ))

        # Check start_node_id exists in nodes
        if "start_node_id" in flow_config and "nodes" in flow_config:
            node_ids = {n.get("id") for n in flow_config["nodes"] if isinstance(n, dict)}
            if flow_config["start_node_id"] not in node_ids:
                errors.append(FlowValidationError(
                    "INVALID_START_NODE",
                    f"Start node '{flow_config['start_node_id']}' not found in nodes"
                ))

        return errors

    @classmethod
    def _validate_node(cls, node: Dict[str, Any], valid_node_ids: Set[str]) -> List[FlowValidationError]:
        """Validate a single node"""
        errors = []

        node_id = node.get("id", "unknown")

        # Check required node fields
        if not node.get("id"):
            errors.append(FlowValidationError(
                "MISSING_NODE_ID",
                "Node is missing 'id' field",
                node_id
            ))

        if not node.get("type"):
            errors.append(FlowValidationError(
                "MISSING_NODE_TYPE",
                "Node is missing 'type' field",
                node_id
            ))
        else:
            # Validate node type
            node_type = node["type"]
            valid_types = [t.value for t in NodeType]
            if node_type not in valid_types:
                errors.append(FlowValidationError(
                    "INVALID_NODE_TYPE",
                    f"Invalid node type: {node_type}. Valid types: {valid_types}",
                    node_id
                ))

        if not node.get("name"):
            errors.append(FlowValidationError(
                "MISSING_NODE_NAME",
                "Node is missing 'name' field",
                node_id,
                severity="warning"
            ))

        # Validate node config
        config = node.get("config", {})
        if node.get("type"):
            errors.extend(cls._validate_node_config(node["type"], config, node_id))

        # Validate node references
        if node.get("next_node_id") and node["next_node_id"] not in valid_node_ids:
            errors.append(FlowValidationError(
                "INVALID_NEXT_NODE",
                f"next_node_id '{node['next_node_id']}' does not exist",
                node_id
            ))

        if node.get("true_node_id") and node["true_node_id"] not in valid_node_ids:
            errors.append(FlowValidationError(
                "INVALID_TRUE_NODE",
                f"true_node_id '{node['true_node_id']}' does not exist",
                node_id
            ))

        if node.get("false_node_id") and node["false_node_id"] not in valid_node_ids:
            errors.append(FlowValidationError(
                "INVALID_FALSE_NODE",
                f"false_node_id '{node['false_node_id']}' does not exist",
                node_id
            ))

        return errors

    @classmethod
    def _validate_node_config(
        cls, node_type: str, config: Dict[str, Any], node_id: str
    ) -> List[FlowValidationError]:
        """Validate node configuration based on node type"""
        errors = []

        required_fields = cls.REQUIRED_FIELDS.get(node_type, [])

        for field in required_fields:
            if not config.get(field):
                errors.append(FlowValidationError(
                    "MISSING_CONFIG_FIELD",
                    f"Node type '{node_type}' requires field '{field}' in config",
                    node_id
                ))

        # Type-specific validations
        if node_type == NodeType.CONDITION.value:
            operador = config.get("operador")
            if operador:
                valid_operators = [o.value for o in Operator]
                if operador not in valid_operators:
                    errors.append(FlowValidationError(
                        "INVALID_OPERATOR",
                        f"Invalid operator: {operador}",
                        node_id
                    ))

        if node_type in [NodeType.WEBHOOK_CALL.value, NodeType.API_INTEGRATION.value]:
            url = config.get("url", "")
            if url and not (url.startswith("http://") or url.startswith("https://") or url.startswith("{")):
                errors.append(FlowValidationError(
                    "INVALID_URL",
                    f"URL must start with http:// or https://",
                    node_id,
                    severity="warning"
                ))

        return errors

    @classmethod
    def _validate_edges(cls, edges: List[Dict], valid_node_ids: Set[str]) -> List[FlowValidationError]:
        """Validate flow edges"""
        errors = []
        edge_ids = set()

        for edge in edges:
            edge_id = edge.get("id", "unknown")

            # Check for duplicate edge IDs
            if edge_id in edge_ids:
                errors.append(FlowValidationError(
                    "DUPLICATE_EDGE_ID",
                    f"Duplicate edge ID: {edge_id}"
                ))
            edge_ids.add(edge_id)

            # Check source exists
            source = edge.get("source")
            if not source:
                errors.append(FlowValidationError(
                    "MISSING_EDGE_SOURCE",
                    f"Edge '{edge_id}' is missing 'source'"
                ))
            elif source not in valid_node_ids:
                errors.append(FlowValidationError(
                    "INVALID_EDGE_SOURCE",
                    f"Edge '{edge_id}' source '{source}' does not exist"
                ))

            # Check target exists
            target = edge.get("target")
            if not target:
                errors.append(FlowValidationError(
                    "MISSING_EDGE_TARGET",
                    f"Edge '{edge_id}' is missing 'target'"
                ))
            elif target not in valid_node_ids:
                errors.append(FlowValidationError(
                    "INVALID_EDGE_TARGET",
                    f"Edge '{edge_id}' target '{target}' does not exist"
                ))

        return errors

    @classmethod
    def _validate_connections(cls, flow_config: Dict[str, Any], valid_node_ids: Set[str]) -> List[FlowValidationError]:
        """Validate that all node connections are valid"""
        errors = []
        nodes = flow_config.get("nodes", [])

        # Find terminal nodes (nodes that should end the flow)
        terminal_types = {NodeType.HANDOFF.value, NodeType.END.value}

        for node in nodes:
            node_type = node.get("type")
            node_id = node.get("id")

            # Check if non-terminal nodes have a next node
            if node_type not in terminal_types:
                has_next = (
                    node.get("next_node_id") or
                    node.get("true_node_id") or
                    node.get("false_node_id") or
                    node.get("case_node_ids")
                )
                if not has_next:
                    errors.append(FlowValidationError(
                        "MISSING_NEXT_NODE",
                        f"Non-terminal node '{node_id}' has no next node",
                        node_id,
                        severity="warning"
                    ))

            # Check CONDITION nodes have both paths
            if node_type == NodeType.CONDITION.value:
                if not node.get("true_node_id"):
                    errors.append(FlowValidationError(
                        "MISSING_TRUE_NODE",
                        "CONDITION node missing 'true_node_id'",
                        node_id,
                        severity="warning"
                    ))
                if not node.get("false_node_id"):
                    errors.append(FlowValidationError(
                        "MISSING_FALSE_NODE",
                        "CONDITION node missing 'false_node_id'",
                        node_id,
                        severity="warning"
                    ))

        return errors

    @classmethod
    def _detect_orphan_nodes(cls, flow_config: Dict[str, Any]) -> List[FlowValidationError]:
        """Detect nodes that are not reachable from the start node"""
        errors = []
        nodes = flow_config.get("nodes", [])
        start_node_id = flow_config.get("start_node_id")

        if not start_node_id or not nodes:
            return errors

        # Build adjacency list
        adjacency = {}
        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                continue

            connections = []
            if node.get("next_node_id"):
                connections.append(node["next_node_id"])
            if node.get("true_node_id"):
                connections.append(node["true_node_id"])
            if node.get("false_node_id"):
                connections.append(node["false_node_id"])
            if node.get("case_node_ids"):
                connections.extend(node["case_node_ids"].values())

            adjacency[node_id] = connections

        # BFS to find all reachable nodes
        reachable = set()
        queue = [start_node_id]

        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)

            for next_node in adjacency.get(current, []):
                if next_node and next_node not in reachable:
                    queue.append(next_node)

        # Find orphan nodes
        all_nodes = {n.get("id") for n in nodes if n.get("id")}
        orphans = all_nodes - reachable

        for orphan in orphans:
            errors.append(FlowValidationError(
                "ORPHAN_NODE",
                f"Node '{orphan}' is not reachable from start node",
                orphan,
                severity="warning"
            ))

        return errors

    @classmethod
    def _detect_cycles(cls, flow_config: Dict[str, Any]) -> List[FlowValidationError]:
        """Detect potential infinite loops in the flow"""
        errors = []
        nodes = flow_config.get("nodes", [])

        if not nodes:
            return errors

        # Build adjacency list
        adjacency = {}
        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                continue

            connections = []
            if node.get("next_node_id"):
                connections.append(node["next_node_id"])
            if node.get("true_node_id"):
                connections.append(node["true_node_id"])
            if node.get("false_node_id"):
                connections.append(node["false_node_id"])

            adjacency[node_id] = connections

        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        cycle_nodes = []

        def dfs(node_id: str, path: List[str]) -> bool:
            if node_id in rec_stack:
                cycle_start = path.index(node_id)
                cycle_nodes.extend(path[cycle_start:])
                return True

            if node_id in visited:
                return False

            visited.add(node_id)
            rec_stack.add(node_id)

            for next_node in adjacency.get(node_id, []):
                if next_node and dfs(next_node, path + [node_id]):
                    return True

            rec_stack.remove(node_id)
            return False

        for node in nodes:
            node_id = node.get("id")
            if node_id and node_id not in visited:
                if dfs(node_id, []):
                    break

        if cycle_nodes:
            cycle_str = " -> ".join(cycle_nodes)
            errors.append(FlowValidationError(
                "CYCLE_DETECTED",
                f"Potential infinite loop detected: {cycle_str}",
                severity="warning"
            ))

        return errors

    @classmethod
    def _validate_global_config(cls, global_config: Dict[str, Any]) -> List[FlowValidationError]:
        """Validate global configuration"""
        errors = []

        # Validate timeout values
        timeout = global_config.get("message_timeout_seconds", 300)
        if isinstance(timeout, int) and timeout < 0:
            errors.append(FlowValidationError(
                "INVALID_TIMEOUT",
                "message_timeout_seconds cannot be negative",
                severity="error"
            ))

        # Validate max_retries
        max_retries = global_config.get("max_retries", 3)
        if isinstance(max_retries, int) and max_retries < 0:
            errors.append(FlowValidationError(
                "INVALID_MAX_RETRIES",
                "max_retries cannot be negative",
                severity="error"
            ))

        # Validate score_qualificacao
        score = global_config.get("score_qualificacao", {})
        if score:
            for field, value in score.items():
                if not isinstance(value, (int, float)) or value < 0:
                    errors.append(FlowValidationError(
                        "INVALID_SCORE",
                        f"Invalid score value for field '{field}'",
                        severity="warning"
                    ))

        return errors

    @classmethod
    def autocorrect(cls, flow_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-correct common issues in flow configuration.

        Args:
            flow_config: Flow configuration dictionary

        Returns:
            Corrected flow configuration
        """
        if not isinstance(flow_config, dict):
            logger.warning("Invalid flow config type, returning empty flow")
            return cls._create_empty_flow()

        corrected = flow_config.copy()

        # Ensure nodes array exists
        if "nodes" not in corrected or not isinstance(corrected["nodes"], list):
            corrected["nodes"] = []

        # Ensure edges array exists
        if "edges" not in corrected or not isinstance(corrected["edges"], list):
            corrected["edges"] = []

        # Correct nodes
        corrected_nodes = []
        node_ids = set()

        for i, node in enumerate(corrected["nodes"]):
            if not isinstance(node, dict):
                continue

            corrected_node = cls._autocorrect_node(node, i)
            if corrected_node:
                node_ids.add(corrected_node["id"])
                corrected_nodes.append(corrected_node)

        corrected["nodes"] = corrected_nodes

        # Ensure start_node_id exists and is valid
        if not corrected.get("start_node_id") or corrected["start_node_id"] not in node_ids:
            if corrected_nodes:
                corrected["start_node_id"] = corrected_nodes[0]["id"]
                logger.info(f"Auto-set start_node_id to '{corrected['start_node_id']}'")
            else:
                # Create a default greeting node
                default_node = cls._create_default_greeting_node()
                corrected["nodes"].append(default_node)
                corrected["start_node_id"] = default_node["id"]
                logger.info("Created default greeting node")

        # Remove invalid edges
        corrected["edges"] = [
            edge for edge in corrected["edges"]
            if (isinstance(edge, dict) and
                edge.get("source") in node_ids and
                edge.get("target") in node_ids)
        ]

        # Remove invalid node references
        for node in corrected["nodes"]:
            if node.get("next_node_id") and node["next_node_id"] not in node_ids:
                node["next_node_id"] = None
            if node.get("true_node_id") and node["true_node_id"] not in node_ids:
                node["true_node_id"] = None
            if node.get("false_node_id") and node["false_node_id"] not in node_ids:
                node["false_node_id"] = None

        # Ensure global_config exists
        if "global_config" not in corrected or not isinstance(corrected.get("global_config"), dict):
            corrected["global_config"] = GlobalConfig().model_dump()

        # Set version
        if "version" not in corrected:
            corrected["version"] = "2.0"

        logger.info("Flow configuration auto-corrected successfully")
        return corrected

    @classmethod
    def _autocorrect_node(cls, node: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """Auto-correct a single node"""
        corrected = node.copy()

        # Ensure ID
        if not corrected.get("id"):
            corrected["id"] = f"node_{index}"
            logger.debug(f"Auto-generated ID: {corrected['id']}")

        # Ensure type (default to MESSAGE)
        if not corrected.get("type"):
            corrected["type"] = NodeType.MESSAGE.value
            logger.debug(f"Auto-set type to MESSAGE for node {corrected['id']}")

        # Ensure name
        if not corrected.get("name"):
            corrected["name"] = f"Node {corrected['id']}"

        # Ensure config
        if "config" not in corrected or not isinstance(corrected.get("config"), dict):
            corrected["config"] = {}

        # Apply default config for node type
        node_type = corrected["type"]
        defaults = cls.DEFAULT_CONFIG.get(node_type, {})

        for key, value in defaults.items():
            if key not in corrected["config"] or corrected["config"][key] is None:
                corrected["config"][key] = value

        # Auto-set campo_destino for data collection nodes
        data_collection_types = {
            NodeType.NOME.value: "nome",
            NodeType.EMAIL.value: "email",
            NodeType.TELEFONE.value: "telefone",
            NodeType.CIDADE.value: "cidade",
            NodeType.ENDERECO.value: "endereco",
            NodeType.CPF.value: "cpf",
            NodeType.DATA_NASCIMENTO.value: "data_nascimento",
            NodeType.INTERESSE.value: "interesse",
            NodeType.ORCAMENTO.value: "orcamento",
            NodeType.URGENCIA.value: "urgencia",
        }

        if node_type in data_collection_types:
            if not corrected["config"].get("campo_destino"):
                corrected["config"]["campo_destino"] = data_collection_types[node_type]

        return corrected

    @classmethod
    def _create_empty_flow(cls) -> Dict[str, Any]:
        """Create an empty flow with default greeting"""
        default_node = cls._create_default_greeting_node()
        return {
            "nodes": [default_node],
            "edges": [],
            "start_node_id": default_node["id"],
            "version": "2.0",
            "global_config": GlobalConfig().model_dump()
        }

    @classmethod
    def _create_default_greeting_node(cls) -> Dict[str, Any]:
        """Create a default greeting node"""
        return {
            "id": "greeting",
            "type": NodeType.GREETING.value,
            "name": "Saudacao",
            "config": {
                "mensagem": "Ola! Como posso ajudar?"
            }
        }

    @classmethod
    def validate_and_correct(cls, flow_config: Dict[str, Any]) -> Tuple[Dict[str, Any], List[FlowValidationError]]:
        """
        Validate and auto-correct a flow configuration.

        Args:
            flow_config: Flow configuration dictionary

        Returns:
            Tuple of (corrected config, list of errors/warnings)
        """
        # First, auto-correct
        corrected = cls.autocorrect(flow_config)

        # Then validate
        is_valid, errors = cls.validate(corrected)

        return corrected, errors


# Singleton-style function for convenience
def validate_flow(flow_config: Dict[str, Any]) -> Tuple[bool, List[FlowValidationError]]:
    """Convenience function to validate a flow"""
    return FlowValidator.validate(flow_config)


def autocorrect_flow(flow_config: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to auto-correct a flow"""
    return FlowValidator.autocorrect(flow_config)
