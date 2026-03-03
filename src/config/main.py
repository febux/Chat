"""
Configuration module contains configuration settings for the application.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings

from src.config.env_config.app import AppConfig
from src.config.env_config.db import DatabaseConfig
from src.config.env_config.redis import RedisConfig
from src.config.env_config.nats import NATSConfig


class Settings(BaseSettings):
    """
    Configuration settings for the application.

    Attributes:
        db (DatabaseConfig): Database configuration settings.
        app (AppConfig): Application configuration settings.
        redis (RedisConfig): Redis configuration settings.

    Methods:
        load(cls) -> "Settings": Loads and returns the application settings.
        settings_customize_sources(cls, **kwargs) -> tuple: Customizes the sources for loading settings.

    Note:
        Use ConfigBase(BaseSettings) as the base class for loading settings
        if you want to load settings from a ENV file and set default factory for each configuration setting.
    """

    db: DatabaseConfig = Field(default_factory=DatabaseConfig)  # env config
    app: AppConfig = Field(default_factory=AppConfig)  # env config
    redis: RedisConfig = Field(default_factory=RedisConfig)  # env config
    nats: NATSConfig = Field(default_factory=NATSConfig)  # env config

    @classmethod
    def load(cls) -> "Settings":
        """
        Loads and returns the application settings.

        :return: An instance of Settings.
        """
        return cls()


@lru_cache()
def get_settings():
    """
    Returns the singleton instance of Settings.
    LRU Cache is used to ensure that the settings are loaded only once.

    :return: An instance of Settings.
    """
    return Settings.load()


settings = get_settings()
