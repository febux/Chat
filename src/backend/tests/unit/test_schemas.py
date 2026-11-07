"""
Unit tests for Pydantic schema validation: UserRegister, UserAuth, User.
"""
from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.backend.schemas.users.user_auth import UserAuth
from src.backend.schemas.users.user_get import User
from src.backend.schemas.users.user_register import UserRegister


class TestUserRegister:
    """Tests for the UserRegister schema."""

    def test_valid_registration(self):
        reg = UserRegister(
            email="alice@example.com",
            password="Secret123",
            password_check="Secret123",
            username="alice",
        )
        assert reg.email == "alice@example.com"
        assert reg.username == "alice"

    def test_email_is_lowercased_and_trimmed(self):
        reg = UserRegister(
            email="  ALICE@Example.COM  ",
            password="Secret123",
            password_check="Secret123",
            username="alice",
        )
        assert reg.email == "alice@example.com"

    def test_empty_password_rejected(self):
        """Empty password is rejected by the Password constraint."""
        with pytest.raises(ValidationError):
            UserRegister(
                email="alice@example.com",
                password="",
                password_check="",
                username="alice",
            )

    def test_short_password_rejected(self):
        """Password must be at least 8 characters long."""
        with pytest.raises(ValidationError):
            UserRegister(
                email="alice@example.com",
                password="x",
                password_check="x",
                username="alice",
            )

    def test_short_username_rejected(self):
        """Username must be at least 3 characters long."""
        with pytest.raises(ValidationError):
            UserRegister(
                email="alice@example.com",
                password="Secret123",
                password_check="Secret123",
                username="ab",
            )

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            UserRegister(
                email="not-an-email",
                password="Secret123",
                password_check="Secret123",
                username="alice",
            )

    def test_extra_field_rejected(self):
        """BaseSnakeRequest uses extra='forbid'."""
        with pytest.raises(ValidationError):
            UserRegister(
                email="alice@example.com",
                password="Secret123",
                password_check="Secret123",
                username="alice",
                rogue_field="nope",
            )

    def test_empty_username_rejected(self):
        """Username must be at least 3 characters long; empty is rejected."""
        with pytest.raises(ValidationError):
            UserRegister(
                email="alice@example.com",
                password="Secret123",
                password_check="Secret123",
                username="",
            )


class TestUserAuth:
    """Tests for the UserAuth (login) schema."""

    def test_valid_auth(self):
        auth = UserAuth(email="bob@example.com", password="Secret123")
        assert auth.email == "bob@example.com"

    def test_short_password_rejected(self):
        """Password must be at least 8 characters long."""
        with pytest.raises(ValidationError):
            UserAuth(email="bob@example.com", password="abc")

    def test_empty_password_rejected(self):
        """Empty password is rejected by the Password constraint."""
        with pytest.raises(ValidationError):
            UserAuth(email="bob@example.com", password="")

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            UserAuth(email="bad-email", password="Secret123")

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            UserAuth(email="bob@example.com", password="Secret123", extra="no")


class TestUserResponse:
    """Tests for the User response schema."""

    def test_valid_user(self):
        now = datetime.now()
        u = User(
            id=uuid4(),
            username="alice",
            email="alice@example.com",
            status="online",
            last_seen=1700000000,
            created_at=now,
            updated_at=now,
        )
        assert u.username == "alice"
        assert u.status == "online"

    def test_optional_fields_accept_none(self):
        now = datetime.now()
        u = User(
            id=uuid4(),
            username="alice",
            email="alice@example.com",
            status=None,
            last_seen=None,
            created_at=now,
            updated_at=now,
        )
        assert u.status is None
        assert u.last_seen is None

    def test_empty_username_rejected(self):
        """min_length=1 from NonEmptyString IS enforced for User schema too."""
        now = datetime.now()
        with pytest.raises(ValidationError):
            User(
                id=uuid4(),
                username="",
                email="alice@example.com",
                created_at=now,
                updated_at=now,
            )

    def test_missing_required_field_rejected(self):
        with pytest.raises(ValidationError):
            User(  # missing username, email, created_at, updated_at
                id=uuid4(),
            )
