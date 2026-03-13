"""
CSRF cookie management.
"""

import secrets

from fastapi import HTTPException, Request, Response

from src.backend.config.main import settings


def issue_csrf(response: Response):
    """
    Issue a CSRF token and set it in the response's cookie.

    :param response: The FastAPI response object.
    :return: The CSRF token as a string.
    """
    token = secrets.token_urlsafe(24)
    response.set_cookie(settings.app.CSRF_COOKIE, token, httponly=False, secure=True, samesite="strict")
    return token


def verify_csrf(request: Request):
    """
    Verify the CSRF token in the request.

    :param request: The FastAPI request object.
    :return: True if the CSRF token is valid, False otherwise.
    """
    body_token = request.headers.get("x-csrf-token") or request.query_params.get("csrf")
    cookie_token = request.cookies.get(settings.app.CSRF_COOKIE)
    if not body_token or body_token != cookie_token:
        raise HTTPException(403, "CSRF check failed")
