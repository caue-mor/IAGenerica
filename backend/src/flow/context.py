"""
Flow Context - Maintains execution state for flow conversations
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Dict, List, Set
from enum import Enum
import json

logger = logging.getLogger(__name__)


class FlowStatus(str, Enum):
    """Status of flow execution"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    WAITING_INPUT = "waiting_input"
    WAITING_MEDIA = "waiting_media"
    COMPLETED = "completed"
    HANDOFF = "handoff"
    ERROR = "error"
    TIMEOUT = "timeout"


class ValidationStatus(str, Enum):
    """Status of field validation"""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    SKIPPED = "skipped"


@dataclass
class FieldValidation:
    """Validation result for a collected field"""
    field_name: str
    value: Any
    status: ValidationStatus = ValidationStatus.PENDING
    error_message: Optional[str] = None
    attempts: int = 0
    validated_at: Optional[datetime] = None


@dataclass
class NodeVisit:
    """Record of a node visit"""
    node_id: str
    node_type: str
    timestamp: datetime
    user_input: Optional[str] = None
    response: Optional[str] = None
    data_collected: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None


@dataclass
class FlowContext:
    """
    Maintains the execution context for a flow conversation.

    This class tracks:
    - Current position in the flow
    - Collected data
    - Visited nodes history
    - Validation errors
    - Timing information
    - Retry counts
    """

    # Identifiers
    conversation_id: int
    lead_id: int
    company_id: Optional[int] = None
    flow_id: Optional[str] = None

    # Current state
    current_node_id: Optional[str] = None
    previous_node_id: Optional[str] = None
    status: FlowStatus = FlowStatus.NOT_STARTED

    # History
    visited_nodes: List[NodeVisit] = field(default_factory=list)
    visited_node_ids: Set[str] = field(default_factory=set)

    # Collected data
    collected_data: Dict[str, Any] = field(default_factory=dict)
    field_validations: Dict[str, FieldValidation] = field(default_factory=dict)

    # Validation and errors
    validation_errors: List[str] = field(default_factory=list)
    last_error: Optional[str] = None

    # Retry tracking
    retry_count: int = 0
    max_retries: int = 3
    current_field_retries: int = 0

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    last_message_at: Optional[datetime] = None

    # Flags
    awaiting_input: bool = False
    awaiting_media: bool = False
    expected_media_type: Optional[str] = None
    is_qualified: bool = False
    qualification_score: int = 0

    # Variables for flow logic
    variables: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def move_to_node(self, node_id: str, node_type: str = "unknown") -> None:
        """
        Move to a new node in the flow.

        Args:
            node_id: ID of the new node
            node_type: Type of the node
        """
        # Record the visit
        visit = NodeVisit(
            node_id=node_id,
            node_type=node_type,
            timestamp=datetime.now()
        )

        self.previous_node_id = self.current_node_id
        self.current_node_id = node_id
        self.visited_nodes.append(visit)
        self.visited_node_ids.add(node_id)
        self.last_activity = datetime.now()
        self.status = FlowStatus.IN_PROGRESS
        self.current_field_retries = 0

        logger.debug(
            f"Context moved to node '{node_id}' (type: {node_type}) "
            f"[conversation: {self.conversation_id}]"
        )

    def record_node_response(
        self,
        user_input: Optional[str] = None,
        response: Optional[str] = None,
        data_collected: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record the response for the current node visit"""
        if self.visited_nodes:
            last_visit = self.visited_nodes[-1]
            last_visit.user_input = user_input
            last_visit.response = response
            last_visit.data_collected = data_collected

            # Calculate duration
            duration = datetime.now() - last_visit.timestamp
            last_visit.duration_ms = int(duration.total_seconds() * 1000)

    def collect_field(
        self,
        field_name: str,
        value: Any,
        validated: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """
        Collect a field value.

        Args:
            field_name: Name of the field
            value: Value to store
            validated: Whether the value passed validation
            error_message: Error message if validation failed
        """
        self.collected_data[field_name] = value
        self.last_activity = datetime.now()

        # Track validation
        validation = self.field_validations.get(field_name, FieldValidation(field_name=field_name, value=None))
        validation.value = value
        validation.attempts += 1
        validation.validated_at = datetime.now()

        if validated:
            validation.status = ValidationStatus.VALID
            validation.error_message = None
            self.current_field_retries = 0
            logger.info(f"Collected field '{field_name}' = '{value}' [conversation: {self.conversation_id}]")
        else:
            validation.status = ValidationStatus.INVALID
            validation.error_message = error_message
            self.validation_errors.append(f"{field_name}: {error_message}")
            logger.warning(
                f"Invalid value for field '{field_name}': {error_message} "
                f"[conversation: {self.conversation_id}]"
            )

        self.field_validations[field_name] = validation

    def get_field(self, field_name: str, default: Any = None) -> Any:
        """Get a collected field value"""
        return self.collected_data.get(field_name, default)

    def has_field(self, field_name: str) -> bool:
        """Check if a field has been collected"""
        return field_name in self.collected_data and self.collected_data[field_name] is not None

    def get_missing_fields(self, required_fields: List[str]) -> List[str]:
        """Get list of required fields that haven't been collected"""
        return [f for f in required_fields if not self.has_field(f)]

    def increment_retry(self) -> bool:
        """
        Increment retry count.

        Returns:
            True if retries are still available, False if max reached
        """
        self.retry_count += 1
        self.current_field_retries += 1

        if self.current_field_retries >= self.max_retries:
            logger.warning(
                f"Max retries reached for current field "
                f"[conversation: {self.conversation_id}]"
            )
            return False

        return True

    def reset_field_retries(self) -> None:
        """Reset retry count for current field"""
        self.current_field_retries = 0

    def is_timed_out(self, timeout_seconds: int = 300) -> bool:
        """
        Check if the session has timed out.

        Args:
            timeout_seconds: Timeout in seconds (default 5 minutes)

        Returns:
            True if timed out
        """
        elapsed = (datetime.now() - self.last_activity).total_seconds()
        is_timeout = elapsed > timeout_seconds

        if is_timeout:
            logger.info(
                f"Session timed out after {elapsed:.0f}s "
                f"[conversation: {self.conversation_id}]"
            )
            self.status = FlowStatus.TIMEOUT

        return is_timeout

    def get_session_duration(self) -> float:
        """Get session duration in seconds"""
        return (datetime.now() - self.started_at).total_seconds()

    def get_idle_time(self) -> float:
        """Get idle time since last activity in seconds"""
        return (datetime.now() - self.last_activity).total_seconds()

    def set_waiting_input(self, field_name: Optional[str] = None) -> None:
        """Set context to waiting for user input"""
        self.awaiting_input = True
        self.status = FlowStatus.WAITING_INPUT
        self.last_activity = datetime.now()

        if field_name:
            self.variables["awaiting_field"] = field_name

    def set_waiting_media(self, media_type: str) -> None:
        """Set context to waiting for media upload"""
        self.awaiting_media = True
        self.expected_media_type = media_type
        self.status = FlowStatus.WAITING_MEDIA
        self.last_activity = datetime.now()

    def clear_waiting(self) -> None:
        """Clear waiting flags"""
        self.awaiting_input = False
        self.awaiting_media = False
        self.expected_media_type = None
        self.variables.pop("awaiting_field", None)

    def set_handoff(self, reason: Optional[str] = None) -> None:
        """Mark flow as handed off to human"""
        self.status = FlowStatus.HANDOFF
        self.last_activity = datetime.now()

        if reason:
            self.metadata["handoff_reason"] = reason

        logger.info(
            f"Flow handed off to human: {reason} "
            f"[conversation: {self.conversation_id}]"
        )

    def set_completed(self) -> None:
        """Mark flow as completed"""
        self.status = FlowStatus.COMPLETED
        self.last_activity = datetime.now()

        logger.info(
            f"Flow completed [conversation: {self.conversation_id}] "
            f"Duration: {self.get_session_duration():.1f}s"
        )

    def set_error(self, error: str) -> None:
        """Mark flow as errored"""
        self.status = FlowStatus.ERROR
        self.last_error = error
        self.validation_errors.append(error)

        logger.error(
            f"Flow error: {error} "
            f"[conversation: {self.conversation_id}]"
        )

    def calculate_qualification_score(self, score_config: Dict[str, int]) -> int:
        """
        Calculate qualification score based on collected fields.

        Args:
            score_config: Dictionary mapping field names to point values

        Returns:
            Total qualification score
        """
        score = 0

        for field_name, points in score_config.items():
            if self.has_field(field_name):
                score += points

        self.qualification_score = score
        return score

    def is_qualified(self, min_score: int, score_config: Dict[str, int]) -> bool:
        """
        Check if lead is qualified based on score.

        Args:
            min_score: Minimum score required
            score_config: Score configuration

        Returns:
            True if qualified
        """
        score = self.calculate_qualification_score(score_config)
        qualified = score >= min_score

        if qualified:
            self.is_qualified = True
            logger.info(
                f"Lead qualified with score {score}/{min_score} "
                f"[conversation: {self.conversation_id}]"
            )

        return qualified

    def set_variable(self, name: str, value: Any) -> None:
        """Set a flow variable"""
        self.variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a flow variable"""
        return self.variables.get(name, default)

    def has_visited_node(self, node_id: str) -> bool:
        """Check if a node has been visited"""
        return node_id in self.visited_node_ids

    def get_visit_count(self, node_id: str) -> int:
        """Get number of times a node was visited"""
        return sum(1 for v in self.visited_nodes if v.node_id == node_id)

    def get_last_response(self) -> Optional[str]:
        """Get the last response sent"""
        for visit in reversed(self.visited_nodes):
            if visit.response:
                return visit.response
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization"""
        return {
            "conversation_id": self.conversation_id,
            "lead_id": self.lead_id,
            "company_id": self.company_id,
            "flow_id": self.flow_id,
            "current_node_id": self.current_node_id,
            "previous_node_id": self.previous_node_id,
            "status": self.status.value,
            "visited_node_ids": list(self.visited_node_ids),
            "collected_data": self.collected_data,
            "validation_errors": self.validation_errors,
            "retry_count": self.retry_count,
            "current_field_retries": self.current_field_retries,
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "awaiting_input": self.awaiting_input,
            "awaiting_media": self.awaiting_media,
            "expected_media_type": self.expected_media_type,
            "is_qualified": self.is_qualified,
            "qualification_score": self.qualification_score,
            "variables": self.variables,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlowContext":
        """Create context from dictionary"""
        context = cls(
            conversation_id=data["conversation_id"],
            lead_id=data["lead_id"],
            company_id=data.get("company_id"),
            flow_id=data.get("flow_id"),
            current_node_id=data.get("current_node_id"),
            previous_node_id=data.get("previous_node_id"),
            status=FlowStatus(data.get("status", "not_started")),
            visited_node_ids=set(data.get("visited_node_ids", [])),
            collected_data=data.get("collected_data", {}),
            validation_errors=data.get("validation_errors", []),
            retry_count=data.get("retry_count", 0),
            current_field_retries=data.get("current_field_retries", 0),
            awaiting_input=data.get("awaiting_input", False),
            awaiting_media=data.get("awaiting_media", False),
            expected_media_type=data.get("expected_media_type"),
            is_qualified=data.get("is_qualified", False),
            qualification_score=data.get("qualification_score", 0),
            variables=data.get("variables", {}),
            metadata=data.get("metadata", {})
        )

        # Parse timestamps
        if data.get("started_at"):
            context.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("last_activity"):
            context.last_activity = datetime.fromisoformat(data["last_activity"])

        return context

    def to_json(self) -> str:
        """Serialize context to JSON string"""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "FlowContext":
        """Deserialize context from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __str__(self) -> str:
        return (
            f"FlowContext(conversation={self.conversation_id}, "
            f"node={self.current_node_id}, status={self.status.value}, "
            f"collected={len(self.collected_data)} fields)"
        )

    def __repr__(self) -> str:
        return self.__str__()


def create_context(
    conversation_id: int,
    lead_id: int,
    company_id: Optional[int] = None,
    flow_id: Optional[str] = None,
    initial_data: Optional[Dict[str, Any]] = None
) -> FlowContext:
    """
    Factory function to create a new FlowContext.

    Args:
        conversation_id: ID of the conversation
        lead_id: ID of the lead
        company_id: ID of the company (optional)
        flow_id: ID of the flow (optional)
        initial_data: Initial collected data (optional)

    Returns:
        New FlowContext instance
    """
    context = FlowContext(
        conversation_id=conversation_id,
        lead_id=lead_id,
        company_id=company_id,
        flow_id=flow_id
    )

    if initial_data:
        context.collected_data = initial_data.copy()

    logger.info(
        f"Created new flow context for conversation {conversation_id}, "
        f"lead {lead_id}"
    )

    return context
