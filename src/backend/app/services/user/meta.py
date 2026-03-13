"""
This module defines the protocol for user services.
"""

from abc import abstractmethod
from typing import Optional, Protocol, Sequence
from uuid import UUID

from pydantic import EmailStr


class UserServiceMeta(Protocol):
    """
    Protocol for API services.
    """

    @abstractmethod
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
        ...

    @abstractmethod
    async def get_all_except_of_current_user(self, user_id: UUID) -> Sequence["User"]:  # type: ignore[return-value]
        """
        Retrieve all users except the current user.

        :param user_id: ID of the user to exclude from the results.
        :return: A list of users.
        """
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional["User"]:  # type: ignore[return-value]
        """
        Retrieve a user by its ID.

        :param user_id: The ID of the user.
        :return: The user if found, otherwise None.
        """
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional["User"]:  # type: ignore[return-value]
        """
        Retrieve a user by their email address.

        :param email: The email address of the user.
        :return: The user with the specified email address, or None if not found.
        """
        ...

    @abstractmethod
    async def create(
        self,
        username: str,
        email: str,
        password_hash: str,
    ) -> "User":  # type: ignore[return-value]
        """
        Create a new user.

        :param username: The name of the user.
        :param email: The email address of the user.
        :param password_hash: The hashed password of the user.
        :return: None
        """
        ...

    @abstractmethod
    async def authenticate_user(self, email: EmailStr, password: str) -> Optional["User"]:  # type: ignore[return-value]
        """
        Authenticate a user by their email and password.

        :param email: The email address of the user.
        :param password: The password of the user.
        :return: The user if authenticated, otherwise None.
        """
        ...