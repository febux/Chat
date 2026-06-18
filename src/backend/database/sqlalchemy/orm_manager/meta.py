"""
Abstract repository manager.
Interface for repository managers.
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Type

from sqlalchemy.ext.asyncio import AsyncSession


class RepositoryManagerMeta(ABC):
    """
    Interface for repository managers.
    """

    @property
    def session(self) -> AsyncSession:
        """
        Returns the session factory for repository interactions.

        :return: The session factory.
        """
        if self._session is None:
            raise RuntimeError("Session factory is not initialized")
        return self._session

    @session.setter
    def session(self, session: AsyncSession) -> None:
        """
        Set the session factory for repository interactions.

        :param session: The session factory.
        :return:
        """
        self._session = session

    @asynccontextmanager
    async def transaction(self):
        """
        A context manager for database transactions.

        :return: A context manager that manages the database transaction.
        """
        try:
            yield
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    @abstractmethod
    def _repo_register(self, name: str, repo_path: str) -> Type["AbstractRepository"]:  # type: ignore[type]
        """
        Register a repository with the manager.

        :param name: The name of the repository.
        :param repo_path: The path to the repository module
        :return: The registered repository instance, or None if the repository is not found.
        """
        ...

    @abstractmethod
    def __getattr__(self, item) -> "AbstractRepository":  # type: ignore[type]
        """
        Dynamically load and return repository instances.

        :param item: The name of the repository to load.
        :return: The repository instance.
        """
        ...
