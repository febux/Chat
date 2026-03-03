"""
Connection failed exception class definition.
"""

from src.common.exceptions.common.base_app_exception import BaseAppException


class ConnectionFailedException(BaseAppException):
    """
    Exception raised when a connection attempt fails.

    This exception is used to indicate that a connection to a remote service,
    database, or any other external resource has failed.

    Attributes:
        error (str): A string describing the error, set to "Connection failed" by default.

    Inherits from:
        BaseAppException: The base exception class for the application.
    """

    error: str = "Connection failed"
