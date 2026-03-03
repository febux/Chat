"""
Request API log schema.
"""

import uuid

from pydantic import BaseModel, Field


class RequestApiLog(BaseModel):
    """
    Schema for storing request API log.
    """

    id: uuid.UUID | None = Field(default_factory=uuid.uuid4)
    api_key: uuid.UUID | None = Field(default=None)
    ip_address: str | None = Field(default=None)
    path: str | None = Field(default=None)
    method: str | None = Field(default=None)
    request_body: dict | list | str | None = Field(default=None)
    query_params: dict | None = Field(default=None)
    path_params: dict | None = Field(default=None)
    headers: dict | None = Field(default=None)
    process_time: float

    class Config:
        """
        Configures Pydantic model to allow arbitrary types.
        """

        arbitrary_types_allowed = True
