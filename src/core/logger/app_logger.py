"""
Logger custom class to customize loguru's behavior
"""

import sys
from multiprocessing import current_process
from os.path import basename, splitext
from threading import current_thread

from _contextvars import ContextVar
from loguru._colorizer import Colorizer
from loguru._datetime import aware_now
from loguru._get_frame import get_frame
from loguru._logger import Logger
from loguru._recattrs import RecordException, RecordFile, RecordLevel, RecordProcess, RecordThread

_tuple: tuple = tuple()
context: ContextVar = ContextVar("loguru_context", default={})
start_time = aware_now()


class LoggerPayloadMixin:
    """
    A mixin class that provides payload handling functionality for logging.
    """

    @staticmethod
    def _get_payload(args):
        """
        Extracts the payload from the given arguments.

        This method determines the appropriate payload based on the number of arguments:
        - If no arguments are provided, it returns None.
        - If a single argument is provided, it returns that argument.
        - If multiple arguments are provided, it returns them as a tuple.

        :param args: A tuple of arguments passed to the logging method.
        :return: The extracted payload (None, a single object, or a tuple of objects).
        """
        if not args:
            return None
        if len(args) == 1:
            return args[0]
        return args


class AppLogger(Logger, LoggerPayloadMixin):
    """
    Customized Logger class for the application.
    """

    def debug(__self, __message, *args, **kwargs):  # noqa: N805
        r"""Log ``message.format(*args, **kwargs)`` with severity ``'DEBUG'``."""
        __self._log("DEBUG", False, __self._options, __message, _tuple, kwargs, payload=__self._get_payload(args))

    def trace(__self, __message, *args, **kwargs):  # noqa: N805
        r"""Log ``message.format(*args, **kwargs)`` with severity ``'TRACE'``."""
        __self._log("TRACE", False, __self._options, __message, _tuple, kwargs, payload=__self._get_payload(args))

    def info(__self, __message, *args, **kwargs):  # noqa: N805
        r"""Log ``message.format(*args, **kwargs)`` with severity ``'INFO'``."""
        __self._log("INFO", False, __self._options, __message, _tuple, kwargs, payload=__self._get_payload(args))

    def success(__self, __message, *args, **kwargs):  # noqa: N805
        r"""Log ``message.format(*args, **kwargs)`` with severity ``'SUCCESS'``."""
        __self._log("SUCCESS", False, __self._options, __message, _tuple, kwargs, payload=__self._get_payload(args))

    def warning(__self, __message, *args, **kwargs):  # noqa: N805
        r"""Log ``message.format(*args, **kwargs)`` with severity ``'WARNING'``."""
        __self._log("WARNING", False, __self._options, __message, _tuple, kwargs, payload=__self._get_payload(args))

    def error(__self, __message, *args, **kwargs):  # noqa: N805
        r"""Log ``message.format(*args, **kwargs)`` with severity ``'ERROR'``."""
        __self._log("ERROR", False, __self._options, __message, _tuple, kwargs, payload=__self._get_payload(args))

    def critical(__self, __message, *args, **kwargs):  # noqa: N805
        r"""Log ``message.format(*args, **kwargs)`` with severity ``'CRITICAL'``."""
        __self._log("CRITICAL", False, __self._options, __message, _tuple, kwargs, payload=__self._get_payload(args))

    def log(__self, __level, __message, *args, **kwargs):  # noqa: N805
        r"""Log ``message.format(*args, **kwargs)`` with severity ``level``."""
        __self._log(__level, False, __self._options, __message, _tuple, kwargs, payload=__self._get_payload(args))

    def _log(self, level, from_decorator, options, message, args, kwargs, payload=None):
        """
        Internal method to handle logging of messages with various severity levels and options.

        This method processes the log message, applies formatting, handles exceptions,
        and emits the log record to all registered handlers.

        Example: logger.info("Redis client connection initialized", url=config.REDIS_URL.__str__())
        Output: {"level": "INFO", "message": "Redis client connection initialized",
                "label": "main", "module": "main", "pid": 10, "pname": "SpawnProcess-3",
                "timestamp": "2025-06-10T07:24:42", "url": "redis://user:qwerty@192.168.0.126:16379/0",
                "app_name": "base_app"}

        :param level: The severity level of the log message (e.g., "DEBUG", "INFO", "ERROR").
        :type level: str or int
        :param from_decorator: Indicates if the log call originated from a decorator.
        :type from_decorator: bool
        :param options: A tuple containing various logging options and configurations.
        :type options: tuple
        :param message: The log message to be recorded.
        :type message: str
        :param args: Positional arguments for message formatting.
        :type args: tuple
        :param kwargs: Keyword arguments for message formatting and additional context.
        :type kwargs: dict
        :param payload: Optional payload to be included in the log record.
        :type payload: Any

        :return: None
        """
        core = self._core

        if not core.handlers:
            return

        try:
            level_id, level_name, level_no, level_icon = core.levels_lookup[level]
        except (KeyError, TypeError):
            if isinstance(level, str):
                raise ValueError("Level '%s' does not exist" % level) from None
            if not isinstance(level, int):
                raise TypeError(
                    "Invalid level, it should be an integer or a string, not: '%s'" % type(level).__name__
                ) from None
            if level < 0:
                raise ValueError("Invalid level value, it should be a positive integer, not: %d" % level) from None
            cache = (None, "Level %d" % level, level, " ")
            level_id, level_name, level_no, level_icon = cache
            core.levels_lookup[level] = cache

        if level_no < core.min_level:
            return

        exception, depth, record, lazy, colors, raw, capture, patchers, extra = options

        try:
            frame = get_frame(depth + 2)
        except ValueError:
            f_globals = {}
            f_lineno = 0
            co_name = "<unknown>"
            co_filename = "<unknown>"
        else:
            f_globals = frame.f_globals
            f_lineno = frame.f_lineno
            co_name = frame.f_code.co_name
            co_filename = frame.f_code.co_filename

        try:
            name = f_globals["__name__"]
        except KeyError:
            name = None

        try:
            if not core.enabled[name]:
                return
        except KeyError:
            enabled = core.enabled
            if name is None:
                status = core.activation_none
                enabled[name] = status
                if not status:
                    return
            else:
                dotted_name = name + "."
                for dotted_module_name, status in core.activation_list:
                    if dotted_name[: len(dotted_module_name)] == dotted_module_name:
                        if status:
                            break
                        enabled[name] = False
                        return
                enabled[name] = True

        current_datetime = aware_now()

        file_name = basename(co_filename)
        thread = current_thread()
        process = current_process()
        elapsed = current_datetime - start_time

        if exception:
            if isinstance(exception, BaseException):
                type_, value, traceback = (type(exception), exception, exception.__traceback__)
            elif isinstance(exception, tuple):
                type_, value, traceback = exception
            else:
                type_, value, traceback = sys.exc_info()
            exception = RecordException(type_, value, traceback)
        else:
            exception = None

        log_record = {
            "elapsed": elapsed,
            "exception": exception,
            "extra": {**core.extra, **context.get(), **extra},
            "file": RecordFile(file_name, co_filename),
            "function": co_name,
            "level": RecordLevel(level_name, level_no, level_icon),
            "line": f_lineno,
            "message": str(message),
            "module": splitext(file_name)[0],
            "name": name,
            "process": RecordProcess(process.ident, process.name),
            "thread": RecordThread(thread.ident, thread.name),
            "time": current_datetime,
        }

        if lazy:
            args = [arg() for arg in args]
            kwargs = {key: value() for key, value in kwargs.items()}

        if capture and kwargs:
            log_record["extra"].update(kwargs)

        if capture and payload:
            log_record["extra"].update(dict(payload=payload))

        if record:
            if "record" in kwargs:
                raise TypeError(
                    "The message can't be formatted: 'record' shall not be used as a keyword "
                    "argument while logger has been configured with '.opt(record=True)'"
                )
            kwargs.update(record=log_record)

        if colors:
            if args or kwargs:
                colored_message = Colorizer.prepare_message(message, args, kwargs)
            else:
                colored_message = Colorizer.prepare_simple_message(str(message))
            log_record["message"] = colored_message.stripped
        elif args or kwargs:
            colored_message = None
            log_record["message"] = message.format(*args, **kwargs)
        else:
            colored_message = None

        if core.patcher:
            core.patcher(log_record)

        for patcher in patchers:
            patcher(log_record)

        for handler in core.handlers.values():
            handler.emit(log_record, level_id, from_decorator, raw, colored_message)
