"""
Audio Transcription Service - OpenAI Whisper integration
Transcription of audio files and URLs for WhatsApp voice messages
"""
import logging
import tempfile
import os
from typing import Optional
import httpx
from openai import OpenAI

from ..core.config import settings

logger = logging.getLogger(__name__)


class AudioTranscriptionService:
    """Service for transcribing audio using OpenAI Whisper API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the audio transcription service.

        Args:
            api_key: OpenAI API key (optional, defaults to settings)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            if not self.api_key:
                raise ValueError("OpenAI API key not configured")
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    async def transcribe_url(
        self,
        audio_url: str,
        language: str = "pt",
        prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Transcribe audio from a URL.

        Args:
            audio_url: URL of the audio file
            language: Language code (default: Portuguese)
            prompt: Optional prompt to guide transcription

        Returns:
            Transcribed text or None if failed
        """
        temp_path = None
        try:
            logger.info(f"Downloading audio from URL: {audio_url[:100]}...")

            # Download the audio file
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(audio_url)
                response.raise_for_status()

            # Determine file extension from content-type or URL
            content_type = response.headers.get("content-type", "")
            extension = self._get_extension(content_type, audio_url)

            # Save to temporary file
            with tempfile.NamedTemporaryFile(
                suffix=extension,
                delete=False
            ) as f:
                f.write(response.content)
                temp_path = f.name

            logger.debug(f"Audio saved to temp file: {temp_path}")

            # Transcribe
            result = await self.transcribe_file(temp_path, language, prompt)
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading audio: {e.response.status_code}")
            return None
        except Exception as e:
            logger.exception(f"Error transcribing audio from URL: {e}")
            return None
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")

    async def transcribe_file(
        self,
        file_path: str,
        language: str = "pt",
        prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Transcribe audio from a local file.

        Args:
            file_path: Path to the audio file
            language: Language code (default: Portuguese)
            prompt: Optional prompt to guide transcription

        Returns:
            Transcribed text or None if failed
        """
        try:
            logger.info(f"Transcribing audio file: {file_path}")

            with open(file_path, "rb") as audio_file:
                kwargs = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "language": language,
                }
                if prompt:
                    kwargs["prompt"] = prompt

                transcription = self.client.audio.transcriptions.create(**kwargs)

            text = transcription.text.strip()
            logger.info(f"Audio transcribed successfully: {text[:100]}...")
            return text

        except FileNotFoundError:
            logger.error(f"Audio file not found: {file_path}")
            return None
        except Exception as e:
            logger.exception(f"Error transcribing audio file: {e}")
            return None

    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.ogg",
        language: str = "pt",
        prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Transcribe audio from bytes.

        Args:
            audio_bytes: Raw audio data
            filename: Filename with extension for format detection
            language: Language code (default: Portuguese)
            prompt: Optional prompt to guide transcription

        Returns:
            Transcribed text or None if failed
        """
        temp_path = None
        try:
            # Get extension from filename
            extension = os.path.splitext(filename)[1] or ".ogg"

            # Save to temporary file
            with tempfile.NamedTemporaryFile(
                suffix=extension,
                delete=False
            ) as f:
                f.write(audio_bytes)
                temp_path = f.name

            # Transcribe
            return await self.transcribe_file(temp_path, language, prompt)

        except Exception as e:
            logger.exception(f"Error transcribing audio bytes: {e}")
            return None
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    def _get_extension(self, content_type: str, url: str) -> str:
        """
        Determine file extension from content-type or URL.

        Args:
            content_type: HTTP content-type header
            url: Original URL

        Returns:
            File extension including dot
        """
        # Map content-types to extensions
        type_map = {
            "audio/ogg": ".ogg",
            "audio/opus": ".opus",
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/mp4": ".m4a",
            "audio/m4a": ".m4a",
            "audio/wav": ".wav",
            "audio/wave": ".wav",
            "audio/webm": ".webm",
            "audio/x-wav": ".wav",
        }

        # Try content-type first
        for mime, ext in type_map.items():
            if mime in content_type.lower():
                return ext

        # Try URL extension
        url_lower = url.lower()
        for ext in [".ogg", ".opus", ".mp3", ".m4a", ".wav", ".webm"]:
            if url_lower.endswith(ext):
                return ext

        # Default to ogg (WhatsApp voice messages)
        return ".ogg"

    async def is_audio_processable(self, audio_url: str) -> bool:
        """
        Check if an audio URL can be processed.

        Args:
            audio_url: URL to check

        Returns:
            True if the audio can be processed
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.head(audio_url)
                if response.status_code != 200:
                    return False

                content_type = response.headers.get("content-type", "")
                content_length = int(response.headers.get("content-length", 0))

                # Check if it's an audio file
                if not content_type.startswith("audio/"):
                    return False

                # Check file size (max 25MB for Whisper)
                max_size = 25 * 1024 * 1024
                if content_length > max_size:
                    logger.warning(f"Audio file too large: {content_length} bytes")
                    return False

                return True

        except Exception as e:
            logger.warning(f"Could not verify audio URL: {e}")
            return False


# Singleton instance
audio_transcription = AudioTranscriptionService()
