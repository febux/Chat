from datetime import datetime, timedelta, timezone

from jose import jwt

from src.backend.config.main import settings


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=366)
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(to_encode, settings.app.JWT_SECRET_KEY, algorithm=settings.app.JWT_ALGORITHM)
    return encode_jwt


def create_centrifugo_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(
        payload,
        settings.app.CENTRIFUGO_CLIENT_TOKEN_HMAC_SECRET_KEY,
        algorithm="HS256",
    )


def create_subscription_token(user_id: str, channel_id: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "channel": f"chat:{channel_id}",
        "exp": now + timedelta(hours=1),  # 30 минут
    }

    token = jwt.encode(
        claims,
        settings.app.CENTRIFUGO_CLIENT_SUBSCRIPTION_TOKEN_HMAC_SECRET_KEY,
        algorithm="HS256",
    )
    return token
