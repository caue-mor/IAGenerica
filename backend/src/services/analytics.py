"""
Analytics Service - Comprehensive metrics tracking for SaaS dashboard.

Tracks all events during conversations for:
- Funnel analysis
- Conversion tracking
- Drop-off points
- Performance metrics
- Lead qualification trends
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from ..core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of analytics events."""
    # Conversation events
    CONVERSATION_STARTED = "conversation_started"
    CONVERSATION_ENDED = "conversation_ended"
    CONVERSATION_ABANDONED = "conversation_abandoned"

    # Message events
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    MESSAGE_FAILED = "message_failed"

    # Data collection events
    FIELD_COLLECTED = "field_collected"
    FIELD_VALIDATION_FAILED = "field_validation_failed"
    FIELD_RETRY = "field_retry"

    # Flow events
    NODE_ENTERED = "node_entered"
    NODE_COMPLETED = "node_completed"
    CONDITION_EVALUATED = "condition_evaluated"
    SWITCH_BRANCH_TAKEN = "switch_branch_taken"
    FLOW_COMPLETED = "flow_completed"
    FLOW_ABANDONED = "flow_abandoned"

    # Qualification events
    LEAD_SCORED = "lead_scored"
    LEAD_QUALIFIED = "lead_qualified"
    LEAD_DISQUALIFIED = "lead_disqualified"
    TEMPERATURE_CHANGED = "temperature_changed"

    # Notification events
    NOTIFICATION_TRIGGERED = "notification_triggered"
    NOTIFICATION_SENT = "notification_sent"
    NOTIFICATION_FAILED = "notification_failed"

    # Handoff events
    HANDOFF_REQUESTED = "handoff_requested"
    HANDOFF_COMPLETED = "handoff_completed"

    # User actions
    USER_INTENT_DETECTED = "user_intent_detected"
    SENTIMENT_DETECTED = "sentiment_detected"

    # System events
    ERROR_OCCURRED = "error_occurred"
    RATE_LIMITED = "rate_limited"


@dataclass
class FunnelMetrics:
    """Funnel metrics for a period."""
    total_conversations: int = 0
    conversations_with_response: int = 0
    reached_qualification: int = 0
    qualified_hot: int = 0
    qualified_warm: int = 0
    cold: int = 0
    handoffs: int = 0
    completed: int = 0
    abandoned: int = 0

    @property
    def response_rate(self) -> float:
        """Percentage of conversations that got a response."""
        return (self.conversations_with_response / self.total_conversations * 100) if self.total_conversations > 0 else 0

    @property
    def qualification_rate(self) -> float:
        """Percentage that reached qualification stage."""
        return (self.reached_qualification / self.total_conversations * 100) if self.total_conversations > 0 else 0

    @property
    def conversion_rate(self) -> float:
        """Percentage of hot leads (primary conversion)."""
        return ((self.qualified_hot + self.handoffs) / self.total_conversations * 100) if self.total_conversations > 0 else 0

    @property
    def completion_rate(self) -> float:
        """Percentage of completed flows."""
        return (self.completed / self.total_conversations * 100) if self.total_conversations > 0 else 0

    @property
    def abandonment_rate(self) -> float:
        """Percentage of abandoned conversations."""
        return (self.abandoned / self.total_conversations * 100) if self.total_conversations > 0 else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_conversations": self.total_conversations,
            "conversations_with_response": self.conversations_with_response,
            "reached_qualification": self.reached_qualification,
            "qualified_hot": self.qualified_hot,
            "qualified_warm": self.qualified_warm,
            "cold": self.cold,
            "handoffs": self.handoffs,
            "completed": self.completed,
            "abandoned": self.abandoned,
            "response_rate": round(self.response_rate, 2),
            "qualification_rate": round(self.qualification_rate, 2),
            "conversion_rate": round(self.conversion_rate, 2),
            "completion_rate": round(self.completion_rate, 2),
            "abandonment_rate": round(self.abandonment_rate, 2),
        }


@dataclass
class FieldPerformance:
    """Performance metrics for a single field."""
    field_name: str
    collection_attempts: int = 0
    successful_collections: int = 0
    validation_failures: int = 0
    avg_attempts_to_collect: float = 0
    drop_off_count: int = 0  # How many abandoned at this field

    @property
    def success_rate(self) -> float:
        return (self.successful_collections / self.collection_attempts * 100) if self.collection_attempts > 0 else 0

    @property
    def drop_off_rate(self) -> float:
        return (self.drop_off_count / self.collection_attempts * 100) if self.collection_attempts > 0 else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "collection_attempts": self.collection_attempts,
            "successful_collections": self.successful_collections,
            "validation_failures": self.validation_failures,
            "avg_attempts_to_collect": round(self.avg_attempts_to_collect, 2),
            "success_rate": round(self.success_rate, 2),
            "drop_off_count": self.drop_off_count,
            "drop_off_rate": round(self.drop_off_rate, 2),
        }


@dataclass
class TimeSeriesPoint:
    """Single point in time series data."""
    timestamp: datetime
    value: int
    label: Optional[str] = None


class AnalyticsService:
    """
    Comprehensive analytics service for tracking all conversation events.

    Stores events in Supabase and provides aggregation methods for
    funnel analysis, conversion tracking, and performance metrics.
    """

    TABLE_NAME = "iagenericanexma_analytics_events"

    def __init__(self):
        """Initialize the analytics service."""
        self._supabase = None

    @property
    def supabase(self):
        """Lazy load Supabase client."""
        if self._supabase is None:
            self._supabase = get_supabase_client()
        return self._supabase

    async def track(
        self,
        company_id: int,
        event_type: EventType | str,
        event_data: Dict[str, Any] = None,
        lead_id: Optional[int] = None,
        conversation_id: Optional[int] = None
    ) -> bool:
        """
        Track an analytics event.

        Args:
            company_id: Company ID
            event_type: Type of event
            event_data: Additional event data
            lead_id: Related lead ID (optional)
            conversation_id: Related conversation ID (optional)

        Returns:
            True if event was tracked successfully
        """
        if isinstance(event_type, EventType):
            event_type = event_type.value

        data = {
            "company_id": company_id,
            "lead_id": lead_id,
            "conversation_id": conversation_id,
            "event_type": event_type,
            "event_data": event_data or {},
            "created_at": datetime.utcnow().isoformat()
        }

        try:
            self.supabase.table(self.TABLE_NAME).insert(data).execute()
            logger.debug(f"Analytics event tracked: {event_type} for company {company_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to track analytics event: {e}")
            return False

    async def track_batch(self, events: List[Dict[str, Any]]) -> int:
        """
        Track multiple events at once.

        Args:
            events: List of event dictionaries

        Returns:
            Number of events tracked successfully
        """
        if not events:
            return 0

        # Add timestamp to all events
        for event in events:
            if "created_at" not in event:
                event["created_at"] = datetime.utcnow().isoformat()
            if isinstance(event.get("event_type"), EventType):
                event["event_type"] = event["event_type"].value

        try:
            self.supabase.table(self.TABLE_NAME).insert(events).execute()
            return len(events)
        except Exception as e:
            logger.error(f"Failed to track batch events: {e}")
            return 0

    async def get_funnel_metrics(
        self,
        company_id: int,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> FunnelMetrics:
        """
        Get funnel metrics for a company.

        Args:
            company_id: Company ID
            start_date: Start of period (default: 30 days ago)
            end_date: End of period (default: now)

        Returns:
            FunnelMetrics with aggregated data
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        try:
            # Get all events in period
            response = self.supabase.table(self.TABLE_NAME).select("*").eq(
                "company_id", company_id
            ).gte(
                "created_at", start_date.isoformat()
            ).lte(
                "created_at", end_date.isoformat()
            ).execute()

            events = response.data if response.data else []

            # Count by event type
            event_counts = {}
            for event in events:
                event_type = event.get("event_type")
                event_counts[event_type] = event_counts.get(event_type, 0) + 1

            # Extract temperature data from lead_scored events
            hot_count = 0
            warm_count = 0
            cold_count = 0
            for event in events:
                if event.get("event_type") == EventType.LEAD_SCORED.value:
                    temp = event.get("event_data", {}).get("temperature")
                    if temp == "hot":
                        hot_count += 1
                    elif temp == "warm":
                        warm_count += 1
                    elif temp == "cold":
                        cold_count += 1

            return FunnelMetrics(
                total_conversations=event_counts.get(EventType.CONVERSATION_STARTED.value, 0),
                conversations_with_response=event_counts.get(EventType.MESSAGE_SENT.value, 0),
                reached_qualification=event_counts.get(EventType.LEAD_SCORED.value, 0),
                qualified_hot=hot_count,
                qualified_warm=warm_count,
                cold=cold_count,
                handoffs=event_counts.get(EventType.HANDOFF_REQUESTED.value, 0),
                completed=event_counts.get(EventType.FLOW_COMPLETED.value, 0),
                abandoned=event_counts.get(EventType.CONVERSATION_ABANDONED.value, 0)
            )

        except Exception as e:
            logger.error(f"Failed to get funnel metrics: {e}")
            return FunnelMetrics()

    async def get_field_performance(
        self,
        company_id: int,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[FieldPerformance]:
        """
        Get field collection performance (where leads drop off).

        Args:
            company_id: Company ID
            start_date: Start of period
            end_date: End of period

        Returns:
            List of FieldPerformance for each field
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        try:
            # Get field-related events
            response = self.supabase.table(self.TABLE_NAME).select("*").eq(
                "company_id", company_id
            ).in_(
                "event_type",
                [
                    EventType.FIELD_COLLECTED.value,
                    EventType.FIELD_VALIDATION_FAILED.value,
                    EventType.FIELD_RETRY.value,
                    EventType.CONVERSATION_ABANDONED.value
                ]
            ).gte(
                "created_at", start_date.isoformat()
            ).lte(
                "created_at", end_date.isoformat()
            ).execute()

            events = response.data if response.data else []

            # Aggregate by field
            field_stats: Dict[str, FieldPerformance] = {}

            for event in events:
                event_type = event.get("event_type")
                event_data = event.get("event_data", {})
                field_name = event_data.get("field", "unknown")

                if field_name not in field_stats:
                    field_stats[field_name] = FieldPerformance(field_name=field_name)

                stats = field_stats[field_name]

                if event_type == EventType.FIELD_COLLECTED.value:
                    stats.collection_attempts += 1
                    stats.successful_collections += 1
                elif event_type == EventType.FIELD_VALIDATION_FAILED.value:
                    stats.collection_attempts += 1
                    stats.validation_failures += 1
                elif event_type == EventType.FIELD_RETRY.value:
                    stats.collection_attempts += 1
                elif event_type == EventType.CONVERSATION_ABANDONED.value:
                    last_field = event_data.get("last_field")
                    if last_field and last_field in field_stats:
                        field_stats[last_field].drop_off_count += 1

            # Calculate averages
            for stats in field_stats.values():
                if stats.successful_collections > 0:
                    stats.avg_attempts_to_collect = stats.collection_attempts / stats.successful_collections

            return list(field_stats.values())

        except Exception as e:
            logger.error(f"Failed to get field performance: {e}")
            return []

    async def get_conversion_timeline(
        self,
        company_id: int,
        days: int = 30,
        granularity: str = "day"
    ) -> List[TimeSeriesPoint]:
        """
        Get conversion timeline data.

        Args:
            company_id: Company ID
            days: Number of days to look back
            granularity: "hour", "day", or "week"

        Returns:
            List of TimeSeriesPoint for the timeline
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        try:
            response = self.supabase.table(self.TABLE_NAME).select("*").eq(
                "company_id", company_id
            ).eq(
                "event_type", EventType.LEAD_QUALIFIED.value
            ).gte(
                "created_at", start_date.isoformat()
            ).execute()

            events = response.data if response.data else []

            # Group by time period
            points_dict: Dict[str, int] = {}

            for event in events:
                timestamp = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))

                if granularity == "hour":
                    key = timestamp.strftime("%Y-%m-%d %H:00")
                elif granularity == "week":
                    # Start of week
                    week_start = timestamp - timedelta(days=timestamp.weekday())
                    key = week_start.strftime("%Y-%m-%d")
                else:  # day
                    key = timestamp.strftime("%Y-%m-%d")

                points_dict[key] = points_dict.get(key, 0) + 1

            # Convert to timeline points
            points = [
                TimeSeriesPoint(
                    timestamp=datetime.strptime(k, "%Y-%m-%d %H:00" if granularity == "hour" else "%Y-%m-%d"),
                    value=v
                )
                for k, v in sorted(points_dict.items())
            ]

            return points

        except Exception as e:
            logger.error(f"Failed to get conversion timeline: {e}")
            return []

    async def get_recent_events(
        self,
        company_id: int,
        limit: int = 50,
        event_types: List[EventType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent events for a company.

        Args:
            company_id: Company ID
            limit: Maximum number of events
            event_types: Filter by event types (optional)

        Returns:
            List of recent events
        """
        try:
            query = self.supabase.table(self.TABLE_NAME).select("*").eq(
                "company_id", company_id
            ).order("created_at", desc=True).limit(limit)

            if event_types:
                query = query.in_("event_type", [e.value for e in event_types])

            response = query.execute()
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []

    async def get_lead_journey(
        self,
        lead_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get all events for a specific lead (journey tracking).

        Args:
            lead_id: Lead ID

        Returns:
            List of events in chronological order
        """
        try:
            response = self.supabase.table(self.TABLE_NAME).select("*").eq(
                "lead_id", lead_id
            ).order("created_at", desc=False).execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Failed to get lead journey: {e}")
            return []

    async def get_dashboard_summary(
        self,
        company_id: int
    ) -> Dict[str, Any]:
        """
        Get summary data for dashboard.

        Args:
            company_id: Company ID

        Returns:
            Dictionary with dashboard summary data
        """
        # Get data for different periods
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Get metrics for each period
        today_metrics = await self.get_funnel_metrics(company_id, today, datetime.utcnow())
        week_metrics = await self.get_funnel_metrics(company_id, week_start, datetime.utcnow())
        month_metrics = await self.get_funnel_metrics(company_id, month_start, datetime.utcnow())

        # Get field performance
        field_performance = await self.get_field_performance(company_id)

        return {
            "today": today_metrics.to_dict(),
            "this_week": week_metrics.to_dict(),
            "this_month": month_metrics.to_dict(),
            "field_performance": [f.to_dict() for f in field_performance],
            "generated_at": datetime.utcnow().isoformat()
        }


# Singleton instance
analytics_service = AnalyticsService()


# Convenience functions
async def track_event(
    company_id: int,
    event_type: EventType | str,
    event_data: Dict[str, Any] = None,
    lead_id: int = None,
    conversation_id: int = None
) -> bool:
    """Track a single analytics event."""
    return await analytics_service.track(
        company_id, event_type, event_data, lead_id, conversation_id
    )


async def track_field_collected(
    company_id: int,
    lead_id: int,
    field: str,
    value: Any,
    attempt: int = 1
) -> bool:
    """Track a field collection event."""
    return await analytics_service.track(
        company_id=company_id,
        event_type=EventType.FIELD_COLLECTED,
        event_data={"field": field, "value": str(value)[:100], "attempt": attempt},
        lead_id=lead_id
    )


async def track_lead_scored(
    company_id: int,
    lead_id: int,
    score: int,
    temperature: str,
    breakdown: Dict[str, Any] = None
) -> bool:
    """Track a lead scoring event."""
    return await analytics_service.track(
        company_id=company_id,
        event_type=EventType.LEAD_SCORED,
        event_data={"score": score, "temperature": temperature, "breakdown": breakdown},
        lead_id=lead_id
    )


async def track_conversation_started(
    company_id: int,
    lead_id: int,
    conversation_id: int,
    source: str = "whatsapp"
) -> bool:
    """Track conversation start."""
    return await analytics_service.track(
        company_id=company_id,
        event_type=EventType.CONVERSATION_STARTED,
        event_data={"source": source},
        lead_id=lead_id,
        conversation_id=conversation_id
    )


async def track_handoff(
    company_id: int,
    lead_id: int,
    reason: str,
    score: int = None
) -> bool:
    """Track handoff event."""
    return await analytics_service.track(
        company_id=company_id,
        event_type=EventType.HANDOFF_REQUESTED,
        event_data={"reason": reason, "score": score},
        lead_id=lead_id
    )
