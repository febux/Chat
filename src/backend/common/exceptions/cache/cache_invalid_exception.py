"""
Cache exceptions
"""


class CacheInvalidException(Exception):
    """Exception raised when cache is invalid"""

    error: str = "Cache invalid"
