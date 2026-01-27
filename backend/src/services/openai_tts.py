"""
OpenAI Text-to-Speech Service
Alternative TTS that works from any server without IP restrictions
"""
import logging
import base64
from typing import Optional
from openai import AsyncOpenAI

from ..core.config import settings

logger = logging.getLogger(__name__)


class OpenAITTSService:
    """Service for text-to-speech using OpenAI API"""

    # Available voices
    VOICES = {
        "alloy": "alloy",       # Neutral
        "echo": "echo",         # Male
        "fable": "fable",       # British
        "onyx": "onyx",         # Male deep
        "nova": "nova",         # Female (good for Portuguese)
        "shimmer": "shimmer",   # Female soft
    }

    # Default voice for Portuguese
    DEFAULT_VOICE = "nova"

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice: Optional[str] = None,
        model: str = "tts-1"
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.voice = voice or self.DEFAULT_VOICE
        self.model = model  # tts-1 (faster) or tts-1-hd (better quality)
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    async def text_to_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[str] = None,
        response_format: str = "opus"  # opus for WhatsApp PTT
    ) -> Optional[bytes]:
        """
        Convert text to speech audio.

        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: Model to use (tts-1 or tts-1-hd)
            response_format: Output format (mp3, opus, aac, flac, wav, pcm)

        Returns:
            Audio bytes or None on error
        """
        if not self.client:
            logger.error("OpenAI client not configured")
            return None

        voice = voice or self.voice
        model = model or self.model

        # Validate voice
        if voice not in self.VOICES:
            logger.warning(f"Unknown voice {voice}, using default {self.DEFAULT_VOICE}")
            voice = self.DEFAULT_VOICE

        try:
            logger.info(f"[OpenAI TTS] Generating audio for {len(text)} chars with voice={voice}")

            response = await self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                response_format=response_format
            )

            # Get audio bytes
            audio_bytes = response.content

            logger.info(f"[OpenAI TTS] Generated {len(audio_bytes)} bytes of audio")
            return audio_bytes

        except Exception as e:
            logger.error(f"[OpenAI TTS] Error: {e}")
            return None

    async def get_audio_base64(
        self,
        text: str,
        voice: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert text to speech and return as base64 string.

        Args:
            text: Text to convert
            voice: Voice to use

        Returns:
            Base64 encoded audio or None on error
        """
        audio_bytes = await self.text_to_speech(text, voice)
        if not audio_bytes:
            return None

        return base64.b64encode(audio_bytes).decode("utf-8")

    def is_configured(self) -> bool:
        """Check if OpenAI TTS is properly configured"""
        return bool(self.api_key and self.client)

    def get_available_voices(self) -> dict[str, str]:
        """Get available voices"""
        return {
            "nova": "Nova (Feminina - Recomendada para PT)",
            "shimmer": "Shimmer (Feminina suave)",
            "alloy": "Alloy (Neutra)",
            "echo": "Echo (Masculina)",
            "fable": "Fable (Britânica)",
            "onyx": "Onyx (Masculina grave)",
        }


# Factory function
def create_openai_tts_service(
    api_key: Optional[str] = None,
    voice: Optional[str] = None
) -> OpenAITTSService:
    """Create OpenAI TTS service instance"""
    return OpenAITTSService(api_key=api_key, voice=voice)


# Default instance
openai_tts = OpenAITTSService()
