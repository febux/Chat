"""
Root conftest — sets test environment variables BEFORE any project imports.

This must execute first so the pydantic-settings config loads with test-safe
defaults instead of requiring a real .env or production secrets.
"""
import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `from src.backend...` resolves.
_PROJECT_ROOT = str(Path(__file__).parent.resolve())
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# --- Set test environment variables before any project code is imported ---
os.environ.setdefault("APP_MODE", "development")
os.environ.setdefault("TESTING_MODE", "true")
os.environ.setdefault("REDIS_USERNAME", "test_user")
os.environ.setdefault("REDIS_DEFAULT_PASSWORD", "test_pass")
os.environ.setdefault("REDIS_PASSWORD", "test_pass")
os.environ.setdefault("REDIS_EXTERNAL_PORT", "6379")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-not-for-production")
os.environ.setdefault("SESSION_SECRET_KEY", "test-session-secret-key")
os.environ.setdefault("AES_KEY", "dGVzdC1hZXMta2V5")  # base64("test-aes-key")
