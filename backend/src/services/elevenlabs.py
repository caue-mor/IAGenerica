"""
ElevenLabs Text-to-Speech Service
Converts text responses to audio for WhatsApp voice messages
"""
import logging
import httpx
import base64
import tempfile
import os
from typing import Optional, Any
from pathlib import Path

from ..core.config import settings

logger = logging.getLogger(__name__)


class ElevenLabsService:
    """Service for text-to-speech using ElevenLabs API"""

    BASE_URL = "https://api.elevenlabs.io/v1"

    # Default voices (multilingual)
    VOICES = {
        "rachel": "21m00Tcm4TlvDq8ikWAM",  # Female, calm
        "drew": "29vD33N1CtxCmqQRPOHJ",     # Male, confident
        "clyde": "2EiwWnXFnvU5JabPnv8n",   # Male, friendly
        "paul": "5Q0t7uMcjvnagumLfvZi",    # Male, news anchor
        "domi": "AZnzlk1XvdvUeBnXmlld",    # Female, confident
        "bella": "EXAVITQu4vr4xnSDxMaL",   # Female, soft
        "antoni": "ErXwobaYiN019PkySvjV",  # Male, friendly
        "elli": "MF3mGyEYCl7XYWbV9V6O",    # Female, young
        "josh": "TxGEqnHWrfWFTfGW9XjX",    # Male, deep
        "arnold": "VR6AewLTigWG4xSOukaG",  # Male, gruff
        "adam": "pNInz6obpgDQGcFmaJgB",    # Male, deep
        "sam": "yoZ06aMxZJJ28mfd3POQ",     # Male, raspy
    }

    # Portuguese/Brazilian voices
    PORTUGUESE_VOICES = {
        "default": "21m00Tcm4TlvDq8ikWAM",  # Rachel works well with Portuguese
    }

    # Output formats optimized for different uses
    OUTPUT_FORMATS = {
        "mp3_44100_128": "mp3_44100_128",      # High quality MP3
        "mp3_44100_64": "mp3_44100_64",        # Standard MP3
        "opus_48000_64": "opus_48000_64",      # Best for WhatsApp PTT
        "pcm_16000": "pcm_16000",              # Raw PCM
        "pcm_22050": "pcm_22050",              # Raw PCM higher quality
        "pcm_24000": "pcm_24000",              # Raw PCM
        "pcm_44100": "pcm_44100",              # Raw PCM highest
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        output_format: Optional[str] = None
    ):
        self.api_key = api_key or settings.ELEVEN_LABS_API_KEY
        self.voice_id = voice_id or settings.ELEVEN_LABS_VOICE_ID or self.VOICES["rachel"]
        self.model_id = model_id or settings.ELEVEN_LABS_MODEL_ID
        self.output_format = output_format or settings.VOICE_OUTPUT_FORMAT

    def _get_headers(self) -> dict[str, str]:
        """Get request headers"""
        return {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key or ""
        }

    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True
    ) -> Optional[bytes]:
        """
        Convert text to speech audio.

        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use (default: configured voice)
            model_id: Model ID to use (default: eleven_multilingual_v2)
            stability: Voice stability (0-1)
            similarity_boost: Voice similarity boost (0-1)
            style: Style exaggeration (0-1)
            use_speaker_boost: Enable speaker boost

        Returns:
            Audio bytes (MP3/OGG format) or None on error
        """
        if not self.api_key:
            logger.error("ElevenLabs API key not configured")
            return None

        voice_id = voice_id or self.voice_id
        model_id = model_id or self.model_id

        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"

        # Add output format to URL if not default
        if self.output_format and self.output_format != "mp3_44100_128":
            url += f"?output_format={self.output_format}"

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": use_speaker_boost
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=60  # TTS can take time for long texts
                )

                if response.status_code == 200:
                    logger.info(f"TTS generated successfully for {len(text)} chars")
                    return response.content
                else:
                    logger.error(f"ElevenLabs error: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
            return None

    async def text_to_speech_stream(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None
    ):
        """
        Stream text to speech (for real-time playback).

        Yields audio chunks as they're generated.
        """
        if not self.api_key:
            logger.error("ElevenLabs API key not configured")
            return

        voice_id = voice_id or self.voice_id
        model_id = model_id or self.model_id

        url = f"{self.BASE_URL}/text-to-speech/{voice_id}/stream"

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=60
                ) as response:
                    if response.status_code == 200:
                        async for chunk in response.aiter_bytes():
                            yield chunk
                    else:
                        logger.error(f"ElevenLabs stream error: {response.status_code}")

        except Exception as e:
            logger.error(f"Error streaming TTS: {e}")

    async def save_to_file(
        self,
        text: str,
        filepath: Optional[str] = None,
        voice_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert text to speech and save to file.

        Args:
            text: Text to convert
            filepath: Output file path (default: temp file)
            voice_id: Voice ID to use

        Returns:
            File path or None on error
        """
        audio_bytes = await self.text_to_speech(text, voice_id)
        if not audio_bytes:
            return None

        # Determine extension based on output format
        ext = ".ogg" if "opus" in self.output_format else ".mp3"

        if not filepath:
            # Create temp file
            fd, filepath = tempfile.mkstemp(suffix=ext)
            os.close(fd)

        try:
            with open(filepath, "wb") as f:
                f.write(audio_bytes)
            logger.info(f"Audio saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            return None

    async def get_audio_base64(
        self,
        text: str,
        voice_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert text to speech and return as base64 string.

        Useful for sending via APIs that accept base64 audio.

        Args:
            text: Text to convert
            voice_id: Voice ID to use

        Returns:
            Base64 encoded audio or None on error
        """
        audio_bytes = await self.text_to_speech(text, voice_id)
        if not audio_bytes:
            return None

        return base64.b64encode(audio_bytes).decode("utf-8")

    async def get_voices(self) -> dict[str, Any]:
        """
        Get available voices from ElevenLabs.

        Returns:
            Dict with voices info
        """
        if not self.api_key:
            return {"success": False, "error": "API key not configured"}

        url = f"{self.BASE_URL}/voices"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "voices": data.get("voices", [])
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_user_info(self) -> dict[str, Any]:
        """
        Get user subscription info (remaining characters, etc).

        Returns:
            Dict with user info
        """
        if not self.api_key:
            return {"success": False, "error": "API key not configured"}

        url = f"{self.BASE_URL}/user/subscription"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "character_count": data.get("character_count"),
                        "character_limit": data.get("character_limit"),
                        "tier": data.get("tier"),
                        "data": data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_configured(self) -> bool:
        """Check if ElevenLabs is properly configured"""
        return bool(self.api_key)


# Factory function
def create_elevenlabs_service(
    api_key: Optional[str] = None,
    voice_id: Optional[str] = None
) -> ElevenLabsService:
    """Create ElevenLabs service instance"""
    return ElevenLabsService(api_key=api_key, voice_id=voice_id)


# Default instance
elevenlabs = ElevenLabsService()
