"""
Configuration settings for the AI Backend.
Uses pydantic-settings to load environment variables.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Google Gemini API Configuration
    GOOGLE_API_KEY: str
    MODEL_NAME: str = "gemini-2.5-flash-preview-05-20"
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
