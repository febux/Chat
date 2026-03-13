"""
Common query parameters for API requests.
"""

from pydantic import BaseModel, ConfigDict, Field


class CommonQueryParams(BaseModel):
    """
    Common query parameters for API requests.

    :param q: Search query.
    :param skip: Number of items to skip.
    :param limit: Maximum number of items to return.
    """

    model_config = ConfigDict(extra="ignore")

    q: str | None = Field(None)
    skip: int = Field(0, ge=0, le=100)
    limit: int = Field(0, ge=0)
