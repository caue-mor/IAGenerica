"""
Voice service - Eleven Labs TTS + WhatsApp integration.

This service converts text to speech using Eleven Labs API and sends
the audio as a voice message (PTT) via WhatsApp using UAZAPI.

Uses the official elevenlabs Python SDK for reliability.
"""
import io
import uuid
import hashlib
import logging
import subprocess
from typing import Optional, Any, Generator
from datetime import datetime, timedelta

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

# Try to import elevenlabs SDK
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings
    ELEVENLABS_SDK_AVAILABLE = True
except ImportError:
    ELEVENLABS_SDK_AVAILABLE = False
    logger.warning("[TTS] elevenlabs SDK not installed. Run: pip install elevenlabs")


class ElevenLabsTTS:
    """
    Client for Eleven Labs Text-to-Speech API.

    Uses the official elevenlabs Python SDK for converting text to natural-sounding speech.

    Example:
        tts = ElevenLabsTTS(api_key="sk_xxx", voice_id="JBFqnCBsd6RMkjVDRZzb")
        audio = await tts.text_to_speech("Hello world!")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None
    ):
        """
        Initialize Eleven Labs TTS client.

        Args:
            api_key: Eleven Labs API key (sk_xxx format)
            voice_id: Default voice ID to use
            model_id: Model ID (default: eleven_multilingual_v2)
        """
        self.api_key = api_key or settings.ELEVEN_LABS_API_KEY
        self.voice_id = voice_id or settings.ELEVEN_LABS_VOICE_ID
        self.model_id = model_id or settings.ELEVEN_LABS_MODEL_ID
        self._client: Optional[ElevenLabs] = None

        if not self.api_key:
            logger.warning("[TTS] Eleven Labs API key not configured")
        elif not ELEVENLABS_SDK_AVAILABLE:
            logger.error("[TTS] elevenlabs SDK not available")

    @property
    def client(self) -> ElevenLabs:
        """Get or create ElevenLabs client (lazy initialization)."""
        if self._client is None:
            if not ELEVENLABS_SDK_AVAILABLE:
                raise ImportError("elevenlabs SDK not installed. Run: pip install elevenlabs")
            if not self.api_key:
                raise ValueError("Eleven Labs API key not configured")
            self._client = ElevenLabs(api_key=self.api_key)
        return self._client

    def text_to_speech_sync(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_format: str = "mp3_44100_128",
        model_id: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        speed: float = 1.0
    ) -> bytes:
        """
        Convert text to speech audio (synchronous version using official SDK).

        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use (overrides default)
            output_format: Audio format (mp3_44100_128, opus_48000_64, etc.)
            model_id: Model ID to use
            stability: Voice stability (0-1)
            similarity_boost: Voice similarity boost (0-1)
            style: Voice style intensity (0-1)
            speed: Speech speed multiplier

        Returns:
            bytes: Audio data
        """
        voice = voice_id or self.voice_id
        if not voice:
            raise ValueError("Voice ID not configured")

        model = model_id or self.model_id

        logger.info(f"[TTS] Converting {len(text)} characters to speech")
        logger.debug(f"[TTS] Voice: {voice}, Model: {model}, Format: {output_format}")

        # Use official SDK
        audio_generator = self.client.text_to_speech.convert(
            text=text,
            voice_id=voice,
            model_id=model,
            output_format=output_format,
            voice_settings=VoiceSettings(
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                speed=speed,
                use_speaker_boost=True
            ) if ELEVENLABS_SDK_AVAILABLE else None
        )

        # Convert generator to bytes
        audio_data = b"".join(chunk for chunk in audio_generator)

        logger.info(f"[TTS] Generated {len(audio_data)} bytes of audio")
        return audio_data

    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_format: str = "mp3_44100_128",
        model_id: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        speed: float = 1.0
    ) -> bytes:
        """
        Convert text to speech audio (async wrapper).

        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use (overrides default)
            output_format: Audio format (mp3_44100_128, opus_48000_64, etc.)
            model_id: Model ID to use
            stability: Voice stability (0-1)
            similarity_boost: Voice similarity boost (0-1)
            style: Voice style intensity (0-1)
            speed: Speech speed multiplier

        Returns:
            bytes: Audio data
        """
        import asyncio

        # Run sync method in thread pool for async compatibility
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.text_to_speech_sync(
                text=text,
                voice_id=voice_id,
                output_format=output_format,
                model_id=model_id,
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                speed=speed
            )
        )

    def text_to_speech_stream_sync(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_format: str = "mp3_44100_128"
    ) -> Generator[bytes, None, None]:
        """
        Stream text to speech for long texts (synchronous).

        Args:
            text: Text to convert
            voice_id: Voice ID to use
            output_format: Audio format

        Yields:
            bytes: Audio chunks
        """
        voice = voice_id or self.voice_id
        if not voice:
            raise ValueError("Voice ID not configured")

        # Use official SDK streaming
        audio_stream = self.client.text_to_speech.convert(
            text=text,
            voice_id=voice,
            model_id=self.model_id,
            output_format=output_format
        )

        for chunk in audio_stream:
            yield chunk

    async def text_to_speech_stream(
        self,
        text: str,
        voice_id: Optional[str] = None,
        output_format: str = "mp3_44100_128"
    ):
        """
        Stream text to speech for long texts (async wrapper).

        Args:
            text: Text to convert
            voice_id: Voice ID to use
            output_format: Audio format

        Yields:
            bytes: Audio chunks
        """
        import asyncio

        loop = asyncio.get_event_loop()

        # Collect all chunks (SDK doesn't support true async streaming)
        chunks = await loop.run_in_executor(
            None,
            lambda: list(self.text_to_speech_stream_sync(text, voice_id, output_format))
        )

        for chunk in chunks:
            yield chunk

    def get_voices_sync(self) -> list[dict[str, Any]]:
        """Get list of available voices (synchronous)."""
        response = self.client.voices.get_all()
        return [
            {
                "voice_id": v.voice_id,
                "name": v.name,
                "category": v.category,
                "labels": v.labels,
                "preview_url": v.preview_url
            }
            for v in response.voices
        ]

    async def get_voices(self) -> list[dict[str, Any]]:
        """Get list of available voices (async wrapper)."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_voices_sync)

    def get_user_info_sync(self) -> dict[str, Any]:
        """Get user subscription info and usage (synchronous)."""
        user = self.client.user.get_subscription()
        return {
            "character_count": user.character_count,
            "character_limit": user.character_limit,
            "tier": user.tier
        }

    async def get_user_info(self) -> dict[str, Any]:
        """Get user subscription info and usage (async wrapper)."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_user_info_sync)


class AudioConverter:
    """
    Converts audio to WhatsApp-compatible OGG OPUS format.

    WhatsApp voice messages require:
    - Codec: libopus
    - Container: OGG
    - Sample rate: 48000 Hz
    - Channels: 1 (mono)
    - Bitrate: 32k minimum
    """

    @staticmethod
    def convert_to_whatsapp_ogg(
        audio_data: bytes,
        input_format: str = "opus"
    ) -> bytes:
        """
        Convert audio to WhatsApp-compatible OGG OPUS format using FFmpeg.

        Args:
            audio_data: Input audio bytes
            input_format: Input format (opus, mp3, wav)

        Returns:
            bytes: OGG OPUS audio data

        Raises:
            RuntimeError: If FFmpeg conversion fails
        """
        logger.info(f"[CONVERTER] Converting {len(audio_data)} bytes from {input_format} to OGG OPUS")

        # FFmpeg command for WhatsApp-compatible OGG OPUS
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-f", input_format,  # Input format
            "-i", "pipe:0",  # Read from stdin
            "-c:a", "libopus",  # Opus codec
            "-b:a", "32k",  # Bitrate
            "-ar", "48000",  # Sample rate (required by WhatsApp)
            "-ac", "1",  # Mono
            "-application", "voip",  # Optimize for voice
            "-vbr", "on",  # Variable bitrate
            "-compression_level", "10",  # Max compression
            "-f", "ogg",  # Output format
            "pipe:1"  # Write to stdout
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            output, error = process.communicate(input=audio_data, timeout=30)

            if process.returncode != 0:
                error_msg = error.decode() if error else "Unknown error"
                logger.error(f"[CONVERTER] FFmpeg error: {error_msg}")
                raise RuntimeError(f"FFmpeg conversion failed: {error_msg}")

            logger.info(f"[CONVERTER] Converted to {len(output)} bytes OGG OPUS")
            return output

        except subprocess.TimeoutExpired:
            process.kill()
            raise RuntimeError("FFmpeg conversion timed out")

    @staticmethod
    def is_ffmpeg_available() -> bool:
        """Check if FFmpeg is installed and available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False


class AudioStorage:
    """
    Storage service for audio files using Supabase Storage.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        bucket: str = "audio-messages"
    ):
        """
        Initialize audio storage.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service key
            bucket: Storage bucket name
        """
        self.supabase_url = supabase_url or settings.SUPABASE_URL
        self.supabase_key = supabase_key or settings.SUPABASE_KEY
        self.bucket = bucket

    async def upload_audio(
        self,
        audio_data: bytes,
        filename: Optional[str] = None,
        content_type: str = "audio/ogg"
    ) -> str:
        """
        Upload audio to Supabase Storage.

        Args:
            audio_data: Audio bytes to upload
            filename: Custom filename (auto-generated if not provided)
            content_type: MIME type of the audio

        Returns:
            str: Public URL of the uploaded file
        """
        if not filename:
            filename = f"{uuid.uuid4()}.ogg"

        # Ensure filename has correct extension
        if not filename.endswith(".ogg"):
            filename = f"{filename}.ogg"

        url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{filename}"

        headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": content_type,
            "x-upsert": "true"  # Overwrite if exists
        }

        logger.info(f"[STORAGE] Uploading {len(audio_data)} bytes as {filename}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                content=audio_data,
                headers=headers
            )

            if response.status_code not in [200, 201]:
                logger.error(f"[STORAGE] Upload failed: {response.status_code} - {response.text}")
                raise RuntimeError(f"Failed to upload audio: {response.text}")

        # Return public URL
        public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket}/{filename}"
        logger.info(f"[STORAGE] Uploaded successfully: {public_url}")

        return public_url

    async def create_signed_url(
        self,
        filename: str,
        expires_in: int = 3600
    ) -> str:
        """
        Create a signed URL with expiration.

        Args:
            filename: File name in storage
            expires_in: Expiration time in seconds

        Returns:
            str: Signed URL
        """
        url = f"{self.supabase_url}/storage/v1/object/sign/{self.bucket}/{filename}"

        headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }

        payload = {"expiresIn": expires_in}

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                raise RuntimeError(f"Failed to create signed URL: {response.text}")

            data = response.json()
            signed_path = data.get("signedURL", "")

            return f"{self.supabase_url}/storage/v1{signed_path}"


class VoiceService:
    """
    Complete voice service: Text-to-Speech + Storage + WhatsApp delivery.

    This service orchestrates the full flow:
    1. Convert text to speech using Eleven Labs
    2. Convert audio format for WhatsApp compatibility
    3. Upload audio to storage
    4. Send voice message via WhatsApp
    """

    def __init__(
        self,
        tts: Optional[ElevenLabsTTS] = None,
        storage: Optional[AudioStorage] = None,
        whatsapp_service: Optional[Any] = None
    ):
        """
        Initialize voice service.

        Args:
            tts: Eleven Labs TTS client
            storage: Audio storage service
            whatsapp_service: WhatsApp service for sending messages
        """
        self.tts = tts or ElevenLabsTTS()
        self.storage = storage or AudioStorage()
        self._whatsapp = whatsapp_service
        self._audio_cache: dict[str, tuple[str, datetime]] = {}

    @property
    def whatsapp(self):
        """Lazy load WhatsApp service to avoid circular imports."""
        if self._whatsapp is None:
            from .whatsapp import WhatsAppService
            self._whatsapp = WhatsAppService()
        return self._whatsapp

    def _get_text_hash(self, text: str, voice_id: str) -> str:
        """Generate hash for text + voice combination."""
        content = f"{text}:{voice_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def send_voice_message(
        self,
        phone: str,
        text: str,
        token: Optional[str] = None,
        voice_id: Optional[str] = None,
        also_send_text: bool = False,
        use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Convert text to speech and send as WhatsApp voice message.

        Full pipeline:
        1. Check cache for existing audio
        2. Convert text to speech (Eleven Labs)
        3. Convert to OGG OPUS (FFmpeg)
        4. Upload to storage
        5. Send as PTT via WhatsApp

        Args:
            phone: Recipient phone number
            text: Text to convert to speech
            token: WhatsApp token (optional, uses default)
            voice_id: Override voice ID
            also_send_text: Also send the text as a regular message
            use_cache: Use cached audio for repeated messages

        Returns:
            dict: Result with success status, audio_url, etc.
        """
        voice = voice_id or self.tts.voice_id
        text_hash = self._get_text_hash(text, voice)

        try:
            # Check cache
            if use_cache and text_hash in self._audio_cache:
                cached_url, cached_time = self._audio_cache[text_hash]
                if datetime.utcnow() - cached_time < timedelta(hours=1):
                    logger.info(f"[VOICE] Using cached audio: {text_hash}")
                    result = await self.whatsapp.send_ptt(phone, cached_url, token)
                    if also_send_text:
                        await self.whatsapp.send_text(phone, text, token=token)
                    return {
                        "success": result.get("success", False),
                        "audio_url": cached_url,
                        "cached": True,
                        "text_length": len(text),
                        "whatsapp_response": result
                    }

            logger.info(f"[VOICE] Starting TTS for {len(text)} characters")

            # 1. Convert text to speech (using MP3 - most reliable format)
            audio_data = await self.tts.text_to_speech(
                text=text,
                voice_id=voice,
                output_format="mp3_44100_128"  # Default SDK format
            )

            logger.info(f"[VOICE] TTS complete: {len(audio_data)} bytes")

            # 2. Convert MP3 to WhatsApp format (OGG OPUS)
            whatsapp_audio = AudioConverter.convert_to_whatsapp_ogg(
                audio_data,
                input_format="mp3"  # Input is MP3 from Eleven Labs
            )

            logger.info(f"[VOICE] Converted to OGG: {len(whatsapp_audio)} bytes")

            # 3. Upload to storage
            filename = f"voice/{text_hash}.ogg"
            audio_url = await self.storage.upload_audio(
                whatsapp_audio,
                filename=filename
            )

            logger.info(f"[VOICE] Uploaded: {audio_url}")

            # 4. Cache the URL
            if use_cache:
                self._audio_cache[text_hash] = (audio_url, datetime.utcnow())

            # 5. Send via WhatsApp
            result = await self.whatsapp.send_ptt(phone, audio_url, token)

            logger.info(f"[VOICE] Sent successfully to {phone}")

            # 6. Optionally send text too
            if also_send_text:
                await self.whatsapp.send_text(phone, text, token=token)

            return {
                "success": result.get("success", False),
                "audio_url": audio_url,
                "cached": False,
                "text_length": len(text),
                "audio_size": len(whatsapp_audio),
                "whatsapp_response": result
            }

        except Exception as e:
            logger.error(f"[VOICE] Error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text_length": len(text)
            }

    async def send_voice_with_fallback(
        self,
        phone: str,
        text: str,
        token: Optional[str] = None,
        voice_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Send voice message with automatic fallback to text on failure.

        Args:
            phone: Recipient phone number
            text: Message text
            token: WhatsApp token
            voice_id: Override voice ID

        Returns:
            dict: Result with success status and delivery method
        """
        try:
            result = await self.send_voice_message(
                phone=phone,
                text=text,
                token=token,
                voice_id=voice_id,
                also_send_text=False
            )

            if result.get("success"):
                return {
                    **result,
                    "delivery_method": "voice"
                }

            # Fallback to text
            logger.warning(f"[VOICE] Voice failed, falling back to text")
            text_result = await self.whatsapp.send_text(phone, text, token=token)

            return {
                "success": text_result.get("success", False),
                "delivery_method": "text_fallback",
                "voice_error": result.get("error"),
                "whatsapp_response": text_result
            }

        except Exception as e:
            logger.error(f"[VOICE] Complete failure: {str(e)}")

            # Last resort: try text
            try:
                text_result = await self.whatsapp.send_text(phone, text, token=token)
                return {
                    "success": text_result.get("success", False),
                    "delivery_method": "text_fallback",
                    "voice_error": str(e),
                    "whatsapp_response": text_result
                }
            except Exception as text_error:
                return {
                    "success": False,
                    "delivery_method": "failed",
                    "voice_error": str(e),
                    "text_error": str(text_error)
                }

    def clear_cache(self):
        """Clear the audio cache."""
        self._audio_cache.clear()
        logger.info("[VOICE] Cache cleared")

    async def check_health(self) -> dict[str, Any]:
        """
        Check health of all voice service components.

        Returns:
            dict: Health status of TTS, FFmpeg, Storage
        """
        health = {
            "tts_configured": bool(self.tts.api_key and self.tts.voice_id),
            "ffmpeg_available": AudioConverter.is_ffmpeg_available(),
            "storage_configured": bool(self.storage.supabase_url),
            "voice_enabled": settings.VOICE_ENABLED
        }

        # Test TTS if configured
        if health["tts_configured"]:
            try:
                user_info = await self.tts.get_user_info()
                health["tts_status"] = "ok"
                health["tts_characters_remaining"] = user_info.get("character_count", 0)
            except Exception as e:
                health["tts_status"] = "error"
                health["tts_error"] = str(e)

        health["overall"] = all([
            health["tts_configured"],
            health["ffmpeg_available"],
            health["storage_configured"]
        ])

        return health


# Singleton instance
_voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    """Get or create the voice service singleton."""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service


# Export
__all__ = [
    "ElevenLabsTTS",
    "AudioConverter",
    "AudioStorage",
    "VoiceService",
    "get_voice_service"
]
