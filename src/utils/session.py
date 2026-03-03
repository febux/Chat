"""
Session management involves storing and managing user sessions in a secure and efficient manner.
"""

from datetime import datetime

from fastapi import Request

from src.core.logger.logger_factory import logger


def is_token_expired(unix_timestamp: int | None) -> bool:
    """
    Validates if the provided Unix timestamp is expired.
    If the timestamp is provided, calculate the difference in minutes between the current time and the provided timestamp.
    If the difference is less than or equal to zero, it means the timestamp is expired.
    If the timestamp is None, it means the session has not been started or the token has expired.

    :param unix_timestamp: Unix timestamp to be validated.
    :return: True if the timestamp is expired, False otherwise.
    """
    if unix_timestamp:
        datetime_from_unix = datetime.fromtimestamp(unix_timestamp)
        current_time = datetime.now()
        difference_in_minutes = (datetime_from_unix - current_time).total_seconds() / 60
        return difference_in_minutes <= 0

    return True


def validate_session(request: Request) -> bool:
    """
    Validates the session by checking if the provided Authorization and access_token are valid and not expired.
    Extract the Authorization and access_token from the request cookies.
    Check if the Authorization and access_token are valid and not expired.
    If either of them is missing or expired, log the issue and redirect the user to the login page.
    If both the Authorization and access_token are valid and not expired, log a successful session validation.

    :param request: Incoming FastAPI request.
    :return: True if the session is valid, False otherwise.
    """
    session_authorization = request.cookies.get("Authorization")
    session_id = request.session.get("session_id")
    session_access_token = request.session.get("access_token")
    token_exp = request.session.get("token_expiry")

    if not session_authorization and not session_access_token:
        logger.info("No Authorization and access_token in session, redirecting to login")
        return False

    if session_authorization != session_id:
        logger.info("Authorization does not match Session Id, redirecting to login")
        return False

    if is_token_expired(token_exp):
        logger.info("Access_token is expired, redirecting to login")
        return False

    logger.info("Valid Session, Access granted.")
    return True
