"""
Repository Manager implementation using SQLAlchemy
Contains access to the database using SQLAlchemy and provides a session factory for repository interactions.
Also contains catalog of repositories and their respective interactions.
"""

import importlib
from typing import Optional

from src.core.logger.logger_factory import logger_bind
from src.database.sqlalchemy.orm_manager.meta import RepositoryManagerMeta

logger = logger_bind("ORMRepositoryManager")


class OrmRepositoryManager(RepositoryManagerMeta):
    """
    Repository manager for interacting with the database using SQLAlchemy.
    Catalog of repositories and their respective interactions
    """

    def __init__(self):
        self._repos = {}

    def _repo_register(self, name: str, repo_path: str) -> Optional["AbstractRepository"]:  # type: ignore[type]
        """
        Register a repository with the manager.

        :param name: The name of the repository.
        :param repo_path: The path to the repository module
        :return: The registered repository instance, or None if the repository is not found.
        """
        try:
            if name != "meta":
                logger.debug(f"Loading repository {name} from {repo_path}")
                plugin_path = repo_path.replace("/", ".")
                module_name = f"{plugin_path}.{name}.repository"
                mod = importlib.import_module(module_name)
                if hasattr(mod, "repository"):
                    repo_instance = mod.repository
                    self._repos[name] = repo_instance
                    logger.info(f"Registered repository: {name} from {module_name}")
                    return repo_instance
                else:
                    logger.exception(f"No 'repository' attribute found in module {module_name}")
        except ModuleNotFoundError as e:
            logger.exception(f"Repository module {name} not found: {e}")
        return None


orm_repository_manager = OrmRepositoryManager()
