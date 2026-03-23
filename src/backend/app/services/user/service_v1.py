"""
User service implementation.
"""
from typing import Optional, Sequence
from uuid import UUID

import arrow
import redis.asyncio as redis
from pydantic import EmailStr

from src.backend.core.logger.logger_factory import logger_bind
from src.backend.database.sqlalchemy.orm_manager.meta import RepositoryManagerMeta
from src.backend.utils.password import verify_password
from src.backend.schemas.users.user_get import User as UserResponse

REDIS_PREFIX_STATUS = "user:status:"
REDIS_PREFIX_LAST_SEEN = "user:last_seen:"
ONLINE_TTL_SECONDS = 90  # сколько секунд после пинга считаем онлайном


class UserService:
    """
    A service class for handling user operations.
    """

    def __init__(
        self,
        orm_manager: RepositoryManagerMeta,
        redis_client: redis.Redis,
    ):
        self.orm_manager = orm_manager
        self.redis_client = redis_client
        self.logger = logger_bind("UserService")

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

    async def get_all_except_of_current_user(self, user_id: UUID) -> list[UserResponse]:
        """
        Retrieve all users except the current user.

        :param user_id: ID of the user to exclude from the results.
        :return: A list of users.
        """
        users = await self.user_repo.get_all_except_of_current_user(user_id=user_id)
        ids = [str(u.id) for u in users]
        pipe = self.redis_client.pipeline()
        for uid in ids:
            await pipe.get(REDIS_PREFIX_STATUS + uid)
            await pipe.get(REDIS_PREFIX_LAST_SEEN + uid)
        raw = await pipe.execute()

        result = []
        for i, user in enumerate(users):
            raw_status: bytes = raw[2 * i]  # get status
            raw_last_seen: bytes = raw[2 * i + 1]  # get last_seen ts or None

            # если ключа нет → считаем offline
            status: str = raw_status.decode() if raw_status else "offline"
            last_seen_int = int(raw_last_seen) if raw_last_seen else None

            result.append(
                UserResponse(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    status=status,
                    last_seen=last_seen_int,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                )
            )

        return result

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

    async def set_user_ping(self, user_id: UUID) -> None:  # type: ignore[return-value]
        """
        Update the last ping timestamp for a user.

        :param user_id: The ID of the user.
        :return: The updated user.
        """
        user_id = str(user_id)
        now_ts = int(arrow.utcnow().timestamp())

        pipe = self.redis_client.pipeline()
        await pipe.set(REDIS_PREFIX_STATUS + user_id, "online", ex=ONLINE_TTL_SECONDS)
        await pipe.set(REDIS_PREFIX_LAST_SEEN + user_id, now_ts)
        await pipe.execute()

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
