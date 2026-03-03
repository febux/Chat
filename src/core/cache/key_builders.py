"""
Key builders module for cache keys
"""

from src.common.complex_serializer import complex_serializer_json_dumps


def response_cache_key(*args, **kwargs):
    """
    Builds a cache key for a response based on the request method, URL, and query parameters.

    :param args: The positional arguments from the request.
    :param kwargs: The keyword arguments from the request.
    :return: The cache key as a string.
    """
    # Combine the request method, URL, and query parameters into a cache key
    # Use lowercase method names and URL paths for consistency
    # Serialize complex data structures using the complex_serializer_json_dumps function
    return "::".join(
        [
            args[0].method.lower(),
            args[0].url.lower(),
            complex_serializer_json_dumps(args[0].get_args()),
            complex_serializer_json_dumps(kwargs),
        ]
    )
