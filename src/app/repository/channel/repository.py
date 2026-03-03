"""
Channel repository module for CRUD operations on Channel model.
"""
from typing import Sequence
from uuid import UUID

from sqlalchemy import select, or_

from src.app.models import Channel
from src.app.repository.meta import AbstractRepository


class ChannelRepository(AbstractRepository[Channel]):
    """
    Channel repository for CRUD operations on Channel model.
    """

    _model = Channel
