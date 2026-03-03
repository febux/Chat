"""
Database Connection Module

This module provides utilities for creating and managing asynchronous database connections
using SQLAlchemy. It supports both MySQL and PostgreSQL databases through their respective
asynchronous drivers (asyncmy for MySQL and asyncpg for PostgreSQL).

The module includes functions for:
- Creating session factories for database interactions
- Providing dependency injection compatible database session generators

These utilities are designed to work with the application's Settings configuration
and integrate with FastAPI's dependency injection system for database access.
"""

import contextlib
from typing import Any, Callable

from asyncpg import ConnectionDoesNotExistError
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.sqlalchemy.base import Base
from src.database.sqlalchemy.session_manager import logger, sessionmanager


@event.listens_for(sessionmanager.engine.sync_engine, "handle_error")
def handle_engine_error(context):
    """
    Database connection error handler.

    Listens for connection errors and attempts to reconnect when the connection is lost.
    Returns True to allow the engine to attempt reconnection.

    Note: This function may be called in an asynchronous context (asyncio.create_task).
    """
    if isinstance(context.original_exception, ConnectionDoesNotExistError):
        logger.warning("Database connection lost. Will attempt to reconnect.")
        return True
    return None


async def init_models(drop_existing: bool = False) -> None:
    """
    Initialize database models.

    Creates all database tables based on the defined models.
    Drops existing tables before creation in development environment.

    :param drop_existing: Whether to drop existing tables before creating. Default is False.
    """
    try:
        async with sessionmanager.engine.begin() as conn:
            if drop_existing:
                logger.info("Dropping all tables before create")
                await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database models initialized successfully")
    except SQLAlchemyError as e:
        logger.exception(f"Failed to initialize database models: {e}")
        raise


def session_factory() -> Callable[[Any], contextlib._AsyncGeneratorContextManager[AsyncSession, None]]:
    """
    Get a database session factory.

    This function returns an asynchronous session factory using the provided settings.

    :return: An asynchronous function that returns a database session.
    """
    return sessionmanager.session


async def get_session() -> AsyncSession:
    """
    Get a database session.

    This function creates a database session using the provided settings and
    asynchronously yields it. It ensures that the session is properly closed
    when the generator is exited.

    :return: An asynchronous generator that yields a database session.
    """
    session_manager = session_factory()
    async with session_manager() as session:
        yield session
