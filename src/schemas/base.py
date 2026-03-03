"""
Base models for schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints
from pydantic.alias_generators import to_camel, to_snake
from pydantic.types import UuidVersion

Slug = Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True, min_length=3, max_length=64)]
ShortSlug = Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True, min_length=3, max_length=32)]
NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
ShortItemsList = Annotated[list[str], Field(max_length=5)]
NonEmptyDict = Annotated[dict, Field(min_length=1)]
NonEmptyList = Annotated[list, Field(min_length=1)]
UserEmailEmpty = Annotated[EmailStr | None, StringConstraints(to_lower=True, strip_whitespace=True)]
UserEmail = Annotated[EmailStr, StringConstraints(to_lower=True, strip_whitespace=True)]
Username = Annotated[str, StringConstraints(min_length=4, max_length=32)]
# Checking for a regular expression (e.g. hex string)
ChecksumString = Annotated[str, StringConstraints(pattern="^[a-fA-F0-9]{64}$")]
# Only from letters, without special characters and numbers
NameString = Annotated[str, StringConstraints(pattern=r"^[^0-9~`!@#$%^&*()_+\=\{\[\}\]\|\\:;\"<>\\\,\/?]*$")]
NameEmptyString = Annotated[
    str | None, StringConstraints(pattern=r"^[^0-9~`!@#$%^&*()_+\=\{\[\}\]\|\\:;\"<>\\\,\/?]*$")
]
ApiKey = Annotated[str, StringConstraints(pattern=r"^sk_\w{32}$")]
PhoneString = Annotated[str, StringConstraints(pattern=r"^\d{10,12}$")]
SmallPositiveInt = Annotated[int, Field(ge=1, le=100)]
Percentage = Annotated[float, Field(ge=0, le=100)]
UUIDv4 = Annotated[UUID, UuidVersion(4)]
TimeStamp = Annotated[datetime, Field(ge=datetime(2020, 1, 1))]
Amount = Annotated[Decimal, Field(gt=0, max_digits=24, decimal_places=2)]
AmountInCents = Annotated[int, Field(gt=0)]


class BaseCamelRequest(BaseModel):
    """
    Base schema for request payloads with config.
    """

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        extra="forbid",
        str_strip_whitespace=True,
    )


class BaseSnakeRequest(BaseModel):
    """
    Base schema for request payloads with config.
    """

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_snake,
        extra="forbid",
        str_strip_whitespace=True,
    )


class BaseExtraRequest(BaseModel):
    """
    Base schema for request payloads with config.
    """

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        str_strip_whitespace=True,
    )


class BaseResponse(BaseModel):
    """
    Base schema for response payloads with config.
    """

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        alias_generator=to_snake,
        extra="ignore",
        strict=True,
        json_encoders={
            datetime: lambda dt: dt.isoformat(),
            Decimal: str,
        },
    )


class BaseCamelDTO(BaseModel):
    """
    Base schema for data transfer objects with config.
    """

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="forbid",
        str_strip_whitespace=True,
        json_encoders={
            datetime: lambda dt: dt.isoformat(),
            Decimal: str,
        },
    )


class BaseSnakeDTO(BaseModel):
    """
    Base schema for data transfer objects with config.
    """

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        populate_by_name=True,
        alias_generator=to_snake,
        extra="forbid",
        str_strip_whitespace=True,
        json_encoders={
            datetime: lambda dt: dt.isoformat(),
            Decimal: str,
        },
    )
