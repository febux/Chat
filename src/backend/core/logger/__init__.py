import atexit as _atexit
import sys as _sys

from loguru import _defaults
from loguru._logger import Core

from src.backend.core.logger.app_logger import AppLogger

logger = AppLogger(
    core=Core(),
    exception=None,
    depth=0,
    record=False,
    lazy=False,
    colors=False,
    raw=False,
    capture=True,
    patchers=[],
    extra={},
)

if _defaults.LOGURU_AUTOINIT and _sys.stderr:
    logger.add(_sys.stderr)

_atexit.register(logger.remove)
