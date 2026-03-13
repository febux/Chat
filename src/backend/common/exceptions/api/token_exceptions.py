"""
Authentication with token exception classes definitions.
"""

from starlette import status
from src.backend.common.exceptions.api.client_exception import ClientAPIException


class TokenExpiredError(ClientAPIException):
    """
    Exception raised when the provided authentication token has expired.

    Inherits from:
        ClientAPIException: The base exception class for client API errors.
    """

    error = "Token expired"
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self) -> None:
        super().__init__(
            loc=["token"],
            msg="Token expired",
            error_type="token_expired",
            status_code=self.status_code,
        )


class TokenNotFoundError(ClientAPIException):
    """
    Exception raised when an authentication token is missing.

    Inherits from:
        ClientAPIException: The base exception class for client API errors.
    """

    error = "Token not found"
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self) -> None:
        super().__init__(
            loc=["token"],
            msg="Token not found",
            error_type="token_not_found",
            status_code=self.status_code,
        )


class InvalidJwtError(ClientAPIException):
    """
    Exception raised when the provided JWT token is invalid.

    Inherits from:
        ClientAPIException: The base exception class for client API errors.
    """

    error = "Invalid JWT token"
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self) -> None:
        super().__init__(
            loc=["token"],
            msg="Invalid JWT token",
            error_type="invalid_jwt",
            status_code=self.status_code,
        )


class ForbiddenError(ClientAPIException):
    """
    Exception raised when the user does not have sufficient permissions.

    Inherits from:
        ClientAPIException: The base exception class for client API errors.
    """

    error = "Forbidden"
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self) -> None:
        super().__init__(
            loc=["permissions"],
            msg="Forbidden",
            error_type="forbidden",
            status_code=self.status_code,
        )
