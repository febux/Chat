"""
Cookie management and authentication.
"""

from fastapi import Request, Response


def get_cookie(request: Request, cookie_key: str) -> str | None:
    """
    Retrieve a cookie value from the incoming FastAPI request.

    :param request: The incoming FastAPI request.
    :param cookie_key: The key of the cookie to retrieve
    :return: The value of the cookie, or None if the cookie doesn't exist.
    """
    return request.cookies.get(cookie_key)


def set_cookie(response: Response, cookie_key: str, cookie_value: str):
    """
    Set a cookie value in the outgoing FastAPI response.

    :param response: The outgoing FastAPI response.
    :param cookie_key: The key of the cookie to set.
    :param cookie_value: The value of the cookie to set.
    """
    response.set_cookie(
        cookie_key,
        cookie_value,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=3600,
    )
