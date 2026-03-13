"""
Setup module for FastAPI application

There are several components that need to be set up:
- Application configuration
- Database session management
- Error handlers
- Logging configuration
- Security configuration
- Tracing configuration
- CORS configuration
- Rate limiting configuration
"""
from pathlib import Path

import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from guard import SecurityConfig, SecurityMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles
from starlette_compress import CompressMiddleware, remove_compress_type

from src.backend.app.handlers.exception_handlers import add_exceptions_handlers
from src.backend.app.lifespan import app_lifespan
from src.backend.config.main import settings
from src.backend.core.logger.app_logger import AppLogger
from src.backend.core.logger.logger_factory import logger_bind
from src.backend.core.opentelemetry.tracing import init_tracing
from src.backend.core.routes_loader import auto_register_routes
from src.backend.database.sqlalchemy.utils import sessionmanager
from src.backend.middleware.etag_middleware import ETagMiddleware
from src.backend.middleware.exception_middleware import ExceptionHandlerMiddleware
from src.backend.middleware.logger_middleware import LoggingMiddleware
from src.backend.middleware.maintenance_mode_middleware import MaintenanceModeMiddleware
from src.backend.middleware.monitor_performance import PerformanceMonitorMiddleware
from src.backend.middleware.rate_limit_middleware import default_limiter
from src.backend.middleware.request_id_middleware import RequestIDMiddleware

load_dotenv()


def create_base_app(title: str, tags: list[dict]) -> FastAPI:
    """
    Creates a base FastAPI application with common middleware.

    :param title: The title of the application.
    :param tags: The list of tags for the application.
    :return: The FastAPI application.
    """
    return FastAPI(
        title=title,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=app_lifespan,
        default_response_class=JSONResponse,
        openapi_tags=tags,
    )


def setup_tracing(app: FastAPI) -> None:
    """
    Initializes OpenTelemetry tracing for the given FastAPI application.

    :param app: The FastAPI application.
    :return: None
    """
    if sessionmanager.engine is not None:
        init_tracing(app, sessionmanager.engine)


def setup_metrics(app: FastAPI) -> None:
    """
    Exposes metrics for the given FastAPI application.

    :param app: The FastAPI application.
    :return: None
    """
    if settings.app.TESTING_MODE:
        return
    Instrumentator().instrument(app).expose(app, include_in_schema=False)


def setup_sentry() -> None:
    """
    Initializes Sentry for error tracking.

    :return: None
    """
    if settings.app.TESTING_MODE:
        return
    sentry_sdk.init(
        dsn="https://your-sentry-dsn@sentry.io/project-id",
        traces_sample_rate=1.0,
        environment="production",
    )


def setup_main_middlewares(app: FastAPI, logger: AppLogger) -> None:
    """
    Sets up main middleware for the FastAPI application.

    :param app: The FastAPI application.
    :param logger: The logger instance to use for logging.
    :return:
    """
    if settings.app.TESTING_MODE:
        return

    config = SecurityConfig(
        whitelist=[
            "127.0.0.1",
            "192.168.0.0/16",
            "10.0.0.0/8",
            "172.16.0.0/12",
        ],
        blacklist=["10.0.0.1", "2001:db8::2"],
        # geo_ip_handler=CFHeaderGeoIPHandler,
        # blocked_countries=["AR", "IT"],  # Block specific countries using ISO 3166-1 alpha-2 codes
        # whitelist_countries=["US", "CA"],  # Optional: Only allow specific countries
        trusted_proxies=[
            "172.20.0.0/16",  # docker / nginx‑proxy
            "192.168.1.0/24",
        ],  # List of trusted proxy IPs or CIDR ranges
        trusted_proxy_depth=1,  # How many proxies to expect in chain
        trust_x_forwarded_proto=True,  # Whether to trust X-Forwarded-Proto for HTTPS detection (default: True)
        # blocked_user_agents=["curl", "wget"],
        auto_ban_threshold=5,  # Ban IP after 5 suspicious requests
        auto_ban_duration=86400,  # Ban duration in seconds (1 day)
        enable_penetration_detection=True,  # True by default
        passive_mode=True,  # False by default, enable to log suspicious activity without blocking requests.
        custom_log_file=None,  # Custom log file path, None for console output only
        # enforce_https=True,
        enable_cors=True,
        cors_allow_origins=settings.app.CORS_ORIGINS,
        cors_allow_methods=settings.app.CORS_METHODS,
        cors_allow_headers=settings.app.CORS_HEADERS,
        cors_allow_credentials=settings.app.CORS_CREDENTIALS,
        # cors_expose_headers=["X-Custom-Header"],
        cors_max_age=600,
        # block_cloud_providers={"AWS", "GCP", "Azure"},
        security_headers={
            "enabled": True,
            "hsts": {"max_age": 31536000, "include_subdomains": True, "preload": False},  # 1 year
            # "csp": {
            #     "default-src": ["'self'"],
            #     "script-src": ["'self'", "https://trusted.cdn.com"],
            #     "style-src": ["'self'", "'unsafe-inline'"],
            #     "img-src": ["'self'", "data:", "https:"],
            #     "connect-src": ["'self'", "https://api.example.com"],
            #     "frame-ancestors": ["'none'"],
            #     "base-uri": ["'self'"],
            #     "form-action": ["'self'"]
            # },
            "frame_options": "DENY",
            "content_type_options": "nosniff",
            "xss_protection": "1; mode=block",
            "referrer_policy": "strict-origin-when-cross-origin",
            "permissions_policy": "geolocation=(), microphone=(), camera=()",
            # "custom": {
            #     "X-Custom-Header": "CustomValue"
            # }
        },
    )

    app.add_middleware(SecurityMiddleware, config=config)  # type: ignore[arg-type]
    app.add_middleware(
        TrustedHostMiddleware,      # type: ignore[arg-type]
        allowed_hosts=settings.app.TRUSTED_HOSTS,
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        SessionMiddleware,      # type: ignore[arg-type]
        secret_key=settings.app.SESSION_SECRET_KEY,
        session_cookie="session",
        same_site="lax",
        path="/",
        max_age=settings.app.SESSION_MAX_AGE,
    )


def setup_admin_middlewares(app: FastAPI, logger: AppLogger) -> None:
    """
    Sets up admin middlewares for the FastAPI application.

    :param app: The FastAPI application.
    :param logger: The logger instance to use for logging.
    :return: None
    """
    if settings.app.TESTING_MODE:
        return
    app.add_middleware(ExceptionHandlerMiddleware, logger=logger)
    app.add_middleware(LoggingMiddleware, logger=logger)
    app.state.logger = logger
    app.add_middleware(PerformanceMonitorMiddleware)


def setup_public_middlewares(app: FastAPI, logger: AppLogger) -> None:
    """
    Sets up public middlewares for the FastAPI application.

    :param app: The FastAPI application.
    :param logger: The logger instance to use for logging.
    :return: None
    """
    if settings.app.TESTING_MODE:
        return
    app.add_middleware(MaintenanceModeMiddleware)
    app.add_middleware(ExceptionHandlerMiddleware, logger=logger)
    app.add_middleware(LoggingMiddleware, logger=logger)
    app.state.logger = logger
    app.add_middleware(SlowAPIMiddleware)
    app.state.limiter = default_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)      # type: ignore[arg-type]
    app.add_middleware(PerformanceMonitorMiddleware)
    app.add_middleware(
        ETagMiddleware,
        cache_paths=[
            "/api/v1/users",
        ],
        skip_paths=[
            "/api/v1/messages",
            "/api/v1/notifications",
        ],
        cache_headers=["X-Cache-OK"],
    )
    app.add_middleware(
        CompressMiddleware,      # type: ignore[arg-type]
        minimum_size=2048,
        zstd_level=3,
        brotli_quality=3,
        gzip_level=5,
    )
    remove_compress_type("image/")
    remove_compress_type("application/pdf")


def setup_admin_html_routes(admin_app: FastAPI, logger: AppLogger) -> None:
    """
    Sets up admin routes for the FastAPI application.

    :param admin_app: The FastAPI application for admin routes.
    :param logger: The logger instance to use for logging.
    :return: None
    """
    auto_register_routes(
        admin_app,
        plugin_path="src/backend/app/routers/admin",
        prefix="/admin",
        logger=logger,
    )


def setup_admin_api_routes(admin_app: FastAPI, logger: AppLogger) -> None:
    """
    Sets up admin routes for the FastAPI application.

    :param admin_app: The FastAPI application for admin routes.
    :param logger: The logger instance to use for logging.
    :return: None
    """
    auto_register_routes(
        admin_app,
        plugin_path="src/backend/app/api/admin/v1",
        prefix="/api/v1",
        logger=logger,
    )
    auto_register_routes(
        admin_app,
        plugin_path="src/backend/app/api/admin/v2",
        prefix="/api/v2",
        logger=logger,
    )


def setup_public_api_routes(public_app: FastAPI, logger: AppLogger) -> None:
    """
    Sets up public routes for the FastAPI application.

    :param public_app: The FastAPI application for public routes.
    :param logger: The logger instance to use for logging.
    :return:
    """
    auto_register_routes(
        public_app,
        plugin_path="src/backend/app/api/public/v1",
        prefix="/api/v1",
        logger=logger,
    )
    auto_register_routes(
        public_app,
        plugin_path="src/backend/app/api/public/v2",
        prefix="/api/v2",
        logger=logger,
    )

    auto_register_routes(
        public_app,
        plugin_path="src/backend/app/plugins/v1",
        prefix="/api/v1",
        logger=logger,
    )
    auto_register_routes(
        public_app,
        plugin_path="src/backend/app/plugins/v2",
        prefix="/api/v2",
        logger=logger,
    )


def setup_public_html_routes(public_app: FastAPI, logger: AppLogger) -> None:
    """
    Sets up public routes for the FastAPI application.

    :param public_app: The FastAPI application for public routes.
    :param logger: The logger instance to use for logging.
    :return:
    """
    auto_register_routes(
        public_app,
        plugin_path="src/backend/app/routers/public",
        prefix="",
        logger=logger,
    )


def setup_exception_handlers(*apps: FastAPI) -> None:
    """
    Sets up exception handlers for the given FastAPI applications.

    :param apps: The FastAPI applications for which exception handlers will be set up.
    :return: None
    """
    for app in apps:
        add_exceptions_handlers(app)


def create_app() -> FastAPI:
    """
    Creates the FastAPI application.

    :return: The FastAPI application.
    """
    BASE_DIR = Path(__file__).parent.parent
    _main_logger = logger_bind(settings.app.APP_NAME)
    _admin_logger = logger_bind("AdminBackendServiceAPI")
    _public_logger = logger_bind("PublicBackendServiceAPI")

    admin_app = create_base_app(
        title="AdminBackendServiceAPI",
        tags=[
            {"name": "unused", "description": "Endpoints that are temporarily unused"},
            {"name": "authorization", "description": "Access to endpoints requiring authorization"},
            {"name": "message", "description": "Message-specific endpoints"},
            {"name": "user", "description": "User-specific endpoints"},
        ],
    )

    public_app = create_base_app(
        title="PublicBackendServiceAPI",
        tags=[
            {"name": "unused", "description": "Endpoints that are temporarily unused"},
            {"name": "authorization", "description": "Access to endpoints requiring authorization"},
        ],
    )

    main_app = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=app_lifespan,
        default_response_class=JSONResponse,
    )

    main_app.mount('/static', StaticFiles(directory=str(BASE_DIR / "app/static")), name='static')

    main_app.mount("/admin", admin_app)
    main_app.mount("/", public_app)
    # Websocket
    # Initialize websocket here because it's required due to cascade lifespan issues
    # socket_manager = RedisConnectionManager(redis_url=settings.redis.get_redis_url())
    # socket_manager = NATSConnectionManager(nats_url=settings.nats.get_nats_url())
    # socket_manager.mount_to_app(public_app, path="/ws")

    setup_public_html_routes(public_app, logger=_public_logger)
    setup_admin_html_routes(admin_app, logger=_admin_logger)

    # setup_metrics(public_app)
    # setup_metrics(admin_app)

    # setup_tracing(public_app)
    # setup_tracing(admin_app)

    setup_main_middlewares(main_app, logger=_main_logger)
    setup_admin_middlewares(admin_app, logger=_admin_logger)
    setup_public_middlewares(public_app, logger=_public_logger)

    setup_admin_api_routes(admin_app, logger=_admin_logger)
    setup_public_api_routes(public_app, logger=_public_logger)

    setup_exception_handlers(main_app, admin_app, public_app)

    return main_app
