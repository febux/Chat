"""
ETag middleware with selective caching.
"""

import hashlib
from typing import List, Optional, Callable

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.backend.config.main import settings


class ETagMiddleware(BaseHTTPMiddleware):
    """
    ETag middleware with selective caching based on paths, headers, and response flags.
    """

    def __init__(
        self,
        app: ASGIApp,
        cache_paths: Optional[List[str]] = None,
        cache_headers: Optional[List[str]] = None,
        skip_paths: Optional[List[str]] = None,
        cache_ttl: Optional[int] = None,
    ):
        super().__init__(app)
        self.cache_paths = cache_paths or []
        self.cache_headers = cache_headers or []
        self.skip_paths = skip_paths or []
        self.cache_ttl = cache_ttl or getattr(settings, 'app', type('obj', (), {'CACHE_ETAG_TTL': 300})()).CACHE_ETAG_TTL

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Processes the request and applies ETag caching logic selectively.

        :param request: Incoming FastAPI Request
        :param call_next: Next middleware in chain
        :return: Response with/without ETag caching
        """
        # Пропускаем не-GET или проблемные статусы
        if request.method != "GET":
            return await call_next(request)

        # Пропускаем пути из skip_paths
        if any(request.url.path.startswith(skip_path) for skip_path in self.skip_paths):
            return await call_next(request)

        # Кэшируем только разрешенные пути (если список задан)
        if self.cache_paths and not any(
            request.url.path.startswith(cache_path) for cache_path in self.cache_paths
        ):
            return await call_next(request)

        response: Response = await call_next(request)

        # Кэшируем только успешные ответы
        if response.status_code != 200:
            return response

        # Проверяем response headers (флаг от эндпоинта)
        if response.headers.get("X-No-Cache") == "true":
            return response

        # Проверяем request headers
        if not any(request.headers.get(header) for header in self.cache_headers):
            return response

        # Генерируем ETag
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        etag = hashlib.blake2b(body, digest_size=8).hexdigest()
        if_none_match = request.headers.get("if-none-match")

        if if_none_match == etag:
            return Response(
                status_code=304,
                headers={
                    "ETag": etag,
                    "Cache-Control": f"public, max-age={self.cache_ttl}",
                    "Vary": "Accept-Encoding",
                },
            )

        # Возвращаем с ETag
        return Response(
            content=body,
            status_code=response.status_code,
            headers={
                **dict(response.headers),
                "ETag": etag,
                "Cache-Control": f"public, max-age={self.cache_ttl}",
                "Vary": "Accept-Encoding",
            },
        )
