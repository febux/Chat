"""
Base settings for env configuration class.
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigBase(BaseSettings):
    """
    Base settings for configuration class.
    """

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
