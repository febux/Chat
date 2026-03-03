from datetime import datetime, timedelta, timezone

from jose import jwt

from src.config.main import settings


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=366)
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(to_encode, settings.app.JWT_SECRET_KEY, algorithm=settings.app.JWT_ALGORITHM)
    return encode_jwt
