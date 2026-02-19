"""
Flow Result - Data class for flow execution results
"""
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List
from datetime import datetime
from enum import Enum


class ResultType(str, Enum):
    """Type of flow result"""
    MESSAGE = "message"
    QUESTION = "question"
    MEDIA_REQUEST = "media_request"
    MEDIA_SEND = "media_send"
    ACTION = "action"
    HANDOFF = "handoff"
    ERROR = "error"
    END = "end"
    CONTINUE = "continue"
    PARALLEL = "parallel"  # For parallel execution paths


class MediaRequestType(str, Enum):
    """Type of media request"""
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    ANY = "any"


@dataclass
class FlowResult:
    """
    Result of a flow node execution.

    This data class contains all possible outcomes from
    executing a flow node, allowing the caller to handle
    different scenarios appropriately.
    """

    # Primary response
    response: str = ""
    result_type: ResultType = ResultType.MESSAGE

    # Navigation
    next_node_id: Optional[str] = None
    should_wait: bool = False
    should_continue: bool = True

    # Data collection
    collected_field: Optional[str] = None
    collected_value: Optional[Any] = None
    validation_error: Optional[str] = None

    # Media handling
    requires_media: bool = False
    media_type: Optional[MediaRequestType] = None
    media_url: Optional[str] = None
    media_caption: Optional[str] = None

    # Actions
    action_triggered: Optional[str] = None
    action_result: Optional[Dict[str, Any]] = None

    # Notifications
    should_notify: bool = False
    notification_data: Optional[Dict[str, Any]] = None

    # Handoff
    should_handoff: bool = False
    handoff_reason: Optional[str] = None
    handoff_department: Optional[str] = None

    # Qualification
    is_qualified: Optional[bool] = None
    qualification_score: Optional[int] = None

    # Error handling
    error: Optional[str] = None
    error_code: Optional[str] = None
    is_recoverable: bool = True

    # Metadata
    node_id: Optional[str] = None
    node_type: Optional[str] = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    extra_messages: List[str] = field(default_factory=list)

    # Parallel execution
    parallel_paths: Optional[List[str]] = None  # For PARALLEL nodes - additional paths to execute
    data: Optional[Dict[str, Any]] = None  # Additional data to pass

    def is_success(self) -> bool:
        """Check if execution was successful"""
        return self.error is None

    def is_error(self) -> bool:
        """Check if there was an error"""
        return self.error is not None

    def is_waiting_input(self) -> bool:
        """Check if waiting for user input"""
        return self.should_wait and not self.requires_media

    def is_waiting_media(self) -> bool:
        """Check if waiting for media upload"""
        return self.requires_media

    def is_terminal(self) -> bool:
        """Check if this is a terminal result (flow ends)"""
        return (
            self.should_handoff or
            self.result_type == ResultType.END or
            (self.error is not None and not self.is_recoverable)
        )

    def add_extra_message(self, message: str) -> None:
        """Add an extra message to send"""
        self.extra_messages.append(message)

    def set_error(
        self,
        error: str,
        error_code: Optional[str] = None,
        is_recoverable: bool = True
    ) -> None:
        """Set error information"""
        self.error = error
        self.error_code = error_code
        self.is_recoverable = is_recoverable
        self.result_type = ResultType.ERROR

    def set_handoff(
        self,
        reason: str,
        department: Optional[str] = None,
        message: Optional[str] = None
    ) -> None:
        """Set handoff information"""
        self.should_handoff = True
        self.handoff_reason = reason
        self.handoff_department = department
        self.result_type = ResultType.HANDOFF
        if message:
            self.response = message

    def set_media_request(
        self,
        media_type: MediaRequestType,
        message: str = "Por favor, envie o arquivo solicitado."
    ) -> None:
        """Set media request"""
        self.requires_media = True
        self.media_type = media_type
        self.should_wait = True
        self.response = message
        self.result_type = ResultType.MEDIA_REQUEST

    def set_media_send(
        self,
        url: str,
        media_type: MediaRequestType,
        caption: Optional[str] = None
    ) -> None:
        """Set media to send"""
        self.media_url = url
        self.media_type = media_type
        self.media_caption = caption
        self.result_type = ResultType.MEDIA_SEND

    def set_notification(
        self,
        channel: str,
        message: str,
        recipients: Optional[List[str]] = None,
        urgency: str = "normal"
    ) -> None:
        """Set notification data"""
        self.should_notify = True
        self.notification_data = {
            "channel": channel,
            "message": message,
            "recipients": recipients or [],
            "urgency": urgency
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "response": self.response,
            "result_type": self.result_type.value,
            "next_node_id": self.next_node_id,
            "should_wait": self.should_wait,
            "should_continue": self.should_continue,
            "collected_field": self.collected_field,
            "collected_value": self.collected_value,
            "validation_error": self.validation_error,
            "requires_media": self.requires_media,
            "media_type": self.media_type.value if self.media_type else None,
            "media_url": self.media_url,
            "media_caption": self.media_caption,
            "action_triggered": self.action_triggered,
            "action_result": self.action_result,
            "should_notify": self.should_notify,
            "notification_data": self.notification_data,
            "should_handoff": self.should_handoff,
            "handoff_reason": self.handoff_reason,
            "handoff_department": self.handoff_department,
            "is_qualified": self.is_qualified,
            "qualification_score": self.qualification_score,
            "error": self.error,
            "error_code": self.error_code,
            "is_recoverable": self.is_recoverable,
            "node_id": self.node_id,
            "node_type": self.node_type,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "extra_messages": self.extra_messages,
            "parallel_paths": self.parallel_paths,
            "data": self.data
        }

    def __str__(self) -> str:
        status = "OK" if self.is_success() else f"ERROR: {self.error}"
        return (
            f"FlowResult({self.result_type.value}, "
            f"node={self.node_id}, status={status})"
        )


# Factory functions for common results

def message_result(
    message: str,
    next_node_id: Optional[str] = None
) -> FlowResult:
    """Create a simple message result"""
    return FlowResult(
        response=message,
        result_type=ResultType.MESSAGE,
        next_node_id=next_node_id,
        should_continue=next_node_id is not None
    )


def question_result(
    question: str,
    field_name: str,
    next_node_id: Optional[str] = None
) -> FlowResult:
    """Create a question result (waiting for input)"""
    return FlowResult(
        response=question,
        result_type=ResultType.QUESTION,
        collected_field=field_name,
        next_node_id=next_node_id,
        should_wait=True,
        should_continue=False
    )


def collected_result(
    field_name: str,
    value: Any,
    next_node_id: Optional[str] = None,
    message: str = ""
) -> FlowResult:
    """Create a result for successful data collection"""
    return FlowResult(
        response=message,
        result_type=ResultType.MESSAGE,
        collected_field=field_name,
        collected_value=value,
        next_node_id=next_node_id,
        should_continue=next_node_id is not None
    )


def validation_error_result(
    field_name: str,
    error_message: str,
    retry_message: str
) -> FlowResult:
    """Create a result for validation error"""
    return FlowResult(
        response=retry_message,
        result_type=ResultType.QUESTION,
        collected_field=field_name,
        validation_error=error_message,
        should_wait=True,
        should_continue=False
    )


def handoff_result(
    message: str,
    reason: str,
    department: Optional[str] = None
) -> FlowResult:
    """Create a handoff result"""
    result = FlowResult(
        response=message,
        result_type=ResultType.HANDOFF
    )
    result.set_handoff(reason, department, message)
    return result


def error_result(
    error: str,
    error_code: Optional[str] = None,
    is_recoverable: bool = True,
    message: str = ""
) -> FlowResult:
    """Create an error result"""
    result = FlowResult(
        response=message or f"Ocorreu um erro: {error}",
        result_type=ResultType.ERROR
    )
    result.set_error(error, error_code, is_recoverable)
    return result


def end_result(message: str = "Atendimento encerrado. Obrigado!") -> FlowResult:
    """Create an end-of-flow result"""
    return FlowResult(
        response=message,
        result_type=ResultType.END,
        should_continue=False
    )


def media_request_result(
    media_type: MediaRequestType,
    message: str
) -> FlowResult:
    """Create a media request result"""
    result = FlowResult()
    result.set_media_request(media_type, message)
    return result


def continue_result(next_node_id: str) -> FlowResult:
    """Create a result that continues to next node without message"""
    return FlowResult(
        result_type=ResultType.CONTINUE,
        next_node_id=next_node_id,
        should_continue=True
    )
