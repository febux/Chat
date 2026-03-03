"""
DB session provider function for FastAPI.

This function retrieves a current DB session instance associated with the incoming FastAPI request.
The current DB session instance is expected to be initialized and stored in the FastAPI request's app state.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.sqlalchemy.utils import get_session

DbSession = Annotated[AsyncSession, Depends(get_session, use_cache=False, scope='request')]
