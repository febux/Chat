from starlette import status

from src.backend.common.exceptions.api import ClientAPIException


class UserAlreadyExistsError(ClientAPIException):
    """
    Exception raised when attempting to create a user that already exists.

    Inherits from:
        ClientAPIException: The base exception class for client API errors.
    """

    error = "User already exists"
    status_code = status.HTTP_409_CONFLICT

    def __init__(self) -> None:
        super().__init__(
            loc=["user"],
            msg="User already exists",
            error_type="user_already_exists",
            status_code=self.status_code,
        )


class UserIdNotFoundError(ClientAPIException):
    """
    Exception raised when the user ID cannot be found or resolved.

    Inherits from:
        ClientAPIException: The base exception class for client API errors.
    """

    error = "User ID not found"
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self) -> None:
        super().__init__(
            loc=["user_id"],
            msg="User ID not found",
            error_type="user_id_not_found",
            status_code=self.status_code,
        )


class UserNotFoundError(ClientAPIException):
    """
    Exception raised when the user cannot be found or resolved.

    Inherits from:
        ClientAPIException: The base exception class for client API errors.
    """

    error = "User not found"
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self) -> None:
        super().__init__(
            loc=["user_id"],
            msg="User ID not found",
            error_type="user_id_not_found",
            status_code=self.status_code,
        )
