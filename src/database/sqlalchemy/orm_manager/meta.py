"""
Abstract repository manager.
Interface for repository managers.
"""

import pkgutil
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Type

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.main import settings


class RepositoryManagerMeta(ABC):
    """
    Interface for repository managers.
    """

    _session: AsyncSession = None

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

    def _load_repo(self, name: str, repo_path: str | None = None) -> Type["AbstractRepository"]:  # type: ignore[type]
        """
        Load and return a repository instance.

        :param name: The name of the repository.
        :param repo_path: The path to the repository module.
        """
        if name in self._repos:
            return self._repos[name]

        return self._repo_register(name, repo_path or settings.app.REPO_PATH)

    def __getattr__(self, item) -> "AbstractRepository":  # type: ignore[type]
        """
        Dynamically load and return repository instances.

        :param item: The name of the repository to load.
        :return: The repository instance.
        """
        repo = self._load_repo(item)
        if repo is not None:
            return repo(self.session)
        raise AttributeError(f"'OrmRepositoryManager' object has no attribute '{item}'")

    def auto_register_repos(
        self,
        repo_path: str | None = None,
    ):
        """
        Automatically include repositories to repository manager.

        :param repo_path: The path to the repositories.
        :return: None
        """
        repo_path = repo_path or settings.app.REPO_PATH
        for finder, name, ispkg in pkgutil.iter_modules([repo_path]):
            self._repo_register(name, repo_path)
