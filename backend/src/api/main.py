"""
FastAPI application
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import settings
from .routes import (
    webhook_router,
    leads_router,
    companies_router,
    whatsapp_router,
    whatsapp_connect_router,
    voice_router,
    lead_statuses_router,
    conversations_router
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

    # Include routers
    app.include_router(webhook_router)
    app.include_router(leads_router, prefix="/api")
    app.include_router(companies_router, prefix="/api")
    app.include_router(lead_statuses_router, prefix="/api")
    app.include_router(conversations_router, prefix="/api")
    app.include_router(whatsapp_router)  # WhatsApp/UAZAPI management (legacy)
    app.include_router(whatsapp_connect_router)  # WhatsApp connection management (new)
    app.include_router(voice_router, prefix="/api")  # Voice/TTS service

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

    @app.on_event("shutdown")
    async def shutdown():
        """Shutdown event"""
        logger.info(f"Shutting down {settings.APP_NAME}...")

    return app


# Create app instance
app = create_app()
