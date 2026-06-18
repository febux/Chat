"""
User service implementation.
"""
from typing import Optional, Sequence
from uuid import UUID

import arrow
import redis.asyncio as redis
from pydantic import EmailStr

from src.backend.core.logger.logger_factory import logger_bind
from src.backend.database.sqlalchemy.orm_manager.meta import \
    RepositoryManagerMeta
from src.backend.schemas.users.user_get import User
from src.backend.utils.password import verify_password

REDIS_PREFIX_STATUS = "user:status:"
REDIS_PREFIX_LAST_SEEN = "user:last_seen:"
ONLINE_TTL_SECONDS = 90  # сколько секунд после пинга считаем онлайном
# last_seen должен переживать offline-статус (показывается как "был в сети"),
# но не расти бесконечно — каждое письмо обновляет TTL.
LAST_SEEN_TTL_SECONDS = 30 * 24 * 3600


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
        self.user_contact_repo = self.orm_manager.user_contact

    @staticmethod
    def _to_user_schema(user) -> User:
        """
        Map a User ORM model (or any object exposing the same attributes) onto
        the public ``User`` schema.

        This is the single boundary that strips sensitive fields such as
        ``password_hash`` before a user object reaches the API layer. Every
        service method consumed by a route must funnel through it.

        :param user: The ORM user instance.
        :return: A clean ``User`` schema safe to serialize and return.
        """
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

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
        users = await self.user_repo.get_all(
            q=q,
            skip=skip,
            limit=limit,
        )
        return [self._to_user_schema(u) for u in users]

    async def get_current_user_contacts(self, user_id: UUID) -> list[User]:
        """
        Retrieve all contacts of the current user.

        :param user_id: ID of the user.
        :return: A list of users.
        """
        users = await self.user_repo.get_current_user_contacts(user_id=user_id)
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

            status: str = raw_status.decode() if raw_status else "offline"
            last_seen_int = int(raw_last_seen) if raw_last_seen else None

            user_schema = self._to_user_schema(user)
            user_schema.status = status
            user_schema.last_seen = last_seen_int
            result.append(user_schema)

        return result

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Retrieve a user by its ID.

        :param user_id: The ID of the user.
        :return: The user with the specified ID, or None if not found.
        """
        user = await self.user_repo.read_one(id=user_id)
        return self._to_user_schema(user) if user else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by their email address.

        :param email: The email address of the user.
        :return: The user with the specified email address, or None if not found.
        """
        user = await self.user_repo.read_one(email=email)
        return self._to_user_schema(user) if user else None

    async def authenticate_user(self, email: EmailStr, password: str) -> Optional[User]:
        """
        Authenticate a user by email and password.

        The raw ORM model is fetched directly from the repository because
        password verification needs ``password_hash``, which the public schema
        intentionally does not expose. Only a clean schema is returned.

        :param email: The email address of the user.
        :param password: The plaintext password to verify.
        :return: The authenticated user schema, or None if credentials are invalid.
        """
        user = await self.user_repo.read_one(email=email)
        if not user or await verify_password(pw=password, digest=user.password_hash) is False:
            return None
        return self._to_user_schema(user)

    async def set_user_ping(self, user_id: UUID) -> None:
        """
        Update the last ping timestamp for a user.

        :param user_id: The ID of the user.
        :return: The updated user.
        """
        uid = str(user_id)
        now_ts = int(arrow.utcnow().timestamp())

        pipe = self.redis_client.pipeline()
        await pipe.set(REDIS_PREFIX_STATUS + uid, "online", ex=ONLINE_TTL_SECONDS)
        await pipe.set(REDIS_PREFIX_LAST_SEEN + uid, now_ts, ex=LAST_SEEN_TTL_SECONDS)
        await pipe.execute()

    async def create(
        self,
        username: str,
        email: EmailStr,
        password_hash: str,
        **kwargs,
    ) -> User:
        """
        Create a new user.

        :param username: The name of the user.
        :param email: The email address of the user.
        :param password_hash: The hashed password of the user.
        :return: The created user.
        """
        async with self.orm_manager.transaction():
            user = await self.user_repo.create(
                username=username,
                email=email,
                password_hash=password_hash,
                **kwargs,
            )
            return self._to_user_schema(user)

    async def contact_user(self, user_id: UUID, contact_email: str) -> bool:
        """
        Add a contact to the current user.

        :param user_id: ID of the user.
        :param contact_email: Email of the contact.
        :return: True if the contact was added, False otherwise.
        """
        contact = await self.get_by_email(email=contact_email)
        if not contact:
            self.logger.info(f"User {user_id} tried to add contact {contact_email} but the contact does not exist")
            return False

        if user_id == contact.id:
            self.logger.info(f"User {user_id} tried to add themselves as a contact")
            return False

        # Check both directions, since contacts are queried bidirectionally.
        if user_contact := await self.user_contact_repo.read_one(
            user_id=user_id,
            contact_id=contact.id,
        ):
            self.logger.info(f"User {user_contact.user_id} already has contact {user_contact.contact_id}")
            return False
        if user_contact := await self.user_contact_repo.read_one(
            user_id=contact.id,
            contact_id=user_id,
        ):
            self.logger.info(f"User {user_id} already has contact {contact.id} (reverse entry)")
            return False
        async with self.orm_manager.transaction():
            await self.user_contact_repo.create(
                user_id=user_id,
                contact_id=contact.id,
            )
        self.logger.info(f"User {user_id} added contact {contact.id}")
        return True
