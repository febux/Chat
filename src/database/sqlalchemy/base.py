"""
Base database model for common attributes.
Base mapped columns for common attributes.
"""

import json
import uuid
from datetime import date, datetime
from typing import Annotated

from sqlalchemy import UUID, Integer, MetaData, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.expression import text

from src.common.complex_serializer import ComplexEncoder

int_pk = Annotated[int, mapped_column(primary_key=True)]
uuid_pk = Annotated[uuid.UUID, mapped_column(primary_key=True, default=uuid.uuid4)]
created_at = Annotated[datetime, mapped_column(server_default=func.now())]
updated_at = Annotated[datetime, mapped_column(server_default=func.now(), onupdate=datetime.now)]
date_db = Annotated[date, mapped_column(nullable=False)]
str_uniq = Annotated[str, mapped_column(unique=True, nullable=False)]
str_null_true = Annotated[str, mapped_column(nullable=True)]


metadata_obj = MetaData()


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all database models.

    Defines common attributes and methods for all database models.
    """

    __abstract__ = True

    metadata = metadata_obj

    id: Mapped[int_pk] = mapped_column(Integer(), primary_key=True, autoincrement=True)

    def __repr__(self):
        dict_repr = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return json.dumps(dict_repr, cls=ComplexEncoder)


class BaseProps(AsyncAttrs, DeclarativeBase):
    """
    Base class for all database models with additional properties.

    Defines common properties and methods for all database models with additional properties.
    """
    __abstract__ = True

    metadata = metadata_obj

    id: Mapped[uuid_pk] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    def __repr__(self):
        dict_repr = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return json.dumps(dict_repr, cls=ComplexEncoder)
