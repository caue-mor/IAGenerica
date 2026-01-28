"""
PostgreSQL Checkpointer for LangGraph state persistence.

This module provides a PostgreSQL-backed checkpointer that replaces
the default MemorySaver, enabling state persistence across server restarts.
"""
from __future__ import annotations

import json
import pickle
import base64
from datetime import datetime
from typing import Any, Optional, Iterator, Tuple, List
from contextlib import contextmanager

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    SerializerProtocol
)
from langchain_core.runnables import RunnableConfig

from ..core.supabase_client import supabase
from ..services.database import TABLE_PREFIX


# Table name for checkpoints
CHECKPOINTS_TABLE = f"{TABLE_PREFIX}checkpoints"


class SupabaseCheckpointSaver(BaseCheckpointSaver):
    """
    Checkpoint saver using Supabase/PostgreSQL for persistence.

    Stores LangGraph state checkpoints in PostgreSQL, allowing
    conversations to persist across server restarts.

    Table schema required:
    CREATE TABLE iagenericanexma_checkpoints (
        id SERIAL PRIMARY KEY,
        thread_id TEXT NOT NULL,
        checkpoint_ns TEXT DEFAULT '',
        checkpoint_id TEXT NOT NULL,
        parent_checkpoint_id TEXT,
        checkpoint JSONB NOT NULL,
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(thread_id, checkpoint_ns, checkpoint_id)
    );

    CREATE INDEX idx_checkpoints_thread ON iagenericanexma_checkpoints(thread_id);
    CREATE INDEX idx_checkpoints_thread_ns ON iagenericanexma_checkpoints(thread_id, checkpoint_ns);
    """

    def __init__(self, serde: Optional[SerializerProtocol] = None):
        """Initialize with optional serializer."""
        super().__init__(serde=serde)

    def _serialize_checkpoint(self, checkpoint: Checkpoint) -> dict[str, Any]:
        """Serialize checkpoint to JSON-compatible dict."""
        # Convert checkpoint to dict and handle non-serializable objects
        cp_dict = dict(checkpoint)

        # Handle channel_values specially (may contain LangChain messages)
        if "channel_values" in cp_dict:
            channel_values = cp_dict["channel_values"]
            serialized_channels = {}
            for key, value in channel_values.items():
                try:
                    # Try JSON serialization first
                    json.dumps(value)
                    serialized_channels[key] = {"type": "json", "data": value}
                except (TypeError, ValueError):
                    # Fall back to pickle + base64 for complex objects
                    pickled = pickle.dumps(value)
                    serialized_channels[key] = {
                        "type": "pickle",
                        "data": base64.b64encode(pickled).decode("utf-8")
                    }
            cp_dict["channel_values"] = serialized_channels

        return cp_dict

    def _deserialize_checkpoint(self, data: dict[str, Any]) -> Checkpoint:
        """Deserialize checkpoint from stored dict."""
        # Handle channel_values
        if "channel_values" in data:
            channel_values = data["channel_values"]
            deserialized_channels = {}
            for key, value in channel_values.items():
                if isinstance(value, dict) and "type" in value:
                    if value["type"] == "pickle":
                        pickled = base64.b64decode(value["data"])
                        deserialized_channels[key] = pickle.loads(pickled)
                    else:
                        deserialized_channels[key] = value["data"]
                else:
                    deserialized_channels[key] = value
            data["channel_values"] = deserialized_channels

        return Checkpoint(**data)

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Get a checkpoint tuple by config."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id")

        try:
            query = supabase.table(CHECKPOINTS_TABLE).select("*").eq(
                "thread_id", thread_id
            ).eq("checkpoint_ns", checkpoint_ns)

            if checkpoint_id:
                query = query.eq("checkpoint_id", checkpoint_id)
            else:
                # Get latest checkpoint
                query = query.order("created_at", desc=True).limit(1)

            response = query.execute()

            if not response.data:
                return None

            row = response.data[0]
            checkpoint = self._deserialize_checkpoint(row["checkpoint"])
            metadata = CheckpointMetadata(**row.get("metadata", {})) if row.get("metadata") else CheckpointMetadata()

            # Build parent config if exists
            parent_config = None
            if row.get("parent_checkpoint_id"):
                parent_config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row["parent_checkpoint_id"]
                    }
                }

            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row["checkpoint_id"]
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config
            )

        except Exception as e:
            print(f"Error getting checkpoint: {e}")
            return None

    def list(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints matching the config."""
        if not config:
            return

        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        try:
            query = supabase.table(CHECKPOINTS_TABLE).select("*").eq(
                "thread_id", thread_id
            ).eq("checkpoint_ns", checkpoint_ns).order("created_at", desc=True)

            if before:
                before_id = before["configurable"].get("checkpoint_id")
                if before_id:
                    # Get the created_at of the before checkpoint
                    before_response = supabase.table(CHECKPOINTS_TABLE).select(
                        "created_at"
                    ).eq("checkpoint_id", before_id).limit(1).execute()
                    if before_response.data:
                        query = query.lt("created_at", before_response.data[0]["created_at"])

            if limit:
                query = query.limit(limit)

            response = query.execute()

            for row in response.data or []:
                checkpoint = self._deserialize_checkpoint(row["checkpoint"])
                metadata = CheckpointMetadata(**row.get("metadata", {})) if row.get("metadata") else CheckpointMetadata()

                parent_config = None
                if row.get("parent_checkpoint_id"):
                    parent_config = {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": row["parent_checkpoint_id"]
                        }
                    }

                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": row["checkpoint_id"]
                        }
                    },
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config=parent_config
                )

        except Exception as e:
            print(f"Error listing checkpoints: {e}")

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, Any]
    ) -> RunnableConfig:
        """Store a checkpoint."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        try:
            serialized_checkpoint = self._serialize_checkpoint(checkpoint)
            metadata_dict = dict(metadata) if metadata else {}

            # Upsert checkpoint
            supabase.table(CHECKPOINTS_TABLE).upsert({
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
                "parent_checkpoint_id": parent_checkpoint_id,
                "checkpoint": serialized_checkpoint,
                "metadata": metadata_dict,
                "created_at": datetime.utcnow().isoformat()
            }, on_conflict="thread_id,checkpoint_ns,checkpoint_id").execute()

            return {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id
                }
            }

        except Exception as e:
            print(f"Error saving checkpoint: {e}")
            raise

    def put_writes(
        self,
        config: RunnableConfig,
        writes: List[Tuple[str, Any]],
        task_id: str
    ) -> None:
        """Store intermediate writes. Not implemented for basic persistence."""
        # This is used for more advanced checkpointing scenarios
        # For basic persistence, we can skip this
        pass

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Async version of get_tuple."""
        return self.get_tuple(config)

    async def alist(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None
    ):
        """Async version of list."""
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, Any]
    ) -> RunnableConfig:
        """Async version of put."""
        return self.put(config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: List[Tuple[str, Any]],
        task_id: str
    ) -> None:
        """Async version of put_writes."""
        self.put_writes(config, writes, task_id)


def create_checkpointer() -> SupabaseCheckpointSaver:
    """Create a Supabase checkpointer instance."""
    return SupabaseCheckpointSaver()


# SQL migration for creating the checkpoints table
CHECKPOINT_TABLE_MIGRATION = """
-- Create checkpoints table for LangGraph state persistence
CREATE TABLE IF NOT EXISTS iagenericanexma_checkpoints (
    id SERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(thread_id, checkpoint_ns, checkpoint_id)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread
    ON iagenericanexma_checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_ns
    ON iagenericanexma_checkpoints(thread_id, checkpoint_ns);
CREATE INDEX IF NOT EXISTS idx_checkpoints_created
    ON iagenericanexma_checkpoints(created_at DESC);

-- Add memory column to leads table for long-term memory
ALTER TABLE iagenericanexma_leads
ADD COLUMN IF NOT EXISTS memory JSONB DEFAULT '{}';

-- Create index for memory queries
CREATE INDEX IF NOT EXISTS idx_leads_memory
    ON iagenericanexma_leads USING GIN (memory);

COMMENT ON TABLE iagenericanexma_checkpoints IS 'LangGraph state checkpoints for conversation persistence';
COMMENT ON COLUMN iagenericanexma_leads.memory IS 'Long-term AI memory for the lead';
"""


def get_migration_sql() -> str:
    """Get the SQL migration for checkpoints table."""
    return CHECKPOINT_TABLE_MIGRATION
