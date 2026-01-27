"""
Entry point for the backend application
"""
import uvicorn
from src.core.config import settings
from src.api.main import app


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
