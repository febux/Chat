"""
User service implementation.
"""

from typing import Optional, Sequence
from uuid import UUID

from pydantic import EmailStr

from src.config.main import Settings
from src.core.logger.app_logger import AppLogger
from src.database.sqlalchemy.orm_manager import RepositoryManagerMeta
from src.utils.password import verify_password


class UserService:
    """
    A service class for handling user operations.
    """

    def __init__(
        self,
        app_config: Settings,
        orm_manager: RepositoryManagerMeta,
        logger: AppLogger,
    ):
        self.app_config = app_config
        self.orm_manager = orm_manager
        self.logger = logger

        self.user_repo = self.orm_manager.user

    async def get_all(
        self,
        q: str | None = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Sequence["User"]:  # type: ignore[return-value]
        """
        Retrieving all users with filters and limits.

        :param q: The query string for filtering users.
        :param skip: The number of records to skip.
        :param limit: The maximum number of records to return.
        :return: A sequence of users that match the specified filters.
        """
        return await self.user_repo.get_all(
            q=q,
            skip=skip,
            limit=limit,
        )

    async def get_all_except_of_current_user(self, user_id: UUID) -> Sequence["User"]:  # type: ignore[return-value]
        """
        Retrieve all users except the current user.

        :param user_id: ID of the user to exclude from the results.
        :return: A list of users.
        """
        return await self.user_repo.get_all_except_of_current_user(user_id=user_id)

    async def get_by_id(self, user_id: UUID) -> Optional["User"]:  # type: ignore[return-value]
        """
        Retrieve a user by its ID.

        :param user_id: The ID of the user.
        :return: The user with the specified ID, or None if not found.
        """
        return await self.user_repo.read_one(id=user_id)

    async def get_by_email(self, email: str) -> Optional["User"]:  # type: ignore[return-value]
        """
        Retrieve a user by their email address.

        :param email: The email address of the user.
        :return: The user with the specified email address, or None if not found.
        """
        return await self.user_repo.read_one(email=email)

    async def authenticate_user(self, email: EmailStr, password: str) -> Optional["User"]:  # type: ignore[return-value]
        user = await self.get_by_email(email=email)
        if not user or await verify_password(pw=password, digest=user.password_hash) is False:
            return None
        return user

    async def create(
        self,
        username: str,
        email: EmailStr,
        password_hash: str,
        **kwargs,
    ) -> "User":    # type: ignore[return-value]
        """
        Create a new user.

        :param username: The name of the user.
        :param email: The email address of the user.
        :param password_hash: The hashed password of the user.
        :return: The created user.
        """
        async with self.orm_manager.transaction():
            return await self.user_repo.create(
                username=username,
                email=email,
                password_hash=password_hash,
                **kwargs,
            )
