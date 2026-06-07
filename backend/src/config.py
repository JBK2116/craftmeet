"""Global environment variable configuration and management

This module loads all .env variables into memory and places them
into a `Settings` object for use throughout the application.

Exmaple Usage

    from src.config import get_settings

    settings = get_settings()
    settings.IS_DEV
    ...
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    "Stores all .env variables loaded into memory for use"

    IS_DEV: bool
    # Logging
    LOG_LEVEL: str
    SERVICE_NAME: str
    # Database
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    # Email
    SENGRID_API_KEY: str
    SENGRID_EMAIL_FROM: str

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns global `Settings` object

    Cached via `lru_cache` allowing this function to be called in modules without initialization overhead.
    """
    return Settings()  # ty:ignore[missing-argument]
