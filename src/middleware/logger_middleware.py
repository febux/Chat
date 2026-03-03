"""
Logger middleware for handling request and response logs.
"""

import time
import uuid
from typing import Callable, Dict, Iterable, Optional, Union

import orjson
from starlette.background import BackgroundTask
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from src.core.logger import AppLogger
from src.schemas.logger.request_api_log import RequestApiLog
from src.schemas.logger.response_api_log import ResponseApiLog

# Configuration constants
MAX_BODY_SIZE = 1024 * 1024  # 1MB limit for bodies
MAX_LOG_BODY_SIZE = 10 * 1024  # 10KB limit for logged content
CHUNK_SIZE = 8192
UUID_HEADER = "x-api-key"
CONTENT_TYPE_JSON = "application/json"


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logging middleware for handling request and response logs.

    Attributes:
        app: FastAPI application.
        logger: Logger instance for logging.
    """

    def __init__(self, app: ASGIApp, logger: AppLogger) -> None:
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Dispatches the incoming request and handles logging.

        :param request: The incoming FastAPI Request object.
        :param call_next: The next middleware or endpoint to call.
        :return: The outgoing response object.
        """
        start_time = time.perf_counter()

        # Optimized request body handling
        req_body = await self._get_request_body_safe(request)

        # Process request
        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        # Handle streaming responses efficiently
        res_body = await self._get_response_body_safe(response)

        # Use background task for logging
        # Log only if not a metrics request
        if not request.url.path.startswith("/metrics"):
            response.background = BackgroundTask(
                self._write_log_background, request, response.status_code, req_body, res_body, process_time
            )

        return response

    async def _write_log_async(
        self,
        request: Request,
        status_code: int,
        req_body: Optional[Union[Dict, str]],
        res_body: Optional[Union[Dict, str]],
        process_time: float,
    ) -> None:
        """
        Asynchronous log writing with optimized data structures.

        :param request: The incoming FastAPI Request object.
        :param status_code: The status code of the response.
        :param req_body: The request body as a dictionary or string.
        :param res_body: The response body as a dictionary or string.
        :param process_time: The processing time of the request in seconds.
        """
        try:
            # Optimized UUID parsing
            api_key = self._parse_api_key_optimized(request.headers.get(UUID_HEADER))

            # Build request log with minimal allocations
            request_log = RequestApiLog(
                api_key=api_key,
                ip_address=request.client.host if request.client else None,
                path=request.url.path,
                method=request.method,
                request_body=req_body,
                query_params=dict(request.query_params) if request.query_params else {},
                path_params=request.path_params if request.path_params else {},
                headers=self._filter_sensitive_headers(dict(request.headers)),
                process_time=process_time,
            )

            response_log = ResponseApiLog(
                status_code=status_code,
                response_body=res_body,
                process_time=process_time,
            )

            # Log with structured data
            self.logger.info(
                f"{request.method} {request.url.path} {status_code}",
                request=request_log.model_dump(exclude_none=True),
                response=response_log.model_dump(exclude_none=True),
            )

        except Exception as e:
            self.logger.exception(f"Error in async log writing: {str(e)}")

    def _parse_api_key_optimized(self, api_key_str: Optional[str]) -> Optional[uuid.UUID]:
        """
        Optimized API key parsing with caching and validation.

        :param api_key_str: The API key string to parse.
        :return: The parsed API key as UUID, or None if the format is invalid.
        """
        if not api_key_str:
            return None

        try:
            # Quick format validation before UUID creation
            if len(api_key_str) != 36 or api_key_str.count("-") != 4:
                return None
            return uuid.UUID(api_key_str)
        except (ValueError, TypeError):
            return None

    def _filter_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Filter out sensitive headers for security.

        :param headers: The headers to filter.
        :return: The filtered headers.
        """
        sensitive_headers = {"authorization", "cookie", "x-api-key", "x-auth-token", "x-csrf-token"}

        return {k: "<redacted>" if k.lower() in sensitive_headers else v for k, v in headers.items()}

    async def _get_request_body_safe(self, request: Request) -> Optional[Union[Dict, str]]:
        """
        Safe request body extraction with limits.

        :param request: The incoming FastAPI Request object.
        :return: The request body as a dictionary or string, or None if the size exceeds the limit.
        """
        try:
            content_length = int(request.headers.get("content-length", 0))
            if content_length > MAX_BODY_SIZE:
                return f"<body too large: {content_length} bytes>"

            # Use request.json() for JSON content
            content_type = request.headers.get("content-type", "").lower()
            if content_type.startswith("application/json"):
                return await request.json()
            else:
                body_bytes = await request.body()
                return body_bytes.decode("utf-8") if body_bytes else None

        except Exception:
            return None

    async def _get_response_body_safe(self, response: Response) -> Optional[Union[Dict, str]]:
        """
        Safe response body extraction with streaming support.

        :param response: The incoming FastAPI Response object.
        :return: The response body as a dictionary or string, or None if the size exceeds the limit.
        """
        if not hasattr(response, "body_iterator"):
            return None

        try:
            # Collect response chunks efficiently
            body_chunks = []
            total_size = 0

            async for chunk in response.body_iterator:
                if total_size + len(chunk) > MAX_BODY_SIZE:
                    body_chunks.append(f"<response truncated at {MAX_BODY_SIZE} bytes>".encode())
                    break
                body_chunks.append(chunk)
                total_size += len(chunk)

            # Reconstruct body iterator for client
            response.body_iterator = self._async_iter_chunks(body_chunks)

            # Parse collected body
            if body_chunks:
                full_body = b"".join(body_chunks)
                try:
                    text = full_body.decode("utf-8")
                    if text.strip().startswith(("{", "[")):
                        return orjson.loads(text)
                    return text
                except (UnicodeDecodeError, orjson.JSONDecodeError):
                    return f"<binary/invalid content: {len(full_body)} bytes>"

            return None

        except Exception as e:
            self.logger.exception(f"Error extracting response body: {str(e)}")
            return None

    async def _async_iter_chunks(self, chunks: Iterable):
        """
        Async iterator for response chunks.

        :param chunks: The chunks to iterate over.
        """
        for chunk in chunks:
            yield chunk

    async def _write_log_background(self, *args, **kwargs):
        """
        Background task wrapper for logging.

        :param args: Positional arguments to pass to the log writing function.
        :param kwargs: Keyword arguments to pass to the log writing function.
        :return: None
        """
        try:
            await self._write_log_async(*args, **kwargs)
        except Exception as e:
            self.logger.exception(f"Background logging error: {str(e)}")
