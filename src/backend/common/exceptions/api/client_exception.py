"""
Client API exception class definition.
"""

from starlette import status


class ClientAPIException(Exception):
    """
    Custom exception class for client-side API errors.

    This exception is raised when a client-side error occurs during API operations.
    It provides information about the error type, details, and HTTP status code.

    Attributes:
        error (str): A general description of the error type.
        status_code (int): The HTTP status code associated with the error.
    """

    error = "Client side error"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(
        self,
        loc: list | None = None,
        msg: str | None = None,
        error_type: str | None = None,
        status_code: int | None = None,
    ):
        self.detail = [
            {"loc": loc or ["client"], "msg": msg or "Client error occurred.", "type": error_type or "client_error"}
        ]
        self.status_code = status_code or self.status_code
        super().__init__(self.detail)

    def to_dict(self):
        """
        Convert the exception information to a dictionary.

        :return: A dictionary containing the error message, details, and HTTP status code.
        """
        return {"detail": self.detail}

    def __reduce__(self):
        """
        Reduce the ClientAPIException instance for pickling.

        This method is used to provide instructions for pickling the exception object.

        :return: A tuple containing the class and a tuple of arguments for reconstructing the exception.
        """
        d = self.detail[0]
        return ClientAPIException, (d["loc"], d["msg"], d["type"], self.status_code)
