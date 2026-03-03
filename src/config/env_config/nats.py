"""
NATS configuration settings.
"""

from pydantic import Field, RedisDsn, NatsDsn
from pydantic_settings import SettingsConfigDict

from src.config.env_config.base import ConfigBase


class NATSConfig(ConfigBase):
    """
    This class represents the configuration settings for Redis.
    It inherits from pydantic_settings.BaseSettings and uses pydantic's Field() function to validate and parse the configuration values.

    Attributes:


    Methods:
        build_redis_url(self) -> RedisDsn: Builds the Redis URL using the provided configuration values.
        get_redis_url(self) -> RedisDsn: Returns the URL for the Redis database.

    """

    model_config = SettingsConfigDict(env_prefix="NATS_")

    HOST: str = Field(
        "localhost",
        description="NATS server host",
        title="NATS server host",
        examples=["localhost", "nats.example.com"],
    )
    PORT: int = Field(
        default=4222,
        description="NATS server port",
        title="NATS server port",
        examples=[4222, 6222],
    )
    CLUSTER_NAME: str | None = Field(
        default=None,
        description="NATS cluster name",
        title="NATS cluster name",
        examples=["nats-cluster", "my-cluster"],
    )
    CLIENT_NAME: str = Field(
        default="nats-client",
        description="NATS client name",
        title="NATS client name",
        examples=["nats-client", "my-client"],
    )
    USER: str | None = Field(
        default=None,
        description="NATS username",
        title="NATS username",
        examples=["nats_user", "my_user"],
    )
    PASS: str | None = Field(
        default=None,
        description="NATS password",
        title="NATS password",
        examples=["nats_password", "my_password"],
    )

    def build_nats_url(self) -> NatsDsn:
        """
        Build the NATS URL using the provided configuration values.
        """
        if self.USER and self.PASS:
            url = f"nats://{self.USER}:{self.PASS}@{self.HOST}:{self.PORT}"
        else:
            url = f"nats://{self.HOST}:{self.PORT}"
        if self.CLUSTER_NAME:
            url += f"/{self.CLUSTER_NAME}"
        return NatsDsn(url)

    def get_nats_url(self) -> str:
        """
        Get the NATS URL as a NatsDsn object.
        """
        return self.build_nats_url().encoded_string()
