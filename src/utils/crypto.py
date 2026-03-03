"""
Crypto utils module
"""

import base64
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.config.main import settings


def encrypt_data(plaintext: str) -> str:
    """
    Encrypts data with AES-256-GCM. Returns the union of IV and ciphertext.
    """
    aesgcm = AESGCM(settings.app.aes_key)
    iv = os.urandom(12)  # 96 бит IV
    ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    encrypted = iv + ciphertext
    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_data(encrypted: str) -> str:
    """
    Decrypts the data, waits at the beginning of the IV with a length of 12 bytes.
    """
    aesgcm = AESGCM(settings.app.aes_key)
    encrypted_b64 = base64.b64decode(encrypted)
    iv = encrypted_b64[:12]
    ciphertext = encrypted_b64[12:]
    plaintext = aesgcm.decrypt(iv, ciphertext, None)
    return plaintext.decode("utf-8")


def create_random_session_string() -> str:
    """
    Creates a random session string.
    """
    return secrets.token_urlsafe(32)  # Generates a random URL-safe string
