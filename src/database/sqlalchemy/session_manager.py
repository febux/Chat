"""
Session manager for managing database connections.
"""

import asyncio
import contextlib
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.config.main import Settings, settings
from src.core.logger.logger_factory import logger_bind
from src.database.sqlalchemy.constants import POOL_RECYCLE

logger = logger_bind("DatabaseSessionManager")


class DatabaseSessionManager:
    """
    Database session manager for managing asynchronous database sessions.
    This class is responsible for creating and managing asynchronous database sessions
    """

    def __init__(self, settings_: Settings):
        self.settings = settings_
        self._db_url = settings_.db.get_database_url()
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None
        self.init_engine_and_session()

    def init_engine_and_session(self):
        """
        Initialize the asynchronous database engine and sessionmaker.

        :return: None
        """
        logger.debug(f"Creating async DB engine for {self._db_url} (pool_size={self.settings.db.POOL_SIZE})")

        self._engine = create_async_engine(
            self._db_url,
            echo=self.settings.db.ECHO,  # print SQL queries during engine creation
            echo_pool=self.settings.db.POOL_ECHO,  # print SQL queries during engine creation for pool connections
            future=True,  # print SQL queries
            pool_size=self.settings.db.POOL_SIZE,  # maximum number of connections in the pool
            max_overflow=self.settings.db.POOL_MAX_OVERFLOW,  # maximum number of connections that can be checked out at a time
            pool_timeout=self.settings.db.POOL_TIMEOUT,  # maximum time in seconds a connection can be idle before being recycled
            pool_recycle=POOL_RECYCLE,  # kill stale connections
            pool_pre_ping=True,  # avoid slow first query on dead conns
            pool_use_lifo=False,  # use LIFO order for connection retrieval
        )
        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        """
        Get the underlying asynchronous database engine.

        :return: The asynchronous database engine.
        """
        if self._engine is None:
            raise RuntimeError("Database engine is not initialized")
        return self._engine

    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """
        Get the asynchronous sessionmaker for creating database sessions.

        :return: The asynchronous sessionmaker.
        """
        if self._sessionmaker is None:
            raise RuntimeError("Database sessionmaker is not initialized")
        return self._sessionmaker

    @property
    def db_url_str(self) -> str:
        """
        Get the database connection str.

        :return: The database connection str.
        """
        return self._db_url.render_as_string(hide_password=False)

    async def close(self):
        """
        Close the database connection manager and release all resources.
        This method should be called when the application is shutting down to
        properly release the database connection pool.

        :return: None
        """
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None
        else:
            raise Exception("DatabaseSessionManager is not initialized")

    @contextlib.asynccontextmanager
    async def session(self, autocommit: bool = False) -> AsyncIterator[AsyncSession]:
        """
        Create a new asynchronous database session.

        This method creates a new asynchronous database session, and yields it.
        The session is automatically closed when the context manager is exited.

        :param autocommit: Whether to automatically commit the session. Defaults to False.

        :return: An asynchronous context manager that yields a database session.
        """
        async with self.sessionmaker() as session:
            try:
                yield session
                if autocommit:
                    await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await asyncio.shield(session.close())

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        """
        Create a new asynchronous database connection and session.

        This method creates a new asynchronous database connection and session,
        and yields it. The session is automatically closed when the context
        manager is exited.

        :return: An asynchronous context manager that yields a database connection and session.
        """
        async with self.engine.connect() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise


sessionmanager = DatabaseSessionManager(settings)
