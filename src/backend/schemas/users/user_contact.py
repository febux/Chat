from pydantic import Field

from src.backend.schemas.base import BaseSnakeRequest, UserEmail


class ContactRequest(BaseSnakeRequest):
    """
    Request body for adding another user as a contact by email.

    Using a JSON body (rather than a path parameter) keeps the email out of the
    URL: it is validated as ``EmailStr`` and never logged in plaintext in
    access logs.
    """

    email: UserEmail = Field(..., description="Email of the user to add as a contact")
