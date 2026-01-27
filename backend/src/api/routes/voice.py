"""
Voice API routes - Test and health endpoints for voice service.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from ...services.voice import get_voice_service, VoiceService
from ...services.openai_tts import openai_tts, create_openai_tts_service
from ...core.config import settings

router = APIRouter(prefix="/voice", tags=["voice"])


class VoiceTestRequest(BaseModel):
    """Request model for voice test endpoint."""
    text: str
    phone: str
    voice_id: Optional[str] = None
    also_send_text: bool = False


class VoiceSynthesizeRequest(BaseModel):
    """Request model for synthesize-only endpoint."""
    text: str
    voice_id: Optional[str] = None


@router.get("/health")
async def voice_health():
    """
    Check health status of voice service components.

    Returns:
        Health status of TTS, FFmpeg, and Storage
    """
    voice = get_voice_service()
    health = await voice.check_health()
    return health


@router.get("/voices")
async def list_voices():
    """
    List available Eleven Labs voices.

    Returns:
        List of available voices with their IDs and names
    """
    voice = get_voice_service()

    if not voice.tts.api_key:
        raise HTTPException(
            status_code=503,
            detail="Eleven Labs API key not configured"
        )

    try:
        voices = await voice.tts.get_voices()
        return {
            "voices": [
                {
                    "id": v.get("voice_id"),
                    "name": v.get("name"),
                    "category": v.get("category"),
                    "labels": v.get("labels", {}),
                    "preview_url": v.get("preview_url")
                }
                for v in voices
            ],
            "total": len(voices)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage")
async def get_usage():
    """
    Get Eleven Labs usage statistics.

    Returns:
        Character usage and limits
    """
    voice = get_voice_service()

    if not voice.tts.api_key:
        raise HTTPException(
            status_code=503,
            detail="Eleven Labs API key not configured"
        )

    try:
        info = await voice.tts.get_user_info()
        return {
            "character_count": info.get("character_count", 0),
            "character_limit": info.get("character_limit", 0),
            "tier": info.get("tier", "unknown")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_voice_message(request: VoiceTestRequest):
    """
    Test voice message delivery.

    Converts text to speech and sends to the specified phone number.

    Args:
        request: VoiceTestRequest with text, phone, and options

    Returns:
        Delivery result with audio URL and status
    """
    if not settings.VOICE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Voice service is disabled. Set VOICE_ENABLED=true in environment."
        )

    voice = get_voice_service()

    # Check health first
    health = await voice.check_health()
    if not health.get("overall"):
        raise HTTPException(
            status_code=503,
            detail=f"Voice service unhealthy: {health}"
        )

    try:
        result = await voice.send_voice_message(
            phone=request.phone,
            text=request.text,
            voice_id=request.voice_id,
            also_send_text=request.also_send_text
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthesize")
async def synthesize_audio(request: VoiceSynthesizeRequest):
    """
    Synthesize audio without sending (for testing).

    Converts text to speech and returns the audio URL.

    Args:
        request: VoiceSynthesizeRequest with text

    Returns:
        Audio URL and metadata
    """
    voice = get_voice_service()

    # Check TTS configuration
    if not voice.tts.api_key:
        raise HTTPException(
            status_code=503,
            detail="Eleven Labs API key not configured"
        )

    try:
        from ...services.voice import AudioConverter

        # Generate audio (MP3 is most reliable from Eleven Labs)
        audio_data = await voice.tts.text_to_speech(
            text=request.text,
            voice_id=request.voice_id,
            output_format="mp3_44100_128"
        )

        # Convert MP3 to OGG OPUS for WhatsApp
        ogg_audio = AudioConverter.convert_to_whatsapp_ogg(
            audio_data,
            input_format="mp3"
        )

        # Upload to storage
        import uuid
        filename = f"test/{uuid.uuid4()}.ogg"
        audio_url = await voice.storage.upload_audio(
            ogg_audio,
            filename=filename
        )

        return {
            "success": True,
            "audio_url": audio_url,
            "text_length": len(request.text),
            "audio_size_bytes": len(ogg_audio)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-cache")
async def clear_voice_cache():
    """
    Clear the voice audio cache.

    Returns:
        Confirmation message
    """
    voice = get_voice_service()
    voice.clear_cache()
    return {"message": "Cache cleared successfully"}


# ==================== OpenAI TTS Endpoints ====================

class OpenAITTSRequest(BaseModel):
    """Request model for OpenAI TTS endpoint."""
    text: str
    voice: Optional[str] = None
    instructions: Optional[str] = None


class OpenAITTSTestRequest(BaseModel):
    """Request model for OpenAI TTS test with phone delivery."""
    text: str
    phone: str
    voice: Optional[str] = None
    instructions: Optional[str] = None


@router.get("/openai/voices")
async def list_openai_voices():
    """
    List available OpenAI TTS voices.

    Returns:
        List of available voices with descriptions
    """
    voices = openai_tts.get_available_voices()
    return {
        "voices": voices,
        "current_voice": openai_tts.voice,
        "current_model": openai_tts.model,
        "configured": openai_tts.is_configured()
    }


@router.get("/openai/presets")
async def list_openai_presets():
    """
    List voice presets for common use cases.

    Returns:
        Dictionary of presets with voice and instructions
    """
    presets = openai_tts.get_voice_presets()
    return {
        "presets": presets,
        "usage": "Use these presets as starting points for voice configuration"
    }


@router.post("/openai/synthesize")
async def synthesize_openai_audio(request: OpenAITTSRequest):
    """
    Synthesize audio using OpenAI TTS.

    Converts text to speech and returns base64 audio.

    Args:
        request: OpenAITTSRequest with text and options

    Returns:
        Base64 encoded audio
    """
    if not openai_tts.is_configured():
        raise HTTPException(
            status_code=503,
            detail="OpenAI TTS not configured. Set OPENAI_API_KEY."
        )

    try:
        audio_base64 = await openai_tts.get_audio_base64(
            text=request.text,
            voice=request.voice,
            instructions=request.instructions
        )

        if not audio_base64:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate audio"
            )

        return {
            "success": True,
            "audio_base64": audio_base64,
            "voice": request.voice or openai_tts.voice,
            "model": openai_tts.model,
            "text_length": len(request.text)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/openai/test")
async def test_openai_voice(request: OpenAITTSTestRequest):
    """
    Test OpenAI TTS by sending audio to a phone number.

    Converts text to speech and sends via WhatsApp.

    Args:
        request: OpenAITTSTestRequest with text, phone, and options

    Returns:
        Delivery result
    """
    if not openai_tts.is_configured():
        raise HTTPException(
            status_code=503,
            detail="OpenAI TTS not configured. Set OPENAI_API_KEY."
        )

    try:
        # Generate audio
        audio_base64 = await openai_tts.get_audio_base64(
            text=request.text,
            voice=request.voice,
            instructions=request.instructions
        )

        if not audio_base64:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate audio"
            )

        # Send via WhatsApp
        from ...services.whatsapp import create_whatsapp_service

        # Get default company for testing (company_id=1)
        from ...services.database import db
        company = await db.get_company(1)

        if not company or not company.uazapi_token:
            raise HTTPException(
                status_code=503,
                detail="No company configured for testing. Create company with UAZAPI token."
            )

        wa = create_whatsapp_service(
            instance=company.uazapi_instancia,
            token=company.uazapi_token
        )

        # Send as PTT (Push-to-Talk voice message)
        audio_data = f"data:audio/ogg;base64,{audio_base64}"
        result = await wa.send_ptt(
            to=request.phone,
            audio_url=audio_data,
            delay=500  # Show "Recording audio..." for 500ms
        )

        return {
            "success": True,
            "message_id": result.get("message_id"),
            "voice": request.voice or openai_tts.voice,
            "text_length": len(request.text)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/openai/config")
async def get_openai_tts_config():
    """
    Get current OpenAI TTS configuration.

    Returns:
        Current TTS settings
    """
    return {
        "configured": openai_tts.is_configured(),
        "model": openai_tts.model,
        "voice": openai_tts.voice,
        "instructions": openai_tts.instructions,
        "available_voices": list(openai_tts.VOICES.keys()),
        "settings": {
            "OPENAI_TTS_MODEL": getattr(settings, 'OPENAI_TTS_MODEL', 'gpt-4o-mini-tts'),
            "OPENAI_TTS_VOICE": getattr(settings, 'OPENAI_TTS_VOICE', 'coral'),
        }
    }
