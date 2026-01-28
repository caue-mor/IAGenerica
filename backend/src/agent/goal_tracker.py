"""
Goal Tracker - Tracks progress of conversation goals in real-time.

This module monitors the completion status of conversation goals,
handles goal updates, and triggers actions when conditions are met.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Callable
from enum import Enum

from .flow_interpreter import (
    FlowIntent, ConversationGoal, FlowCondition,
    NotificationConfig, HandoffTrigger, GoalPriority
)
from .memory import UnifiedMemory


class GoalStatus(str, Enum):
    """Status of a goal."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COLLECTED = "collected"
    SKIPPED = "skipped"
    FAILED = "failed"


class ConditionResult(str, Enum):
    """Result of condition evaluation."""
    TRUE = "true"
    FALSE = "false"
    NOT_EVALUATED = "not_evaluated"


@dataclass
class GoalUpdate:
    """Represents an update to a goal."""
    field_name: str
    old_value: Any
    new_value: Any
    status: GoalStatus
    timestamp: str
    source: str = "user_message"  # user_message, extraction, manual


@dataclass
class TriggeredCondition:
    """A condition that was triggered."""
    condition: FlowCondition
    result: ConditionResult
    triggered_at: str
    action_to_take: str


@dataclass
class GoalProgress:
    """Progress report for goals."""
    total_goals: int
    completed: int
    required_completed: int
    required_total: int
    pending: list[ConversationGoal]
    next_priority: Optional[ConversationGoal]
    completion_percentage: float
    required_completion_percentage: float
    qualification_score: int


@dataclass
class ExtractionResult:
    """Result of data extraction from AI response."""
    field: str
    value: Any
    confidence: float  # 0.0 to 1.0
    source_text: str = ""


class GoalTracker:
    """
    Tracks progress of conversation goals in real-time.

    Responsibilities:
    - Monitor goal completion status
    - Update goals based on AI extractions
    - Check and trigger conditions
    - Calculate qualification scores
    - Determine next actions
    """

    def __init__(self, flow_intent: FlowIntent, memory: UnifiedMemory):
        """
        Initialize GoalTracker.

        Args:
            flow_intent: The interpreted flow intent with goals
            memory: UnifiedMemory instance for state
        """
        self.flow_intent = flow_intent
        self.memory = memory
        self.goal_updates: list[GoalUpdate] = []
        self.triggered_conditions: list[TriggeredCondition] = []

        # Sync goals with memory
        self._sync_with_memory()

    def _sync_with_memory(self):
        """Sync goal status with memory's collected data."""
        collected = self.memory.collected_data or {}

        for goal in self.flow_intent.goals:
            if goal.field_name in collected:
                value = collected[goal.field_name]
                if value is not None and value != "":
                    goal.collected = True
                    goal.value = value

    def get_progress(self) -> GoalProgress:
        """Get current progress report."""
        goals = self.flow_intent.goals
        total = len(goals)
        completed = sum(1 for g in goals if g.collected)
        required = [g for g in goals if g.required]
        required_completed = sum(1 for g in required if g.collected)
        required_total = len(required)
        pending = [g for g in goals if not g.collected]
        next_goal = self.flow_intent.get_next_priority_goal()

        completion_pct = (completed / total * 100) if total > 0 else 100
        required_pct = (required_completed / required_total * 100) if required_total > 0 else 100

        return GoalProgress(
            total_goals=total,
            completed=completed,
            required_completed=required_completed,
            required_total=required_total,
            pending=pending,
            next_priority=next_goal,
            completion_percentage=round(completion_pct, 1),
            required_completion_percentage=round(required_pct, 1),
            qualification_score=self.calculate_qualification_score()
        )

    def update_from_extractions(self, extractions: list[ExtractionResult]) -> list[GoalUpdate]:
        """
        Update goals based on AI extractions.

        Args:
            extractions: List of extraction results from AI

        Returns:
            List of goal updates that were applied
        """
        updates = []
        now = datetime.utcnow().isoformat()

        for extraction in extractions:
            field = extraction.field
            value = extraction.value

            # Find matching goal
            goal = self._find_goal(field)
            if not goal:
                # Create a custom goal for unexpected extractions
                continue

            # Skip if already collected with same value
            if goal.collected and goal.value == value:
                continue

            # Create update record
            update = GoalUpdate(
                field_name=field,
                old_value=goal.value,
                new_value=value,
                status=GoalStatus.COLLECTED,
                timestamp=now,
                source="extraction"
            )
            updates.append(update)
            self.goal_updates.append(update)

            # Update goal
            goal.collected = True
            goal.value = value

            # Update memory
            self.memory.update_collected_data(field, value)
            self.memory.update_goal_progress(field, True, value)

        return updates

    def mark_collected(self, field: str, value: Any, source: str = "manual") -> Optional[GoalUpdate]:
        """
        Mark a goal as collected.

        Args:
            field: Field name
            value: Collected value
            source: Source of the update

        Returns:
            GoalUpdate if successful
        """
        goal = self._find_goal(field)
        if not goal:
            return None

        now = datetime.utcnow().isoformat()
        update = GoalUpdate(
            field_name=field,
            old_value=goal.value,
            new_value=value,
            status=GoalStatus.COLLECTED,
            timestamp=now,
            source=source
        )
        self.goal_updates.append(update)

        goal.collected = True
        goal.value = value

        # Update memory
        self.memory.update_collected_data(field, value)
        self.memory.update_goal_progress(field, True, value)

        return update

    def mark_failed(self, field: str, reason: str = "") -> Optional[GoalUpdate]:
        """Mark a goal as failed (e.g., max retries reached)."""
        goal = self._find_goal(field)
        if not goal:
            return None

        now = datetime.utcnow().isoformat()
        update = GoalUpdate(
            field_name=field,
            old_value=goal.value,
            new_value=None,
            status=GoalStatus.FAILED,
            timestamp=now,
            source="system"
        )
        self.goal_updates.append(update)

        goal.attempts += 1
        self.memory.update_goal_progress(field, False, None)

        return update

    def mark_skipped(self, field: str) -> Optional[GoalUpdate]:
        """Mark a goal as skipped (user declined to provide)."""
        goal = self._find_goal(field)
        if not goal:
            return None

        now = datetime.utcnow().isoformat()
        update = GoalUpdate(
            field_name=field,
            old_value=goal.value,
            new_value=None,
            status=GoalStatus.SKIPPED,
            timestamp=now,
            source="user_declined"
        )
        self.goal_updates.append(update)

        goal.collected = True  # Consider it "handled"
        goal.value = None
        self.memory.update_goal_progress(field, True, None)

        return update

    def increment_attempts(self, field: str):
        """Increment attempts counter for a goal."""
        goal = self._find_goal(field)
        if goal:
            goal.attempts += 1

    def check_conditions(self) -> list[TriggeredCondition]:
        """
        Check all conditions and return triggered ones.

        Returns:
            List of conditions that were triggered
        """
        triggered = []
        now = datetime.utcnow().isoformat()

        for condition in self.flow_intent.conditions:
            result = self._evaluate_condition(condition)

            if result != ConditionResult.NOT_EVALUATED:
                action = condition.true_action if result == ConditionResult.TRUE else condition.false_action

                triggered_cond = TriggeredCondition(
                    condition=condition,
                    result=result,
                    triggered_at=now,
                    action_to_take=action
                )
                triggered.append(triggered_cond)
                self.triggered_conditions.append(triggered_cond)

        return triggered

    def _evaluate_condition(self, condition: FlowCondition) -> ConditionResult:
        """Evaluate a single condition."""
        field_value = self._get_field_value(condition.field)

        if field_value is None:
            return ConditionResult.NOT_EVALUATED

        target_value = condition.value
        operator = condition.operator.lower()

        try:
            if operator == "equals":
                result = str(field_value).lower() == str(target_value).lower()
            elif operator == "not_equals":
                result = str(field_value).lower() != str(target_value).lower()
            elif operator == "contains":
                result = str(target_value).lower() in str(field_value).lower()
            elif operator == "not_contains":
                result = str(target_value).lower() not in str(field_value).lower()
            elif operator == "greater_than":
                result = float(field_value) > float(target_value)
            elif operator == "less_than":
                result = float(field_value) < float(target_value)
            elif operator == "greater_or_equal":
                result = float(field_value) >= float(target_value)
            elif operator == "less_or_equal":
                result = float(field_value) <= float(target_value)
            elif operator == "is_empty":
                result = not field_value or str(field_value).strip() == ""
            elif operator == "is_not_empty":
                result = bool(field_value) and str(field_value).strip() != ""
            elif operator == "exists":
                result = field_value is not None
            elif operator == "starts_with":
                result = str(field_value).lower().startswith(str(target_value).lower())
            elif operator == "ends_with":
                result = str(field_value).lower().endswith(str(target_value).lower())
            elif operator == "in_list":
                if isinstance(target_value, list):
                    result = field_value in target_value
                else:
                    result = str(field_value) in str(target_value).split(",")
            else:
                return ConditionResult.NOT_EVALUATED

            return ConditionResult.TRUE if result else ConditionResult.FALSE

        except (ValueError, TypeError):
            return ConditionResult.NOT_EVALUATED

    def _get_field_value(self, field: str) -> Any:
        """Get field value from collected data or goals."""
        # Check memory first
        if field in self.memory.collected_data:
            return self.memory.collected_data[field]

        # Check goals
        goal = self._find_goal(field)
        if goal and goal.collected:
            return goal.value

        return None

    def _find_goal(self, field: str) -> Optional[ConversationGoal]:
        """Find a goal by field name."""
        for goal in self.flow_intent.goals:
            if goal.field_name == field:
                return goal
        return None

    def calculate_qualification_score(self) -> int:
        """
        Calculate lead qualification score based on collected data.

        Returns:
            Score from 0 to 100
        """
        score_map = self.flow_intent.qualification_score_map or {}
        total_score = 0

        for goal in self.flow_intent.goals:
            if goal.collected and goal.value:
                field_score = score_map.get(goal.field_name, 0)
                total_score += field_score

        return min(total_score, 100)

    def is_qualified(self) -> bool:
        """Check if lead meets qualification threshold."""
        score = self.calculate_qualification_score()
        threshold = self.flow_intent.qualification_threshold
        return score >= threshold

    def should_handoff(self) -> tuple[bool, Optional[str]]:
        """
        Check if conversation should be handed off to human.

        Returns:
            Tuple of (should_handoff, reason)
        """
        # Check if ALL goals (not just required) are complete
        all_goals_complete = all(g.collected for g in self.flow_intent.goals) if self.flow_intent.goals else False

        # Check if required goals are complete
        required_complete = self.flow_intent.is_complete()

        # Check if qualified
        is_qualified = self.is_qualified()

        # If there are handoff triggers, check them
        if self.flow_intent.handoff_triggers:
            for trigger in self.flow_intent.handoff_triggers:
                if trigger.condition == "qualified" and is_qualified:
                    return True, trigger.reason or "Lead qualificado"
                if trigger.condition == "goal_complete" and (all_goals_complete or required_complete):
                    return True, trigger.reason or "Todos os dados coletados"
                if trigger.condition == "all_complete" and all_goals_complete:
                    return True, trigger.reason or "Coleta completa"

        # Default: handoff when all goals are complete (even without explicit trigger)
        if all_goals_complete:
            return True, "Todos os dados foram coletados - passar para consultor"

        # Or when required goals are complete and we have handoff triggers
        if required_complete and self.flow_intent.handoff_triggers:
            return True, "Dados obrigatórios coletados - passar para consultor"

        return False, None

    def get_notifications_to_send(self) -> list[NotificationConfig]:
        """Get notifications that should be sent based on current state."""
        notifications = []

        for notif in self.flow_intent.notifications:
            # Check trigger conditions
            if notif.trigger == "on_qualification" and self.is_qualified():
                notifications.append(notif)
            elif notif.trigger == "on_complete" and self.flow_intent.is_complete():
                notifications.append(notif)
            # Add more trigger types as needed

        return notifications

    def get_next_goal_to_collect(self) -> Optional[ConversationGoal]:
        """Get the next goal the AI should try to collect."""
        return self.flow_intent.get_next_priority_goal()

    def get_context_for_prompt(self) -> dict[str, Any]:
        """Get context data for AI prompt generation."""
        progress = self.get_progress()
        next_goal = progress.next_priority

        return {
            "total_goals": progress.total_goals,
            "completed_goals": progress.completed,
            "completion_percentage": progress.completion_percentage,
            "qualification_score": progress.qualification_score,
            "is_qualified": self.is_qualified(),
            "next_goal": next_goal.to_dict() if next_goal else None,
            "pending_count": len(progress.pending),
            "collected_data": self.memory.collected_data,
            "required_remaining": progress.required_total - progress.required_completed
        }

    def format_status_for_prompt(self) -> str:
        """Format current status for AI prompt."""
        progress = self.get_progress()
        lines = []

        lines.append(f"**Progresso: {progress.completion_percentage}%** ({progress.completed}/{progress.total_goals} objetivos)")
        lines.append(f"Score de qualificação: {progress.qualification_score}/100")

        if progress.next_priority:
            goal = progress.next_priority
            lines.append(f"\n**Próximo objetivo:** Coletar {goal.field_name}")
            lines.append(f"  - Descrição: {goal.description}")
            if goal.options:
                lines.append(f"  - Opções: {', '.join(goal.options)}")
            if goal.suggested_question:
                lines.append(f"  - Sugestão: {goal.suggested_question}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert tracker state to dictionary."""
        progress = self.get_progress()
        return {
            "progress": {
                "total": progress.total_goals,
                "completed": progress.completed,
                "percentage": progress.completion_percentage,
                "qualification_score": progress.qualification_score
            },
            "goals": [g.to_dict() for g in self.flow_intent.goals],
            "updates": [
                {
                    "field": u.field_name,
                    "value": u.new_value,
                    "status": u.status.value,
                    "timestamp": u.timestamp
                }
                for u in self.goal_updates
            ],
            "triggered_conditions": [
                {
                    "field": tc.condition.field,
                    "result": tc.result.value,
                    "action": tc.action_to_take
                }
                for tc in self.triggered_conditions
            ]
        }
