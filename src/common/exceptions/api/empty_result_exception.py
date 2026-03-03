"""
Empty result error exception class definition.
"""

from starlette import status

from src.common.exceptions.api.client_exception import ClientAPIException


class EmptyResultError(ClientAPIException):
    """
    Exception raised when an empty result is received from a service.

    This exception is used to handle cases where a service call
    returns an empty result when a non-empty result was expected.

    Attributes:
        error (str): A string describing the error, set to "Empty result received" by default.
        status_code (int): The HTTP status code for the exception, set to 404 by default.

    Inherits from:
        ClientAPIException: The base exception class for client API errors.
    """

    status_code = status.HTTP_404_NOT_FOUND
