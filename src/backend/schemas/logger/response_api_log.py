"""
Response API log schema.
"""

import uuid

from pydantic import BaseModel, Field


class ResponseApiLog(BaseModel):
    """
    Schema for storing response API log.
    """

    id: uuid.UUID | None = Field(default_factory=uuid.uuid4)
    status_code: int | None = Field(default=None)
    response_body: dict | list | str | None = Field(default=None)
    process_time: float

    class Config:
        """
        Configures Pydantic model to allow arbitrary types.
        """

        allow_arbitrary_types = True
