"""
Configuration settings using Pydantic
"""
import os
from functools import lru_cache
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings

# Get the backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App
    APP_NAME: str = "IA Generica"
    DEBUG: bool = False

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # UAZAPI (supports both UAZAPI_SERVER and UAZAPI_BASE_URL)
    UAZAPI_SERVER: str = "https://api.uazapi.com"
    UAZAPI_TOKEN: Optional[str] = None
    UAZAPI_ADMIN_TOKEN: Optional[str] = None
    WEBHOOK_BASE_URL: Optional[str] = None  # For webhook configuration

    @property
    def UAZAPI_BASE_URL(self) -> str:
        """Alias for UAZAPI_SERVER for backwards compatibility"""
        return self.UAZAPI_SERVER

    # Eleven Labs (Text-to-Speech)
    ELEVEN_LABS_API_KEY: Optional[str] = None
    ELEVEN_LABS_VOICE_ID: Optional[str] = None  # Default voice ID
    ELEVEN_LABS_MODEL_ID: str = "eleven_multilingual_v2"

    # Voice Configuration
    VOICE_ENABLED: bool = False
    VOICE_OUTPUT_FORMAT: str = "opus_48000_64"  # Best for WhatsApp

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Buffer (Message Debouncing)
    BUFFER_DEBOUNCE_SECONDS: float = 7.0  # Wait 7 seconds before processing
    BUFFER_MAX_SIZE: int = 50  # Max messages before forcing processing

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
