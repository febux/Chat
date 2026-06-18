"""
This module defines the protocol for user services.
"""

from abc import abstractmethod
from typing import Optional, Protocol, Sequence
from uuid import UUID

from pydantic import EmailStr

from src.backend.schemas.users.user_get import User


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
    ) -> Sequence[User]:
        """
        Retrieving all users with filters and limits.

        :param q: The query string for filtering users.
        :param skip: The number of records to skip.
        :param limit: The maximum number of records to return.
        :return: A sequence of users that match the specified filters.
        """
        ...

    @abstractmethod
    async def get_current_user_contacts(self, user_id: UUID) -> Sequence[User]:
        """
        Retrieve all contacts of the current user.

        :param user_id: ID of the user.
        :return: A list of users.
        """
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Retrieve a user by its ID.

        :param user_id: The ID of the user.
        :return: The user if found, otherwise None.
        """
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
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
    ) -> User:
        """
        Create a new user.

        :param username: The name of the user.
        :param email: The email address of the user.
        :param password_hash: The hashed password of the user.
        :return: None
        """
        ...

    @abstractmethod
    async def contact_user(self, user_id: UUID, contact_email: str) -> bool:
        """
        Add a contact to the current user.

        :param user_id: ID of the user.
        :param contact_email: ID of the contact.
        :return: None
        """
        ...

    @abstractmethod
    async def authenticate_user(self, email: EmailStr, password: str) -> Optional[User]:
        """
        Authenticate a user by their email and password.

        :param email: The email address of the user.
        :param password: The password of the user.
        :return: The user if authenticated, otherwise None.
        """
        ...

    @abstractmethod
    async def set_user_ping(self, user_id: UUID) -> None:
        """
        Update the last ping timestamp for a user.

        :param user_id: The ID of the user.
        :return: The updated user.
        """
        ...
