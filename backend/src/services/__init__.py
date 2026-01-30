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

# ElevenLabs TTS (simplified service)
from .elevenlabs import (
    elevenlabs,
    ElevenLabsService,
    create_elevenlabs_service
)

# OpenAI TTS (fallback/alternative)
from .openai_tts import (
    openai_tts,
    OpenAITTSService,
    create_openai_tts_service
)

# Proposal Service
from .proposal_service import (
    proposal_service,
    ProposalService
)

# Document Extractor
from .document_extractor import (
    document_extractor,
    DocumentExtractor,
    DocumentType,
    ExtractedField,
    ExtractionResult,
    extract_document
)

# Enhanced Followup Service
from .enhanced_followup import (
    enhanced_followup,
    EnhancedFollowupService,
    schedule_inactivity_followup,
    cancel_followups_for_lead
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

    # ElevenLabs TTS (simplified)
    "elevenlabs",
    "ElevenLabsService",
    "create_elevenlabs_service",

    # OpenAI TTS (fallback)
    "openai_tts",
    "OpenAITTSService",
    "create_openai_tts_service",

    # Proposal Service
    "proposal_service",
    "ProposalService",

    # Document Extractor
    "document_extractor",
    "DocumentExtractor",
    "DocumentType",
    "ExtractedField",
    "ExtractionResult",
    "extract_document",

    # Enhanced Followup Service
    "enhanced_followup",
    "EnhancedFollowupService",
    "schedule_inactivity_followup",
    "cancel_followups_for_lead",
]
