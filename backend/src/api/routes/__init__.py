from .webhook import router as webhook_router
from .leads import router as leads_router
from .companies import router as companies_router
from .whatsapp import router as whatsapp_router
from .whatsapp_connect import router as whatsapp_connect_router
from .voice import router as voice_router
from .voice_calls import router as voice_calls_router
from .voice_calls_webhook import router as voice_calls_webhook_router
from .lead_statuses import router as lead_statuses_router
from .conversations import router as conversations_router
from .analytics import router as analytics_router
from .proposals import router as proposals_router
from .documents import router as documents_router

__all__ = [
    "webhook_router",
    "leads_router",
    "companies_router",
    "whatsapp_router",
    "whatsapp_connect_router",
    "voice_router",
    "voice_calls_router",
    "voice_calls_webhook_router",
    "lead_statuses_router",
    "conversations_router",
    "analytics_router",
    "proposals_router",
    "documents_router"
]
