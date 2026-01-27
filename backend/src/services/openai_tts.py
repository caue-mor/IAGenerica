"""
OpenAI Text-to-Speech Service
Uses gpt-4o-mini-tts model with 13 voices and instructions support
"""
import logging
import base64
from typing import Optional
from openai import AsyncOpenAI

from ..core.config import settings

logger = logging.getLogger(__name__)


class OpenAITTSService:
    """
    Service for text-to-speech using OpenAI API.

    Uses gpt-4o-mini-tts model which supports:
    - 13 built-in voices
    - Instructions parameter for tone/style control
    - Multiple output formats
    """

    # All 13 available voices for gpt-4o-mini-tts
    VOICES = {
        # Recommended for best quality
        "marin": "marin",       # High quality (recommended)
        "cedar": "cedar",       # High quality (recommended)

        # Standard voices
        "alloy": "alloy",       # Neutral
        "ash": "ash",           # Clear
        "ballad": "ballad",     # Expressive
        "coral": "coral",       # Warm
        "echo": "echo",         # Male
        "fable": "fable",       # British accent
        "nova": "nova",         # Female (good for Portuguese)
        "onyx": "onyx",         # Male deep
        "sage": "sage",         # Calm
        "shimmer": "shimmer",   # Female soft
        "verse": "verse",       # Versatile
    }

    # Voices available for tts-1 and tts-1-hd models (subset)
    LEGACY_VOICES = {"alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer"}

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice: Optional[str] = None,
        model: Optional[str] = None,
        instructions: Optional[str] = None
    ):
        """
        Initialize the TTS service.

        Args:
            api_key: OpenAI API key
            voice: Default voice to use
            model: TTS model (gpt-4o-mini-tts, tts-1, tts-1-hd)
            instructions: Default instructions for voice style
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.voice = voice or getattr(settings, 'OPENAI_TTS_VOICE', 'coral')
        self.model = model or getattr(settings, 'OPENAI_TTS_MODEL', 'gpt-4o-mini-tts')
        self.instructions = instructions or getattr(
            settings,
            'OPENAI_TTS_INSTRUCTIONS',
            'Fale em português brasileiro de forma natural, amigável e profissional.'
        )
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    async def text_to_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[str] = None,
        instructions: Optional[str] = None,
        response_format: str = "opus"  # opus for WhatsApp PTT
    ) -> Optional[bytes]:
        """
        Convert text to speech audio.

        Args:
            text: Text to convert to speech
            voice: Voice to use (see VOICES dict)
            model: Model to use (gpt-4o-mini-tts, tts-1, tts-1-hd)
            instructions: Instructions for voice style/tone
            response_format: Output format (mp3, opus, aac, flac, wav, pcm)

        Returns:
            Audio bytes or None on error
        """
        if not self.client:
            logger.error("OpenAI client not configured")
            return None

        voice = voice or self.voice
        model = model or self.model
        instructions = instructions or self.instructions

        # Validate voice for model
        if model in ["tts-1", "tts-1-hd"]:
            if voice not in self.LEGACY_VOICES:
                logger.warning(f"Voice {voice} not available for {model}, using nova")
                voice = "nova"
        elif voice not in self.VOICES:
            logger.warning(f"Unknown voice {voice}, using default {self.DEFAULT_VOICE}")
            voice = self.DEFAULT_VOICE

        try:
            logger.info(f"[OpenAI TTS] Generating audio: model={model}, voice={voice}, chars={len(text)}")

            # Build request params
            params = {
                "model": model,
                "voice": voice,
                "input": text,
                "response_format": response_format
            }

            # Add instructions only for gpt-4o-mini-tts
            if model == "gpt-4o-mini-tts" and instructions:
                params["instructions"] = instructions

            response = await self.client.audio.speech.create(**params)

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
        voice: Optional[str] = None,
        instructions: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert text to speech and return as base64 string.

        Args:
            text: Text to convert
            voice: Voice to use
            instructions: Instructions for voice style

        Returns:
            Base64 encoded audio or None on error
        """
        audio_bytes = await self.text_to_speech(text, voice, instructions=instructions)
        if not audio_bytes:
            return None

        return base64.b64encode(audio_bytes).decode("utf-8")

    def is_configured(self) -> bool:
        """Check if OpenAI TTS is properly configured"""
        return bool(self.api_key and self.client)

    def get_available_voices(self) -> dict[str, str]:
        """Get available voices with descriptions"""
        return {
            # Recommended
            "marin": "Marin (Alta qualidade - Recomendada)",
            "cedar": "Cedar (Alta qualidade - Recomendada)",
            "coral": "Coral (Quente e amigável)",

            # Portuguese-friendly
            "nova": "Nova (Feminina - Boa para PT-BR)",
            "shimmer": "Shimmer (Feminina suave)",

            # Male voices
            "echo": "Echo (Masculina)",
            "onyx": "Onyx (Masculina grave)",
            "ash": "Ash (Masculina clara)",

            # Special
            "alloy": "Alloy (Neutra)",
            "fable": "Fable (Sotaque britânico)",
            "sage": "Sage (Calma)",
            "ballad": "Ballad (Expressiva)",
            "verse": "Verse (Versátil)",
        }

    def get_voice_presets(self) -> dict[str, dict]:
        """
        Get voice presets with recommended settings.

        Returns preset configurations for common use cases.
        """
        return {
            "atendimento": {
                "voice": "coral",
                "instructions": "Fale em português brasileiro de forma amigável e profissional. "
                               "Seja acolhedor mas direto. Tom de conversa natural."
            },
            "vendas": {
                "voice": "nova",
                "instructions": "Fale em português brasileiro com entusiasmo e energia. "
                               "Seja persuasivo mas não agressivo. Tom animado e positivo."
            },
            "suporte": {
                "voice": "sage",
                "instructions": "Fale em português brasileiro de forma calma e paciente. "
                               "Seja empático e compreensivo. Tom tranquilizador."
            },
            "formal": {
                "voice": "onyx",
                "instructions": "Fale em português brasileiro de forma formal e profissional. "
                               "Seja sério e respeitoso. Tom corporativo."
            },
            "casual": {
                "voice": "shimmer",
                "instructions": "Fale em português brasileiro de forma descontraída e natural. "
                               "Seja simpático e informal. Tom de conversa entre amigos."
            },
            "rapido": {
                "voice": "alloy",
                "instructions": "Fale em português brasileiro de forma objetiva e rápida. "
                               "Vá direto ao ponto. Velocidade um pouco mais rápida."
            }
        }


# Factory function
def create_openai_tts_service(
    api_key: Optional[str] = None,
    voice: Optional[str] = None,
    instructions: Optional[str] = None
) -> OpenAITTSService:
    """Create OpenAI TTS service instance"""
    return OpenAITTSService(api_key=api_key, voice=voice, instructions=instructions)


# Default instance
openai_tts = OpenAITTSService()
