"""
Flow Module - Extended Flow Execution System

This module provides a complete flow execution system with:
- 25+ node types for data collection, qualification, and automation
- Full validation and auto-correction of flow configurations
- Context management for conversation state
- Media handling (images, documents, audio, video)
- Webhook/API integrations
- Notification system
- Commercial actions (proposals, scheduling, visits)
"""

from .executor import FlowExecutor, create_flow_executor
from .evaluator import ConditionEvaluator, evaluator
from .validator import (
    FlowValidator,
    FlowValidationError,
    validate_flow,
    autocorrect_flow
)
from .context import (
    FlowContext,
    FlowStatus,
    ValidationStatus,
    FieldValidation,
    NodeVisit,
    create_context
)
from .result import (
    FlowResult,
    ResultType,
    MediaRequestType,
    message_result,
    question_result,
    collected_result,
    validation_error_result,
    handoff_result,
    error_result,
    end_result,
    media_request_result,
    continue_result
)

__all__ = [
    # Executor
    "FlowExecutor",
    "create_flow_executor",

    # Evaluator
    "ConditionEvaluator",
    "evaluator",

    # Validator
    "FlowValidator",
    "FlowValidationError",
    "validate_flow",
    "autocorrect_flow",

    # Context
    "FlowContext",
    "FlowStatus",
    "ValidationStatus",
    "FieldValidation",
    "NodeVisit",
    "create_context",

    # Result
    "FlowResult",
    "ResultType",
    "MediaRequestType",
    "message_result",
    "question_result",
    "collected_result",
    "validation_error_result",
    "handoff_result",
    "error_result",
    "end_result",
    "media_request_result",
    "continue_result",
]


# Version info
__version__ = "2.0.0"
