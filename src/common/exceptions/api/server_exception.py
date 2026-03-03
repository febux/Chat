"""
Server API exception class definition.
"""

from starlette import status


class ServerAPIException(Exception):
    """
    Exception raised for server errors (5xx).

    Attributes:
        error (str): A brief description of the server side error.
        status_code (int): HTTP status code for the server error. Defaults to 500.
    """

    error = "Server side error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        loc: list | None = None,
        msg: str | None = None,
        error_type: str | None = None,
    ):
        self.detail = [
            {"loc": loc or ["server"], "msg": msg or "Internal server error.", "type": error_type or "server_error"}
        ]
        super().__init__(self.detail)

    def to_dict(self):
        """
        Convert the exception information to a dictionary.

        :return: A dictionary containing the error message, details, and HTTP status code.
        """
        return {"detail": self.detail}

    def __reduce__(self):
        """
        Reduce the ServerAPIException instance for pickling.

        This method is used to provide instructions for pickling the exception object.

        :return: A tuple containing the class and a tuple of arguments for reconstructing the exception.
        """
        detail_dict = self.detail[0]
        return ServerAPIException, (detail_dict["loc"], detail_dict["msg"], detail_dict["type"])
