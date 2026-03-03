"""
Password encryption and decryption using bcrypt methods.
"""

import asyncio

from passlib.hash import argon2  # type: ignore[missing-module]

from src.core.logger.logger_factory import logger_bind

logger = logger_bind("PasswordUtils")

argon2_hasher = argon2.using(rounds=12, memory_cost=65536, parallelism=4)


async def hash_password(pw: str) -> str:
    """
    Asynchronously hashes a password with bcrypt and 12 rounds.

    :param pw: The password to hash.
    :return: The hashed password.
    """
    try:
        return await asyncio.to_thread(argon2_hasher.hash, pw)
    except Exception as e:
        logger.exception(f"Failed to hash password: {e}")
        raise e


def hash_password_sync(pw: str) -> str:
    """
    Synchronously hashes a password with bcrypt and 12 rounds.

    :param pw: The password to hash.
    :return: The hashed password.
    """
    return argon2_hasher.hash(pw)


async def verify_password(pw: str, digest: str) -> bool:
    """
    Verifies the password asynchronously using bcrypt.

    :param pw: The password to verify.
    :param digest: The hashed password to compare against.
    :return: True if the password matches the digest, False otherwise.
    """
    try:
        return await asyncio.to_thread(argon2_hasher.verify, pw, digest)
    except Exception as e:
        logger.error(f"Failed to verify password: {e}")
        return False


def verify_password_sync(pw: str, digest: str) -> bool:
    """
    Verifies the password synchronously using bcrypt.

    :param pw: The password to verify.
    :param digest: The hashed password to compare against.
    :return: True if the password matches the digest, False otherwise.
    """
    return argon2_hasher.verify(pw, digest)
