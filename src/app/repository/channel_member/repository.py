"""
Channel member repository module for CRUD operations on ChannelMember model.
"""
from typing import Sequence
from uuid import UUID

from sqlalchemy import select, or_

from src.app.models import ChannelMember
from src.app.repository.meta import AbstractRepository


class ChannelMemberRepository(AbstractRepository[ChannelMember]):
    """
    Channel member repository for CRUD operations on ChannelMember model.
    """

    _model = ChannelMember
