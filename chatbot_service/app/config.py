"""
Application configuration using pydantic-settings.
Loads settings from environment variables and .env file.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings. All values can be overridden via environment variables.

    Environment variables are case-insensitive and loaded from .env file.
    """

    # 360dialog WhatsApp API settings
    d360_api_key: str = ""
    d360_base_url: str = "https://waba-sandbox.360dialog.io"
    my_phone_number: str = ""

    # Gym API settings
    use_mock_data: bool = True
    gym_api_base_url: str = "https://mulaigym.id"
    gym_api_key: str = ""

    # HTTP client settings
    http_timeout: int = 30

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
