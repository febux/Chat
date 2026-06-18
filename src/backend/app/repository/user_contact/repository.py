"""
User Contact repository module for CRUD operations on UserContact model.
"""
from typing import Sequence
from uuid import UUID

from sqlalchemy import select

from src.backend.app.models import UserContact
from src.backend.app.repository.meta import AbstractRepository


class UserContactRepository(AbstractRepository[UserContact]):
    """
    User Contact repository for CRUD operations on UserContact model.
    """

    _model = UserContact

    async def get_all_contacts_by_user_id(self, user_id: UUID) -> Sequence[UserContact]:
        query = select(self._model).filter(self._model.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalars().all()


repository = UserContactRepository
