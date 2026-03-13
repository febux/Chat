"""
Monitoring the application performance is crucial for optimizing the performance and resource usage of your FastAPI application.
"""

import os
import time

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.backend.core.logger.logger_factory import logger_bind

logger = logger_bind("PerformanceMonitorMiddleware")

REQUEST_COUNT = Counter(
    "requests_total",
    "Total HTTP Requests",
    ["endpoint", "method", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    ["endpoint", "method", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
RESPONSE_SIZE = Histogram(
    "response_size_bytes",
    "Response size in bytes",
    ["endpoint", "method", "status_code"],
)
IN_FLIGHT_REQUESTS = Gauge(
    "in_flight_requests",
    "Number of requests being processed currently",
)
REQUEST_EXCEPTIONS_COUNT = Counter(
    "request_exceptions_total",
    "Total request exceptions encountered",
    ["endpoint", "method"],
)


class PerformanceMonitorMiddleware(BaseHTTPMiddleware):
    """
    Performance monitoring middleware for tracking request performance.
    """

    async def dispatch(self, request: Request, call_next):
        """
        This middleware tracks request performance and helps identify bottlenecks.
        Use this to monitor your production deployment.

        :param request: The incoming FastAPI Request object.
        :param call_next: The next middleware or endpoint to call.
        :return: A Starlette Response object representing the response to the client.
        """
        endpoint = request.url.path
        method = request.method

        IN_FLIGHT_REQUESTS.inc()
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as e:
            REQUEST_EXCEPTIONS_COUNT.labels(endpoint=endpoint, method=method).inc()
            IN_FLIGHT_REQUESTS.dec()
            raise e

        process_time = time.perf_counter() - start_time
        status_code = str(response.status_code)
        response_size = len(response.body) if hasattr(response, "body") and response.body else 0

        REQUEST_COUNT.labels(endpoint=endpoint, method=method, status_code=status_code).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint, method=method, status_code=status_code).observe(process_time)
        RESPONSE_SIZE.labels(endpoint=endpoint, method=method, status_code=status_code).observe(response_size)
        IN_FLIGHT_REQUESTS.dec()

        response.headers["X-Process-Time"] = f"{process_time:.2f}s"
        response.headers["X-Worker-PID"] = str(os.getpid())

        if process_time > 2.0:
            logger.debug(f"Slow request detected: {endpoint} [{method}] took {process_time:.2f}s")

        return response
