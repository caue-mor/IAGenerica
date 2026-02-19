"""
FastAPI application
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import settings
from ..services.followup_scheduler import followup_scheduler
from ..services.notification import notification_service
from ..services.enhanced_followup import enhanced_followup
from ..middleware.rate_limiter import rate_limiter, rate_limit_middleware
from .routes import (
    webhook_router,
    leads_router,
    companies_router,
    whatsapp_router,
    whatsapp_connect_router,
    voice_router,
    voice_calls_router,
    voice_calls_webhook_router,
    lead_statuses_router,
    conversations_router,
    analytics_router,
    proposals_router,
    documents_router
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title=settings.APP_NAME,
        description="IA Generica - Assistente Virtual Multi-Segmento",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify allowed origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting middleware
    @app.middleware("http")
    async def rate_limiting(request: Request, call_next):
        """Apply rate limiting to requests."""
        return await rate_limit_middleware(request, call_next)

    # Include routers
    app.include_router(webhook_router)
    app.include_router(leads_router, prefix="/api")
    app.include_router(companies_router, prefix="/api")
    app.include_router(lead_statuses_router, prefix="/api")
    app.include_router(conversations_router, prefix="/api")
    app.include_router(whatsapp_router)  # WhatsApp/UAZAPI management (legacy)
    app.include_router(whatsapp_connect_router)  # WhatsApp connection management (new)
    app.include_router(voice_router, prefix="/api")  # Voice/TTS service
    app.include_router(voice_calls_router, prefix="/api")  # Voice calls (ElevenLabs)
    app.include_router(voice_calls_webhook_router)  # ElevenLabs webhooks (no prefix)
    app.include_router(analytics_router, prefix="/api")  # Analytics and metrics
    app.include_router(proposals_router, prefix="/api")  # Proposal management
    app.include_router(documents_router, prefix="/api")  # Document extraction

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "status": "running"
        }

    @app.get("/health")
    async def health():
        """Health check endpoint"""
        return {"status": "ok"}

    @app.on_event("startup")
    async def startup():
        """Startup event"""
        logger.info(f"Starting {settings.APP_NAME}...")

        # Start the follow-up scheduler
        await followup_scheduler.start_scheduler()
        logger.info("Follow-up scheduler started")

        # Start the notification delivery worker
        await notification_service.start_worker()
        logger.info("Notification worker started")

        # Start rate limiter cleanup task
        await rate_limiter.start_cleanup_task()
        logger.info("Rate limiter cleanup task started")

        # Start the enhanced follow-up scheduler
        await enhanced_followup.start_scheduler()
        logger.info("Enhanced follow-up scheduler started")

    @app.on_event("shutdown")
    async def shutdown():
        """Shutdown event"""
        logger.info(f"Shutting down {settings.APP_NAME}...")

        # Stop the follow-up scheduler
        await followup_scheduler.stop_scheduler()
        logger.info("Follow-up scheduler stopped")

        # Stop the notification worker
        await notification_service.stop_worker()
        logger.info("Notification worker stopped")

        # Stop rate limiter cleanup
        await rate_limiter.stop_cleanup_task()
        logger.info("Rate limiter cleanup stopped")

        # Stop the enhanced follow-up scheduler
        await enhanced_followup.stop_scheduler()
        logger.info("Enhanced follow-up scheduler stopped")

    return app


# Create app instance
app = create_app()
