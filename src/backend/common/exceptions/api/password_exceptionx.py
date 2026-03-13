from starlette import status

from src.backend.common.exceptions.api import ClientAPIException


class PasswordMismatchError(ClientAPIException):
    """
    Exception raised when the provided passwords do not match.

    Inherits from:
        ClientAPIException: The base exception class for client API errors.
    """

    error = "Password mismatch"
    status_code = status.HTTP_409_CONFLICT

    def __init__(self) -> None:
        super().__init__(
            loc=["password"],
            msg="Password mismatch",
            error_type="password_mismatch",
            status_code=self.status_code,
        )


class IncorrectEmailOrPasswordError(ClientAPIException):
    """
    Exception raised when email or password is incorrect during authentication.

    Inherits from:
        ClientAPIException: The base exception class for client API errors.
    """

    error = "Incorrect email or password"
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self) -> None:
        super().__init__(
            loc=["auth"],
            msg="Incorrect email or password",
            error_type="incorrect_email_or_password",
            status_code=self.status_code,
        )