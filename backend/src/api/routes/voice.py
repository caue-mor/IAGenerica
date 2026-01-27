"""
Voice API routes - Test and health endpoints for voice service.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from ...services.voice import get_voice_service, VoiceService
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
