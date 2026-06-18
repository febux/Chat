"""
Repository Manager implementation using SQLAlchemy.

Provides a lazy, attribute-based catalog of repositories over a single
AsyncSession. Repositories are imported and instantiated on first attribute
access (``manager.message``) and then cached on the instance, so there is no
eager ``_repos`` dict to populate or share. A throwaway manager with no session
can still run :meth:`validate_repos` at startup, since validation only imports
modules and never touches the database.
"""

import importlib
import pkgutil
from typing import Optional, Type

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config.main import settings
from src.backend.core.logger.logger_factory import logger_bind
from src.backend.database.sqlalchemy.orm_manager.meta import \
    RepositoryManagerMeta

logger = logger_bind("ORMRepositoryManager")


class OrmRepositoryManager(RepositoryManagerMeta):
    """
    Repository manager for interacting with the database using SQLAlchemy.

    Repositories are lazy: the first ``manager.<name>`` access imports the
    matching ``<name>.repository`` module, instantiates the repository class
    with this manager's session, and stores the instance on the manager so
    every subsequent access on the same manager returns the same instance.
    Nothing is preloaded.
    """

    def __init__(self, session: AsyncSession | None = None):
        # ``session`` is optional: a no-session manager can be built purely for
        # startup validation (which only imports modules). Real request-time
        # managers always carry a live AsyncSession.
        self._session = session

    def _repo_register(self, name: str, repo_path: str) -> Optional[Type["AbstractRepository"]]:  # type: ignore[type]
        """
        Import a repository module and return its repository *class*.

        Nothing is cached here — this is the import step shared by both the
        lazy :meth:`__getattr__` path and the startup :meth:`validate_repos`
        check. The ``repository`` symbol exposed by each module is the class
        (e.g. ``MessageRepository``); it is bound to a session on demand.

        :param name: The name of the repository.
        :param repo_path: The path to the repository module.
        :return: The repository class, or None if it cannot be resolved.
        """
        try:
            if name != "meta":
                logger.debug(f"Loading repository {name} from {repo_path}")
                plugin_path = repo_path.replace("/", ".")
                module_name = f"{plugin_path}.{name}.repository"
                mod = importlib.import_module(module_name)
                if hasattr(mod, "repository"):
                    logger.info(f"Resolved repository: {name} from {module_name}")
                    return mod.repository
                logger.exception(f"No 'repository' attribute found in module {module_name}")
        except ModuleNotFoundError as e:
            logger.exception(f"Repository module {name} not found: {e}")
        return None

    def __getattr__(self, item) -> "AbstractRepository":  # type: ignore[type]
        """
        Lazily load, instantiate, and cache a repository on first access.

        Only public attribute names are treated as repository lookups; private
        and dunder names raise immediately so they resolve via normal attribute
        access (and never trigger an import attempt, or recursion before
        ``__init__`` has run).

        After the first ``manager.<name>`` access the bound instance is stored
        on the manager, so subsequent accesses resolve through the normal
        attribute machinery and never re-enter ``__getattr__``.

        :param item: The name of the repository to load.
        :return: A repository instance bound to this manager's session.
        :raises AttributeError: If the name is private or the repository
            module/class cannot be resolved.
        """
        if item.startswith("_"):
            raise AttributeError(item)
        repo_class = self._repo_register(item, settings.app.REPO_PATH)
        if repo_class is None:
            raise AttributeError(f"'OrmRepositoryManager' object has no attribute '{item}'")
        instance = repo_class(self.session)
        # Cache the bound instance on this manager so the next access is a
        # plain attribute lookup (no import, no re-instantiation).
        object.__setattr__(self, item, instance)
        return instance

    def validate_repos(self, repo_path: str | None = None) -> list[str]:
        """
        Verify at startup that every repository module imports and exposes a
        ``repository`` class. Fail fast if any cannot be resolved.

        This does NOT cache or instantiate anything — repositories remain lazy.
        It only imports each module so a broken repo path or a missing
        ``repository`` attribute aborts the boot instead of surfacing later as a
        request-time ``AttributeError``.

        :param repo_path: Optional override for the repository directory.
        :return: Sorted names of the repositories that validated successfully.
        :raises RuntimeError: If one or more repositories fail to resolve.
        """
        repo_path = repo_path or settings.app.REPO_PATH
        expected = [
            name for _, name, ispkg in pkgutil.iter_modules([repo_path])
            if name != "meta" and ispkg
        ]
        resolved = [
            name for name in expected
            if self._repo_register(name, repo_path) is not None
        ]
        missing = [n for n in expected if n not in resolved]
        if missing:
            raise RuntimeError(
                f"Failed to resolve repositories at startup (repo_path={repo_path!r}): {missing}. "
                "Check that each directory under the repository path exposes a 'repository' attribute."
            )
        logger.info(f"All repositories validated at startup: {sorted(resolved)}")
        return sorted(resolved)
