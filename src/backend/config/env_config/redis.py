"""
Redis configuration settings.
"""

from pydantic import Field, RedisDsn
from pydantic_settings import SettingsConfigDict

from src.backend.config.env_config.base import ConfigBase


class RedisConfig(ConfigBase):
    """
    This class represents the configuration settings for Redis.
    It inherits from pydantic_settings.BaseSettings and uses pydantic's Field() function to validate and parse the configuration values.

    Attributes:
        USERNAME (str): The Redis username.
        DEFAULT_PASSWORD (str): The default Redis password.
        HOST (str): The Redis host.
        PORT (int): The Redis port.
        DB (int): The Redis database index.
        EXTERNAL_PORT (int): The external Redis port.

    Methods:
        build_redis_url(self) -> RedisDsn: Builds the Redis URL using the provided configuration values.
        get_redis_url(self) -> RedisDsn: Returns the URL for the Redis database.

    """

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    USERNAME: str = Field(
        default=None,
        description="Redis username",
        title="Redis username",
        examples=["redis_user"],
    )
    DEFAULT_PASSWORD: str = Field(
        default=None,
        description="Default Redis password",
        title="Default Redis password",
        examples=["redis_password"],
    )
    HOST: str = Field(
        default="localhost",
        description="Redis host",
        title="Redis host",
        examples=["localhost", "redis.example.com"],
    )
    PASSWORD: str = Field(
        default=None,
        description="Redis password",
        title="Redis password",
        examples=["redis_password"],
    )
    DB: int = Field(
        default=0,
        description="Redis database index",
        title="Redis database index",
        examples=[0, 1],
    )
    PORT: int = Field(
        default=6379,
        description="Redis port",
        title="Redis port",
        examples=[6379, 6380],
    )
    EXTERNAL_PORT: int = Field(
        default=None,
        description="External Redis port",
        title="External Redis port",
        examples=[6379, 6380],
    )

    def build_redis_url(self) -> RedisDsn:
        """
        Build the Redis URL using the provided configuration values.

        :return: The Redis URL.
        """
        return RedisDsn(f"redis://{self.USERNAME or ''}:{self.PASSWORD or ''}@{self.HOST}:{self.PORT}/{self.DB}")

    def get_redis_url(self) -> str:
        """
        Get the Redis URL.

        :return: The Redis URL.
        """
        return self.build_redis_url().encoded_string()
