"""
Application configuration.
"""

import base64

from pydantic import AliasChoices, Field, computed_field

from src.backend.config.env_config.base import ConfigBase


class AppConfig(ConfigBase):
    """
    This class represents the configuration settings for the application.
    It inherits from pydantic_settings.BaseSettings and uses pydantic's Field() function to validate and parse the configuration values.

    Attributes:
        TIMEOUT (int): The timeout for API requests. Defaults to 30 seconds.
        TTL_KEY_SESSION (int): The time-to-live (TTL) for session keys in seconds. Defaults to 10800 seconds (3 hours).
        LOG_LEVEL (str): The logging level for the application. Defaults to "INFO".
        CORS_ORIGINS (str): The origins from which Cross-Origin Resource Sharing (CORS) requests are allowed. Defaults to "*".
        TRUSTED_HOSTS (str): The trusted hosts for the application. Defaults to "*".
        RETRY_PER_REQUEST_AMOUNT (int, optional): The number of retries for each request. Defaults to 3.
        RATE_LIMIT_DURATION (int, optional): The duration in minutes for which the client's requests will be limited. Defaults to 1 minute.
        RATE_LIMIT_REQUESTS (int, optional): The maximum number of requests allowed within the specified time duration. Defaults to 3.
        TESTING_MODE (bool, optional): A flag indicating whether the application is in test mode. Defaults to False.
        MAINTENANCE_MODE (bool, optional): A flag indicating whether the application is in maintenance mode. Defaults to False.
        REQUEST_SIZE_LIMIT (int, optional): The maximum size of incoming request payloads in bytes. Defaults to 10485760 (10 MB).
        APP_NAME (str, optional): The name of the application. Defaults to "Project K API".
        REPO_PATH (str, optional): The path to the repository directory. Defaults to "/path/to/repository".
        JWT_SECRET_KEY (str, optional): The secret key for encrypting and decrypting sensitive data. Defaults to "secret_key".
        JWT_ALGORITHM (str, optional): The encryption algorithm for sensitive data. Defaults to "AES-256-CBC".
        SESSION_SECRET_KEY (str, optional): The secret key for encrypting and decrypting session keys. Defaults to "secret_key".
        SESSION_MAX_AGE (int, optional): The maximum age of a session in seconds. Defaults to 86400 (1 day).
        CSRF_COOKIE (str, optional): The name of the CSRF cookie. Defaults to "csrf_token".
    """

    TIMEOUT: int = Field(
        30,
        description="Timeout for API requests",
        title="Timeout",
        examples=[30, 60],
    )
    TTL_KEY_SESSION: int = Field(
        10800,
        description="Time-to-live (TTL) for session keys in seconds",
        title="TTL key session",
        examples=[10800, 36000],
    )
    LOG_LEVEL: str = Field(
        "INFO",
        description="Logging level for the application",
        title="Log level",
        examples=["INFO", "DEBUG"],
    )
    CORS_ORIGINS: list[str] = Field(
        ["*"],
        description="Origins from which Cross-Origin Resource Sharing (CORS) requests are allowed",
        title="CORS origins",
        examples=["http://localhost:8080", "https://example.com"],
    )
    CORS_HEADERS: list[str] = Field(
        ["*"],
        description="Additional headers for CORS requests",
        title="CORS headers",
        examples=["Access-Control-Allow-Origin", "Content-Type", "Accept", "X-Custom-Header"],
    )
    CORS_METHODS: list[str] = Field(
        ["*"],
        description="Methods allowed for CORS requests",
        title="CORS methods",
        examples=["GET", "POST", "PUT", "DELETE"],
    )
    CORS_CREDENTIALS: bool = Field(
        False,
        description="Include credentials in CORS requests",
        title="CORS credentials",
        examples=[True, False],
    )
    TRUSTED_HOSTS: list[str] = Field(
        ["*"],
        description="Trusted hosts for the application, it could be user as IP filtering",
        title="Trusted hosts",
        examples=["localhost", "example.com", "10.0.10.1"],
    )
    RETRY_PER_REQUEST_AMOUNT: int | None = Field(
        3,
        description="Number of retries for each request",
        title="Retry per request amount",
        examples=[3, 5],
    )

    RATE_LIMIT_DURATION: int | None = Field(
        1,
        description="Duration in minutes for the rate limit",
        title="Rate limit duration",
        examples=[1, 5],
    )
    RATE_LIMIT_REQUESTS: int | None = Field(
        3,
        description="Number of requests allowed within the rate limit duration",
        title="Rate limit requests",
        examples=[3, 10],
    )
    TESTING_MODE: bool = Field(
        False,
        description="Indicates if the application is running in testing mode",
        title="Testing mode",
        examples=[True, False],
    )
    MAINTENANCE_MODE: bool = Field(
        False,
        description="Indicates if the application is in maintenance mode",
        title="Maintenance mode",
        examples=[True, False],
    )
    REQUEST_SIZE_LIMIT: int | None = Field(
        None,
        description="Maximum size of the request payload in bytes",
        title="Request size limit",
        examples=[1024 * 1024, 1024 * 1024 * 2],
        validation_alias=AliasChoices("REQUEST_SIZE_LIMIT", "REQUEST_SIZE_LIMIT_MB"),
    )
    APP_NAME: str = Field(
        "BackendServiceAPI",
        description="Name of the application",
        title="Application name",
        examples=["base_app", "my_app"],
    )
    APP_MODE: str = Field(
        "production",
        description="Mode of the application",
        title="Application mode",
        examples=["production", "development"],
    )
    REPO_PATH: str = Field(
        "src/backend/app/repository",
        description="Path to the repository module",
        title="Repository path",
        examples=["src/domain/repository", "my_app/repository"],
    )
    JWT_SECRET_KEY: str = Field(
        "your-secret-key",
        description="Secret key for JWT authentication",
        title="Secret key",
        examples=["your-secret-key", "my-secret-key"],
    )
    JWT_ALGORITHM: str = Field(
        "HS256",
        description="Algorithm used for JWT authentication",
        title="Algorithm",
        examples=["HS256", "RS256"],
    )

    SESSION_SECRET_KEY: str = Field(
        "your-session-secret-key",
        description="Secret key for session management",
        title="Session secret key",
        examples=["your-session-secret-key", "my-session-secret-key"],
    )
    SESSION_MAX_AGE: int = Field(
        86400,
        description="Maximum age of a session in seconds",
        title="Session max age",
        examples=[3600, 7200],
    )

    CACHE_ETAG_TTL: int = Field(
        10,
        description="Time-to-live (TTL) for cache ETag values in seconds",
        title="Cache ETag TTL",
        examples=[30, 60],
    )

    CSRF_COOKIE: str = Field(
        "csrf_token",
        description="Name of the CSRF cookie",
        title="CSRF cookie",
        examples=["csrf_token", "my_csrf_token"],
    )

    AES_KEY: str = Field(
        "your-aes-key",
        description="AES key for encryption/decryption",
        title="AES key",
        examples=["your-aes-key", "my-aes-key"],
    )
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(
        "http://localhost:4317",
        description="OTel Exporter OTLP endpoint",
        title="OTel exporter OTLP endpoint",
        examples=["http://localhost:4317", "my-otel-exporter-otlp-endpoint"],
    )
    CENTRIFUGO_HOST: str = Field(
        "localhost",
        description="Centrifugo host",
        title="Centrifugo host",
        examples=["localhost", "my-centrifugo-host"],
    )
    CENTRIFUGO_PORT: int = Field(
        8000,
        description="Centrifugo port",
        title="Centrifugo port",
        examples=[8080, 18080],
    )
    CENTRIFUGO_EXTERNAL_PORT: int = Field(
        None,
        description="External Centrifugo port",
        title="External Centrifugo port",
        examples=[8000, 18080],
    )
    CENTRIFUGO_ADMIN_PASSWORD: str = Field(
        "your-admin-password",
        description="Admin password for Centrifugo",
        title="Admin password",
        examples=["your-admin-password", "my-admin-password"],
    )
    CENTRIFUGO_ADMIN_SECRET: str = Field(
        "your-admin-secret",
        description="Admin secret for Centrifugo",
        title="Admin secret",
        examples=["your-admin-secret", "my-admin-secret"],
    )
    CENTRIFUGO_HTTP_API_KEY: str = Field(
        "your-http-api-key",
        description="HTTP API key for Centrifugo",
        title="HTTP API key",
        examples=["your-http-api-key", "my-http-api-key"],
    )
    CENTRIFUGO_BROKER_NATS_URL: str = Field(
        "nats://localhost:4222",
        description="NATS URL for Centrifugo broker",
        title="NATS URL",
        examples=["nats://localhost:4222", "nats://my-nats-url"],
    )
    CENTRIFUGO_CLIENT_TOKEN_HMAC_SECRET_KEY: str = Field(
        "your-client-token-hmac-secret-key",
        description="HMAC secret key for Centrifugo client token",
        title="HMAC secret key",
        examples=["your-client-token-hmac-secret-key", "my-client-token-hmac-secret-key"],
    )

    @computed_field
    @property
    def aes_key(self) -> bytes:
        return base64.b64decode(self.AES_KEY)

    @computed_field
    @property
    def centrifugo_http_url(self) -> str:
        if self.CENTRIFUGO_EXTERNAL_PORT:
            return f"http://{self.CENTRIFUGO_HOST}:{self.CENTRIFUGO_EXTERNAL_PORT}"
        else:
            return f"http://{self.CENTRIFUGO_HOST}:{self.CENTRIFUGO_PORT}"
