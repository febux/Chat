"""
Stale While Revalidation (SWR) middleware for FastAPI.

This middleware caches responses to GET requests and serves them from cache for the specified TTL (Time To Live).

The middleware also implements a stale-while-revalidate policy, where it serves cached responses for the specified TTL,
but also includes a 5-second delay to allow for any updates to the cached response to propagate to the client.
"""

import asyncio
import time

from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware


class SWRMiddleware(BaseHTTPMiddleware):
    """
    Stale While Revalidation (SWR) middleware for FastAPI.

    Attributes:
        app: The FastAPI application instance.
        ttl: The Time To Live (TTL) for cached responses in seconds.
        swr: The Stale While Revalidate time in seconds.
    Vars:
        store: A dictionary to store cached responses.
        inflight: A dictionary to store in-flight tasks for cache refreshing.
    """

    def __init__(self, app, ttl: int = 30, swr: int = 300):
        super().__init__(app)
        self.ttl, self.swr = ttl, swr
        self.store = {}  # key -> (ts, headers, body)
        self.inflight = {}  # key -> asyncio.Task

    def _key(self, request):
        """
        Generate a unique key for the request.

        :param request: The incoming FastAPI Request object.
        :return: The unique key for the request.
        """
        return f"{request.url.path}?{request.url.query}"

    async def dispatch(self, request, call_next):
        """
        Dispatches the incoming request and handles SWR caching.

        :param request: The incoming FastAPI Request object.
        :param call_next: The next middleware or endpoint to call.
        :return: The outgoing response object.
        """
        if request.method != "GET":  # only cache GET
            return await call_next(request)

        key = self._key(request)
        entry = self.store.get(key)
        now = time.time()

        async def refresh():
            """
            Refresh the cached response.
            """
            resp = await call_next(request)
            body = await resp.body()
            self.store[key] = (now, dict(resp.headers), body)

        # Fresh
        if entry and now - entry[0] < self.ttl:
            headers, body = entry[1], entry[2]
            return Response(
                content=body,
                headers={**headers, "Cache-Control": f"max-age={self.ttl}, stale-while-revalidate={self.swr}"},
            )

        # Stale but serveable; kick off refresh if not already
        if entry and now - entry[0] < self.ttl + self.swr:
            if key not in self.inflight or self.inflight[key].done():
                self.inflight[key] = asyncio.create_task(refresh())
            headers, body = entry[1], entry[2]
            return Response(
                content=body,
                headers={
                    **headers,
                    "Warning": '110 - "stale"',
                    "Cache-Control": f"max-age={self.ttl}, stale-while-revalidate={self.swr}",
                },
            )

        # Miss: fetch and store synchronously
        resp = await call_next(request)
        body = await resp.body()
        self.store[key] = (now, dict(resp.headers), body)
        return Response(content=body, status_code=resp.status_code, headers=resp.headers)
