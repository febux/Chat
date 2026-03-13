"""
Module to generate hashes using MD5, SHA-1, and SHA-256 algorithms.
"""

import hashlib
import os


def hash_md5(text: str) -> str:
    """Generating an MD5 hash from a string"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def hash_sha1(text: str) -> str:
    """Generating a SHA-1 hash from a string"""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def hash_sha256(text: str) -> str:
    """Generating a SHA-256 hash from a string"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hashing(text: str, algorithm: str = "sha256") -> str:
    """
    Hash generation with the specified algorithm.
    The default is SHA-256.

    :param text: The text to hash.
    :param algorithm: The hashing algorithm to use.
    :return: The hashed text.
    """
    hash_input = text.encode("utf-8")
    if algorithm == "md5":
        return hashlib.md5(hash_input).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(hash_input).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(hash_input).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def generate_salt(length: int = 16) -> str:
    """Random salt generation at the right length"""
    return os.urandom(length).hex()


def hash_with_salt(text: str, salt: str, algorithm: str = "sha256") -> str:
    """
    Hash generation with salt.
    The default is SHA-256.

    :param text: The text to hash.
    :param salt: The salt to use for hashing.
    :param algorithm: The hashing algorithm to use.
    :return: The hashed text with the salt.
    """
    hash_input = (salt + text).encode("utf-8")
    if algorithm == "md5":
        return hashlib.md5(hash_input).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(hash_input).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(hash_input).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def verify_hash_with_salt(text: str, salt: str, hash_to_check: str, algorithm: str = "sha256") -> bool:
    """Checking if the hash matches the input and salt"""
    return hash_with_salt(text, salt, algorithm) == hash_to_check


def verify_hash(text: str, hash_to_check: str, algorithm: str = "sha256") -> bool:
    """Checking if the hash matches the input"""
    return hashing(text, algorithm) == hash_to_check
