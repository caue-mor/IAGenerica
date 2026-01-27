"""
Message Buffer Service
Accumulates messages before processing to handle multi-message inputs
"""
import logging
import asyncio
from typing import Dict, List, Optional, Callable, Any, Awaitable
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BufferedMessage:
    """Represents a single buffered message"""
    content: str
    timestamp: datetime
    message_type: str = "text"  # text, audio, image, document, video
    media_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationBuffer:
    """Buffer for a single conversation"""
    messages: List[BufferedMessage] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.now)
    processing: bool = False
    timer_task: Optional[asyncio.Task] = None


class MessageBufferService:
    """
    Service for buffering messages before processing.

    This allows accumulating multiple rapid messages (common in WhatsApp)
    before sending them to the AI for processing.
    """

    def __init__(self, debounce_seconds: float = 2.0, max_buffer_size: int = 50):
        """
        Initialize the message buffer service.

        Args:
            debounce_seconds: Time to wait before processing (default: 2 seconds)
            max_buffer_size: Maximum messages to buffer before forcing processing
        """
        self.buffers: Dict[str, ConversationBuffer] = {}
        self.debounce_seconds = debounce_seconds
        self.max_buffer_size = max_buffer_size
        self.callbacks: Dict[str, Callable[[str, Dict[str, Any]], Awaitable[None]]] = {}
        self._lock = asyncio.Lock()

    def get_buffer_key(self, company_id: int, lead_id: int) -> str:
        """
        Generate unique key for a conversation buffer.

        Args:
            company_id: Company ID
            lead_id: Lead ID

        Returns:
            Unique buffer key
        """
        return f"{company_id}:{lead_id}"

    async def add_message(
        self,
        company_id: int,
        lead_id: int,
        content: str,
        message_type: str = "text",
        media_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None
    ) -> bool:
        """
        Add a message to the buffer and schedule processing.

        Args:
            company_id: Company ID
            lead_id: Lead ID
            content: Message content
            message_type: Type of message (text, audio, image, etc.)
            media_url: URL for media messages
            metadata: Additional message metadata
            callback: Async callback to execute when buffer is processed

        Returns:
            True if message was added successfully
        """
        key = self.get_buffer_key(company_id, lead_id)

        async with self._lock:
            # Create buffer if doesn't exist
            if key not in self.buffers:
                self.buffers[key] = ConversationBuffer()

            buffer = self.buffers[key]

            # Cancel existing timer
            if buffer.timer_task and not buffer.timer_task.done():
                buffer.timer_task.cancel()
                try:
                    await buffer.timer_task
                except asyncio.CancelledError:
                    pass

            # Add message to buffer
            buffer.messages.append(BufferedMessage(
                content=content,
                timestamp=datetime.now(),
                message_type=message_type,
                media_url=media_url,
                metadata=metadata or {}
            ))
            buffer.last_activity = datetime.now()

            # Register callback
            if callback:
                self.callbacks[key] = callback

            logger.debug(
                f"Message added to buffer {key}: {content[:50]}... "
                f"(total: {len(buffer.messages)} messages)"
            )

            # Force processing if buffer is full
            if len(buffer.messages) >= self.max_buffer_size:
                logger.info(f"Buffer {key} full, forcing processing")
                buffer.timer_task = asyncio.create_task(self.process_buffer(key))
            else:
                # Schedule processing after debounce
                buffer.timer_task = asyncio.create_task(
                    self._schedule_processing(key)
                )

        return True

    async def _schedule_processing(self, key: str) -> None:
        """
        Wait for debounce period and then process the buffer.

        Args:
            key: Buffer key
        """
        try:
            await asyncio.sleep(self.debounce_seconds)
            await self.process_buffer(key)
        except asyncio.CancelledError:
            logger.debug(f"Processing cancelled for buffer {key}")
            raise

    async def process_buffer(self, key: str) -> Optional[str]:
        """
        Process all messages in a buffer.

        Args:
            key: Buffer key

        Returns:
            Combined message text or None
        """
        async with self._lock:
            if key not in self.buffers:
                return None

            buffer = self.buffers[key]

            if buffer.processing or not buffer.messages:
                return None

            buffer.processing = True

        try:
            # Combine messages
            combined_text = self._combine_messages(buffer.messages)
            metadata = self._collect_metadata(buffer.messages)

            logger.info(
                f"Buffer {key} processing {len(buffer.messages)} messages: "
                f"{combined_text[:100]}..."
            )

            # Execute callback if registered
            if key in self.callbacks:
                try:
                    await self.callbacks[key](combined_text, metadata)
                except Exception as e:
                    logger.exception(f"Error in buffer callback: {e}")

            # Clear processed messages
            async with self._lock:
                buffer.messages.clear()

            return combined_text

        except Exception as e:
            logger.exception(f"Error processing buffer {key}: {e}")
            return None
        finally:
            async with self._lock:
                if key in self.buffers:
                    self.buffers[key].processing = False

    def _combine_messages(self, messages: List[BufferedMessage]) -> str:
        """
        Combine multiple messages into a single text.

        Args:
            messages: List of buffered messages

        Returns:
            Combined message text
        """
        texts = []

        for msg in messages:
            if msg.message_type == "text":
                texts.append(msg.content)
            elif msg.message_type == "audio":
                if msg.content:
                    texts.append(f"[Audio transcrito: {msg.content}]")
                else:
                    texts.append("[Audio enviado]")
            elif msg.message_type == "image":
                if msg.content:
                    texts.append(f"[Imagem: {msg.content}]")
                else:
                    texts.append("[Imagem enviada]")
            elif msg.message_type == "document":
                texts.append(f"[Documento enviado: {msg.content or 'arquivo'}]")
            elif msg.message_type == "video":
                texts.append("[Video enviado]")
            elif msg.message_type == "sticker":
                texts.append("[Sticker enviado]")
            elif msg.message_type == "location":
                texts.append(f"[Localizacao: {msg.content}]")
            elif msg.message_type == "contact":
                texts.append(f"[Contato compartilhado: {msg.content}]")
            else:
                texts.append(msg.content)

        return " ".join(texts)

    def _collect_metadata(self, messages: List[BufferedMessage]) -> Dict[str, Any]:
        """
        Collect metadata from all messages.

        Args:
            messages: List of buffered messages

        Returns:
            Combined metadata
        """
        metadata = {
            "message_count": len(messages),
            "message_types": [],
            "media_urls": [],
            "has_audio": False,
            "has_image": False,
            "has_document": False,
            "first_timestamp": None,
            "last_timestamp": None,
        }

        for msg in messages:
            metadata["message_types"].append(msg.message_type)

            if msg.media_url:
                metadata["media_urls"].append(msg.media_url)

            if msg.message_type == "audio":
                metadata["has_audio"] = True
            elif msg.message_type == "image":
                metadata["has_image"] = True
            elif msg.message_type == "document":
                metadata["has_document"] = True

            if metadata["first_timestamp"] is None:
                metadata["first_timestamp"] = msg.timestamp
            metadata["last_timestamp"] = msg.timestamp

        return metadata

    def clear_buffer(self, company_id: int, lead_id: int) -> bool:
        """
        Clear a conversation buffer.

        Args:
            company_id: Company ID
            lead_id: Lead ID

        Returns:
            True if buffer was cleared
        """
        key = self.get_buffer_key(company_id, lead_id)

        if key in self.buffers:
            buffer = self.buffers[key]

            # Cancel timer if running
            if buffer.timer_task and not buffer.timer_task.done():
                buffer.timer_task.cancel()

            del self.buffers[key]

        if key in self.callbacks:
            del self.callbacks[key]

        logger.debug(f"Buffer {key} cleared")
        return True

    def get_pending_count(self, company_id: int, lead_id: int) -> int:
        """
        Get number of pending messages in a buffer.

        Args:
            company_id: Company ID
            lead_id: Lead ID

        Returns:
            Number of pending messages
        """
        key = self.get_buffer_key(company_id, lead_id)
        if key in self.buffers:
            return len(self.buffers[key].messages)
        return 0

    def is_processing(self, company_id: int, lead_id: int) -> bool:
        """
        Check if a buffer is currently being processed.

        Args:
            company_id: Company ID
            lead_id: Lead ID

        Returns:
            True if buffer is being processed
        """
        key = self.get_buffer_key(company_id, lead_id)
        if key in self.buffers:
            return self.buffers[key].processing
        return False

    async def flush_all(self) -> int:
        """
        Force process all pending buffers.

        Returns:
            Number of buffers processed
        """
        count = 0
        keys = list(self.buffers.keys())

        for key in keys:
            result = await self.process_buffer(key)
            if result:
                count += 1

        logger.info(f"Flushed {count} buffers")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get buffer service statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "active_buffers": len(self.buffers),
            "total_pending_messages": sum(
                len(b.messages) for b in self.buffers.values()
            ),
            "processing_count": sum(
                1 for b in self.buffers.values() if b.processing
            ),
            "debounce_seconds": self.debounce_seconds,
            "max_buffer_size": self.max_buffer_size,
        }


# Singleton instance
message_buffer = MessageBufferService()
