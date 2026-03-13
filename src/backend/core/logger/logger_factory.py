"""Logger instance reconfiguration.

Contains a function to bind application name to logger instance based on the environment settings.
"""

import logging
import re
import sys

from src.backend.app.context import cid, tenant
from src.backend.config.main import settings

# noinspection PyUnresolvedReferences
from src.backend.core.logger import logger
from src.backend.core.logger.app_logger import AppLogger

# Scrub
secret = re.compile(r"(Bearer\s+[A-Za-z0-9-_]{20,})")


def patch_cid_secret(record) -> None:
    """Patches the log record with cid and tenant information.

    :param record: The log record to be patched.
    :return:
    """
    record["extra"]["cid"] = cid.get()
    record["extra"]["tenant"] = tenant.get()
    record["message"] = secret.sub("Bearer <redacted>", record["message"])


class InterceptHandler(logging.Handler):
    """Intercepts log records and sends them to the logger."""

    def emit(self, record) -> None:
        """Emits the record.

        :param record: The log record to be emitted.
        """
        # Get corresponding Loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller to get correct stack depth
        frame, depth = logging.currentframe(), 2
        while frame.f_back and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def setup_logger() -> None:
    """Sets up the logger for the application.
    Logs to stdout and a files. Patches cid and tenant information.

    :return:
    """
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.INFO)

    for lib in (
        "sqlalchemy.engine",
        "uvicorn",
        "gunicorn",
        "gunicorn.access",
        "gunicorn.error",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "faststream",
        "asyncio",
        "starlette",
    ):
        lg = logging.getLogger(lib)
        lg.handlers.clear()
        lg.propagate = True

    global logger  # Set logger usage across all modules
    logger.remove()
    logger = logger.patch(patch_cid_secret)

    logger.add(
        sys.stdout,
        level=settings.app.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <blue>{message}</blue> | {extra}",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # logger.add(
    #     "logs/application.log",
    #     format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function} | {message}",
    #     serialize=True,
    #     rotation="10 MB",
    #     retention="10 days",
    #     compression="zip",
    #     enqueue=True,
    #     backtrace=True,
    #     diagnose=True,
    # )
    #
    # logger.add(
    #     "logs/db.log",
    #     format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function} | {message}",
    #     rotation="50 MB",
    #     retention="7 days",
    #     compression="zip",
    #     enqueue=True,
    #     filter=lambda r: r["name"].startswith("sqlalchemy.engine"),
    # )


def logger_bind(context_name: str, **kwargs) -> AppLogger:
    """Binding the application name to the logger.

    :param context_name: The name of the context.
    :return: A configured Logger instance.
    """
    context_logger = logger.bind(context=context_name, **kwargs)
    return context_logger
