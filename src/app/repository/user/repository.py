"""
User repository module for CRUD operations on User model.
"""
from typing import Sequence
from uuid import UUID

from sqlalchemy import select, or_

from src.app.models import User
from src.app.repository.meta import AbstractRepository


class UserRepository(AbstractRepository[User]):
    """
    User repository for CRUD operations on User model.
    """

    _model = User

    async def get_all(
        self,
        q: str | None = None,
        skip: int = 0,
        limit: int = 0,
    ) -> Sequence[User]:
        """
        Retrieve all users.

        :param q: Search query for filtering users.
        :param skip: Number of users to skip before retrieving results.
        :param limit: Maximum number of users to retrieve.
        :return: A list of users.
        """
        query = select(self.model)
        if q:
            query = query.filter(or_(self.model.email.ilike(f"%{q}%"), self.model.username.ilike(f"%{q}%")))

        if skip > 0:
            query = query.offset(skip)
        if limit > 0:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_all_except_of_current_user(self, user_id: UUID) -> Sequence[User]:
        """
        Retrieve all users except the current user.

        :param user_id: ID of the user to exclude from the results.
        :return: A list of users.
        """
        query = select(self.model).filter(self.model.id != user_id)
        result = await self.session.execute(query)
        return result.scalars().all()


repository = UserRepository
