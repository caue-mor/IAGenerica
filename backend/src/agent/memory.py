"""
Unified Memory System for intelligent AI conversations.

This module provides a comprehensive memory system that handles:
- Short-term: Current conversation state
- Long-term: Lead profile and preferences
- Episodic: Interaction history
- Semantic: Known facts about the lead
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum


class InteractionStyle(str, Enum):
    """Lead's interaction style preferences."""
    FORMAL = "formal"
    CASUAL = "casual"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class Sentiment(str, Enum):
    """Conversation sentiment tracking."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class LeadProfile:
    """Long-term profile of the lead."""
    # Preferences learned over time
    preferences: dict[str, Any] = field(default_factory=dict)
    # Behavioral patterns observed
    behavior_patterns: list[str] = field(default_factory=list)
    # Interaction style (formal, casual, mixed)
    interaction_style: InteractionStyle = InteractionStyle.UNKNOWN
    # Communication preferences
    preferred_contact_time: Optional[str] = None
    language_style: str = "pt-BR"

    def to_dict(self) -> dict[str, Any]:
        return {
            "preferences": self.preferences,
            "behavior_patterns": self.behavior_patterns,
            "interaction_style": self.interaction_style.value,
            "preferred_contact_time": self.preferred_contact_time,
            "language_style": self.language_style
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadProfile":
        if not data:
            return cls()
        return cls(
            preferences=data.get("preferences", {}),
            behavior_patterns=data.get("behavior_patterns", []),
            interaction_style=InteractionStyle(data.get("interaction_style", "unknown")),
            preferred_contact_time=data.get("preferred_contact_time"),
            language_style=data.get("language_style", "pt-BR")
        )


@dataclass
class KnownFacts:
    """Semantic memory - facts known about the lead."""
    # Explicitly stated facts
    stated_facts: dict[str, Any] = field(default_factory=dict)
    # Inferred information
    inferred_facts: dict[str, Any] = field(default_factory=dict)
    # Topics of interest
    interests: list[str] = field(default_factory=list)
    # Pain points mentioned
    pain_points: list[str] = field(default_factory=list)
    # Budget information
    mentioned_budget: Optional[str] = None
    # Urgency level
    urgency: Optional[str] = None
    # Timeline mentioned
    timeline: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stated_facts": self.stated_facts,
            "inferred_facts": self.inferred_facts,
            "interests": self.interests,
            "pain_points": self.pain_points,
            "mentioned_budget": self.mentioned_budget,
            "urgency": self.urgency,
            "timeline": self.timeline
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnownFacts":
        if not data:
            return cls()
        return cls(
            stated_facts=data.get("stated_facts", {}),
            inferred_facts=data.get("inferred_facts", {}),
            interests=data.get("interests", []),
            pain_points=data.get("pain_points", []),
            mentioned_budget=data.get("mentioned_budget"),
            urgency=data.get("urgency"),
            timeline=data.get("timeline")
        )


@dataclass
class Interaction:
    """Single interaction record for episodic memory."""
    timestamp: str
    user_message: str
    ai_response: str
    extracted_data: dict[str, Any] = field(default_factory=dict)
    sentiment: Sentiment = Sentiment.NEUTRAL
    topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "user_message": self.user_message,
            "ai_response": self.ai_response,
            "extracted_data": self.extracted_data,
            "sentiment": self.sentiment.value,
            "topics": self.topics
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Interaction":
        return cls(
            timestamp=data.get("timestamp", ""),
            user_message=data.get("user_message", ""),
            ai_response=data.get("ai_response", ""),
            extracted_data=data.get("extracted_data", {}),
            sentiment=Sentiment(data.get("sentiment", "neutral")),
            topics=data.get("topics", [])
        )


@dataclass
class ConversationState:
    """Short-term state of current conversation."""
    # Current topic being discussed
    current_topic: Optional[str] = None
    # Last action taken by AI
    last_ai_action: Optional[str] = None
    # Retry count for current field
    retry_count: int = 0
    # Current sentiment
    sentiment: Sentiment = Sentiment.NEUTRAL
    # User intent detected
    user_intent: Optional[str] = None
    # Awaiting specific input type
    awaiting_input: Optional[str] = None
    # Last question asked
    last_question: Optional[str] = None
    # Context from recent messages
    recent_context: str = ""
    # Flow phase (qualification, proposal, etc.)
    current_phase: str = "initial"
    # Triggered conditions
    triggered_conditions: list[str] = field(default_factory=list)
    # Pending actions
    pending_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_topic": self.current_topic,
            "last_ai_action": self.last_ai_action,
            "retry_count": self.retry_count,
            "sentiment": self.sentiment.value,
            "user_intent": self.user_intent,
            "awaiting_input": self.awaiting_input,
            "last_question": self.last_question,
            "recent_context": self.recent_context,
            "current_phase": self.current_phase,
            "triggered_conditions": self.triggered_conditions,
            "pending_actions": self.pending_actions
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationState":
        if not data:
            return cls()
        return cls(
            current_topic=data.get("current_topic"),
            last_ai_action=data.get("last_ai_action"),
            retry_count=data.get("retry_count", 0),
            sentiment=Sentiment(data.get("sentiment", "neutral")),
            user_intent=data.get("user_intent"),
            awaiting_input=data.get("awaiting_input"),
            last_question=data.get("last_question"),
            recent_context=data.get("recent_context", ""),
            current_phase=data.get("current_phase", "initial"),
            triggered_conditions=data.get("triggered_conditions", []),
            pending_actions=data.get("pending_actions", [])
        )


@dataclass
class GoalProgress:
    """Progress tracking for conversation goals."""
    # All goals with status
    goals: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Completion percentage
    completion: float = 0.0
    # Last updated timestamp
    last_updated: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "goals": self.goals,
            "completion": self.completion,
            "last_updated": self.last_updated
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalProgress":
        if not data:
            return cls()
        return cls(
            goals=data.get("goals", {}),
            completion=data.get("completion", 0.0),
            last_updated=data.get("last_updated")
        )


@dataclass
class UnifiedMemory:
    """
    Complete memory system for the AI agent.

    This class unifies all memory types:
    - Short-term: conversation_state (current session)
    - Long-term: lead_profile (persisted across sessions)
    - Episodic: interaction_history (past interactions)
    - Semantic: known_facts (facts about the lead)
    """

    # Identifiers
    lead_id: int
    conversation_id: int

    # Short-term memory (current conversation)
    conversation_state: ConversationState = field(default_factory=ConversationState)

    # Long-term memory (lead profile)
    lead_profile: LeadProfile = field(default_factory=LeadProfile)

    # Episodic memory (interaction history)
    interaction_history: list[Interaction] = field(default_factory=list)

    # Semantic memory (known facts)
    known_facts: KnownFacts = field(default_factory=KnownFacts)

    # Goal progress tracking
    goal_progress: GoalProgress = field(default_factory=GoalProgress)

    # Collected data (structured)
    collected_data: dict[str, Any] = field(default_factory=dict)

    # History summary (AI-generated)
    history_summary: str = ""

    # Last topics discussed
    last_topics: list[str] = field(default_factory=list)

    # Timestamps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        now = datetime.utcnow().isoformat()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now

    def update_conversation_state(self, **kwargs):
        """Update conversation state with new values."""
        for key, value in kwargs.items():
            if hasattr(self.conversation_state, key):
                setattr(self.conversation_state, key, value)
        self.updated_at = datetime.utcnow().isoformat()

    def add_interaction(self, user_message: str, ai_response: str,
                       extracted_data: dict = None, sentiment: Sentiment = None,
                       topics: list = None):
        """Add an interaction to episodic memory."""
        interaction = Interaction(
            timestamp=datetime.utcnow().isoformat(),
            user_message=user_message,
            ai_response=ai_response,
            extracted_data=extracted_data or {},
            sentiment=sentiment or Sentiment.NEUTRAL,
            topics=topics or []
        )
        self.interaction_history.append(interaction)

        # Keep last 50 interactions
        if len(self.interaction_history) > 50:
            self.interaction_history = self.interaction_history[-50:]

        # Update last topics
        if topics:
            self.last_topics = (topics + self.last_topics)[:10]

        self.updated_at = datetime.utcnow().isoformat()

    def add_known_fact(self, fact_key: str, fact_value: Any, is_inferred: bool = False):
        """Add a fact to semantic memory."""
        if is_inferred:
            self.known_facts.inferred_facts[fact_key] = fact_value
        else:
            self.known_facts.stated_facts[fact_key] = fact_value
        self.updated_at = datetime.utcnow().isoformat()

    def update_collected_data(self, field: str, value: Any):
        """Update collected data."""
        self.collected_data[field] = value
        self.updated_at = datetime.utcnow().isoformat()

    def update_goal_progress(self, field: str, collected: bool, value: Any = None):
        """Update goal progress for a specific field."""
        self.goal_progress.goals[field] = {
            "collected": collected,
            "value": value,
            "updated_at": datetime.utcnow().isoformat()
        }
        # Recalculate completion
        total = len(self.goal_progress.goals)
        completed = sum(1 for g in self.goal_progress.goals.values() if g.get("collected"))
        self.goal_progress.completion = completed / total if total > 0 else 0.0
        self.goal_progress.last_updated = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    def get_context_summary(self) -> str:
        """Generate a summary of current context for AI prompts."""
        parts = []

        # Lead info
        if self.collected_data:
            parts.append(f"Dados coletados: {self.collected_data}")

        # Known facts
        if self.known_facts.stated_facts:
            parts.append(f"Fatos conhecidos: {self.known_facts.stated_facts}")

        # Pain points
        if self.known_facts.pain_points:
            parts.append(f"Pontos de dor: {', '.join(self.known_facts.pain_points)}")

        # Interests
        if self.known_facts.interests:
            parts.append(f"Interesses: {', '.join(self.known_facts.interests)}")

        # Current topic
        if self.conversation_state.current_topic:
            parts.append(f"Tópico atual: {self.conversation_state.current_topic}")

        # History summary
        if self.history_summary:
            parts.append(f"Resumo: {self.history_summary}")

        return "\n".join(parts) if parts else "Novo lead, sem histórico anterior."

    def get_recent_conversation(self, n: int = 5) -> str:
        """Get last N interactions as formatted string."""
        recent = self.interaction_history[-n:] if self.interaction_history else []
        if not recent:
            return "Início da conversa."

        lines = []
        for interaction in recent:
            lines.append(f"Lead: {interaction.user_message}")
            lines.append(f"Assistente: {interaction.ai_response}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "lead_id": self.lead_id,
            "conversation_id": self.conversation_id,
            "conversation_state": self.conversation_state.to_dict(),
            "lead_profile": self.lead_profile.to_dict(),
            "interaction_history": [i.to_dict() for i in self.interaction_history],
            "known_facts": self.known_facts.to_dict(),
            "goal_progress": self.goal_progress.to_dict(),
            "collected_data": self.collected_data,
            "history_summary": self.history_summary,
            "last_topics": self.last_topics,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UnifiedMemory":
        """Create from dictionary (loaded from database)."""
        if not data:
            raise ValueError("Cannot create UnifiedMemory from empty data")

        return cls(
            lead_id=data.get("lead_id", 0),
            conversation_id=data.get("conversation_id", 0),
            conversation_state=ConversationState.from_dict(data.get("conversation_state", {})),
            lead_profile=LeadProfile.from_dict(data.get("lead_profile", {})),
            interaction_history=[Interaction.from_dict(i) for i in data.get("interaction_history", [])],
            known_facts=KnownFacts.from_dict(data.get("known_facts", {})),
            goal_progress=GoalProgress.from_dict(data.get("goal_progress", {})),
            collected_data=data.get("collected_data", {}),
            history_summary=data.get("history_summary", ""),
            last_topics=data.get("last_topics", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def to_lead_memory(self) -> dict[str, Any]:
        """
        Convert to format stored in lead.memory field.

        This is the long-term memory that persists across conversations.
        """
        return {
            "profile": self.lead_profile.to_dict(),
            "facts": self.known_facts.to_dict(),
            "history_summary": self.history_summary,
            "last_topics": self.last_topics,
            "collected_data": self.collected_data,
            "updated_at": self.updated_at
        }

    def to_conversation_context(self) -> dict[str, Any]:
        """
        Convert to format stored in conversation.context field.

        This is the session-specific memory that persists within a conversation.
        """
        return {
            "goal_progress": self.goal_progress.to_dict(),
            "conversation_state": self.conversation_state.to_dict(),
            "flow_position": {
                "current_phase": self.conversation_state.current_phase,
                "triggered_conditions": self.conversation_state.triggered_conditions,
                "pending_actions": self.conversation_state.pending_actions
            },
            "recent_interactions": [i.to_dict() for i in self.interaction_history[-10:]],
            "updated_at": self.updated_at
        }


class MemoryManager:
    """
    Manages loading and saving of UnifiedMemory.

    Handles persistence to:
    - conversation.context (session memory)
    - lead.memory (long-term memory)
    - lead.dados_coletados (collected data)
    """

    def __init__(self, db_service):
        """
        Initialize MemoryManager with database service.

        Args:
            db_service: DatabaseService instance for persistence
        """
        self.db = db_service

    async def load_memory(self, lead_id: int, conversation_id: int) -> UnifiedMemory:
        """
        Load unified memory from database.

        Combines:
        - Lead's long-term memory (lead.memory)
        - Lead's collected data (lead.dados_coletados)
        - Conversation's session memory (conversation.context)

        Args:
            lead_id: Lead ID
            conversation_id: Conversation ID

        Returns:
            UnifiedMemory instance with all data loaded
        """
        # Load lead data
        lead = await self.db.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        # Load conversation data
        conversation = await self.db.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Get memory from lead (if exists)
        lead_memory = getattr(lead, 'memory', {}) or {}

        # Get context from conversation
        conv_context = conversation.context or {}

        # Create unified memory
        memory = UnifiedMemory(
            lead_id=lead_id,
            conversation_id=conversation_id,
            collected_data=lead.dados_coletados or {}
        )

        # Load lead profile from long-term memory
        if "profile" in lead_memory:
            memory.lead_profile = LeadProfile.from_dict(lead_memory["profile"])

        # Load known facts from long-term memory
        if "facts" in lead_memory:
            memory.known_facts = KnownFacts.from_dict(lead_memory["facts"])

        # Load history summary
        memory.history_summary = lead_memory.get("history_summary", "")
        memory.last_topics = lead_memory.get("last_topics", [])

        # Load conversation state from session
        if "conversation_state" in conv_context:
            memory.conversation_state = ConversationState.from_dict(conv_context["conversation_state"])

        # Load goal progress from session
        if "goal_progress" in conv_context:
            memory.goal_progress = GoalProgress.from_dict(conv_context["goal_progress"])

        # Load recent interactions from session
        if "recent_interactions" in conv_context:
            memory.interaction_history = [
                Interaction.from_dict(i) for i in conv_context["recent_interactions"]
            ]

        return memory

    async def save_memory(self, memory: UnifiedMemory) -> None:
        """
        Save unified memory to database.

        Persists to:
        - lead.memory (long-term)
        - lead.dados_coletados (collected data)
        - conversation.context (session)

        Args:
            memory: UnifiedMemory instance to save
        """
        from ..core.supabase_client import supabase

        # Prepare lead memory (long-term)
        lead_memory = memory.to_lead_memory()

        # Prepare conversation context (session)
        conv_context = memory.to_conversation_context()

        # Update lead with memory and collected data
        from ..services.database import LEADS_TABLE
        supabase.table(LEADS_TABLE).update({
            "memory": lead_memory,
            "dados_coletados": memory.collected_data
        }).eq("id", memory.lead_id).execute()

        # Update conversation context
        await self.db.update_conversation_context(
            memory.conversation_id,
            conv_context
        )

    async def save_collected_data(self, memory: UnifiedMemory) -> None:
        """Save only collected data (lighter operation)."""
        from ..core.supabase_client import supabase
        from ..services.database import LEADS_TABLE

        supabase.table(LEADS_TABLE).update({
            "dados_coletados": memory.collected_data
        }).eq("id", memory.lead_id).execute()

    async def save_conversation_state(self, memory: UnifiedMemory) -> None:
        """Save only conversation state (lighter operation)."""
        conv_context = memory.to_conversation_context()
        await self.db.update_conversation_context(
            memory.conversation_id,
            conv_context
        )
