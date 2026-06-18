"""
Unit tests for JWT auth utilities: token creation, decoding, and expiry logic.
"""
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from src.backend.app.utils.auth import (create_access_token,
                                        create_centrifugo_token,
                                        create_subscription_token)
from src.backend.config.main import settings


class TestCreateAccessToken:
    """Tests for create_access_token()."""

    def test_returns_valid_jwt_string(self):
        token = create_access_token({"sub": "user-123"})
        assert isinstance(token, str)
        assert token.count(".") == 2  # header.payload.signature

    def test_payload_contains_subject(self):
        token = create_access_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.app.JWT_SECRET_KEY, algorithms=[settings.app.JWT_ALGORITHM])
        assert payload["sub"] == "user-123"

    def test_payload_contains_future_expiry(self):
        token = create_access_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.app.JWT_SECRET_KEY, algorithms=[settings.app.JWT_ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > datetime.now(timezone.utc)

    def test_expiry_is_approximately_one_year(self):
        token = create_access_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.app.JWT_SECRET_KEY, algorithms=[settings.app.JWT_ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        delta = exp - datetime.now(timezone.utc)
        # 366 days — allow a small window for test execution time
        assert timedelta(days=365) < delta < timedelta(days=367)

    def test_does_not_mutate_input_dict(self):
        original = {"sub": "user-123"}
        create_access_token(original)
        assert original == {"sub": "user-123"}

    def test_token_decodable_with_correct_secret(self):
        token = create_access_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.app.JWT_SECRET_KEY, algorithms=[settings.app.JWT_ALGORITHM])
        assert "exp" in payload

    def test_token_rejected_with_wrong_secret(self):
        token = create_access_token({"sub": "user-123"})
        with pytest.raises(Exception):
            jwt.decode(token, "wrong-secret", algorithms=[settings.app.JWT_ALGORITHM])


class TestCreateCentrifugoToken:
    """Tests for create_centrifugo_token()."""

    def test_returns_valid_jwt(self):
        token = create_centrifugo_token("user-456")
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_payload_has_subject_and_expiry(self):
        token = create_centrifugo_token("user-456")
        payload = jwt.decode(
            token,
            settings.app.CENTRIFUGO_CLIENT_TOKEN_HMAC_SECRET_KEY,
            algorithms=["HS256"],
        )
        assert payload["sub"] == "user-456"
        assert "exp" in payload

    def test_expiry_is_one_hour(self):
        token = create_centrifugo_token("user-456")
        payload = jwt.decode(
            token,
            settings.app.CENTRIFUGO_CLIENT_TOKEN_HMAC_SECRET_KEY,
            algorithms=["HS256"],
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        delta = exp - datetime.now(timezone.utc)
        assert timedelta(minutes=59) < delta < timedelta(minutes=61)


class TestCreateSubscriptionToken:
    """Tests for create_subscription_token()."""

    def test_returns_valid_jwt(self):
        token = create_subscription_token("user-789", "channel-abc")
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_payload_has_channel_claim(self):
        token = create_subscription_token("user-789", "channel-abc")
        payload = jwt.decode(
            token,
            settings.app.CENTRIFUGO_CLIENT_SUBSCRIPTION_TOKEN_HMAC_SECRET_KEY,
            algorithms=["HS256"],
        )
        assert payload["sub"] == "user-789"
        assert payload["channel"] == "chat:channel-abc"

    def test_expiry_is_one_hour(self):
        token = create_subscription_token("user-789", "channel-abc")
        payload = jwt.decode(
            token,
            settings.app.CENTRIFUGO_CLIENT_SUBSCRIPTION_TOKEN_HMAC_SECRET_KEY,
            algorithms=["HS256"],
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        delta = exp - datetime.now(timezone.utc)
        assert timedelta(minutes=59) < delta < timedelta(minutes=61)
