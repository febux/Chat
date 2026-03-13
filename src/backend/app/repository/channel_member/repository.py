"""
Channel member repository module for CRUD operations on ChannelMember model.
"""
from typing import Sequence

from sqlalchemy import select

from src.backend.app.models import ChannelMember
from src.backend.app.repository.meta import AbstractRepository


class ChannelMemberRepository(AbstractRepository[ChannelMember]):
    """
    Channel member repository for CRUD operations on ChannelMember model.
    """

    _model = ChannelMember

    async def get_all_channel_members_by_channel_id(self, channel_id: int) -> Sequence[ChannelMember]:
        query = select(self._model).filter(self._model.channel_id == channel_id)
        result = await self.session.execute(query)
        return result.scalars().all()


repository = ChannelMemberRepository
