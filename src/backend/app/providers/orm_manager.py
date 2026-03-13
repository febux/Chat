"""
ORM manager provider function for FastAPI.
"""

from typing import Annotated

from fastapi import Depends
from starlette.requests import Request

from src.backend.app.providers.db import DbSession
from src.backend.database.sqlalchemy.orm_manager import OrmRepositoryManager, RepositoryManagerMeta, orm_repository_manager


async def get_orm_manager(
    request: Request,
    session: DbSession,
) -> OrmRepositoryManager:
    """
    This function retrieves an ORM manager instance associated with the incoming FastAPI request.

    :param request: The incoming FastAPI request. It is used to access the application state,
                    where the Logger instance is stored.
    :param session: The database session instance associated with the request.
    :return: An ORM manager instance associated with the request.
    """
    orm_repository_manager.session = session
    return orm_repository_manager


OrmRepositoryManagerProvider = Annotated[RepositoryManagerMeta, Depends(get_orm_manager)]
