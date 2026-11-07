"""
Admin authorization dependency.

Enforces that the current authenticated user has admin privileges.
"""
from typing import Annotated

from fastapi import Depends

from src.backend.app.utils.current_user import get_current_user
from src.backend.common.exceptions.api.token_exceptions import ForbiddenError
from src.backend.schemas.users.user_get import User


async def require_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency that requires the authenticated user to be an admin.

    :param current_user: The authenticated user from the current request.
    :return: The authenticated admin user.
    :raises ForbiddenError: If the user is not an admin.
    """
    if not current_user.is_admin:
        raise ForbiddenError
    return current_user
