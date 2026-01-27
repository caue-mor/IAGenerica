"""
Services Module
All backend services for IA Generica
"""

# Database service
from .database import db, DatabaseService

# WhatsApp integration
from .whatsapp import whatsapp, WhatsAppService, create_whatsapp_service

# UAZAPI Instance Management
from .uazapi import uazapi, UazapiService, create_uazapi_service

# Audio transcription (OpenAI Whisper)
from .audio_transcription import audio_transcription, AudioTranscriptionService

# Vision/Image analysis (GPT-4 Vision)
from .vision import vision, VisionService

# Message buffering
from .buffer import message_buffer, MessageBufferService, BufferedMessage, ConversationBuffer

# Follow-up scheduling
from .followup_scheduler import (
    followup_scheduler,
    FollowupSchedulerService,
    ScheduledFollowup,
    FollowupStatus,
    FollowupType
)

# Notifications
from .notification import (
    notification_service,
    NotificationService,
    Notification,
    NotificationType,
    NotificationPriority
)

# Voice/TTS (Eleven Labs)
from .voice import (
    get_voice_service,
    VoiceService,
    ElevenLabsTTS,
    AudioConverter,
    AudioStorage
)


__all__ = [
    # Database
    "db",
    "DatabaseService",

    # WhatsApp
    "whatsapp",
    "WhatsAppService",
    "create_whatsapp_service",

    # UAZAPI
    "uazapi",
    "UazapiService",
    "create_uazapi_service",

    # Audio Transcription
    "audio_transcription",
    "AudioTranscriptionService",

    # Vision
    "vision",
    "VisionService",

    # Buffer
    "message_buffer",
    "MessageBufferService",
    "BufferedMessage",
    "ConversationBuffer",

    # Follow-up Scheduler
    "followup_scheduler",
    "FollowupSchedulerService",
    "ScheduledFollowup",
    "FollowupStatus",
    "FollowupType",

    # Notifications
    "notification_service",
    "NotificationService",
    "Notification",
    "NotificationType",
    "NotificationPriority",

    # Voice/TTS
    "get_voice_service",
    "VoiceService",
    "ElevenLabsTTS",
    "AudioConverter",
    "AudioStorage",
]
