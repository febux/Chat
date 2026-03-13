"""
Database configuration settings.
"""

from pydantic import Field
from pydantic_settings import SettingsConfigDict
from sqlalchemy import URL

from src.backend.config.env_config.base import ConfigBase


class DatabaseConfig(ConfigBase):
    """
    This class represents the configuration settings for the application.
    It inherits from pydantic_settings.BaseSettings and uses pydantic's Field() function to validate and parse the configuration values.

    Attributes:
        DRIVER (str): The type of database to use. Defaults to "postgresql".
        USER (str): The username for database authentication. Defaults to "user".
        PASSWORD (str): The password for database authentication. Defaults to "password".
        HOST (str): The host address of the database. Defaults to "localhost".
        PORT (int): The port number for the database connection. Defaults to 5672.
        EXTERNAL_PORT (int): The external port number for the database connection. Defaults to 5672.
        SCHEMA (str): The database schema to use. Defaults to "public".
        CHARSET (str): The character set for the database. Defaults to "utf8".
        ECHO (bool): Whether to print SQL queries during database operations.
                                if True, the Engine will log all statements
                                as well as a ``repr()`` of their parameter lists to the default log
                                handler. Defaults to False.
        POOL_ECHO (bool): Whether to print SQL queries during database pool operations.
                                    if True, the connection pool will log
                                    informational output such as when connections are invalidated
                                    as well as when connections are recycled to the default log handler. Defaults to False.

    Methods:
        get_database_url(self) -> URL: Returns the database connection URL.
    """

    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    DRIVER: str = Field(
        "postgresql",
        description="Database driver to use",
        title="Database driver",
        examples=["postgresql", "mysql", "postgresql+asyncpg"],
    )
    USER: str = Field(
        "user",
        description="Username for database authentication",
        title="Database user",
        examples=["admin", "user"],
    )
    PASSWORD: str = Field(
        "password",
        description="Password for database authentication",
        title="Database password",
        examples=["password", "secret"],
    )
    HOST: str = Field(
        "localhost",
        description="Host address of the database",
        title="Database host",
        examples=["localhost", "db.example.com"],
    )
    PORT: int = Field(
        5672,
        description="Port number for the database connection",
        title="Database port",
        examples=[5672, 15672],
    )
    EXTERNAL_PORT: int = Field(
        15672,
        description="External port number for the database connection",
        title="Database external port",
        examples=[15672, 25672],
    )
    SCHEMA: str = Field(
        "public",
        description="Database schema to use",
        title="Database schema",
        examples=["public", "my_schema"],
    )
    CHARSET: str = Field(
        "utf8",
        description="Character set for the database",
        title="Database charset",
        examples=["utf8", "utf-16"],
    )
    ECHO: bool = Field(
        False,
        description="Whether to print SQL queries during database operations",
        title="Database echo",
        examples=[True, False],
    )
    POOL_ECHO: bool = Field(
        False,
        description="Whether to print SQL queries during database pool operations",
        title="Database pool echo",
        examples=[True, False],
    )
    POOL_SIZE: int = Field(
        10,
        description="Size of the database connection pool",
        title="Database pool size",
        examples=[10, 20],
    )
    POOL_MAX_OVERFLOW: int = Field(
        20,
        description="Maximum number of connections in the database connection pool that can be overflowed",
        title="Database pool max overflow",
        examples=[5, 10, 20],
    )
    POOL_TIMEOUT: int = Field(
        30,
        description="Timeout for database connection pool operations",
        title="Database pool timeout",
        examples=[30, 60],
    )

    def get_database_url(
        self,
        unittest: bool = False,
    ) -> URL:
        """
        Get database connection URL based on the provided application settings.

        This function constructs a database connection URL using the provided settings.
        It supports MySQL and PostgreSQL databases, and includes optional charset for MySQL.

        Note:
           This function assumes that the SQLAlchemy library is installed and
           available for use.

        :param unittest: A boolean indicating whether the database connection URL should be for testing.
        :return: A SQLAlchemy URL object representing the database connection.
        """
        url = URL.create(
            drivername="mysql+asyncmy" if self.DRIVER == "mysql" else "postgresql+asyncpg",
            username=self.USER,
            password=self.PASSWORD,
            host=self.HOST,
            port=self.PORT,
            database=self.SCHEMA if not unittest else f"{self.SCHEMA}_test",
        )
        if self.DRIVER == "mysql":
            url.update_query_dict({"charset": self.CHARSET})
        return url
