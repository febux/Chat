"""
Unit tests for password hashing and verification utilities.
"""
import pytest

from src.backend.utils.password import (hash_password, hash_password_sync,
                                        verify_password, verify_password_sync)


class TestHashPassword:
    """Tests for hash_password() / hash_password_sync()."""

    @pytest.mark.asyncio
    async def test_async_hash_returns_string(self):
        hashed = await hash_password("MySecret123")
        assert isinstance(hashed, str)
        assert hashed != "MySecret123"

    def test_sync_hash_returns_string(self):
        hashed = hash_password_sync("MySecret123")
        assert isinstance(hashed, str)
        assert hashed != "MySecret123"

    @pytest.mark.asyncio
    async def test_async_hash_is_argon2_format(self):
        hashed = await hash_password("MySecret123")
        assert hashed.startswith("$argon2")

    @pytest.mark.asyncio
    async def test_same_password_produces_different_hashes(self):
        h1 = await hash_password("MySecret123")
        h2 = await hash_password("MySecret123")
        assert h1 != h2  # salt is random

    @pytest.mark.asyncio
    async def test_empty_password_produces_valid_hash(self):
        """argon2 accepts empty strings (min_length enforced at schema level, not here)."""
        hashed = await hash_password("")
        assert hashed.startswith("$argon2")


class TestVerifyPassword:
    """Tests for verify_password() / verify_password_sync()."""

    @pytest.mark.asyncio
    async def test_async_verify_correct_password(self):
        hashed = await hash_password("CorrectPass123")
        assert await verify_password("CorrectPass123", hashed) is True

    @pytest.mark.asyncio
    async def test_async_verify_wrong_password(self):
        hashed = await hash_password("CorrectPass123")
        assert await verify_password("WrongPass456", hashed) is False

    def test_sync_verify_correct_password(self):
        hashed = hash_password_sync("CorrectPass123")
        assert verify_password_sync("CorrectPass123", hashed) is True

    def test_sync_verify_wrong_password(self):
        hashed = hash_password_sync("CorrectPass123")
        assert verify_password_sync("WrongPass456", hashed) is False

    @pytest.mark.asyncio
    async def test_verify_with_invalid_digest_returns_false(self):
        """verify_password should return False (not raise) on a corrupt digest."""
        assert await verify_password("any", "not-a-valid-hash") is False

    @pytest.mark.asyncio
    async def test_roundtrip_hash_then_verify(self):
        hashed = await hash_password("RoundtripPass99")
        assert await verify_password("RoundtripPass99", hashed) is True
        assert await verify_password("different", hashed) is False
